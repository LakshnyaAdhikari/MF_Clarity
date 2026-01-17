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
        
        # Calculate Moving Averages
        sma_200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        sma_50 = hist['Close'].rolling(window=50).mean().iloc[-1]
        
        # Simple Logic for Phase
        # PE data is hard to get reliably free from yfinance, so we use Price vs SMA Trend as proxy along with momentum
        
        # If Current Price is > 15% above 200 SMA -> Potentially Overheated
        deviation_200 = (current_price - sma_200) / sma_200
        
        phase = "NEUTRAL"
        details = f"Market is fair. Nifty @ {int(current_price)}."
        
        if deviation_200 > 0.15:
            phase = "OVERHEATED"
            details = f"Market is running hot ({int(deviation_200*100)}% above 200 SMA). Caution advised."
        elif deviation_200 < -0.10:
            phase = "UNDERVALUED"
            details = f"Market is corrected ({int(abs(deviation_200)*100)}% below 200 SMA). Good time to accumulate."
        
        return {
            "phase": phase,
            "current_price": current_price,
            "sma_200": sma_200 if not pd.isna(sma_200) else current_price,
            "details": details
        }
        
    except Exception as e:
        print(f"Error fetching market data: {e}")
        return {"phase": "NEUTRAL", "details": "Error analyzing market, defaulted to Neutral."}

if __name__ == "__main__":
    print(get_market_status())
