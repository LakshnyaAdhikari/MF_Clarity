def run_simulation(portfolio, scenario_id):
    """
    Replays the portfolio weights against known historical drawdowns.
    """
    scenarios = {
        "2008_CRASH": {"Equity": -0.55, "Debt": 0.08, "Liquid": 0.05}, # GFC
        "2020_COVID": {"Equity": -0.38, "Debt": 0.06, "Liquid": 0.04}, # Covid Crash
        "2022_RATES": {"Equity": -0.10, "Debt": -0.02, "Liquid": 0.03} # Rate Hike
    }
    
    if scenario_id not in scenarios:
        return {"error": "Unknown Scenario"}
        
    impact = scenarios[scenario_id]
    
    initial_val = sum(p['amount'] for p in portfolio)
    final_val = 0
    
    details = []
    
    for item in portfolio:
        asset = item['asset_class']
        # Map category to crude impact
        pct_change = impact.get(asset, 0)
        
        # Micro-adjustments
        if asset == 'Equity' and item.get('category') == 'Large Cap':
            pct_change += 0.05 # Large caps fell less
        elif asset == 'Equity' and item.get('category') == 'Small Cap':
            pct_change -= 0.10 # Small caps fell more
            
        new_amt = item['amount'] * (1 + pct_change)
        final_val += new_amt
        
        details.append({
            "fund": item['fund_name'],
            "original": item['amount'],
            "simulated": round(new_amt, 2),
            "change_pct": round(pct_change * 100, 1)
        })
        
    total_drop = (final_val - initial_val) / initial_val
    
    return {
        "scenario": scenario_id,
        "initial_value": round(initial_val, 2),
        "final_value": round(final_val, 2),
        "drawdown_pct": round(total_drop * 100, 2),
        "details": details
    }
