# ML_Predictor2026_V2 - AGENTS.md

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
- CV Accuracy: ~44.8% (+/- 1.1%) on 3-class problem
- Log-Loss: ~1.066 (model) vs 1.077 (naive) vs ~1.005 (bookie)
- Training samples: ~6,416 (was ~340; cold-start imputation added)
- CV: tournament-aware (date-gap boundaries), early stopping enabled
- Features: 24

## Configuration (src/config.py)

```python
BASE_ELO = 1500          # Starting Elo for new/promoted teams
K_FACTOR = 30            # Elo change per match
HOME_ADVANTAGE = 65      # Elo bonus for home team
BASE_GOAL_RATE = 1.11    # NaN fallback for new teams: (1.26 + 0.96) / 2
HOME_BOOST = 1.15        # Home team xG multiplier
POISSON_DRAW_ADJUSTMENT = 1.11  # Calibrated draw adjustment
ML_POISSON_BLEND_RATIO = 0.6    # DEPRECATED: Poisson features feed model directly
TRAILING_WINDOW = 8      # Last N matches for form stats
MODEL_TYPE = "catboost"  # Override via ML_PREDICTOR_MODEL env var
```

## Scoreline Logic (_calculate_hybrid_goals)

Uses `floor(xG)` as the base (Poisson mode, not round), then applies ML directional adjustment when `max_prob >= 0.35`:
- Home win predicted + p_h >= p_d,p_a → ensure home > away; bump if p_h >= 0.50
- Away win predicted → symmetric
- Draw predicted → equalise at max(floor_h, floor_a)

## Data Sources

| Source | File | Scraper | Status |
|--------|------|---------|--------|
| football-data.co.uk | `data/ARG.csv` | Auto (DataIngestor) | Reliable |
| TyC Sports | `Partidos.txt` | `scrape_tyc.py --url URL --fecha LABEL` | Manual |
| FBref | `src/fbref_*.csv` | `scrape_stats_manual.py` (CDP) | Manual CAPTCHA |
| FootyStats | `src/footystats_*.csv` | `scrape_footystats.py` | Blocked (403) |
| Sofascore | `src/sofascore_stats.json` | `scrape_sofascore_apify.py` | API-based |
| PDF reports | `Reporte/{year}/Resumen F{round}.pdf` | `parse_reporte_pdfs.py` | Manual upload |

## Web Scraping Challenges

### Anti-Bot Protection (September 2026)

Both FBref and FootyStats employ enterprise-grade anti-bot protection (likely DataDome or similar) that blocks automated scraping:

- **FBref**: HTTP 403 on all automated requests (including Playwright/Selenium)
- **FootyStats**: HTTP 403 on all automated requests
- **Solution**: Chrome Remote Debugging Protocol (CDP) with manual CAPTCHA solving

### Scrapling Evaluation (September 2026)

**Tested library:** [Scrapling](https://github.com/d4vinci/scrapling) (84k GitHub stars)

**Test Results:**
- `Fetcher.get()` (HTTP): HTTP 403 on FBref and FootyStats
- `DynamicFetcher.fetch()` (Playwright): HTTP 403 on FBref and FootyStats  
- `StealthyFetcher.fetch()` (Stealth Playwright): Browser installation issues

**Conclusion:** Scrapling cannot bypass current FBref/FootyStats protection without residential proxies.

**Recommendation:** Keep current CDP approach for FBref. Consider Scrapling with proxy services (ColdProxy, NodeMaven, Proxidize) for future automation if budget allows.

**Archived implementation:** `Archive/scrapers_unused_20260919/scrape_fbref_scrapling.py` contains a working Scrapling integration that can be restored if proxy services are added.

### Current Scraping Workflow

**FBref/Stats Scraping (CDP Method):**
```powershell
# Step 1: Script auto-launches Chrome with remote debugging
python scrape_stats_manual.py

# Step 2: Navigate manually to FBref/FootyStats in the Chrome window
# Step 3: Solve any CAPTCHA as a normal user
# Step 4: Script automatically scrapes the page once loaded
```

**Advantages:**
- Works reliably (bypasses all bot detection)
- No API costs
- Full browser rendering (JS tables load correctly)

**Disadvantages:**
- Requires manual intervention each time
- Not fully automated
- User must be available to solve CAPTCHAs

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
- Run `python -m pytest tests/ -v` after any change (expect 131+ passing)
- Run `pip-audit -r dev-requirements.txt` after any dependency change (dev dep)
- Model name in summary reads from `type(result.model).__name__`

<!-- GSD Configuration — managed by gsd-core installer -->
# Instructions for GSD

- Use the gsd-core skill when the user asks for GSD or uses a `gsd-*` command.
- Treat `/gsd-...` or `gsd-...` as command invocations and load the matching file from `.github/skills/gsd-*`.
- When a command says to spawn a subagent, prefer a matching custom agent from `.github/agents`.
- Do not apply GSD workflows unless the user explicitly asks for them.
- After completing any `gsd-*` command (or any deliverable it triggers: feature, bug fix, tests, docs, etc.), ALWAYS: (1) offer the user the next step by prompting via `ask_user`; repeat this feedback loop until the user explicitly indicates they are done.
<!-- /GSD Configuration -->
