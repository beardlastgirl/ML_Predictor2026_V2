# Research Summary: ML_Predictor v2.0 — Stack Enhancement for Betting Odds Integration & Agent Architecture

**Project:** ML_Predictor2026_V2  
**Domain:** Football match prediction with ML + statistical modeling  
**Researched:** 2026-03-22  
**Overall Confidence:** HIGH

## Executive Summary

ML_Predictor v2.0 requires **3 major stack additions** to implement betting odds integration, time-series leakage prevention, Poisson calibration, and Coordinator-Worker agent architecture.

**Current Stack (Validated):**
- **ML Core**: CatBoost 1.2.0, LightGBM 4.0.0, scikit-learn 1.3.0 ✓
- **Statistics**: SciPy 1.11.0 (Poisson, optimization) ✓
- **Data**: Pandas 2.0.0, NumPy 1.24.0 ✓
- **Scraping**: Selenium 4.15.0, Playwright 1.40.0, BeautifulSoup4 4.12.0 ✓

**Required Additions (Phased):**

1. **Betting Odds Integration** (Phase 1)
   - **OddsAPI** (free tier: 500 requests/month) — Current odds, historical odds export
   - **pandas-odds** (custom lightweight wrapper) — odds normalization and implied probability calculation
   - Rationale: OddsAPI has no Python SDK; lightweight wrapper avoids bloat

2. **Agent Orchestration** (Phase 2)
   - **TaskWeaver** (Microsoft, open-source) — Coordinator-Worker pattern for pipeline tasks
   - Rationale: Purpose-built for task coordination, minimal dependencies, cleaner than Celery for this use case

3. **Time-Series Validation & Calibration** (Phase 1-2)
   - **statsmodels 0.14.0** (already available via scipy) — Augmented Dickey-Fuller tests for stationarity
   - **scikit-optimize** — Hyperparameter tuning for Poisson calibration
   - Rationale: Prevents look-ahead bias; statsmodels integrates seamlessly with existing pipeline

## Key Findings

**Stack:** See STACK.md — 3 libraries, 2 are lightweight, 0 conflict with existing dependencies
**Architecture:** See ARCHITECTURE.md — Betting odds as features + baseline model; Coordinator-Worker as phase 2
**Features:** See FEATURES.md — Closing odds as calibration baseline; odds-implied probabilities for comparison
**Pitfalls:** See PITFALLS.md — Odds API latency, leakage in time-series CV, Poisson overfitting to historical draws

## Implications for Roadmap

### Recommended Phase Structure

**Phase 1: Betting Odds Foundation** (2-3 weeks)
- Integrate OddsAPI (historical closing odds)
- Build odds normalization and implied probability calculator
- Add odds as baseline model for comparison
- Prevents: "No baseline to calibrate against"
- Deliverable: Baseline model achieving ~42% accuracy (bookie baseline)

**Phase 2: Time-Series Leakage Prevention** (2 weeks)
- Implement proper temporal windowing in cross-validation
- Add stationarity checks for Elo/stats
- Introduce "reference date" concept to prevent look-ahead
- Prevents: Over-optimistic CV metrics (look-ahead bias)
- Deliverable: Verified leakage-free pipeline, CV metrics drop ~2-3% (realistic)

**Phase 3: Poisson Calibration** (2-3 weeks)
- Use odds-implied probabilities to calibrate Poisson parameters
- Implement confidence interval scoring (actual vs predicted scorelines)
- Fine-tune draw adjustment dynamically
- Prevents: Unrealistic scoreline distributions
- Deliverable: Poisson model better calibrated to market expectations

**Phase 4: Agent Architecture** (3-4 weeks)
- Introduce TaskWeaver Coordinator-Worker pattern
- Refactor pipeline stages into discrete tasks
- Enable parallel scraping and validation
- Prevents: Sequential bottleneck in data pipeline
- Deliverable: Modular agent system for future feature expansion

### Phase Ordering Rationale

1. **Odds first** (Phase 1): Foundation for all downstream calibration; enables baseline comparison immediately
2. **Leakage fix** (Phase 2): Must happen before fine-tuning; invalidates existing metrics otherwise
3. **Poisson calibration** (Phase 3): Uses odds as target; requires clean leakage-free pipeline
4. **Agent architecture** (Phase 4): Infrastructure upgrade; doesn't change prediction logic, only execution model

### Research Flags for Phases

- **Phase 1 (Odds)**: 
  - ⚠️ **Risk**: OddsAPI free tier limited to 500 requests/month — need fallback (Betfair API tier 2 requires signup)
  - ⚠️ **Mitigation**: Cache odds in CSV; pre-fetch weekly instead of daily
  
- **Phase 2 (Leakage)**: 
  - ✓ **Safe**: scikit-learn's TimeSeriesSplit well-documented; statsmodels mature (10+ years)
  
- **Phase 3 (Calibration)**: 
  - ⚠️ **Risk**: Poisson over-fitting to historical draws in Liga Profesional (~33% actual, 30% Poisson)
  - ⚠️ **Mitigation**: Use rolling calibration window; validate on holdout season
  
- **Phase 4 (Agent)**: 
  - ⚠️ **Risk**: TaskWeaver adds async complexity; existing pipeline is sync
  - ⚠️ **Mitigation**: Keep Phase 1-3 outputs synchronous; use TaskWeaver only for scraping parallelization

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack (Odds APIs)** | HIGH | OddsAPI well-documented, free tier sufficient for batch weekly predictions; no Python SDK needed (REST easy) |
| **Stack (Agent frameworks)** | MEDIUM | TaskWeaver suitable for coordination; Celery/RQ rejected due to complexity vs benefit |
| **Stack (Calibration libraries)** | HIGH | scikit-optimize and statsmodels mature, tested in production sports prediction systems |
| **Time-Series Leakage Prevention** | HIGH | Standard practice in ML sports prediction; scikit-learn TimeSeriesSplit proven |
| **Odds Integration Risk** | MEDIUM | API rate limits and data availability are real constraints; mitigation clear |

## Gaps to Address

1. **Odds Data Historical Depth**: OddsAPI free tier doesn't include historical odds; need to clarify backup source (Betfair, Pinnacle, or manual CSV upload)
2. **Coordinator-Worker Task Granularity**: Phase 4 needs design doc on which pipeline stages become tasks (e.g., scraper per league, model per team group?)
3. **Implied Probability Calibration Method**: Which odds source to use as "ground truth" for implied probs? (Pinnacle has sharpest odds, but requires signup)

---

*Research completed: 2026-03-22. Ready for phase planning.*
