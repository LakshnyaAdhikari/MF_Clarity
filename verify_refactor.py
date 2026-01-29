from portfolio_service import generate_portfolio
import json

def verify():
    # Large portfolio to trigger Gold + Thematic
    user = {
        'amount': 12000000, # 1.2 Cr
        'horizon_years': 5, 
        'risk_tolerance': 'High', 
        'age': 30,
        'goal': 'Wealth'
    }
    
    print("Generating Portfolio for 1.2 Crore...")
    res = generate_portfolio(user)
    
    print("\n--- ALLOCATION OUTPUT ---")
    print(json.dumps(res['allocation'], indent=2))
    
    print("\n--- ASSET CLASSES ---")
    totals = {}
    for p in res['portfolio']:
        ac = p['asset_class']
        w = p['weight']
        amt = p['amount']
        print(f"{p['fund_name'][:40]}... | {ac} | {w*100}% | ₹{amt}")
        totals[ac] = totals.get(ac, 0) + w

    print("\n--- CALCULATED TOTALS ---")
    for k,v in totals.items():
        print(f"{k}: {round(v, 4)}")

    # Validations
    print("\n--- CHECKS ---")
    eq_alloc = res['allocation'].get('Equity', 0)
    comm_alloc = res['allocation'].get('Commodity', 0)
    debt_alloc = res['allocation'].get('Debt', 0)
    
    calc_eq = totals.get('Equity', 0)
    calc_comm = totals.get('Commodity', 0)
    
    if abs(eq_alloc - calc_eq) < 0.02:
        print("✅ Equity Allocation Matches Weights")
    else:
        print(f"❌ Equity Mismatch: Alloc {eq_alloc} vs Calc {calc_eq}")

    if abs(comm_alloc - calc_comm) < 0.02:
        print("✅ Commodity Allocation Matches Weights")
    else:
        print(f"❌ Commodity Mismatch: Alloc {comm_alloc} vs Calc {calc_comm}")

    # Check Thematic is inside Equity
    thematic_funds = [p for p in res['portfolio'] if p.get('subtype') == 'Thematic']
    if thematic_funds:
        print(f"✅ Thematic Funds Found: {len(thematic_funds)} (Tagged as {thematic_funds[0]['asset_class']})")
    else:
        print("⚠️ No Thematic Funds found (Check logic)")

if __name__ == "__main__":
    verify()
