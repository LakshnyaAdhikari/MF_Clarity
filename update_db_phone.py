from sqlalchemy import text
from score_service import engine

def add_phone_column():
    with engine.begin() as conn:
        try:
            # Check if column exists to avoid error
            # Or just try-except the ALTER
            conn.execute(text("ALTER TABLE users ADD COLUMN phone_number VARCHAR(20)"))
            print("SUCCESS: Added phone_number column to users table.")
        except Exception as e:
            print(f"INFO: Column might already exist or error: {e}")

if __name__ == "__main__":
    add_phone_column()
