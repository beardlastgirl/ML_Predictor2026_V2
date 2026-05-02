# ML_Predictor2026_V2 — Project

## What It Is

Football match prediction system for Liga Profesional Argentina (2 championships/year). Combines Poisson distribution goal modeling with CatBoost/LightGBM gradient boosting to predict match outcomes (1X2) and scorelines.

## Current Status

Operational. Apertura 2026 regular season complete. Playoffs pending (format TBD).

## Core Value

Weekly scoreline predictions for Liga Profesional Argentina fixtures, for entertainment purposes.

## Architecture

```
Scrapers → Local files (CSV/JSON/TXT)
         ↓
   src/pipeline.py
         ↓
Features → Train/Validate → Predict → PrediccionFechaXX.txt
```

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Poisson + ML ensemble | Poisson for calibrated baseline; ML for pattern recognition |
| CatBoost/LightGBM | Best performance on tabular data with categorical features |
| floor(xG) for scorelines | round() collapses Liga Profesional xG values to 1 |
| Time-series CV | Prevents look-ahead bias in sports data |
| 60% ML + 40% Poisson | ML captures nuance; Poisson prevents extreme predictions |

## Out of Scope

- Real-time betting integration
- Multi-league expansion
- Deep learning models
