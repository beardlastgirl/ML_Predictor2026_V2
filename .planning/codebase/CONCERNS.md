# Codebase Concerns

**Analysis Date:** 2026-03-15

## Tech Debt

**Hardcoded API Token:**
- Issue: Apify token embedded in `scrape_sofascore_apify.py` (line 32)
- Files: `scrape_sofascore_apify.py`
- Impact: Security risk if code is shared publicly; token may expire
- Fix approach: Move to environment variable with no default fallback

**Duplicate Logging Functions:**
- Issue: Each scraper defines its own `log_info`, `log_ok`, `log_error` functions
- Files: `scrape_stats_enhanced.py`, `scrape_footystats.py`, `scrape_tyc.py`, `scrape_stats_manual.py`
- Impact: Code duplication, inconsistent logging if changes needed
- Fix approach: Import from `src/utils.py` in all scrapers

**Duplicate Team Name Cleaning:**
- Issue: `clean_team_name` function duplicated across scrapers with slight variations
- Files: `scrape_stats_enhanced.py`, `scrape_footystats.py`, `scrape_stats_manual.py`
- Impact: Inconsistent normalization across data sources
- Fix approach: Centralize in `src/data_processing.py`

**Large Functions:**
- Issue: `predict_gameweek` (193 lines), `fetch_page_with_selenium` (90 lines)
- Files: `src/model_engine.py`, `scrape_stats_enhanced.py`
- Impact: Hard to test, hard to maintain
- Fix approach: Extract smaller helper functions

## Known Bugs

**Draw Bias in Predictions:**
- Symptoms: Model tends to predict draws more than actual occurrence rate
- Files: `src/model_engine.py` (lines 155-184), `src/pipeline.py` (line 176)
- Trigger: Any prediction run
- Workaround: Sample weights (0.7 for draws) and Poisson ensemble partially mitigate

**Fixture Parsing Failures:**
- Symptoms: Some fixtures not parsed from `partidos.txt`
- Files: `src/data_processing.py` (`parse_fixtures`)
- Trigger: Non-standard formatting in input file
- Workaround: Manual editing of partidos.txt

## Security Considerations

**API Token Exposure:**
- Risk: Apify token in source code (`scrape_sofascore_apify.py` line 32)
- Files: `scrape_sofascore_apify.py`
- Current mitigation: None
- Recommendations:
  - Remove hardcoded token
  - Require `APIFY_API_TOKEN` environment variable
  - Add `.env` to `.gitignore` (already present)

**No Input Validation:**
- Risk: File paths from command line not validated
- Files: All scraper scripts with argparse
- Current mitigation: None
- Recommendations: Path validation, prevent path traversal

## Performance Bottlenecks

**Sequential Scraping:**
- Problem: Scrapers run one at a time
- Files: `run_model.ps1` menu workflow
- Cause: No parallel execution
- Improvement path: Add `--parallel` option to run multiple scrapers concurrently

**Full History Re-read:**
- Problem: `data/ARG.csv` (837KB) read every run
- Files: `src/pipeline.py` (`load_data`)
- Cause: No caching of loaded data
- Improvement path: Add pickle cache for parsed historical data

**Poisson Feature Recalculation:**
- Problem: `calculate_poisson_features` called for every match in loop
- Files: `src/pipeline.py` (line 126-133)
- Cause: No vectorization
- Improvement path: Vectorize Poisson calculations with numpy

## Fragile Areas

**Web Scrapers:**
- Files: `scrape_stats_enhanced.py`, `scrape_footystats.py`, `scrape_tyc.py`
- Why fragile: HTML structure changes break scrapers silently
- Safe modification: Add schema validation or visual regression tests
- Test coverage: None

**Team Name Glossary:**
- Files: `Glossary.txt`
- Why fragile: New teams or name variations cause silent mismatches
- Safe modification: Add validation step to detect unmapped teams
- Test coverage: Partial (normalization tested, glossary completeness not)

**PDF Parser:**
- Files: `parse_reporte_pdfs.py`
- Why fragile: PDF format changes break parsing
- Safe modification: Add error handling for missing fields
- Test coverage: None

## Scaling Limits

**Historical Data:**
- Current capacity: 6049 matches in `data/ARG.csv`
- Limit: pandas DataFrame in memory (~100K rows manageable)
- Scaling path: Chunked reading for larger datasets

**Model Training:**
- Current: CatBoost with 500 iterations, 6 depth
- Limit: ~10K samples trains in reasonable time (< 1 min)
- Scaling path: Reduce iterations or use LightGBM for larger datasets

## Dependencies at Risk

**Selenium/Playwright:**
- Risk: Browser automation libraries require ChromeDriver version matching
- Impact: Scrapers fail when Chrome updates
- Migration plan: Use webdriver-manager (already imported, fallback present)

**Apify:**
- Risk: External API dependency for Sofascore data
- Impact: API changes or rate limits break standings fetch
- Migration plan: Implement direct scraper fallback

## Missing Critical Features

**Model Persistence:**
- Problem: Model trained fresh every run
- Blocks: Cannot deploy pre-trained model; no inference-only mode
- Recommendation: Add `save_model` and `load_model` functions

**Backtesting:**
- Problem: No historical backtesting framework
- Blocks: Cannot evaluate prediction accuracy over time
- Recommendation: Add backtest module to compare predictions vs actual results

**Configuration Management:**
- Problem: Hyperparameters in `src/config.py` only
- Blocks: Cannot tune without code changes
- Recommendation: Add YAML/JSON config file support

## Test Coverage Gaps

**Pipeline Orchestration:**
- What's not tested: `src/pipeline.py` (351 lines, 0 tests)
- Files: `src/pipeline.py`
- Risk: Integration bugs undetected
- Priority: High

**Prediction Logic:**
- What's not tested: `predict_gameweek` function
- Files: `src/model_engine.py`
- Risk: Prediction bugs undetected
- Priority: High

**Scrapers:**
- What's not tested: All `scrape_*.py` scripts
- Files: 6 scraper scripts
- Risk: Breaking changes undetected
- Priority: Medium

**Data Processing:**
- What's not tested: `load_glossary`, `parse_fixtures`, `load_soforcescore_data`
- Files: `src/data_processing.py`
- Risk: Data loading bugs undetected
- Priority: Medium

---

*Concerns audit: 2026-03-15*
