from sqlalchemy import text
from score_service import engine
from auth_service import verify_password
import sys

def check_user(email, password_attempt):
    with engine.connect() as conn:
        print(f"Checking for user: {email}")
        result = conn.execute(text("SELECT id, email, password_hash FROM users WHERE email = :e"), {"e": email}).fetchone()
        
        if not result:
            print("❌ User not found in database.")
            list_all_users()
            return

        user_id, db_email, db_hash = result
        print(f"✅ User found: ID={user_id}")
        
        print(f"Verifying password: '{password_attempt}'")
        is_valid = verify_password(password_attempt, db_hash)
        
        if is_valid:
            print("✅ Password verification SUCCESS.")
        else:
            print(f"❌ Password verification FAILED.")
            print(f"DB Hash start: {db_hash[:20]}...")

def list_all_users():
    with engine.connect() as conn:
        print("\n--- All Registered Users ---")
        rows = conn.execute(text("SELECT email FROM users")).fetchall()
        for r in rows:
            print(f"- {r[0]}")
        print("----------------------------\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python debug_auth.py <email> <password>")
    else:
        check_user(sys.argv[1], sys.argv[2])
