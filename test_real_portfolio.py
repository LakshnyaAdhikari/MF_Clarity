from portfolio_service import generate_portfolio
import json

def test():
    user = {
        'amount': 500000,
        'age': 35, 
        'risk_tolerance': 'High',
        'horizon_years': 10,
        'goal': 'Wealth'
    }
    
    print("Generating Portfolio for:", user)
    try:
        res = generate_portfolio(user)
        print("\n--- RESULTS ---")
        print(f"Confidence: {res['confidence_score']}")
        print(f"Breakdown: {res['breakdown']}")
        
        print("\n--- EQUITY ---")
        for p in res['sections']['equity']:
            print(f"- {p['fund_name']} ({p['category']}) | {p['weight']*100}% | ₹{p['amount']}")
            
        print("\n--- DEBT ---")
        for p in res['sections']['debt']:
            print(f"- {p['fund_name']} ({p['category']}) | {p['weight']*100}% | ₹{p['amount']}")
            
    except Exception as e:
        print("ERROR:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
