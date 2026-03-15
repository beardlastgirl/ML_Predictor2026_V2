# Codebase Structure

**Analysis Date:** 2026-03-15

## Directory Layout

```
C:\Scripts\ML_Predictor2026_V2\
├── .venv/                      # Python virtual environment (gitignored)
├── .planning/                  # GSD planning documents
├── data/                       # Historical match data
├── src/                        # Core source code modules
├── tests/                      # Automated test suite
├── Reporte/                    # PDF match reports (external data)
├── catboost_info/              # CatBoost training logs (generated)
├── DEV_CONTEXT/                # Development documentation
├── .git/                       # Git repository
├── .github/                    # GitHub workflows/config
├── .claude/                    # Claude Code configuration
├── .agents/                    # Agent configuration
├── .codex/                     # Codex configuration
├── .gemini/                    # Gemini configuration
├── .opencode/                  # OpenCode configuration
├── main.py                     # Main entry point
├── scrape_*.py                 # Web scraper scripts (6 files)
├── parse_reporte_pdfs.py       # PDF report parser
├── run_model.ps1               # PowerShell menu wrapper
├── setup_venv.ps1              # Venv setup script
├── update_arg_csv.py           # Historical data updater
├── convert_results.ps1         # Results conversion script
├── convert_results.py          # Results conversion Python
├── partidos.txt                # Fixtures file (generated)
├── Glossary.txt                # Team name mappings
├── requirements.txt            # Python dependencies
├── CLAUDE.md                   # Project documentation
├── Readme.md                   # Project readme
├── AGENTS.md                   # Agent instructions
└── .env.example                # Environment template
```

## Directory Purposes

**src/:**
- Purpose: Core prediction engine modules
- Contains: 8 Python files (~1133 lines total)
- Key files:
  - `src/pipeline.py` (351 lines) - Main orchestration
  - `src/model_engine.py` (193 lines) - ML model logic
  - `src/stats_engine.py` (172 lines) - Math implementations
  - `src/data_processing.py` (205 lines) - Data loading
  - `src/features.py` (121 lines) - Feature engineering
  - `src/config.py` (64 lines) - Constants and hyperparameters
  - `src/utils.py` (26 lines) - Logging utilities
  - `src/__init__.py` - Package marker

**data/:**
- Purpose: Historical match results
- Contains: `ARG.csv` (837KB, 6000+ matches from football-data.co.uk)
- Key files: `data/ARG.csv`

**tests/:**
- Purpose: Automated test suite
- Contains: `tests/test_main.py` (359 lines)
- Coverage: Elo, Poisson, trailing stats, normalization

**Reporte/:**
- Purpose: PDF match reports from league
- Contains: Year subdirectories with PDF files
- Used by: `parse_reporte_pdfs.py`

**catboost_info/:**
- Purpose: CatBoost training output
- Generated: Yes (by CatBoost during training)
- Committed: No (typically gitignored)

**DEV_CONTEXT/:**
- Purpose: Development documentation
- Contains: Design docs, meeting notes

## Key File Locations

**Entry Points:**
- `main.py`: Main prediction pipeline entry
- `scrape_stats_enhanced.py`: FBref scraper (Selenium)
- `scrape_footystats.py`: FootyStats scraper (Playwright)
- `scrape_sofascore_apify.py`: Sofascore scraper (Apify)
- `scrape_tyc.py`: TyC Sports fixtures scraper
- `scrape_stats_manual.py`: CDP manual browser scraper
- `parse_reporte_pdfs.py`: PDF report parser

**Configuration:**
- `src/config.py`: Elo, Poisson, ML hyperparameters
- `requirements.txt`: Python dependencies
- `Glossary.txt`: Team name mappings (186 entries)
- `.env.example`: Environment variable template

**Core Logic:**
- `src/pipeline.py`: End-to-end workflow
- `src/stats_engine.py`: Elo and Poisson math
- `src/model_engine.py`: Model creation and prediction
- `src/features.py`: Trailing-average features

**Testing:**
- `tests/test_main.py`: pytest test suite

## Naming Conventions

**Files:**
- snake_case for Python: `main.py`, `scrape_stats_enhanced.py`
- PascalCase for PowerShell: `run_model.ps1`
- Descriptive prefixes: `scrape_*` for scrapers

**Directories:**
- lowercase: `src/`, `data/`, `tests/`
- Descriptive: `Reporte/`, `DEV_CONTEXT/`

## Where to Add New Code

**New Feature:**
- Primary code: `src/` (new module or extend existing)
- Tests: `tests/test_main.py`

**New Scraper:**
- Implementation: Project root as `scrape_<source>.py`
- Follow pattern: `scrape_tyc.py` (requests + BeautifulSoup)

**New ML Model:**
- Add to `src/config.py` MODEL_PARAMS dict
- Update `src/model_engine.create_model()` function

**Utilities:**
- Shared helpers: `src/utils.py`
- New config: `src/config.py`

**Data Sources:**
- Historical CSV: `data/`
- Scraped output: `src/` (CSV/JSON)
- Standings: `src/sofascore_stats.json`

## Special Directories

**.venv/:**
- Purpose: Python virtual environment
- Generated: Yes (`python -m venv .venv`)
- Committed: No (gitignored)

**.planning/:**
- Purpose: GSD planning documents
- Generated: Yes (by codebase mapper)
- Committed: Yes (for project context)

**catboost_info/:**
- Purpose: CatBoost training logs and model info
- Generated: Yes (by CatBoost library)
- Committed: No (typically gitignored)

## Generated Files

**Runtime:**
- `Resultados_*.txt` - Prediction output
- `feature_importance_*.png` - Feature importance chart
- `partidos.txt` - Fixtures (updated by scraper)
- `src/results*.csv`, `src/stats*.csv` - Scraped data
- `src/sofascore_stats.json` - Standings cache

---

*Structure analysis: 2026-03-15*
