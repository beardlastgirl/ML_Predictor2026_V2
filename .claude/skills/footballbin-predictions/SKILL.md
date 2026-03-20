---
name: footballbin-predictions
description: Get AI-powered match predictions for Liga Profesional Argentina using Poisson distribution and machine learning (LightGBM/CatBoost). Provides expected goals (xG), match outcomes, and confidence levels.
metadata: {"clawdbot":{"emoji":"soccer","requires":{"bins":["python"],"files":["scripts/*","../../main.py","../../src/*"]}}}
---

# Liga Profesional Argentina Match Predictions

Get AI-powered predictions for Liga Profesional Argentina matches using the local ML_Predictor2026_V2 prediction system.

## Quick Start

Run `scripts/liga_argentina.sh` with the following commands:

### Get predictions for current fixtures
```bash
scripts/liga_argentina.sh predict
```

### Run full pipeline (update data + predict)
```bash
scripts/liga_argentina.sh run
```

### Show recent results
```bash
scripts/liga_argentina.sh results
```

### Show model statistics
```bash
scripts/liga_argentina.sh stats
```

## Commands

| Command | Description |
|---------|-------------|
| `predict` | Generate predictions from existing data |
| `run` | Run full pipeline: scrape data + predict |
| `results` | Show most recent prediction results |
| `stats` | Show model accuracy and performance metrics |
| `help` | Display usage information |

## Prediction Output

Each prediction includes:
- **Match**: Home team vs Away team
- **Score Prediction**: Predicted scoreline (e.g., "2-1")
- **Outcome**: Home Win, Draw, or Away Win
- **xG**: Expected goals for home and away teams
- **Confidence**: High/Medium/Low based on Elo difference and Poisson probability

## Data Sources

The system uses multiple data sources:
1. **Historical Data**: `data/ARG.csv` (football-data.co.uk)
2. **Current Standings**: Sofascore via Apify
3. **Fixtures**: TyC Sports
4. **Squad Stats**: FBref

## Model Details

- **Algorithm**: CatBoost (default) or LightGBM
- **Features**: 21 features including Poisson-derived probabilities
- **Time-Series CV Accuracy**: ~0.421
- **Poisson Integration**: Uses Poisson distribution for goal modeling

## Configuration

The skill uses the following configuration from the project:
- Elo rating system with home advantage
- 8-match trailing window for form calculation
- Base goal rate: 1.89 (Argentine league average)

## Requirements

- Python 3.8+
- Virtual environment: `.venv` at project root
- Dependencies: See `requirements.txt`

## File Structure

```
ML_Predictor2026_V2/
├── main.py                    # Main prediction engine
├── src/
│   ├── config.py             # Elo, Poisson, ML parameters
│   ├── model_engine.py       # ML model and prediction logic
│   ├── stats_engine.py       # Elo and Poisson mathematics
│   ├── features.py           # Feature engineering
│   └── data_processing.py    # Data loading and normalization
├── data/ARG.csv              # Historical match data
├── partidos.txt              # Current fixtures
└── src/sofascore_stats.json  # Current standings
```

## Security

- All data processing happens locally
- No external API calls (except for optional data scraping)
- No user data collected or stored
- Read-only predictions for entertainment purposes
