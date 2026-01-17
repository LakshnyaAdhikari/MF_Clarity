import pandas as pd
from score_service import recommend, load_latest_features, engine
from market_service import get_market_status
from reasoning_engine import explain_portfolio

def allocate_assets(user_profile, market_phase):
    """
    Determine target asset allocation based on risk, horizon, AGE, and MARKET PHASE.
    """
    risk = (user_profile.get('risk_tolerance') or 'Moderate').lower()
    horizon = float(user_profile.get('horizon_years') or 3)
    age = user_profile.get('age')
    
    # 1. Base Allocation (Rule of Thumb: 100 - Age for Equity, but capped)
    if age:
        equity_base = min(0.90, max(0.10, (110 - age) / 100.0))
        debt_base = 1.0 - equity_base
    else:
        # Fallback if age not provided
        if risk in ('high', 'aggressive'):
            equity_base, debt_base = 0.80, 0.20
        elif risk in ('low', 'conservative', 'safety'):
            equity_base, debt_base = 0.20, 0.80
        else:
            equity_base, debt_base = 0.50, 0.50

    # 2. Risk Profile Adjustment
    if risk in ('high', 'aggressive'):
        equity_base = min(1.0, equity_base + 0.10)
    elif risk in ('low', 'conservative'):
        equity_base = max(0.0, equity_base - 0.15)
        
    # 3. Horizon Adjustment
    if horizon < 3:
        equity_base = max(0.0, equity_base - 0.25) # Penalize equity for short term
    
    # 4. Market Phase Adjustment (Tactical)
    if market_phase == "OVERHEATED":
        # Reduce equity by 15% (e.g., 0.60 -> 0.45) to protect capital
        equity_base = equity_base * 0.85
    elif market_phase == "UNDERVALUED":
        # Increase equity by 10% to capture value
        equity_base = min(1.0, equity_base * 1.10)
        
    # Normalize
    debt_base = 1.0 - equity_base
    return {'Equity': round(equity_base, 2), 'Debt': round(debt_base, 2)}

def generate_portfolio(user_profile):
    """
    Construct a portfolio (Combo) for the user w/ Reasoning.
    """
    # 1. Get Market Context
    market_status = get_market_status()
    market_phase = market_status['phase']
    
    # 2. Determine Allocation
    allocation = allocate_assets(user_profile, market_phase)
    total_amount = float(user_profile.get('amount') or 10000)
    current_investment = float(user_profile.get('current_investments') or 0)
    
    # 3. Load Data
    df_features = load_latest_features(engine)
    
    portfolio = []
    
    # 4. Select Funds (TOP 5 Strategy)
    # Strategy: 3 Equity Funds (Large, Mid, Flexi ideally, but here simulated by 'Top') + 2 Debt Funds
    
    equity_amt = total_amount * allocation['Equity']
    debt_amt = total_amount * allocation['Debt']
    
    # Helper to pick top N
    def pick_funds(cat_filter, count, total_alloc_amt):
        df_res = recommend(user_profile, category_filter=cat_filter, topk=count, df=df_features)
        recs = df_res.to_dict(orient='records')
        items = []
        if not recs: return []
        
        weight_per_fund = 1.0 / len(recs)
        for r in recs:
            items.append({
                "fund_id": r['fund_id'],
                "fund_name": r.get('fund_name'),
                "category": r.get('category'),
                "asset_class": cat_filter,
                "weight": round(weight_per_fund * (total_alloc_amt/total_amount), 4),
                "amount": round(total_alloc_amt * weight_per_fund, 2),
                "score": round(r.get('TotalScore', 0), 2),
                "rationale": f"Top rated {cat_filter} Fund"
            })
        return items

    if allocation['Equity'] > 0.1:
        # We want diversity in Equity. Let's try to get 3 funds.
        portfolio.extend(pick_funds('Equity', 3, equity_amt))
        
    if allocation['Debt'] > 0.1:
        # 2 Debt funds
        portfolio.extend(pick_funds('Debt', 2, debt_amt))
        
    # 5. Generate Explanation
    # Construct a temporary structure to pass to reasoning engine
    temp_data = {"user_profile": user_profile, "allocation": allocation}
    explanation = explain_portfolio(temp_data, market_status)

    return {
        "user_profile": user_profile,
        "market_status": market_status,
        "allocation": allocation,
        "portfolio": portfolio,
        "explanation": explanation
    }

if __name__ == "__main__":
    # Test
    u = {'amount': 100000, 'horizon_years': 10, 'risk_tolerance': 'High', 'age': 30}
    print("Testing Portfolio for:", u)
    res = generate_portfolio(u)
    print("\nALLOCATION:", res['allocation'])
    print("MARKET:", res['market_status']['phase'])
    print("EXPLANATION:\n", res['explanation'])
    import json
    print("\nPORTFOLIO:", json.dumps(res['portfolio'][:2], indent=2))
