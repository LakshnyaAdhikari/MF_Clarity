import pandas as pd
from sqlalchemy import create_engine
import os

DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL)

def debug_merge():
    print("Loading Features...")
    q = "SELECT * FROM fund_features WHERE as_of_date = (SELECT MAX(as_of_date) FROM fund_features)"
    df = pd.read_sql(q, engine, parse_dates=['as_of_date'])
    print(f"Features Cols: {df.columns.tolist()}")
    
    print("\nLoading Meta...")
    meta = pd.read_sql("SELECT fund_id, fund_name, expense_ratio, aum_cr, top10_concentration, rating, category, turnover FROM funds", engine)
    print(f"Meta Cols: {meta.columns.tolist()}")
    print(f"Meta Sample: {meta[['fund_id', 'fund_name']].head(1).to_dict('records')}")
    
    df['fund_id'] = df['fund_id'].astype(str)
    meta['fund_id'] = meta['fund_id'].astype(str)
    
    drop_cols = ['fund_name', 'expense_ratio', 'aum_cr', 'top10_concentration', 'rating', 'category', 'turnover']
    print(f"\nDropping: {drop_cols}")
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True, errors='ignore')
    print(f"Features Cols After Drop: {df.columns.tolist()}")

    merged = df.merge(meta, on='fund_id', how='left')
    print(f"\nMerged Cols: {merged.columns.tolist()}")
    
    if 'fund_name' in merged.columns:
        print("✅ fund_name EXISTS in merged.")
    else:
        print("❌ fund_name MISSING in merged.")

if __name__ == "__main__":
    debug_merge()
