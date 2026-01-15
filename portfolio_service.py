import pandas as pd
from score_service import recommend, load_latest_features, engine

def allocate_assets(user_profile):
    """
    Determine target asset allocation based on risk and horizon.
    Returns dict: {'Equity': x, 'Debt': y} where x+y = 1.0
    """
    risk = (user_profile.get('risk_tolerance') or 'Moderate').lower()
    horizon = float(user_profile.get('horizon_years') or 3)
    
    # Base allocation
    if risk in ('high', 'aggressive'):
        allocation = {'Equity': 0.80, 'Debt': 0.20}
    elif risk in ('low', 'conservative', 'safety'):
        allocation = {'Equity': 0.20, 'Debt': 0.80}
    else: # Moderate
        allocation = {'Equity': 0.50, 'Debt': 0.50}
        
    # Horizon adjustments
    if horizon < 3:
        # Short term -> Reduce equity risk
        allocation['Equity'] = max(0.0, allocation['Equity'] - 0.20)
        allocation['Debt'] = min(1.0, allocation['Debt'] + 0.20)
    elif horizon > 7:
        # Long term -> Can take more equity risk
        allocation['Equity'] = min(1.0, allocation['Equity'] + 0.10)
        allocation['Debt'] = max(0.0, allocation['Debt'] - 0.10)
        
    return allocation

def generate_portfolio(user_profile):
    """
    Construct a portfolio (Combo) for the user.
    """
    # 1. Determine Allocation
    allocation = allocate_assets(user_profile)
    total_amount = float(user_profile.get('amount') or 10000)
    
    # 2. Load Data Once
    df_features = load_latest_features(engine)
    
    portfolio = []
    
    # 3. Select Funds for each bucket
    for asset_class, weight in allocation.items():
        if weight <= 0.01:
            continue
            
        # Define filter keywords for score_service
        # "Equity" matches "Equity Scheme - Large Cap", etc.
        # "Debt" matches "Debt Scheme - ...", "Liquid"
        cat_filter = 'Equity' if asset_class == 'Equity' else 'Debt'
        if asset_class == 'Debt':
             # Broaden Debt to include Hybrid if strictly Low risk? 
             # For now, let's stick to simple "Debt" keyword or "Liquid"
             pass
        
        # Get best 2 funds for this category
        top_funds_df = recommend(
            user_profile, 
            category_filter=cat_filter, 
            topk=2, 
            persist=False, 
            df=df_features
        )
        
        # Distribute weight among selected funds (50/50 split of the asset class weight)
        recs = top_funds_df.to_dict(orient='records')
        count = len(recs)
        if count == 0:
            print(f"Warning: No funds found for {asset_class}")
            continue
            
        for rec in recs:
            fund_weight = weight / count
            portfolio.append({
                "fund_id": rec['fund_id'],
                "fund_name": rec.get('fund_name'),
                "category": rec.get('category'),
                "asset_class": asset_class,
                "weight": round(fund_weight, 4),
                "amount": round(total_amount * fund_weight, 2),
                "score": round(rec.get('TotalScore', 0), 2),
                "rationale": f"Top scorer in {asset_class}"
            })
            
    return {
        "user_profile": user_profile,
        "allocation": allocation,
        "portfolio": portfolio
    }

if __name__ == "__main__":
    # Test
    u = {'amount': 100000, 'horizon_years': 10, 'risk_tolerance': 'High'}
    print("Testing Portfolio for:", u)
    res = generate_portfolio(u)
    print("Allocation:", res['allocation'])
    import json
    print(json.dumps(res['portfolio'], indent=2))
