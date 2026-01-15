from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import os
from typing import Optional, List, Dict, Any

from portfolio_service import generate_portfolio
from score_service import load_latest_features, engine
import pandas as pd

app = FastAPI(title="MF-Clarity API", version="1.0")

class UserProfile(BaseModel):
    amount: float = Field(..., gt=0, description="Investment Amount")
    horizon_years: float = Field(..., gt=0, description="Investment Horizon in Years")
    risk_tolerance: str = Field(..., description="Risk Tolerance: Low, Moderate, High")
    goal: Optional[str] = Field(None, description="Investment Goal e.g. Wealth, Retirement")

class PortfolioItem(BaseModel):
    fund_id: str
    fund_name: Optional[str]
    category: Optional[str]
    asset_class: str
    weight: float
    amount: float
    score: float
    rationale: str

class RecommendationResponse(BaseModel):
    user_profile: Dict[str, Any]
    allocation: Dict[str, float]
    portfolio: List[PortfolioItem]

@app.get("/")
def health_check():
    return {"status": "ok", "service": "MF-Clarity Engine"}

@app.post("/recommend", response_model=RecommendationResponse)
def get_recommendation(profile: UserProfile):
    try:
        # Convert pydantic model to dict
        user_dict = profile.model_dump()
        result = generate_portfolio(user_dict)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/funds")
def list_funds():
    try:
        with engine.connect() as conn:
            # Simple query to list funds
            from sqlalchemy import text
            res = conn.execute(text("SELECT fund_id, fund_name, category FROM funds LIMIT 100"))
            funds = [dict(row._mapping) for row in res]
            return funds
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
