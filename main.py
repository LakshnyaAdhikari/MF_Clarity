from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
import uvicorn
import os
import json
from typing import Optional, List, Dict, Any
from sqlalchemy import text
from datetime import timedelta

from portfolio_service import generate_portfolio
from score_service import load_latest_features, engine
from auth_service import (
    Token, verify_password, get_password_hash, create_access_token, decode_token, ACCESS_TOKEN_EXPIRE_MINUTES
)
from memory_service import save_portfolio_snapshot, log_interaction, get_user_risk_score

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MF-Clarity API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- DATA MODELS ---

class UserRegister(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    amount: float = Field(..., gt=0, description="Investment Amount")
    horizon_years: float = Field(..., gt=0, description="Investment Horizon in Years")
    risk_tolerance: str = Field(..., description="Risk Tolerance: Low, Moderate, High")
    goal: Optional[str] = Field(None, description="Investment Goal e.g. Wealth, Retirement")
    age: Optional[int] = Field(None, description="User Age")
    current_investments: Optional[float] = Field(0.0, description="Existing Investments")

class PortfolioItem(BaseModel):
    fund_id: str
    fund_name: Optional[str]
    category: Optional[str]
    asset_class: str
    weight: float
    amount: float
    score: float
    rationale: str

class RecommendationsBreakdown(BaseModel):
    lump_sum_total: float
    sip_total: float

class RecommendationResponse(BaseModel):
    user_profile: Dict[str, Any]
    market_status: Dict[str, Any]
    allocation: Dict[str, float]
    portfolio: List[PortfolioItem]
    sections: Optional[Dict[str, List[PortfolioItem]]] = None
    breakdown: Optional[RecommendationsBreakdown] = None
    explanation: str
    confidence_score: Optional[float] = 80.0
    stability_label: Optional[str] = "High"

# --- DEPENDENCIES ---

def get_current_user(token: str = Depends(oauth2_scheme)):
    email = decode_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email

# Helper to get user ID
def get_user_id(email: str):
    with engine.connect() as conn:
        res = conn.execute(text("SELECT id FROM users WHERE email = :e"), {'e': email}).fetchone()
        return res[0] if res else None

# --- AUTH ROUTES ---

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserRegister):
    hashed_pw = get_password_hash(user.password)
    try:
        with engine.begin() as conn:
            # Check exist
            exists = conn.execute(text("SELECT id FROM users WHERE email = :e"), {'e': user.email}).fetchone()
            if exists:
                raise HTTPException(status_code=400, detail="Email already registered")
            
            # Insert User
            res = conn.execute(
                text("INSERT INTO users (email, password_hash) VALUES (:e, :p) RETURNING id"),
                {'e': user.email, 'p': hashed_pw}
            )
            user_id = res.fetchone()[0]
            
            # Create Profile Placeholder
            conn.execute(text("INSERT INTO user_profiles (user_id) VALUES (:uid)"), {'uid': user_id})
            
    except Exception as e:
        if "Email already registered" in str(e): raise e
        raise HTTPException(status_code=500, detail=str(e))
    return {"message": "User created successfully"}

@app.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # 1. Fetch User from DB
    try:
        with engine.connect() as conn:
            user = conn.execute(text("SELECT email, password_hash FROM users WHERE email = :e"), {'e': form_data.username}).fetchone()
    except Exception as e:
         raise HTTPException(status_code=500, detail="Database error")

    # 2. Authenticate
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Create Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- APP ROUTES ---

@app.post("/recommend", response_model=RecommendationResponse)
def get_recommendation(profile: UserProfile, current_user_email: str = Depends(get_current_user)):
    try:
        # Convert pydantic model to dict
        user_dict = profile.model_dump()
        
        # PERSISTENCE READ (Memory Layer)
        user_id = get_user_id(current_user_email)
        if user_id:
            # Inject historical risk score if exists
            hist_score = get_user_risk_score(user_id)
            if hist_score is not None:
                user_dict['historic_risk_score'] = float(hist_score)

        # Generator Portfolio
        result = generate_portfolio(user_dict)
        
        # PERSISTENCE WRITE (Memory Layer)
        if user_id:
            # Save Snapshot
            save_portfolio_snapshot(
                user_id, 
                result['portfolio'], 
                result['allocation'], 
                result.get('market_status', {}).get('phase', 'UNKNOWN')
            )
            # Log Interaction
            log_interaction(user_id, 'generate_portfolio', details=result['allocation'])
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from chat_service import handle_chat_message

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[int] = None

@app.post("/chat/message")
def chat_endpoint(request: ChatRequest, current_user_email: Optional[str] = Depends(get_current_user)):
    user_id = None
    if current_user_email:
        user_id = get_user_id(current_user_email)
    
    # Logic to fetch profile if needed
    # For now, pass basic context
    response = handle_chat_message(user_id, request.message)
    return response

from simulation_engine import run_simulation

class SimulationRequest(BaseModel):
    portfolio: List[PortfolioItem]
    scenario_id: str

@app.post("/simulate")
def simulate_endpoint(req: SimulationRequest):
    # Convert Pydantic list to dict list
    port_list = [p.dict() for p in req.portfolio]
    return run_simulation(port_list, req.scenario_id)

@app.get("/funds")
def list_funds(current_user: str = Depends(get_current_user)):
    try:
        with engine.connect() as conn:
            # Simple query to list funds
            res = conn.execute(text("SELECT fund_id, fund_name, category FROM funds LIMIT 100"))
            funds = [dict(row._mapping) for row in res]
            return funds
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
