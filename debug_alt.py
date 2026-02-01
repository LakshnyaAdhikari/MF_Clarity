from score_service import engine
from sqlalchemy import text
import traceback

def test_alt(fund_id):
    print(f"Testing alternatives for {fund_id}...")
    try:
        with engine.connect() as conn:
            # 1. Get category
            target = conn.execute(
                text("SELECT category, fund_name FROM funds WHERE fund_id = :fid"), 
                {'fid': fund_id}
            ).fetchone()
            
            if not target:
                print("Fund not found!")
                return
            
            category = target[0]
            print(f"Category: {category}")
            
            # 2. Run the JOIN Query
            query = text("""
                    SELECT f.fund_id, f.fund_name, f.category, 
                           COALESCE(ff.ann_return_3y, 0) as ret, 
                           COALESCE(ff.ann_vol, 0) as vol
                    FROM funds f
                    JOIN fund_features ff ON f.fund_id = ff.fund_id
                    WHERE f.category = :cat 
                      AND f.fund_id != :fid
                      AND ff.as_of_date = (SELECT MAX(as_of_date) FROM fund_features)
                    ORDER BY ff.ann_return_3y DESC
                    LIMIT 3
                """)
            
            print("Executing JOIN query...")
            res = conn.execute(query, {'cat': category, 'fid': fund_id})
            
            results = list(res)
            print(f"Found {len(results)} alternatives.")
            for row in results:
                print(row)
                
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    # Need a valid fund_id. Let's fetch one first.
    with engine.connect() as conn:
        fid = conn.execute(text("SELECT fund_id FROM funds LIMIT 1")).scalar()
    
    if fid:
        test_alt(fid)
    else:
        print("No funds in DB to test.")
