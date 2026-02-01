from score_service import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("\n--- FUND_FEATURES COLUMNS ---")
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'fund_features' ORDER BY column_name"))
    cols = [r[0] for r in res]
    print(", ".join(cols))
