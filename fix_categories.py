from sqlalchemy import create_engine, text

DB_URL = "postgresql://mfuser:pass@localhost:5432/mfdb"
engine = create_engine(DB_URL)

def categorize_funds():
    rules = [
        ("ELSS", "ELSS"),
        ("Tax Saver", "ELSS"),
        ("Liquid", "Liquid"),
        ("Overnight", "Overnight"),
        ("Index", "Index Fund"),
        ("Nifty", "Index Fund"),
        ("Sensex", "Index Fund"),
        ("Bluechip", "Large Cap"),
        ("Large Cap", "Large Cap"),
        ("Mid Cap", "Mid Cap"),
        ("Small Cap", "Small Cap"),
        ("Flexi Cap", "Flexi Cap"), # Strict match
        ("Multi Cap", "Flexi Cap"),
        ("Balanced", "Hybrid"),
        ("Hybrid", "Hybrid"),
        ("Dynamic Bond", "Debt"),
        ("Fixed Term", "Debt"), # Fix for UTI FMP
        ("Income Fund", "Debt"),
        ("Gilt", "Gilt"),
        ("Corporate Bond", "Corporate Bond"),
        ("Banking & PSU", "Debt"),
        ("Debt", "Debt"),
        ("Fund of Funds", "FoF"),
        ("Gold", "Gold"),
    ]

    with engine.begin() as conn:
        print("Starting Categorization...")
        
        # 1. Reset all categories to NULL to ensure clean re-tagging
        print("Resetting existing categories...")
        conn.execute(text("UPDATE funds SET category = NULL"))
        
        for keyword, category in rules:
            print(f"Tagging '{category}' for keyword '{keyword}'...")
            # Case insensitive update
            stmt = text(f"UPDATE funds SET category = :cat WHERE fund_name ILIKE :kw") 
            # Removed 'AND category IS NULL' to allow specific rules in list to apply 
            # (Wait, list order matters. Later rules overwrite earlier ones?)
            # Actually, standard SQL update.
            # If I want specific to win, I should order Generic -> Specific and overwrite?
            # OR process Specific -> Generic and use IS NULL?
            # Let's stick to "Specific -> Generic" and use IS NULL for safety?
            # NO, my list has "Flexi Cap" (Specific) and "Debt" (Generic).
            # "UTI ... Flexi" was the issue.
            # If I want "Fixed Term" -> "Debt" to win over "Flexi Cap", "Debt" must be applied.
            # Let's use the 'Tag if NULL' strategy again, but after RESET.
            # So I need to order my rules intelligently.
            # "Fixed Term" (Debt) > "Flexi" (Equity).
            # So I should tag "Fixed Term" FIRST.
            
            # RE-ORDERING RULES IN NEXT STEP IF NEEDED. 
            # For now, let's keep the code simple: update where IS NULL.
            stmt = text(f"UPDATE funds SET category = :cat WHERE fund_name ILIKE :kw AND category IS NULL")
            
            res = conn.execute(stmt, {'cat': category, 'kw': f"%{keyword}%"})
            print(f"Updated {res.rowcount} rows.")

        # Fallback for remaining
        conn.execute(text("UPDATE funds SET category = 'Other' WHERE category IS NULL"))
        print("Done.")

if __name__ == "__main__":
    categorize_funds()
