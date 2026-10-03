# Handoff Document - ML_Predictor2026_V2

**Date**: 2026-09-27
**Status**: Roadmap Complete ✅

---

## Project Location
Local Project Root: `C:\Scripts\ML_Predictor2026_V2\` (documented for current machine context) / `/c/Users/argen/ML_Predictor2026_V2/` (WSL)

**Note on Execution:** To avoid import errors with the canonical path module, always execute Python scripts as modules from the root:
`python -m src.module_name` (e.g., `python -m src.main`)

---

## Completed Work (September 2026 Roadmap)

### Phase 1: High Priority - Quality Gates & Cleanliness ✅
| Item | Status | Details |
|------|--------|---------|
| CI/CD Pipeline | ✅ Complete | `.github/workflows/ci.yml` - pytest, pip-audit, artifact tracking |
| Repository Governance | ✅ Complete | Updated `.gitignore`: catboost_info/, Reporte/, Prediccion*.txt, *.pdf, Partidos.txt/partidos.txt |
| Skill-Tree Canonicalization | ✅ Verified | `.claude/skills` and `.agents/skills` identical |

### Phase 2: Medium Priority - Code Quality & Testing ✅
| Item | Status | Details |
|------|--------|---------|
| Type Hints | ✅ Complete | PEP 484 on `features.py`, `stats_engine.py`, `pipeline.py` |
| cv_split.py Fallback | ✅ Complete | `src/cv_split.py` with boundary detection, fallback warnings, n_splits clamping |
| Golden Math Regression Suite | ✅ Complete | `tests/test_golden_math.py` - 17 tests freezing exact numerical snapshots |
| Pipeline Integration Tests | ✅ Complete | `tests/test_pipeline_integration.py` - 19 tests covering end-to-end execution |
| Documentation Refresh | ✅ Complete | `Readme.md`, `DEV_CONTEXT/PROJECT_STATUS.md` updated with current metrics |

### Critical Bug Fixes ✅
| Bug | Fix | Impact |
|-----|-----|--------|
| Shin Imputation | Missing odds → 1/3 (was NaN) | Restored 5,788 matches to training corpus |

---

## Test Results
```
Total: 80/80 PASSING ✅
- test_golden_math.py:       17 tests
- test_main.py:              29 tests  
- test_pipeline_integration: 19 tests
- test_scraper_utils.py:     15 tests
```

---

## Current Baseline Metrics (2026-09-26)
| Metric | Value |
|--------|-------|
| Historical Matches | 6,128 |
| Training Samples (post warm-up) | 340 |
| Mean CV Accuracy (5-fold) | 0.343 ± 0.067 |
| Mean CV Log Loss (5-fold) | 1.254 |
| Naive Baseline Log Loss | ~1.08 |
| Bookmaker Baseline Log Loss | ~1.04 |
| Features Used | 24 |

**Note**: Model performs at naive baseline level (per audit findings). Objective clarification needed before hyperparameter tuning.

---

## Key Files Created/Modified (Sep 2026)

### Created
- `src/cv_split.py` - Tournament-aware cross-validation
- `tests/test_golden_math.py` - Golden math regression suite
- `tests/test_pipeline_integration.py` - Pipeline integration tests
- `.github/workflows/ci.yml` - CI/CD pipeline

### Modified
- `src/features.py` - Type hints added
- `src/stats_engine.py` - Type hints added
- `src/pipeline.py` - Shin imputation fix, tournament-aware CV integration
- `.gitignore` - Added ignore patterns
- `Readme.md` - Complete rewrite with current architecture

---

## Operational Notes

### Weekly Workflow
```powershell
.\run_model.ps1
# Menu options 1-8 for individual or full pipeline runs
```

### Key Scripts
- `main.py` - Orchestration entry point
- `scrape_stats_enhanced.py` / `scrape_stats_manual.py` - FBref stats
- `scrape_footystats.py` - FootyStats advanced metrics
- `scrape_tyc.py` - Fixtures
- `scrape_sofascore_apify.py` - Current standings

### Model
- Default: CatBoost
- Switch via env: `MODEL_TYPE=lightgbm` or `MODEL_TYPE=catboost`

---

## Known Issues (Per Roadmap)
1. **Scraper Fragility** - DOM changes break scrapers; mitigated by triple-source strategy
2. **Manual Mapping** - New teams require Glossary.txt updates
3. **Browser Dependencies** - CDP scraper needs Chrome with DevTools
4. **Model Performance** - At naive baseline; needs objective clarification

---

## Remaining Roadmap (Phase 3 - Lower Priority)
*Not completed - architectural evolution items*
- Configuration migration to YAML/Pydantic Settings
- SHAP interpretability analysis script (`scripts/`)
- Pipeline deconstruction: `orchestration.py`, `feature_pipeline.py`, `reporting.py`

---

## Cleanup Performed
- ❌ No `Critiques/CONSOLIDATED_CRITIQUES_AND_ROADMAP.md` existed (empty Critiques folder)
- ❌ No `handsoff.md` existed (created this file)
- ⚠️ `DEV_CONTEXT/` historical docs preserved (document March 2026 Tier 1 implementation)

---

## Next Steps for Continuation
1. Clarify prediction objective (3-class vs goal-count regression)
2. If tuning: start with CatBoost hyperparameter search
3. Apply `@resilient_scraper` decorator to production scrapers
4. Consider Phase 3 items if architecture needs modularization