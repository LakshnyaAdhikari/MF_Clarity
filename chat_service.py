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
    elif "hello" in msg or "hi" in msg:
        return "GREETING"
    else:
        return "GENERAL_QA"

def handle_chat_message(user_id, message, user_profile_dict=None):
    intent = classify_intent(message)
    
    if intent == "GREETING":
        return {
            "response": "Hello! I am your AI Investment Assistant. I can explain your portfolio options, compare funds, or simulate market scenarios. How can I help?",
            "action": None
        }
        
    elif intent == "EXPLAIN_DECISION":
        # Check if we have a recent portfolio
        # For MVP, we'll re-generate the latest reasoning or just generalize
        return {
            "response": "I selected this portfolio based on your Risk Tolerance and the current 'Overheated' market phase. The high debt allocation is designed to protect your capital.",
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
        
    else:
        return {
            "response": "I see. While I focus on investment strategy, could you clarify? You can ask me 'Why did you pick this?' or 'Run a simulation'.",
            "action": None
        }
