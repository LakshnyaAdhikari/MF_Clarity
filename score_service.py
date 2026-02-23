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

# --- CONFIGURATION ---
MIN_AUM_CR = 1000  # Minimum AUM in Crores — filters out small/junk funds

# Strict Category Whitelists
EQUITY_CATEGORIES = [
    'Large Cap', 'Mid Cap', 'Flexi Cap', 'Large & Mid Cap', 
    'Index Fund', 'ELSS', 'Small Cap', 'Multi Cap'
]
# Note: 'Sectoral'/'Thematic' can be allowed IF specifically requested, 
# but for general ranking we prefer the above. We will allow them but rank them carefully.

DEBT_CATEGORIES = [
    'Liquid', 'Corporate Bond', 'Gilt', 'Banking and PSU Fund', 
    'Overnight', 'Money Market', 'Ultra Short Duration', 'Low Duration'
]
# BANNED: 'Credit Risk', 'Floater', 'Medium Duration' (if high risk)

def load_latest_features(engine):
    # load latest features snapshot
    q = "SELECT * FROM fund_features WHERE as_of_date = (SELECT MAX(as_of_date) FROM fund_features)"
    df = pd.read_sql(q, engine, parse_dates=['as_of_date'])
    
    # load meta columns
    meta_q = "SELECT fund_id, fund_name, expense_ratio, aum_cr, top10_concentration, rating, category, turnover FROM funds"
    meta = pd.read_sql(meta_q, engine)

    # ensure fund_id is same type for join
    df['fund_id'] = df['fund_id'].astype(str)
    meta['fund_id'] = meta['fund_id'].astype(str)

    # Explicit list of columns to drop from 'features' df to avoid overlap with 'meta'
    # These columns exist in 'features' but we want the version from 'meta' (funds table)
    drop_cols = ['fund_name', 'expense_ratio', 'aum_cr', 'top10_concentration', 'rating', 'category', 'turnover']
    
    cols_to_drop = [c for c in drop_cols if c in df.columns]
    
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
    
    # Merge
    merged = df.merge(meta, on='fund_id', how='left')
    return merged

def percentile_rank(series, ascending=True):
    """
    Returns percentile (0-1). 
    ascending=True -> Higher value is better (e.g. Sharpe).
    ascending=False -> Lower value is better (e.g. Volatility).
    """
    if ascending:
        return series.rank(pct=True)
    else:
        return 1 - series.rank(pct=True)

def apply_constraints(df):
    """
    Apply HARD FILTERS. Funds failing these are excluded from scoring.
    """
    initial_count = len(df)
    
    if 'fund_name' not in df.columns:
        print(f"CRITICAL ERROR: 'fund_name' missing in apply_constraints. Columns: {df.columns.tolist()}")
        # Check first row
        if not df.empty:
            print(f"Sample Row: {df.iloc[0].to_dict()}")

    # 1. AUM Constraint (>= 1000 Cr)
    # Only apply if AUM data is actually populated in the DB.
    # If all values are NaN (data not yet ingested), skip to avoid wiping everything out.
    aum_populated = df['aum_cr'].notna().sum()
    if aum_populated > 0:
        df = df[df['aum_cr'].fillna(0) >= MIN_AUM_CR]
        print(f"AUM filter applied (>= {MIN_AUM_CR} Cr): {initial_count} -> {len(df)}")
    else:
        print(f"WARNING: AUM data missing in DB — skipping AUM filter. Populate 'aum_cr' in funds table to enable.")

    
    # 2. Category Constraint
    # We only score funds in known safe/standard categories for the core recommendation engine.
    # We allow 'Sectoral'/'Thematic' strictly for the Alpha slots, so we keep them but flag them.
    # For Debt, we strictly ENFORCE the whitelist.
    
    def is_valid_category(cat):
        if not cat: return False
        cat_lower = cat.lower()
        # Allow Equity
        if any(c.lower() in cat_lower for c in EQUITY_CATEGORIES): return True
        # Allow Safe Debt
        if any(c.lower() in cat_lower for c in DEBT_CATEGORIES): return True
        # Allow Gold/Commodity
        if 'gold' in cat_lower or 'commodity' in cat_lower: return True
        # Allow Thematic/Sectoral (will be filtered downstream if not needed)
        if 'sector' in cat_lower or 'thematic' in cat_lower: return True
        
        return False

    df = df[df['category'].apply(is_valid_category)]
    
    # 3. Exclude "Credit Risk" explicitly via Name/Category
    # (Just in case it slipped through)
    df = df[~df['fund_name'].str.contains('Credit Risk', case=False, na=False)]
    df = df[~df['category'].str.contains('Credit Risk', case=False, na=False)]
    
    # 4. Exclude Direct Plans (Business requirement: Regular only)
    # (Assuming we want to recommend Regular plans)
    df = df[~df['fund_name'].str.contains('Direct', case=False, na=False)]

    # 5. Exclude IDCW/Dividend Plans (Growth Only)
    df = df[~df['fund_name'].str.contains('IDCW|Dividend|Bonus', case=False, na=False)]

    print(f"Constraints applied: {initial_count} -> {len(df)} funds remaining.")
    return df

def compute_consistency_index(df):
    """
    Calculates the 'Consistency Score' (0-100) comprising:
    1. Reliability    — % positive months (30%)
    2. Downside       — Max drawdown protection (25%)
    3. Quality        — Risk-adjusted returns / Sharpe (25%)
    4. Momentum       — Recent performance 3m + 6m (20%)  <-- NEW
    5. Debt Safety Penalty (applied after)

    Momentum is scored WITHIN CATEGORY so a Large Cap isn't
    penalized for lower returns vs a Small Cap.
    """
    # Fill defaults for missing metrics to avoid crashes
    df['pct_pos_months_36'] = df['pct_pos_months_36'].fillna(0.5)
    df['max_drawdown']       = df['max_drawdown'].fillna(-0.5)
    df['sharpe']             = df['sharpe'].fillna(0)
    df['ann_vol']            = df['ann_vol'].fillna(0.20)
    df['ret_consistency']    = df['ret_consistency'].fillna(0)
    df['ret_3m']             = df['ret_3m'].fillna(0)
    df['ret_6m']             = df['ret_6m'].fillna(0)

    # --- COMPONENT SCORING (Normalized 0-1) ---

    # 1. Reliability (30%) - Higher positive months is better
    df['score_rel'] = percentile_rank(df['pct_pos_months_36'], ascending=True)

    # 2. Downside (25%) - Max drawdown is negative; closer to 0 is better
    df['score_dd'] = percentile_rank(df['max_drawdown'], ascending=True)

    # 3. Quality (25%) - Higher Sharpe is better
    df['score_qual'] = percentile_rank(df['sharpe'], ascending=True)

    # 4. Momentum (20%) — Category-aware: rank ret_3m and ret_6m WITHIN category
    #    so that a Large Cap fund is compared to other Large Cap funds only.
    #    Average of 3m and 6m percentile ranks within the fund's category.
    df['score_mom_3m'] = df.groupby('category')['ret_3m'].rank(pct=True)
    df['score_mom_6m'] = df.groupby('category')['ret_6m'].rank(pct=True)
    df['score_mom']    = (df['score_mom_3m'] + df['score_mom_6m']) / 2
    # Fill NaN for categories with only 1 fund (rank is undefined)
    df['score_mom'] = df['score_mom'].fillna(0.5)

    # --- COMPOSITE SCORE ---
    df['ConsistencyScore'] = (
        0.30 * df['score_rel']  +
        0.25 * df['score_dd']   +
        0.25 * df['score_qual'] +
        0.20 * df['score_mom']
    ) * 100

    # --- DEBT SAFETY PENALTY ---
    # For debt funds, volatility is the enemy.
    def apply_debt_penalty(row):
        cols = str(row['category']).lower()
        is_debt = any(c.lower() in cols for c in DEBT_CATEGORIES)
        if is_debt:
            if row['ann_vol'] > 0.05:
                return 25  # high volatility debt — massive penalty
            if row['ann_vol'] > 0.03:
                return 10  # moderate penalty
        return 0

    df['safety_penalty'] = df.apply(apply_debt_penalty, axis=1)
    df['ConsistencyScore'] = df['ConsistencyScore'] - df['safety_penalty']

    # Clip to 0-100
    df['ConsistencyScore'] = df['ConsistencyScore'].clip(0, 100)

    return df

def assign_tiers_and_explain(df):
    """
    Bucket funds into Tiers and generate Rationale string.
    """
    # Simply Rank by Score
    df = df.sort_values('ConsistencyScore', ascending=False)
    
    # Assign Tiers
    # Tier 1: Top 15%
    # Tier 2: Next 30%
    # Tier 3: Rest
    n = len(df)
    df['Tier'] = 'Tier 3'
    if n > 0:
        df.iloc[:int(n*0.15), df.columns.get_loc('Tier')] = 'Tier 1 (Elite)'
        df.iloc[int(n*0.15):int(n*0.45), df.columns.get_loc('Tier')] = 'Tier 2 (Strong)'
    
    # Generate Rationale
    def gen_rationale(row):
        reasons = []
        if row['Tier'] == 'Tier 1 (Elite)':
            reasons.append("Top 15% Consistency")
        
        # Highlight specific strengths
        if row['score_dd'] > 0.8:
            reasons.append("Superior Downside Protection")
        elif row['score_rel'] > 0.8:
            reasons.append("High Reliability (>80% Positive Months)")
        elif row['score_qual'] > 0.8:
            reasons.append("Top-Tier Risk-Adjusted Returns")
            
        return " | ".join(reasons) if reasons else "Selected for Balanced Performance"

    df['rationale'] = df.apply(gen_rationale, axis=1)
    return df

def compute_scores(df, user_profile):
    """
    Main Entry Point.
    User Profile is unused for SCORING (Constraint-Driven), 
    but we keep signature for compatibility.
    
    Returns dataframe with 'TotalScore' (which is ConsistencyScore).
    """
    # 1. Apply Constraints
    df = apply_constraints(df)
    
    # 2. Compute Index
    df = compute_consistency_index(df)
    
    # 3. Rank & Explain
    df = assign_tiers_and_explain(df)
    
    # Compatibility mapping
    df['TotalScore'] = df['ConsistencyScore'] / 100.0 # Normalize back to 0-1 for compatibility if needed, or keep 0-100?
    # Existing frontend expects score ~60-90. 
    # If I return 0.85, frontend displays "85". 
    # Current frontend code: ${(item.score * 100).toFixed(0)}
    # So if I return 0.85, it shows 85.
    # So ConsistencyScore (0-100) should be divided by 100.
    
    return df

def extract_recommendations(scored_df, topk=3):
    return scored_df.head(topk)

# --- COMPATIBILITY WRAPPERS ---

def recommend(user_profile, category_filter=None, topk=3, persist=False, df=None):
    if df is None:
        df = load_latest_features(engine)
    
    scored = compute_scores(df, user_profile)
    
    # Apply Category Filter if requested
    if category_filter:
        mask = scored['category'].str.contains(category_filter, case=False, na=False)
        scored = scored[mask]

    return scored.head(topk)

if __name__ == "__main__":
    # Test
    print("Testing Ranking Engine...")
    df = load_latest_features(engine)
    print(f"Loaded {len(df)} funds.")
    
    scored = compute_scores(df, {})
    print("\nTop 5 Funds:")
    cols = ['fund_name', 'category', 'aum_cr', 'ConsistencyScore', 'Tier', 'rationale']
    print(scored[cols].head(5).to_string())
