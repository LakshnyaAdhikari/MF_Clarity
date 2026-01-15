# backtest.py
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from datetime import datetime
from dateutil.relativedelta import relativedelta

# -------------------------------------------------------
# CONNECT TO DATABASE
# -------------------------------------------------------
engine = create_engine("postgresql://mfuser:pass@localhost:5432/mfdb")

# Load NAV and feature data
nav = pd.read_sql("SELECT fund_id, nav_date, nav FROM navs", engine)
features = pd.read_sql("SELECT * FROM fund_features", engine)

# Optional benchmark table (if exists)
try:
    benchmark = pd.read_sql("SELECT nav_date, nav FROM benchmark_nav", engine)
except Exception as e:
    print("No benchmark table found — continuing without benchmark.")
    benchmark = None

# -------------------------------------------------------
# SIMULATION PARAMETERS
# -------------------------------------------------------
start_date = pd.to_datetime("2018-01-31")   # beginning of backtest
end_date   = pd.to_datetime("2025-01-31")   # end of backtest
horizon_months = 36                         # hold period (3 years)
top_n = 3                                   # top N funds to simulate
results = []                                # store results

features['as_of_date'] = pd.to_datetime(features['as_of_date'])

# -------------------------------------------------------
# MONTHLY ROLLING SIMULATION
# -------------------------------------------------------
current_date = start_date
while current_date <= end_date:
    current_date = pd.to_datetime(current_date)
    print(f"\nRunning simulation for {current_date.date()}")

    # --- Get features available up to current_date ---
    df_t = features[features['as_of_date'] <= pd.Timestamp(current_date)].copy()
    if df_t.empty:
        current_date += relativedelta(months=1)
        continue

    latest_date = df_t['as_of_date'].max()
    df_latest = df_t[df_t['as_of_date'] == latest_date].copy()

    # --- Compute simple composite score (proxy for score_service.py) ---
    df_latest['Score'] = (
        0.4 * df_latest['sharpe'].fillna(0) +
        0.3 * df_latest['ann_return'].fillna(0) / 20 +
        0.3 * (1 - df_latest['ann_vol'].fillna(0) / 20)
    )

    top_funds = df_latest.sort_values('Score', ascending=False).head(top_n)['fund_id'].tolist()
    print(f"Top funds on {current_date.date()}: {top_funds}")
    if not top_funds:
     print("⚠️  No funds selected for this date — skipping.")


    # --- Calculate realized return for each top fund after holding horizon ---
    t_future = current_date + relativedelta(months=horizon_months)

    for fid in top_funds:
        try:
            nav_t = nav[(nav['fund_id'] == fid) & (nav['nav_date'] <= current_date)].sort_values('nav_date').iloc[-1]['nav']
            nav_future = nav[(nav['fund_id'] == fid) & (nav['nav_date'] <= t_future)].sort_values('nav_date').iloc[-1]['nav']
            realized_return = (nav_future / nav_t) - 1
        except Exception:
            realized_return = np.nan

        # Optional benchmark comparison
        if benchmark is not None:
            try:
                bm_t = benchmark[benchmark['nav_date'] <= current_date].sort_values('nav_date').iloc[-1]['nav']
                bm_future = benchmark[benchmark['nav_date'] <= t_future].sort_values('nav_date').iloc[-1]['nav']
                benchmark_return = (bm_future / bm_t) - 1
            except Exception:
                benchmark_return = np.nan
        else:
            benchmark_return = np.nan

        results.append({
            'as_of_date': current_date,
            'fund_id': fid,
            'realized_return': realized_return,
            'benchmark_return': benchmark_return,
            'excess_return': realized_return - benchmark_return if not np.isnan(benchmark_return) else np.nan,
            'horizon_months': horizon_months
        })

    current_date += relativedelta(months=1)

# -------------------------------------------------------
# RESULTS SUMMARY
# -------------------------------------------------------
res_df = pd.DataFrame(results)
print("res_df columns:", res_df.columns)
print("res_df head:\n", res_df.head())
res_df.dropna(subset=['realized_return'], inplace=True)

if not res_df.empty:
    hit_rate = (res_df['excess_return'] > 0).mean()
    mean_excess_return = res_df['excess_return'].mean()
    volatility = res_df['realized_return'].std()
    max_drawdown = (res_df['realized_return'].cummax() - res_df['realized_return']).max()

    print("\n===== BACKTEST SUMMARY =====")
    print(f"Hit Rate: {hit_rate:.2%}")
    print(f"Mean Excess Return: {mean_excess_return:.2%}")
    print(f"Volatility: {volatility:.2%}")
    print(f"Max Drawdown: {max_drawdown:.2%}")
else:
    print("\nNo valid backtest results found.")

# -------------------------------------------------------
# SAVE RESULTS
# -------------------------------------------------------
res_df.to_csv("backtest_results.csv", index=False)
print("\nDetailed results saved to backtest_results.csv")
