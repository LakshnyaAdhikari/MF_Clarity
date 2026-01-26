from portfolio_service import recommend, engine
from score_service import load_latest_features

def debug_recs():
    print("Loading Features...")
    df = load_latest_features(engine)
    
    print("\n--- MID CAP CHECK ---")
    mid = recommend({'goal':'Wealth', 'risk_tolerance':'Moderate'}, category_filter='Mid Cap', topk=5, df=df)
    print("Mid Cap Recs found:", len(mid))
    
    # ALWAYS check raw for debugging
    print("Checking raw Mid Cap data...")
    raw = df[df['category'] == 'Mid Cap']
    print(f"Raw Mid Cap count: {len(raw)}")
    if not raw.empty:
        print(raw[['fund_name', 'aum_cr', 'category']].head())
    
    # Check Regular Filter
    reg = raw[~raw['fund_name'].str.contains('Direct', case=False, na=False)]
    print(f"Regular Mid Cap count: {len(reg)}")

    print("\n--- DB COUNT CHECK ---")
    import pandas as pd
    funds_count = pd.read_sql("SELECT COUNT(*) FROM funds WHERE category='Mid Cap'", engine).iloc[0,0]
    print(f"Mid Cap in FUNDS table: {funds_count}")
    
    feat_count = pd.read_sql("SELECT COUNT(*) FROM fund_features ff JOIN funds f ON ff.fund_id=f.fund_id WHERE f.category='Mid Cap'", engine).iloc[0,0]
    print(f"Mid Cap in FEATURES table: {feat_count}")

if __name__ == "__main__":
    debug_recs()
