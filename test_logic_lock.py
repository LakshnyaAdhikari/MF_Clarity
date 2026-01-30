from portfolio_service import generate_portfolio
import json

def test_logic():
    print("=== TEST 1: High Risk (Should be Large + Mid + Small) ===")
    u1 = {'amount': 100000, 'horizon_years': 10, 'risk_tolerance': 'High', 'age': 30}
    res1 = generate_portfolio(u1)
    equity_funds1 = [p for p in res1['portfolio'] if p['asset_class'] == 'Equity']
    print(f"Equity Funds: {[f['category'] for f in equity_funds1]}")
    print(f"Funds Config: {[f['rationale'] for f in equity_funds1]}")
    
    print("\n=== TEST 2: Low Risk (Should be Large + Flexi) ===")
    u2 = {'amount': 100000, 'horizon_years': 3, 'risk_tolerance': 'Low', 'age': 50}
    res2 = generate_portfolio(u2)
    equity_funds2 = [p for p in res2['portfolio'] if p['asset_class'] == 'Equity']
    print(f"Equity Funds: {[f['category'] for f in equity_funds2]}")
    print(f"Funds Config: {[f['rationale'] for f in equity_funds2]}")

    # Check for IDCW in names
    all_funds = res1['portfolio'] + res2['portfolio']
    has_idcw = any("IDCW" in f['fund_name'] or "Dividend" in f['fund_name'] for f in all_funds if f['fund_name'])
    print(f"\nIDCW/Dividend found? {has_idcw}")
    
    # Check for duplicates
    ids = [f['fund_id'] for f in res1['portfolio']]
    duplicates = len(ids) != len(set(ids))
    print(f"Duplicates found in High Risk? {duplicates}")
    if duplicates:
        print(f"IDs: {ids}")

    ids2 = [f['fund_id'] for f in res2['portfolio']]
    duplicates2 = len(ids2) != len(set(ids2))
    print(f"Duplicates found in Low Risk? {duplicates2}")

if __name__ == "__main__":
    test_logic()
