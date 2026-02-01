from sqlalchemy import text
from score_service import engine
import json

def save_portfolio_snapshot(user_id, portfolio_data, allocation, market_phase):
    """
    Saves a generated portfolio to the user_portfolios table.
    """
    if not user_id:
        return None

    try:
        with engine.begin() as conn:
            query = text("""
                INSERT INTO user_portfolios 
                (user_id, portfolio_data, allocation_equity, allocation_debt, market_phase)
                VALUES (:uid, :pdata, :alloc_eq, :alloc_debt, :mphase)
                RETURNING id
            """)
            
            result = conn.execute(query, {
                'uid': user_id,
                'pdata': json.dumps(portfolio_data),
                'alloc_eq': allocation.get('Equity', 0),
                'alloc_debt': allocation.get('Debt', 0),
                'mphase': market_phase
            })
            return result.fetchone()[0]
    except Exception as e:
        print(f"Error saving portfolio snapshot: {e}")
        return None

def log_interaction(user_id, action_type, details=None):
    """
    Logs a user action (e.g. 'generate', 'login').
    """
    if not user_id:
        return

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO interaction_logs (user_id, action_type, details)
                VALUES (:uid, :act, :det)
            """), {
                'uid': user_id,
                'act': action_type,
                'det': json.dumps(details) if details else '{}'
            })
    except Exception as e:
        print(f"Error logging interaction: {e}")

def get_user_risk_score(user_id):
    """
    Fetches the persisted numeric risk score if available.
    """
    if not user_id:
        return None
        
    with engine.connect() as conn:
        res = conn.execute(text("SELECT risk_score FROM user_profiles WHERE user_id = :uid"), {'uid': user_id}).fetchone()
        if res:
            return res[0]
    return None

def get_latest_portfolio(user_id):
    """
    Retrieves the most recent portfolio for the user.
    """
    if not user_id: return None
    
    with engine.connect() as conn:
        query = text("""
            SELECT portfolio_data, allocation_equity, allocation_debt, market_phase, created_at
            FROM user_portfolios 
            WHERE user_id = :uid 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        res = conn.execute(query, {'uid': user_id}).fetchone()
        
        if res:
            return {
                "portfolio": json.loads(res[0]),
                "allocation": {"Equity": res[1], "Debt": res[2]},
                "market_phase": res[3],
                "saved_at": str(res[4])
            }
    return None
