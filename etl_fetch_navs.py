# etl_fetch_navs.py
import os
import requests
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import date

DB_URL = os.getenv("DB_URL")  # e.g., postgresql://mfuser:pass@localhost:5432/mfdb
SOURCE_URL = "https://www.amfiindia.com/spages/NAVAll.txt"

if DB_URL is None:
    raise RuntimeError("DB_URL environment variable not set. Example: postgresql://mfuser:pass@localhost:5432/mfdb")

engine = create_engine(DB_URL, pool_pre_ping=True)

def parse_amfi_navall(text_content):
    import io
    from csv import reader

    # Read manually and handle variable-length rows
    lines = text_content.strip().splitlines()
    rows = list(reader(lines, delimiter=';'))

    # Skip header line if present
    data_rows = [r for r in rows if len(r) >= 5 and r[0].strip().isdigit()]

    records = []
    for r in data_rows:
        try:
            fund_id = r[0].strip()
            fund_name = r[3].strip()
            nav = float(r[-2].strip())
            nav_date = pd.to_datetime(r[-1].strip(), errors='coerce').date()
            records.append({
                "fund_id": fund_id,
                "fund_name": fund_name,
                "nav": nav,
                "nav_date": nav_date
            })
        except Exception:
            continue

    return pd.DataFrame(records)


def upsert_navs(df_navs):
    with engine.begin() as conn:
        # Upsert fund metadata
        fund_meta = df_navs[['fund_id', 'fund_name']].drop_duplicates()
        for _, r in fund_meta.iterrows():
            conn.execute(text("""
                INSERT INTO funds (fund_id, fund_name)
                VALUES (:fid, :fname)
                ON CONFLICT (fund_id) DO UPDATE SET fund_name = EXCLUDED.fund_name
            """), {'fid': r['fund_id'], 'fname': r['fund_name']})
        
        # Upsert NAVs (avoid duplicates)
        for _, r in df_navs.iterrows():
            conn.execute(text("""
                INSERT INTO navs (fund_id, nav_date, nav)
                VALUES (:fid, :ndate, :nval)
                ON CONFLICT (fund_id, nav_date) DO UPDATE SET nav = EXCLUDED.nav
            """), {'fid': r['fund_id'], 'ndate': r['nav_date'], 'nval': r['nav']})

def fetch_and_store():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }
    resp = requests.get(SOURCE_URL, headers=headers, timeout=30)
    resp.raise_for_status()

    df = parse_amfi_navall(resp.text)
    if df.empty:
        print("No NAV records parsed from source.")
        return
    upsert_navs(df)
    print(f"Inserted/updated {len(df)} NAV records.")

if __name__ == "__main__":
    fetch_and_store()
