# ML_Predictor2026_V2 — Development

<!-- GSD Configuration -->

## Development Setup

1. Create `.venv`: `python -m venv .venv`
2. Activate: `.\.venv\Scripts\Activate.ps1`
3. Install: `pip install -r requirements.txt`

## Running Tests

```powershell
python -m pytest tests/ -v
```
Expected: 131+ passing. Key test modules:
- `tests/test_main.py` (29 unit tests)
- `tests/test_pipeline_integration.py` (19 integration tests)
- `tests/test_golden_math.py` (17 golden math regression tests)
- `tests/test_scraper_utils.py` (15 scraper tests)
- `tests/test_leakage.py`, `tests/test_temporal_ordering.py`, etc.

## Hyperparameter Changes
Edit `src/config.py` only. Never hardcode in functions. All hyperparameters are centralized there.

## Key Source Files for Development

| File | Purpose |
|---|---|
| `main.py` | Entry point (`run_pipeline()`) |
| `src/pipeline.py` | Orchestration: load → features → train → predict |
| `src/model_engine.py` | CatBoost + `_calculate_hybrid_goals()` |
| `src/stats_engine.py` | Elo ratings, Poisson xG, Shin method |
| `src/features.py` | Trailing stats (8-match exponential decay) |
| `src/config.py` | Hyperparameters |
| `src/data_processing.py` | Team normalization (`Glossary.txt`) |
| `src/validation.py` | Pre-flight data validation |

## Coding Guidelines (from AGENTS.md)
- No ANSI colors, icons, or emojis in output.
- Plain ASCII only.
- All hyperparameters in `src/config.py` — never hardcode.

## Dependency Auditing
```powershell
pip-audit -r dev-requirements.txt
```

## Scraping Development
- `scrape_stats_manual.py` uses Chrome Remote Debugging Protocol (CDP) — requires manual CAPTCHA solving. The script launches Chrome with `--remote-debugging-port=9222`; navigate manually and solve CAPTCHA; script then scrapes loaded tables.
- `scrape_footystats.py` is blocked (HTTP 403) by FootyStats anti-bot protection; kept for reference but not operational without proxy services (`ColdProxy`, `NodeMaven`, `Proxidize`).
- `scrape_sofascore_apify.py` requires `APIFY_API_TOKEN` in `.env` (not tracked).

## Model Experiment Workflow
```
main.py → pipeline() → build_features() → train_catboost() → predict()
```
Check `outputs/` and `feature_importance_*.png` after runs. Metrics: CV Accuracy (~0.448 ± 0.011), Log-Loss (~1.066 model vs ~1.005 bookie). Note: model currently performs at naive baseline level; objective clarification recommended before hyperparameter tuning (per `CLAUDE.md`).
