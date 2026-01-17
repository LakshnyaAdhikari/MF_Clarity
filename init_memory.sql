-- Add memory columns to profiles
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS risk_score NUMERIC(5,2);
ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS behavior_tags JSONB DEFAULT '{}';

-- Table to store accepted/generated portfolios (Snapshots)
CREATE TABLE IF NOT EXISTS user_portfolios (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    portfolio_data JSONB NOT NULL, -- Full JSON of the recommendation
    allocation_equity NUMERIC(5,2),
    allocation_debt NUMERIC(5,2),
    confidence_score NUMERIC(5,2),
    market_phase VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to verify User Interactions (Feedback Loop)
CREATE TABLE IF NOT EXISTS interaction_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action_type VARCHAR(50), -- 'generate', 'accept', 'reject', 'click_fund'
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
