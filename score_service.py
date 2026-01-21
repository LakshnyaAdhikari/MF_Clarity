# score_service.py
import os
import json
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from datetime import date

DB_URL = os.getenv("DB_URL")
if not DB_URL:
    raise RuntimeError("DB_URL not set. Example: postgresql://mfuser:pass@localhost:5432/mfdb")

engine = create_engine(DB_URL)

WEIGHTS = {
    'RAR': 0.28, 'ST': 0.18, 'CS': 0.12, 'LIQ': 0.08,
    'CN': 0.08, 'FH': 0.06, 'TF': 0.10, 'PF': 0.05
}

def load_latest_features(engine):
    # load latest features snapshot
    q = "SELECT * FROM fund_features WHERE as_of_date = (SELECT MAX(as_of_date) FROM fund_features)"
    df = pd.read_sql(q, engine, parse_dates=['as_of_date'])

    # load meta columns we expect; if some do not exist in DB this will still run
    # (we will add any missing columns later)
    meta = pd.read_sql("SELECT fund_id, fund_name, expense_ratio, aum_cr, top10_concentration, rating, category, turnover FROM funds", engine)

    # ensure fund_id is same type for join
    df['fund_id'] = df['fund_id'].astype(str)
    meta['fund_id'] = meta['fund_id'].astype(str)

    merged = df.merge(meta, on='fund_id', how='left')

    # Debug print: columns present
    print("DEBUG: fund_features columns:", df.columns.tolist())
    print("DEBUG: funds(meta) columns:", meta.columns.tolist())
    print("DEBUG: merged columns:", merged.columns.tolist())

    return merged

def percentile_rank(series):
    return series.rank(method='average', pct=True)

def ensure_columns(df, cols_defaults):
    """Ensure dataframe has required columns; if not, create with default."""
    for c, default in cols_defaults.items():
        if c not in df.columns:
            print(f"INFO: column '{c}' missing — creating with default {default!r}")
            df[c] = default
    return df

def compute_scores(df, user_profile):
    # ensure required numeric columns exist (with safe defaults)
    defaults = {
        'sharpe': 0.0, 'ann_return': 0.0, 'ann_vol': 0.0, 'max_drawdown': 0.0,
        'expense_ratio': 0.0, 'aum_cr': 0.0, 'top10_concentration': 0.0,
        'pct_pos_months_36': 0.0, 'manager_tenure_years': 0.0, 'rating': 3.0,
        'turnover': 0.0, 'inflow_1y_pct': 0.0
    }
    df = ensure_columns(df, defaults)

    # build percentiles (fillna handled by ensure_columns)
    df['sharpe_pct'] = percentile_rank(df['sharpe'].fillna(0))
    df['ann_return_pct'] = percentile_rank(df['ann_return'].fillna(0))
    df['ann_vol_pct'] = 1 - percentile_rank(df['ann_vol'].fillna(0))
    df['max_drawdown_pct'] = 1 - percentile_rank(df['max_drawdown'].fillna(0))
    df['expense_ratio_pct'] = 1 - percentile_rank(df['expense_ratio'].fillna(0))
    df['aum_pct'] = percentile_rank(df['aum_cr'].fillna(0))
    df['top10_conc_pct'] = 1 - percentile_rank(df['top10_concentration'].fillna(0))
    df['pct_pos_36_pct'] = percentile_rank(df['pct_pos_months_36'].fillna(0))
    df['manager_tenure_pct'] = percentile_rank(df['manager_tenure_years'].fillna(0))
    df['rating_pct'] = percentile_rank(df['rating'].fillna(3))

    # component scores
    df['RAR'] = df['sharpe_pct']
    df['ST'] = 0.6 * df['pct_pos_36_pct'] + 0.4 * df['manager_tenure_pct']
    df['CS'] = df['expense_ratio_pct']
    df['LIQ'] = 0.7 * df['aum_pct'] + 0.3 * percentile_rank(df['turnover'].fillna(0))
    df['CN'] = df['top10_conc_pct']
    df['FH'] = df['rating_pct']

    # TF: goal match (rudimentary)
    def goal_tax_fit(cat, goal):
        goal = (goal or "").lower()
        cat = (cat or "").lower()
        if goal == 'tax saving' and 'elss' in cat:
            return 1.0
        if goal in ('retirement', 'wealth') and any(k in cat for k in ('hybrid', 'large', 'index', 'large cap')):
            return 0.9
        if goal == 'safety' and 'debt' in cat:
            return 1.0
        return 0.7

    df['TF'] = df['category'].apply(lambda c: goal_tax_fit(c, user_profile.get('goal', 'wealth')))
    df['PF'] = 0.5

    df['TotalScore'] = (
        WEIGHTS['RAR']*df['RAR'] +
        WEIGHTS['ST']*df['ST'] +
        WEIGHTS['CS']*df['CS'] +
        WEIGHTS['LIQ']*df['LIQ'] +
        WEIGHTS['CN']*df['CN'] +
        WEIGHTS['FH']*df['FH'] +
        WEIGHTS['TF']*df['TF'] +
        WEIGHTS['PF']*df['PF']
    )

    # penalties (apply safely)
    df.loc[df['max_drawdown'] < -0.35, 'TotalScore'] -= 0.12
    if 'inflow_1y_pct' in df.columns:
        df.loc[df['inflow_1y_pct'] < -2.0, 'TotalScore'] -= 0.15

    # sort and return
    return df.sort_values('TotalScore', ascending=False)

def persist_recommendations(engine, user_profile, scored_df, topk=3):
    """Write topk recommendations to recommendation_logs (audit)"""
    recs = scored_df.head(topk).to_dict(orient='records')
    with engine.begin() as conn:
        q = text("INSERT INTO recommendation_logs (user_profile, recommendations) VALUES (:u, :r)")
        conn.execute(q, {'u': json.dumps(user_profile), 'r': json.dumps(recs)})
    print(f"INFO: persisted {len(recs)} recommendations to recommendation_logs")

def recommend(user_profile, category_filter=None, topk=3, persist=False, df=None):
    if df is None:
        df = load_latest_features(engine)
    
    scored = compute_scores(df, user_profile)
    
    # FILTER: REGULAR PLANS ONLY (Business Logic)
    # Exclude 'Direct' to ensure distributor commissions
    scored = scored[~scored['fund_name'].str.contains('Direct', case=False, na=False)]
    # Explicitly prefer 'Regular'
    # scored = scored[scored['fund_name'].str.contains('Regular', case=False, na=False)]
    
    # Apply Category Filter
    if category_filter:
        # category_filter can be a string (e.g., 'Equity', 'Debt')
        # We perform a case-insensitive partial match on the 'category' column
        mask = scored['category'].str.contains(category_filter, case=False, na=False)
        scored = scored[mask]

    if persist:
        persist_recommendations(engine, user_profile, scored, topk=topk)
    return scored.head(topk)

if __name__ == "__main__":
    sample_user = {'amount':25000, 'horizon_years':5, 'risk_tolerance':'Moderate','goal':'Wealth'}
    top = recommend(sample_user, 3, persist=False)
    # show limited columns for readability
    cols_to_show = ['fund_id', 'as_of_date', 'TotalScore', 'sharpe', 'ann_return', 'ann_vol']
    print(top[cols_to_show].to_string(index=False))
