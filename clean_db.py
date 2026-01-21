from sqlalchemy import create_engine, text
import os

# Connect
DB_URL = "postgresql://mfuser:pass@localhost:5432/mfdb"
engine = create_engine(DB_URL)

def clean_and_check():
    with engine.connect() as conn:
        # 1. Delete Mock Data (Cascade manually)
        print("Deleting mock funds (f001, f002, f003)...")
        mock_ids = "('f001', 'f002', 'f003')"
        conn.execute(text(f"DELETE FROM navs WHERE fund_id IN {mock_ids}"))
        conn.execute(text(f"DELETE FROM fund_features WHERE fund_id IN {mock_ids}"))
        conn.execute(text(f"DELETE FROM funds WHERE fund_id IN {mock_ids}"))
        conn.commit()
        
        # 2. Check Real Data Count
        count = conn.execute(text("SELECT COUNT(*) FROM funds")).scalar()
        print(f"Total Funds in DB: {count}")
        
        # 3. Sample Real Data
        if count > 0:
            print("\nSample Real Funds:")
            rows = conn.execute(text("SELECT fund_id, fund_name, category FROM funds LIMIT 5")).fetchall()
            for r in rows:
                print(r)
        else:
            print("\nWARNING: Database is empty! You need to run ETL.")

if __name__ == "__main__":
    clean_and_check()
