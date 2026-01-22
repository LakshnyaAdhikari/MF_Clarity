from memory_service import get_user_risk_score
from portfolio_service import generate_portfolio

def classify_intent(message):
    msg = message.lower()
    if "why" in msg or "reason" in msg:
        return "EXPLAIN_DECISION"
    elif "compare" in msg or "better" in msg:
        return "COMPARE_FUNDS"
    elif "simulate" in msg or "crash" in msg or "what if" in msg:
        return "SIMULATE_SCENARIO"
    elif "where" in msg or "invest" in msg or "list" in msg or "portfolio" in msg:
        return "SHOW_PORTFOLIO"
    elif "alternative" in msg or "replace" in msg or "option" in msg:
        return "ALTERNATIVES"
    elif "hello" in msg or msg.strip() == "hi" or " hi " in msg:
        return "GREETING"
    else:
        return "GENERAL_QA"

def handle_chat_message(user_id, message, user_profile_dict=None, context=None):
    intent = classify_intent(message)
    
    # 1. Context-Aware Explanation
    if context and context.get('funds'):
        funds = context['funds']
        if intent == "EXPLAIN_DECISION" or "why" in message.lower() or "explain" in message.lower():
            # Build specific explanation
            details = []
            for f in funds:
                metrics = f.get('metrics', {})
                details.append(f"• **{f['fund_name']}**: Selected for its {f.get('rationale')} (Sharpe: {metrics.get('sharpe', 'N/A')})")
            
            response_text = "Here is the specific reasoning for your portfolio:\n\n" + "\n".join(details)
            return {"response": response_text, "action": None}

    if intent == "GREETING":
        return {
            "response": "Hello! I am your AI Investment Assistant. I can explain your portfolio options, compare funds, or simulate market scenarios. How can I help?",
            "action": None
        }
        
    elif intent == "EXPLAIN_DECISION":
        return {
            "response": "I selected this portfolio based on your Risk Tolerance and the current Market Phase. I prioritized funds with high Sharpe Ratios and low Expense Ratios to maximize your risk-adjusted returns.",
            "action": "view_portfolio"
        }
    
    elif intent == "SHOW_PORTFOLIO":
         return {
            "response": "Based on your profile, I recommend a mix of high-growth Equity funds and stable Debt funds. You can see the specific scheme names like 'Axis Bluechip' or 'HDFC Top 100' in the dashboard list on the right. Would you like me to explain why I chose them?",
            "action": "view_portfolio"
        }
        
    elif intent == "COMPARE_FUNDS":
        return {
            "response": "I can compare funds. For example, comparing HDFC Index Fund vs Axis Bluechip -> HDFC Index Fund has lower expense ratio (0.2%) compared to Axis (0.5%), making it better for long term compounding.",
            "action": "compare_view"
        }

    elif intent == "SIMULATE_SCENARIO":
        return {
            "response": "Run a simulation? I can stress-test your portfolio against the 2008 Crash or 2020 Covid Pandemic.",
            "action": "trigger_simulation"
        }

    elif intent == "ALTERNATIVES":
        from portfolio_service import get_alternatives
        alts = get_alternatives()
        
        # Simple heuristic: Check which category fits the context/message
        target_cat = "Corporate Bond" # Default for the user's specific query
        if "liquid" in message.lower(): target_cat = "Liquid"
        elif "equity" in message.lower() or "large" in message.lower(): target_cat = "Large Cap"
        elif "mid" in message.lower(): target_cat = "Mid Cap"
        elif "flexi" in message.lower(): target_cat = "Flexi Cap"
        
        # Format Response
        items = alts.get(target_cat, [])[:5]
        txt = f"Here are 5 alternatives for **{target_cat}** schemes (scored 0-100):\n\n"
        for i, fund in enumerate(items, 1):
            txt += f"{i}. **{fund['fund_name']}** (Score: {fund['score']})\n"
            
        return { "response": txt, "action": "view_list" }
        
    else:
        # Fallback for specific queries the rule-engine misses
        if "alpha" in message.lower():
             return {
                "response": "'Alpha Equity' was a placeholder category. I have updated the list to show REAL funds now. Please check the dashboard!",
                "action": "view_portfolio"
            }
        
            
        return {
            "response": "I understand you're asking about investment details. Could you check the 'Recommended Funds' section on the dashboard? It lists the specific schemes I've selected for you.",
            "action": None
        }
