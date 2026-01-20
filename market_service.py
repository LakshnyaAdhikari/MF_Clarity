import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

MARKET_INDEX_SYMBOL = "^NSEI" # Nifty 50

def get_market_status():
    """
    Analyzes the market phase based on Nifty 50 Trends.
    Returns: dict with 'phase' (OVERHEATED, NEUTRAL, UNDERVALUED) and 'details'.
    """
    try:
        # Fetch last 1 year data
        ticker = yf.Ticker(MARKET_INDEX_SYMBOL)
        hist = ticker.history(period="1y")
        
        if hist.empty:
            return {"phase": "NEUTRAL", "details": "Market data unavailable, assuming Neutral."}
            
        current_price = hist['Close'].iloc[-1]
        
        # Calculate Daily Returns
        hist['returns'] = hist['Close'].pct_change()
        
        # Calculate Volatility (30-day annualized)
        current_vol = hist['returns'].tail(30).std() * (252 ** 0.5) * 100
        
        # Regime Detection
        regime = "Normal"
        if current_vol > 20: regime = "Volatile"
        elif current_vol < 10: regime = "Stable"
        
        # Simple Logic for Phase
        deviation_200 = (current_price - sma_200) / sma_200
        
        phase = "NEUTRAL"
        phase_label = "Neutral"
        
        if deviation_200 > 0.15:
            phase = "OVERHEATED"
            phase_label = "Overheated"
        elif deviation_200 < -0.10:
            phase = "UNDERVALUED"
            phase_label = "Undervalued"
            
        details = f"{regime} {phase_label} Market. Nifty @ {int(current_price)}. Volatility: {int(current_vol)}%."
        
        return {
            "phase": phase,
            "regime": regime,
            "volatility": round(current_vol, 1),
            "current_price": current_price,
            "sma_200": sma_200 if not pd.isna(sma_200) else current_price,
            "details": details
        }
        
    except Exception as e:
        print(f"Error fetching market data: {e}")
        return {"phase": "NEUTRAL", "details": "Error analyzing market, defaulted to Neutral."}

if __name__ == "__main__":
    print(get_market_status())
