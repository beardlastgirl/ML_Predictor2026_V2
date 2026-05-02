# ML_Predictor2026_V2 - CLAUDE.md

## Project Overview

Football match prediction system for Liga Profesional Argentina (2 championships/year: Apertura / Clausura). Combines Poisson distribution goal modeling with CatBoost/LightGBM gradient boosting.

## Quick Start

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point — calls `run_pipeline()` |
| `src/pipeline.py` | Orchestrates load → features → train → predict |
| `src/config.py` | All hyperparameters (edit here only) |
| `src/stats_engine.py` | Elo ratings, Poisson xG, Shin method |
| `src/model_engine.py` | CatBoost/LightGBM + `_calculate_hybrid_goals()` |
| `src/features.py` | Trailing stats with exponential decay |
| `src/data_processing.py` | Team name normalization, fixture parsing |
| `src/validation.py` | Pre-flight data validation |
| `src/scraper_utils.py` | `@resilient_scraper` decorator, CAPTCHA detection |
| `Partidos.txt` | Current round fixtures (update each week) |
| `Glossary.txt` | Team name mappings across all sources |
| `data/ARG.csv` | Historical match data (auto-updated from football-data.co.uk) |

## Current Metrics (May 2026)

- Model: CatBoost (default)
- CV Accuracy: ~35% (+/- 6%) on 3-class problem
- Log-Loss: ~1.20 (model) vs 1.077 (naive) vs ~1.005 (bookie)
- Features: 24
- Training samples: ~6,200 matches

## Configuration (src/config.py)

```python
BASE_ELO = 1500          # Starting Elo for new/promoted teams
K_FACTOR = 30            # Elo change per match
HOME_ADVANTAGE = 65      # Elo bonus for home team
BASE_GOAL_RATE = 2.22    # NaN fallback for new teams (not used in xG formula)
HOME_BOOST = 1.15        # Home team xG multiplier
POISSON_DRAW_ADJUSTMENT = 0.85  # Reduces raw Poisson draw bias
ML_POISSON_BLEND_RATIO = 0.6    # 60% ML + 40% Poisson
TRAILING_WINDOW = 8      # Last N matches for form stats
MODEL_TYPE = "catboost"  # Override via ML_PREDICTOR_MODEL env var
```

## Scoreline Logic (_calculate_hybrid_goals)

Uses `floor(xG)` as the base (Poisson mode, not round), then applies ML directional adjustment when `max_prob >= 0.35`:
- Home win predicted + p_h >= p_d,p_a → ensure home > away; bump if p_h >= 0.50
- Away win predicted → symmetric
- Draw predicted → equalise at max(floor_h, floor_a)

## Data Sources

| Source | File | Scraper |
|--------|------|---------|
| football-data.co.uk | `data/ARG.csv` | Auto (DataIngestor) |
| TyC Sports | `Partidos.txt` | `scrape_tyc.py --url URL --fecha LABEL` |
| FBref | `src/fbref_*.csv` | `scrape_stats_enhanced.py` |
| FootyStats | `src/footystats_*.csv` | `scrape_footystats.py` |
| Sofascore | `src/sofascore_stats.json` | `scrape_sofascore_apify.py` |
| PDF reports | `Reporte/{year}/Resumen F{round}.pdf` | `parse_reporte_pdfs.py` |

## Season Start Protocol

1. Download latest `ARG.csv`
2. Refresh Sofascore standings
3. Check `[SEASON CHECK]` warnings for new/promoted teams
4. Add new team name variants to `Glossary.txt`
5. Update `Partidos.txt` with first round fixtures

## Calibration Tool

To validate Poisson calibration against historical data:

```python
from src.stats_engine import calibrate_poisson_params
from src.pipeline import load_data, build_features
_, _, matches, _, _, _ = load_data()
matches_feat, _ = build_features(matches)
print(calibrate_poisson_params(matches_feat.dropna(subset=['Home_Elo'])))
```

## Development Guidelines

- NO ANSI colors, icons, or emojis in output
- Plain ASCII only
- All hyperparameters in `src/config.py` — never hardcode in functions
- Run `python -m pytest tests/ -v` after any change (expect 34+ passing)
- Model name in summary reads from `type(result.model).__name__`
