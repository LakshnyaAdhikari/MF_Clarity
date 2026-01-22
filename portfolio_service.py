import pandas as pd
from score_service import recommend, load_latest_features, engine
from market_service import get_market_status
from reasoning_engine import explain_portfolio, generate_confidence_score

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
    
    # 4. Select Funds (Slot-Based Strategy)
    portfolio = []
    
    # --- EQUITY STRATEGY ---
    equity_budget = total_amount * allocation['Equity']
    if equity_budget > 0:
        # A. Core: Large Cap or Index (50% of Equity)
        core_amt = equity_budget * 0.50
        core_funds = recommend(user_profile, category_filter='Large Cap', topk=1, df=df_features).to_dict('records')
        if not core_funds: # Fallback to Index
             core_funds = recommend(user_profile, category_filter='Index Fund', topk=1, df=df_features).to_dict('records')
        
        if core_funds:
            f = core_funds[0]
            portfolio.append({
                "fund_id": f['fund_id'], "fund_name": f.get('fund_name'), "category": f.get('category'),
                "asset_class": "Equity", "weight": round(allocation['Equity'] * 0.50, 4),
                "amount": round(core_amt, 2), "score": round(f.get('TotalScore', 0), 2),
                "rationale": "Core Portfolio Anchor (Stability)",
                "metrics": {
                    "sharpe": round(f.get('sharpe', 0), 2),
                    "volatility": round(f.get('ann_vol', 0)*100, 1),
                    "returns": round(f.get('ann_return', 0)*100, 1)
                }
            })

        # B. Growth: Flexi Cap (30% of Equity)
        growth_amt = equity_budget * 0.30
        growth_funds = recommend(user_profile, category_filter='Flexi Cap', topk=1, df=df_features).to_dict('records')
        if growth_funds:
            f = growth_funds[0]
            portfolio.append({
                "fund_id": f['fund_id'], "fund_name": f.get('fund_name'), "category": f.get('category'),
                "asset_class": "Equity", "weight": round(allocation['Equity'] * 0.30, 4),
                "amount": round(growth_amt, 2), "score": round(f.get('TotalScore', 0), 2),
                "rationale": "Flexi Cap for Growth across sectors",
                "metrics": {
                    "sharpe": round(f.get('sharpe', 0), 2),
                    "volatility": round(f.get('ann_vol', 0)*100, 1),
                    "returns": round(f.get('ann_return', 0)*100, 1)
                }
            })
            
        # C. Alpha: Mid/Small Cap (20% of Equity) - Only if Risk is NOT Low
        if user_profile.get('risk_tolerance', 'Moderate').lower() != 'low':
            alpha_amt = equity_budget * 0.20
            alpha_funds = recommend(user_profile, category_filter='Mid Cap', topk=1, df=df_features).to_dict('records')
            if alpha_funds:
                f = alpha_funds[0]
                portfolio.append({
                    "fund_id": f['fund_id'], "fund_name": f.get('fund_name'), "category": f.get('category'),
                    "asset_class": "Equity", "weight": round(allocation['Equity'] * 0.20, 4),
                    "amount": round(alpha_amt, 2), "score": round(f.get('TotalScore', 0), 2),
                    "rationale": "Mid Cap for extra returns (Alpha)",
                    "metrics": {
                        "sharpe": round(f.get('sharpe', 0), 2),
                        "volatility": round(f.get('ann_vol', 0)*100, 1),
                        "returns": round(f.get('ann_return', 0)*100, 1)
                    }
                })
        else:
            # If Low risk, move Alpha budget to Core
            if portfolio: portfolio[0]['amount'] += round(equity_budget * 0.20, 2)
            if portfolio: portfolio[0]['weight'] += round(allocation['Equity'] * 0.20, 4)

    # --- DEBT STRATEGY ---
    debt_budget = total_amount * allocation['Debt']
    if debt_budget > 0:
        # A. Safety: Liquid Fund (60% of Debt)
        safe_amt = debt_budget * 0.60
        safe_funds = recommend(user_profile, category_filter='Liquid', topk=1, df=df_features).to_dict('records')
        if safe_funds:
            f = safe_funds[0]
            portfolio.append({
                "fund_id": f['fund_id'], "fund_name": f.get('fund_name'), "category": f.get('category'),
                "asset_class": "Debt", "weight": round(allocation['Debt'] * 0.60, 4),
                "amount": round(safe_amt, 2), "score": round(f.get('TotalScore', 0), 2),
                "rationale": "Liquid Fund for Emergency access & Low Risk",
                "metrics": {
                    "sharpe": round(f.get('sharpe', 0), 2),
                    "volatility": round(f.get('ann_vol', 0)*100, 1),
                    "returns": round(f.get('ann_return', 0)*100, 1)
                }
            })
            
        # B. Yield: Corporate Bond / Gilt (40% of Debt)
        yield_amt = debt_budget * 0.40
        yield_cat = 'Gilt' if user_profile.get('risk_tolerance') == 'Low' else 'Corporate Bond'
        yield_funds = recommend(user_profile, category_filter=yield_cat, topk=1, df=df_features).to_dict('records')
        # Fallback to debt generic
        if not yield_funds: 
             yield_funds = recommend(user_profile, category_filter='Debt', topk=1, df=df_features).to_dict('records')

        if yield_funds:
            f = yield_funds[0]
            portfolio.append({
                "fund_id": f['fund_id'], "fund_name": f.get('fund_name'), "category": f.get('category'),
                "asset_class": "Debt", "weight": round(allocation['Debt'] * 0.40, 4),
                "amount": round(yield_amt, 2), "score": round(f.get('TotalScore', 0), 2),
                "rationale": f"{yield_cat} for better Yield stability",
                "metrics": {
                    "sharpe": round(f.get('sharpe', 0), 2),
                    "volatility": round(f.get('ann_vol', 0)*100, 1),
                    "returns": round(f.get('ann_return', 0)*100, 1)
                }
            })

    # 5. Generate Explanation
    # Construct a temporary structure to pass to reasoning engine
    temp_data = {"user_profile": user_profile, "allocation": allocation}
    explanation = explain_portfolio(temp_data, market_status)

    # 6. Calculate Confidence Score
    stability_score = generate_confidence_score(portfolio, market_phase)

    # 7. Structure Output for UI
    equity_schemes = [p for p in portfolio if p['asset_class'] == 'Equity']
    debt_schemes = [p for p in portfolio if p['asset_class'] == 'Debt']
    
    return {
        "user_profile": user_profile,
        "market_status": market_status,
        "allocation": allocation,
        "portfolio": portfolio, # Keep flat list for legacy or charts
        "sections": {
            "equity": equity_schemes,
            "debt": debt_schemes
        },
        "breakdown": {
            "lump_sum_total": total_amount,
            "sip_total": round(total_amount * 0.015, 0) # 1.5% monthly SIP typical
        },
        "explanation": explanation,
        "confidence_score": stability_score,
        "stability_label": "High" if stability_score > 80 else "Moderate" if stability_score > 50 else "Low"
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
