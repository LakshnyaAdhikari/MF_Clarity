
import os
import sqlalchemy
from sqlalchemy import create_engine, text

DB_URL = os.getenv("DB_URL", "postgresql://mfuser:pass@localhost:5432/mfdb")

def check():
    print(f"Attempting connection to {DB_URL}...")
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            print("Connection Successful!")
            res = conn.execute(text("SELECT 1")).scalar()
            print(f"SELECT 1 returned: {res}")
            
            # Check tables
            res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
            tables = [row[0] for row in res]
            print(f"Tables found: {tables}")
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    check()
