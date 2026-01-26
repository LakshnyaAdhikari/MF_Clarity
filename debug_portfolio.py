from portfolio_service import generate_portfolio
import traceback

def test():
    user = {
        'amount': 600000, 
        'horizon_years': 5, 
        'risk_tolerance': 'High', 
        'age': 30,
        'goal': 'Wealth'
    }
    print("Calling generate_portfolio...")
    try:
        # Import inside to debug scope
        from market_service import get_market_status
        print("Market Status check...")
        ms = get_market_status()
        print("Market Status:", ms['phase'])
        
        from score_service import load_latest_features, engine
        print("Loading Features...")
        df = load_latest_features(engine)
        print(f"Features Loaded: {len(df)} rows")
        
        res = generate_portfolio(user)
        print("Success! Portfolio keys:", res.keys())
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    test()
