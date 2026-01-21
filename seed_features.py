import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from datetime import date

DB_URL = "postgresql://mfuser:pass@localhost:5432/mfdb"
engine = create_engine(DB_URL)

def seed_features():
    print("Fetching funds...")
    funds = pd.read_sql("SELECT fund_id, category FROM funds", engine)
    
    if funds.empty:
        print("No funds to seed.")
        return

    print(f"Seeding features for {len(funds)} funds...")
    
    features = []
    today = date.today()
    
    for _, row in funds.iterrows():
        cat = str(row['category']).lower()
        
        # Default Baseline
        ann_return = 0.12 # 12%
        ann_vol = 0.15    # 15%
        sharpe = 0.8
        
        if 'large' in cat or 'index' in cat or 'bluechip' in cat:
            ann_return = np.random.uniform(0.10, 0.15)
            ann_vol = np.random.uniform(0.12, 0.18)
        elif 'mid' in cat or 'flexi' in cat:
            ann_return = np.random.uniform(0.14, 0.22)
            ann_vol = np.random.uniform(0.18, 0.25)
        elif 'small' in cat:
            ann_return = np.random.uniform(0.18, 0.30)
            ann_vol = np.random.uniform(0.22, 0.35)
        elif 'debt' in cat or 'bond' in cat or 'gilt' in cat:
            ann_return = np.random.uniform(0.06, 0.08)
            ann_vol = np.random.uniform(0.02, 0.05)
        elif 'liquid' in cat or 'overnight' in cat:
            ann_return = np.random.uniform(0.05, 0.065)
            ann_vol = np.random.uniform(0.005, 0.01)
            
        sharpe = (ann_return - 0.05) / (ann_vol + 0.0001)
        
        features.append({
            "fund_id": row['fund_id'],
            "as_of_date": today,
            "ann_return": round(ann_return, 4),
            "ann_vol": round(ann_vol, 4),
            "sharpe": round(sharpe, 4),
            "max_drawdown": round(ann_vol * -1.5, 4), # Simple heuristic
            "pct_pos_months_36": round(np.random.uniform(0.5, 0.8), 2),
            "manager_tenure_years": round(np.random.uniform(1, 10), 1)
        })
        
    df = pd.DataFrame(features)
    
    print("Writing to DB...")
    # Use chunksize to avoid packet size error
    df.to_sql('fund_features', engine, if_exists='append', index=False, chunksize=1000)
    print("Done!")

if __name__ == "__main__":
    seed_features()
