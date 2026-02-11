Intelligent Mutual Fund Portfolio Recommendation Platform
Overview

This project is a data-driven mutual fund recommendation system that constructs personalized portfolios based on user goals, risk tolerance, and time horizon. The platform prioritizes deterministic financial logic, explainability, and consistency, while using AI for personalization and conversational insights.

Features

Constraint-based fund filtering (AUM thresholds, category filters, plan type control)

Consistency-driven ranking using volatility, drawdowns, and risk-adjusted return metrics

Dynamic asset allocation across Equity, Debt, and Commodity funds

Personalized portfolio construction based on user risk and investment horizon

Explainable recommendation logic with fund-level reasoning

Conversational interface for portfolio queries and fund comparisons

Tech Stack

Backend: Python (FastAPI/Flask), modular portfolio engine
Frontend: Web-based dashboard (React/Next.js or similar)
Database: Fund metrics database + user profile storage
ML (optional layer): Logistic Regression / Gradient Boosting for user preference modeling
LLM Layer: Retrieval-Augmented Generation for explanations and contextual chatbot responses

How It Works

Fund data is ingested from trusted sources and stored with structured metadata.

Hard constraints filter out unsuitable funds.

A consistency-based scoring model ranks eligible funds.

Asset allocation is computed and portfolios are constructed.

The chatbot explains recommendations and supports interactive queries.

Goals

The system is designed to provide transparent, explainable, and risk-aware investment recommendations, with AI enhancing user experience without replacing financial logic.
