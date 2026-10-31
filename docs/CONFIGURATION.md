# ML_Predictor2026_V2 — Configuration

<!-- GSD Configuration -->
<!-- VERIFY: Hyperparameters verified against src/config.py; infrastructure claims verified against repository -->

## Configuration Location
All hyperparameters are centralized in `src/config.py`. Never hardcode values in functions.

## Active Hyperparameters

```python
BASE_ELO = 1500              # Starting Elo for new/promoted teams
K_FACTOR = 30                # Elo change per match
HOME_ADVANTAGE = 65          # Elo bonus for home team
BASE_GOAL_RATE = 1.11        # NaN fallback for new teams: (1.26 + 0.96) / 2
HOME_BOOST = 1.15            # Home team xG multiplier
POISSON_DRAW_ADJUSTMENT = 1.11  # Calibrated draw adjustment
ML_POISSON_BLEND_RATIO = 0.6  # DEPRECATED (Poisson features feed directly)
TRAILING_WINDOW = 8          # Last 8 matches for form statistics
MODEL_TYPE = "catboost"      # Override via ML_PREDICTOR_MODEL env var
```

## Model Selection
Default model: `catboost` (from `src/config.py`). Alternative lightgbm via environment override, but CatBoost is the verified default based on `type(result.model).__name__`.

## Scraping / Data Sources
Configured in `AGENTS.md` and source modules:
- `scrape_tyc.py` (manual fixtures)
- `scrape_stats_manual.py` / `scrape_stats_enhanced.py` (FBref via CDP)
- `scrape_sofascore_apify.py` (API-based standings)
- `scrape_footystats.py` (blocked 403 — requires manual CDP or proxy)

## Security / Secret Scan
No hardcoded secrets in `src/`. `scrape_sofascore_apify.py` uses `.env` for Apify tokens (not tracked). Verify `.env.example` exists but `.env` is `.gitignore`-d.

## Deployment Configuration
No deploy config (`Dockerfile`, `vercel.json`, `netlify.toml`, `Procfile`) found in this repository. `docs/CONFIGURATION.md` claims verified only from repository contents; deploy claims would require manual verification (`<!-- VERIFY: ... -->` markers not required here since no deploy claims made beyond absence confirmation).
