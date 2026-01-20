def generate_confidence_score(portfolio, market_phase):
    """
    Calculates a 0-100 stability score based on:
    1. Market Phase Alignment (e.g. High Debt in Overheated market = Good)
    2. Fund quality (Average Scores)
    3. Diversification
    """
    score = 70.0 # Base score
    
    # 1. Market Phase Adjustment
    equity_weight = sum(p['weight'] for p in portfolio if p['asset_class'] == 'Equity')
    debt_weight = sum(p['weight'] for p in portfolio if p['asset_class'] == 'Debt')
    
    if market_phase == 'OVERHEATED':
        # Reward caution
        if debt_weight >= 0.4: score += 10
        if equity_weight > 0.6: score -= 10
    elif market_phase == 'UNDERVALUED':
        # Reward aggression
        if equity_weight >= 0.6: score += 10
    
    # 2. Fund Quality
    avg_fund_score = sum(p.get('score', 50) for p in portfolio) / len(portfolio) if portfolio else 0
    # Normalize fund score to add up to 20 points
    score += (avg_fund_score / 100.0) * 20
    
    # Cap at 99
    return min(99.0, round(score, 1))

def generate_market_context_text(market_status):
    phase = market_status.get('phase', 'NEUTRAL')
    regime = market_status.get('regime', 'Normal')
    
    context = ""
    # Regime Context
    if regime == "Volatile":
        context += "The market is currently experiencing **High Volatility (>20%)**. "
    elif regime == "Stable":
        context += "The market is currently **Stable (<10% Volatility)**. "
        
    # Phase Context
    if phase == "OVERHEATED":
        context += "Valuations appear **Overheated**. To protect your capital from potential corrections, we have increased allocation to Debt/Liquid funds."
    elif phase == "UNDERVALUED":
        context += "Valuations are **Attractive**. We have maximized Equity allocation to capture potential upside."
    else:
        context += "Valuations are **Fair**. We have maintained a standard allocation aligned with your goals."
        
    return context

def generate_allocation_text(allocation, user_profile, age):
    equity_pct = allocation.get('Equity', 0) * 100
    debt_pct = allocation.get('Debt', 0) * 100
    
    risk = user_profile.get('risk_tolerance', 'Moderate')
    horizon = user_profile.get('horizon_years', 5)
    
    reasons = []
    
    # Age factor
    if age and age < 40 and equity_pct > 60:
         reasons.append(f"At {age} years old, you have a long runway to compound wealth, justifying a higher equity exposure.")
    elif age and age > 50 and debt_pct > 40:
         reasons.append(f"At {age}, preserving your accumulated capital is key, hence the significant debt cushion.")
         
    # Horizon factor
    if horizon > 7 and equity_pct > 60:
        reasons.append("Your long investment horizon allow you to ride out short-term market volatility for higher returns.")
    elif horizon < 3 and debt_pct > 60:
        reasons.append("Since you need the money soon (within 3 years), we prioritized stability over aggressive growth.")
        
    # Risk factor
    if risk == 'High' and equity_pct > 70:
        reasons.append("Reflecting your high risk tolerance, this portfolio is aggressively positioned for maximum growth.")
    elif risk == 'Low' and debt_pct > 70:
        reasons.append("We respected your preference for safety by keeping exposure to volatile stocks minimal.")
        
    return " ".join(reasons)

def explain_portfolio(portfolio_data, market_status):
    """
    Generates a cohesive paragraph explaining the request.
    """
    profile = portfolio_data['user_profile']
    alloc = portfolio_data['allocation']
    phase = market_status.get('phase', 'NEUTRAL')
    
    age = profile.get('age')
    
    # 1. Market Context
    market_text = generate_market_context_text(market_status)
    
    # 2. Allocation Logic
    alloc_text = generate_allocation_text(alloc, profile, age)
    
    # 3. Strategy Summary
    equity_int = int(alloc.get('Equity', 0) * 100)
    debt_int = int(alloc.get('Debt', 0) * 100)
    
    intro = f"We have designed a **{equity_int}% Equity / {debt_int}% Debt** portfolio for you."
    
    final_text = f"{intro}\n\n**Why this split?** {alloc_text}\n\n**Market Sensitivity:** {market_text}"
    
    return final_text
