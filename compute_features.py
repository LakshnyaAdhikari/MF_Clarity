# compute_features.py
import os
import pandas as pd
import numpy as np
import math
from sqlalchemy import create_engine, text
from datetime import date

DB_URL = os.getenv("DB_URL")
if DB_URL is None:
    raise RuntimeError("DB_URL env var not set. Example: postgresql://mfuser:pass@localhost:5432/mfdb")

engine = create_engine(DB_URL, pool_pre_ping=True)

def fetch_all_funds(engine):
    return pd.read_sql("SELECT fund_id FROM funds", engine)

def fetch_navs_for_fund(engine, fund_id):
    sql = text("SELECT nav_date, nav FROM navs WHERE fund_id = :fid ORDER BY nav_date")
    df = pd.read_sql(sql, engine, params={'fid': fund_id}, parse_dates=['nav_date'])
    return df

def compute_metrics(nav_df):
    if nav_df is None or nav_df.empty:
        return None
    nav_df = nav_df.dropna(subset=['nav'])
    nav_df = nav_df.sort_values('nav_date')
    nav_df = nav_df.set_index('nav_date')
    nav = nav_df['nav'].astype(float)
    if len(nav) < 2:
        return None

    # monthly returns using month-end NAV
    monthly = nav.resample('ME').last().pct_change().dropna()
    if monthly.empty:
        return None

    def comp_ret(months):
        if len(monthly) >= months:
            return (1 + monthly.tail(months)).prod() - 1
        return float('nan')

    metrics = {}
    metrics['ret_1m'] = comp_ret(1)
    metrics['ret_3m'] = comp_ret(3)
    metrics['ret_6m'] = comp_ret(6)
    metrics['ret_12m'] = comp_ret(12)
    metrics['ret_36m'] = comp_ret(36)

    monthly_mean = monthly.mean()
    ann_return = (1 + monthly_mean) ** 12 - 1
    ann_vol = monthly.std() * math.sqrt(12) if monthly.std() is not None else float('nan')
    metrics['ann_return'] = float(ann_return) if pd.notna(ann_return) else None
    metrics['ann_vol'] = float(ann_vol) if pd.notna(ann_vol) else None

    rf = 0.04
    metrics['sharpe'] = float((metrics['ann_return'] - rf) / metrics['ann_vol']) if metrics['ann_vol'] and metrics['ann_vol'] > 0 else None

    # max drawdown on full NAV series
    cummax = nav.cummax()
    drawdown = (nav - cummax) / cummax
    metrics['max_drawdown'] = float(drawdown.min()) if not drawdown.empty else None

    # pct positive months in last 36 months
    tail36 = monthly.tail(36)
    metrics['pct_pos_months_36'] = float((tail36 > 0).sum() / max(1, min(36, len(tail36))))

    return metrics

def upsert_features(engine, fund_id, as_of, metrics):
    if not metrics:
        return
    insert_sql = text("""
    INSERT INTO fund_features (fund_id, as_of_date, ret_1m, ret_3m, ret_6m, ret_12m, ret_36m,
                               ann_return, ann_vol, sharpe, max_drawdown, pct_pos_months_36, updated_at)
    VALUES (:fund_id, :as_of, :ret_1m, :ret_3m, :ret_6m, :ret_12m, :ret_36m,
            :ann_return, :ann_vol, :sharpe, :max_drawdown, :pct_pos_36, now())
    ON CONFLICT (fund_id, as_of_date) DO UPDATE SET
      ret_1m = EXCLUDED.ret_1m, ret_3m = EXCLUDED.ret_3m, ret_6m = EXCLUDED.ret_6m,
      ret_12m = EXCLUDED.ret_12m, ret_36m = EXCLUDED.ret_36m,
      ann_return = EXCLUDED.ann_return, ann_vol = EXCLUDED.ann_vol, sharpe = EXCLUDED.sharpe,
      max_drawdown = EXCLUDED.max_drawdown, pct_pos_months_36 = EXCLUDED.pct_pos_months_36, updated_at = now()
    """)
    params = {'fund_id': fund_id, 'as_of': as_of,
              'ret_1m': metrics.get('ret_1m'),
              'ret_3m': metrics.get('ret_3m'),
              'ret_6m': metrics.get('ret_6m'),
              'ret_12m': metrics.get('ret_12m'),
              'ret_36m': metrics.get('ret_36m'),
              'ann_return': metrics.get('ann_return'),
              'ann_vol': metrics.get('ann_vol'),
              'sharpe': metrics.get('sharpe'),
              'max_drawdown': metrics.get('max_drawdown'),
              'pct_pos_36': metrics.get('pct_pos_months_36')
    }
    with engine.begin() as conn:
        conn.execute(insert_sql, params)

def main():
    funds = fetch_all_funds(engine)

    # Get all unique month-end dates from NAVs to compute features historically
    all_months = pd.read_sql("""
        SELECT DISTINCT DATE_TRUNC('month', nav_date)::date AS month_start
        FROM navs
        WHERE nav IS NOT NULL
        ORDER BY month_start
    """, engine)

    print(f"Found {len(all_months)} months of NAV data.")

    for _, month_row in all_months.iterrows():
        as_of = pd.to_datetime(month_row['month_start']) + pd.offsets.MonthEnd(0)
        print(f"\n📅 Computing features as of {as_of.date()}")

        for _, row in funds.iterrows():
            fid = row['fund_id']
            navs = fetch_navs_for_fund(engine, fid)

            # filter NAVs up to this month-end only (simulate historical "as of")
            navs = navs[navs['nav_date'] <= as_of]

            metrics = compute_metrics(navs)
            if metrics:
                upsert_features(engine, fid, as_of, metrics)


if __name__ == "__main__":
    main()
