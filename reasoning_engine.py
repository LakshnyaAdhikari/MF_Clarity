def generate_market_context_text(market_phase):
    if market_phase == "OVERHEATED":
        return "The market currently appears overheated (trading significantly above its long-term trend). To protect your capital from potential corrections, we have slightly increased the allocation towards safer Debt/Liquid funds."
    elif market_phase == "UNDERVALUED":
        return "The market valuations are attractive right now. We have maximized your Equity allocation to help you capture potential upside as the market recovers."
    else:
        return "Market valuations are currently fair. We have maintained a standard allocation aligned with your long-term goals."

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
    market_text = generate_market_context_text(phase)
    
    # 2. Allocation Logic
    alloc_text = generate_allocation_text(alloc, profile, age)
    
    # 3. Strategy Summary
    equity_int = int(alloc.get('Equity', 0) * 100)
    debt_int = int(alloc.get('Debt', 0) * 100)
    
    intro = f"We have designed a **{equity_int}% Equity / {debt_int}% Debt** portfolio for you."
    
    final_text = f"{intro}\n\n**Why this split?** {alloc_text}\n\n**Market Sensitivity:** {market_text}"
    
    return final_text
