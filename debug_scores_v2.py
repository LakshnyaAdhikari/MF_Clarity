from score_service import load_latest_features, engine, compute_scores
import pandas as pd

def debug_scores():
    print("Loading Features...")
    df = load_latest_features(engine)
    print(f"Loaded {len(df)} rows.")
    
    print("Columns:", df.columns.tolist())
    
    # Check if aum_cr exists
    if 'aum_cr' not in df.columns:
        print("CRITICAL: aum_cr MISSING from merged dataframe!")
        # Let's see what keys we merged on
        # checking raw
        q = "SELECT * FROM fund_features WHERE as_of_date = (SELECT MAX(as_of_date) FROM fund_features)"
        feat = pd.read_sql(q, engine)
        print("Features fund_id type:", feat['fund_id'].dtype)
        print("Sample feat IDs:", feat['fund_id'].head(3).tolist())
        
        meta = pd.read_sql("SELECT fund_id, fund_name, aum_cr FROM funds", engine)
        print("Meta fund_id type:", meta['fund_id'].dtype)
        print("Sample meta IDs:", meta['fund_id'].head(3).tolist())
        return

    # Inspect AUM
    print("\n--- AUM CHECK ---")
    print(df[['fund_name', 'aum_cr']].head())
    print("AUM NaNs:", df['aum_cr'].isna().sum())
    
    # Compute Scores
    scores = compute_scores(df, {'goal':'Wealth'})
    
    print("\n--- SCORE CHECK ---")
    print(scores[['fund_name', 'TotalScore', 'aum_cr', 'is_small_aum', 'ret_consistency']].head(10))
    
    print("\n--- CATEGORY CHECK ---")
    cats = scores['category'].unique()
    print("Categories found:", cats)
    print("Has Commodity?", any('commodity' in str(c).lower() for c in cats))
    print("Has Gold?", any('gold' in str(c).lower() for c in cats))
    print("Has Thematic/Sector?", any('sector' in str(c).lower() for c in cats))

    print("\n--- THEMATIC NAME CHECK ---")
    banking = pd.read_sql("SELECT fund_name, category FROM funds WHERE fund_name ILIKE '%%Banking%%' LIMIT 3", engine)
    print("Banking Funds:", banking.to_dict('records'))

if __name__ == "__main__":
    debug_scores()
