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
    debt_budget = total_amount * allocation['Debt']

    # --- GOLD/COMMODITY STRATEGY (Diversification) ---
    # Only if amount > 5L
    if total_amount > 500000:
        gold_budget = total_amount * 0.10 # 10% allocation
        # Re-balance: Take 5% from Equity, 5% from Debt
        equity_budget -= (gold_budget * 0.5)
        debt_budget -= (gold_budget * 0.5)
        
        gold_funds = recommend(user_profile, category_filter='Commodity', topk=1, df=df_features).to_dict('records')
        # If no explicit commodity fund, try Gold
        if not gold_funds:
             gold_funds = recommend(user_profile, category_filter='Gold', topk=1, df=df_features).to_dict('records')
             
        if gold_funds:
            f = gold_funds[0]
            portfolio.append({
                "fund_id": f['fund_id'], "fund_name": f.get('fund_name'), "category": f.get('category'),
                "asset_class": "Commodity", "weight": round(gold_budget / total_amount, 4),
                "amount": round(gold_budget, 2), "score": round(f.get('TotalScore', 0), 2),
                "rationale": "Gold as a hedge against inflation",
                "metrics": {
                    "sharpe": round(f.get('sharpe', 0), 2),
                    "volatility": round(f.get('ann_vol', 0)*100, 1),
                    "returns": round(f.get('ann_return', 0)*100, 1)
                }
            })
    


    # --- EQUITY STRATEGY (Explicit Slots) ---
    if equity_budget > 0:
        risk_profile = user_profile.get('risk_tolerance', 'Moderate').lower()
        selected_ids = {p['fund_id'] for p in portfolio}

        def add_equity_slot(candidate_list, weight_pct, slot_rationale):
             for f in candidate_list:
                 if f['fund_id'] not in selected_ids:
                     amt = equity_budget * weight_pct
                     portfolio.append({
                        "fund_id": f['fund_id'], 
                        "fund_name": f.get('fund_name'), 
                        "category": f.get('category'),
                        "asset_class": "Equity", 
                        "weight": round(amt / total_amount, 4),
                        "amount": round(amt, 2), 
                        "score": round(f.get('TotalScore', 0), 2),
                        "rationale": slot_rationale,
                        "metrics": {
                            "sharpe": round(f.get('sharpe', 0), 2),
                            "volatility": round(f.get('ann_vol', 0)*100, 1),
                            "returns": round(f.get('ann_return', 0)*100, 1)
                        }
                     })
                     selected_ids.add(f['fund_id'])
                     return

        # Strategy A: High/Moderate Risk -> Large + Mid + Small
        if risk_profile not in ('low', 'conservative', 'safety'):
             # Slot 1: Large (50%)
             f_large = recommend(user_profile, category_filter='Large Cap', topk=1, df=df_features).to_dict('records')
             if not f_large: f_large = recommend(user_profile, category_filter='Index Fund', topk=1, df=df_features).to_dict('records')
             add_equity_slot(f_large, 0.50, "Core Anchor (Large Cap)")

             # Slot 2: Mid (30%)
             f_mid = recommend(user_profile, category_filter='Mid Cap', topk=2, df=df_features).to_dict('records')
             add_equity_slot(f_mid, 0.30, "Growth Booster (Mid Cap)")

             # Slot 3: Small (20%)
             f_small = recommend(user_profile, category_filter='Small Cap', topk=2, df=df_features).to_dict('records')
             add_equity_slot(f_small, 0.20, "High Alpha Potential (Small Cap)")

        # Strategy B: Low Risk -> Large + Flexi
        else:
             # Slot 1: Large (60%)
             f_large = recommend(user_profile, category_filter='Large Cap', topk=1, df=df_features).to_dict('records')
             if not f_large: f_large = recommend(user_profile, category_filter='Index Fund', topk=1, df=df_features).to_dict('records')
             add_equity_slot(f_large, 0.60, "Core Anchor (Large Cap)")

             # Slot 2: Flexi (40%)
             f_flexi = recommend(user_profile, category_filter='Flexi Cap', topk=2, df=df_features).to_dict('records')
             add_equity_slot(f_flexi, 0.40, "Stable Growth (Flexi Cap)")


    # --- DEBT STRATEGY ---
    if debt_budget > 0:
        # A. Safety: Liquid Fund (60% of Debt)
        safe_amt = debt_budget * 0.60
        safe_funds = recommend(user_profile, category_filter='Liquid', topk=1, df=df_features).to_dict('records')
        if safe_funds:
            f = safe_funds[0]
            portfolio.append({
                "fund_id": f['fund_id'], "fund_name": f.get('fund_name'), "category": f.get('category'),
                "asset_class": "Debt", "weight": round(safe_amt / total_amount, 4),
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
        if not yield_funds: 
             yield_funds = recommend(user_profile, category_filter='Debt', topk=1, df=df_features).to_dict('records')

        if yield_funds:
            f = yield_funds[0]
            portfolio.append({
                "fund_id": f['fund_id'], "fund_name": f.get('fund_name'), "category": f.get('category'),
                "asset_class": "Debt", "weight": round(yield_amt / total_amount, 4),
                "amount": round(yield_amt, 2), "score": round(f.get('TotalScore', 0), 2),
                "rationale": f"{yield_cat} for consistent yield (AUM > 1000Cr)",
                "metrics": {
                    "sharpe": round(f.get('sharpe', 0), 2),
                    "volatility": round(f.get('ann_vol', 0)*100, 1),
                    "returns": round(f.get('ann_return', 0)*100, 1)
                }
            })

    # 5. RECALCULATE WEIGHTS & ALLOCATION (Bottom-Up)
    # Ensure consistency: Sum of weights = 100%, Allocation based on actuals
    
    total_pk = sum(p['amount'] for p in portfolio) if portfolio else 0
    actual_allocation = {'Equity': 0.0, 'Debt': 0.0, 'Commodity': 0.0}
    
    if total_pk > 0:
        for p in portfolio:
            # 1. Update Weight
            p['weight'] = round(p['amount'] / total_pk, 4)
            
            # 2. Update Allocation
            # Thematic is Equity, Gold is Commodity
            ac = p['asset_class']
            
            # Subtype handling (internal tag correction)
            if 'Thematic' in ac:
                p['asset_class'] = 'Equity' # Roll up to Equity
                p['subtype'] = 'Thematic'
            elif 'Commodity' in ac or 'Gold' in ac:
                p['asset_class'] = 'Commodity'
            
            # Sum up
            if p['asset_class'] in actual_allocation:
                actual_allocation[p['asset_class']] += p['weight']
            else:
                # Fallback for unexpected types
                actual_allocation[p['asset_class']] = actual_allocation.get(p['asset_class'], 0) + p['weight']

    # Round allocation for display
    for k in actual_allocation:
        actual_allocation[k] = round(actual_allocation[k], 2)

    # 6. Generate Explanation
    # Construct a temporary structure to pass to reasoning engine
    temp_data = {"user_profile": user_profile, "allocation": actual_allocation}
    explanation = explain_portfolio(temp_data, market_status)

    # 7. Calculate Confidence Score
    stability_score = generate_confidence_score(portfolio, market_phase)

    # 8. Structure Output for UI
    # Explicitly filter by asset_class (now cleaned up)
    equity_schemes = [p for p in portfolio if p['asset_class'] == 'Equity']
    debt_schemes = [p for p in portfolio if p['asset_class'] == 'Debt']
    commodity_schemes = [p for p in portfolio if p['asset_class'] == 'Commodity']
    
    # We pass 'sections' dynamically. Frontend handles keys it knows (Equity, Debt)
    # But updated frontend also handles 'Commodities / Gold' via flat list filter.
    # To be safe and cleaner, we can pass commodities in sections if we updated frontend data contract.
    # The current frontend reads `data.portfolio` for flat filtering too.
    
    return {
        "user_profile": user_profile,
        "market_status": market_status,
        "allocation": actual_allocation, # NOW THE TRUTH
        "portfolio": portfolio, 
        "sections": {
            "equity": equity_schemes,
            "debt": debt_schemes,
            "commodity": commodity_schemes
        },
        "breakdown": {
            "lump_sum_total": total_pk,
            "sip_total": round(total_pk * 0.015, 0)
        },
        "explanation": explanation,
        "confidence_score": stability_score,
        "stability_label": "High" if stability_score > 80 else "Moderate" if stability_score > 50 else "Low"
    }


def get_alternatives(limit=5):
    """
    Returns alternative funds for each category to support 'What else?' queries.
    """
    df_features = load_latest_features(engine)
    alternatives = {}
    
    # 1. Categories to find alts for
    categories = ['Large Cap', 'Flexi Cap', 'Mid Cap', 'Liquid', 'Corporate Bond', 'Gilt']
    
    for cat in categories:
        # Get top 10 for this category
        recs = recommend({'risk_tolerance': 'High'}, category_filter=cat, topk=10, df=df_features)
        
        # Format for chat
        alts = []
        for _, row in recs.iterrows():
            alts.append({
                "fund_name": row['fund_name'],
                "score": round(row['TotalScore'] * 100, 0),
                "risk": "High" if row['ann_vol'] > 0.15 else "Low"
            })
        alternatives[cat] = alts
        
    return alternatives

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
