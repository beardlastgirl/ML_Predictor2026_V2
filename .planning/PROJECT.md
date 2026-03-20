# ML_Predictor2026_V2 - Enhanced Prediction System

## What This Is

A modular, agent-based football prediction system for Argentine leagues (Liga Profesional Argentina). It combines statistical modeling (Poisson distribution for goal counts) with machine learning (CatBoost/LightGBM) to predict match outcomes and scorelines. The system is built for accuracy, leveraging Elo ratings, advanced features, and a clean data pipeline.

## Core Value

Deliver match outcome (1X2) and scoreline predictions that outperform naive baselines with realistic probability distributions and data-driven insights.

## Current Milestone: v2.0 Initialization & Alignment

**Goal:** Re-initialize the project foundation to ensure a clean path for engine calibration, data quality improvements, and agent architecture expansion.

**Target features:**
- Betting odds integration (closing odds for calibration)
- Time-series validation (preventing data leakage)
- Poisson calibration (realistic scoreline spread)
- Coordinator-Worker agent architecture
- Advanced feature engineering (form, xG, congestion)

## Requirements

### Validated

- ✓ Modular Architecture (`src/` with clear layering) — existing
- ✓ Statistical Engine (Elo, Poisson implementations) — existing
- ✓ Multi-source Scraping (FBref, Sofascore, TyC, etc.) — existing
- ✓ Orchestrated Pipeline (`src/pipeline.py`) — existing

### Active

- [ ] **DATA-01**: Integrate betting odds as features and calibration baselines
- [ ] **DATA-02**: Improve data alignment and leakage prevention (time-series)
- [ ] **POISS-01**: Calibrate Poisson model for realistic scoreline distributions
- [ ] **MODEL-01**: Implement baseline performance comparisons (naive, bookie)
- [ ] **AGENT-01**: Evolve to Coordinator-Worker agent architecture

### Out of Scope

- Real-time betting integration (focus on batch prediction)
- Multi-league expansion (focused on Argentina)
- Deep learning models (maintaining tree-based + Poisson)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Modular Pipeline | Separation of concerns, testability, and easier maintenance | — Existing |
| Poisson Modeling | Better scoreline probability estimation than direct classification | — Existing |
| CatBoost/LightGBM | Superior performance on tabular data with categorical features | — Existing |
| Time-series Validation | Crucial for avoiding look-ahead bias in sports data | — Planned |

---
*Last updated: 2026-03-19 after initialization*
