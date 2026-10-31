# ML_Predictor2026_V2 — Testing

<!-- GSD Configuration -->

## Running Tests

```powershell
python -m pytest tests/ -v
```
Expected 131+ passing (per AGENTS.md guideline).

## Key Test Suites

| File | Tests | Coverage |
|---|---|---|
| `tests/test_main.py` | 29 | Core pipeline functions |
| `tests/test_golden_math.py` | 17 | Poisson xG / Shin / Elo regression (golden math) |
| `tests/test_pipeline_integration.py` | 19 | End-to-end from `ARG.csv` to predictions |
| `tests/test_scraper_utils.py` | 15 | `@resilient_scraper` decorator, CAPTCHA detection |
| `tests/test_leakage.py` | — | Temporal order (no future-match leakage) |
| `tests/test_temporal_ordering.py` | — | Tournament-aware CV boundary checks |
| `tests/test_form_variants.py` | — | Team name normalization variants |

## CI Pipeline (`.github/workflows/ci.yml`)
Runs on every PR:
- `pytest` (all tests)
- `pip-audit` (vulnerability scan)
- Artifact tracking (prevents committing generated files like `feature_importance_*.png` or `Resultados_*.txt`)

## Golden Math Tests
`tests/test_golden_math.py` validates Poisson probabilities, Shin-method extraction, and Elo updates against hand-computed reference values. These must pass after any `stats_engine` or `model_engine` change.

## Scraping Tests
`tests/test_scraper_utils.py` tests the `@resilient_scraper` decorator (retries with exponential backoff, handles 403/503, detects CAPTCHA patterns in response HTML).

## Verification Note
All test claims verified against `tests/` directory contents at time of generation. `docs/TESTING.md` does not claim external test services or APIs.
