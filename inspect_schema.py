from score_service import engine
from sqlalchemy import text

with engine.connect() as conn:
    print("\n--- FUNDS TABLE ---")
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'funds'"))
    print([r[0] for r in res])
    
    print("\n--- FEATURES TABLE ---")
    res = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'fund_features'"))
    print([r[0] for r in res])
