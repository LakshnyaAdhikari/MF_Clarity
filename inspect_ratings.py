import pandas as pd
from sqlalchemy import create_engine
import os

DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL)

def inspect():
    print("Inspecting Debt Ratings...")
    q = "SELECT fund_name, rating, category FROM funds WHERE category IN ('Corporate Bond', 'Liquid', 'Credit Risk') LIMIT 20"
    df = pd.read_sql(q, engine)
    print(df)
    
    print("\nUnique Ratings in DB:")
    print(pd.read_sql("SELECT DISTINCT rating FROM funds", engine))

if __name__ == "__main__":
    inspect()
