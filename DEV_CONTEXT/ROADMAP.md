# ROADMAP.md

## Planned Features & Improvements

### High Priority

1. **Enhanced Sofascore Features**
   - Use team ratings from Sofascore (currently partially available)
   - Implement form-based features from recent standings
   - Add home/away specific standings if available

2. **Model Performance Optimization**
   - Hyperparameter tuning for CatBoost
   - Feature selection to reduce overfitting
   - Ensemble methods (combine LightGBM + CatBoost)

3. **Data Pipeline Automation**
   - Concurrent execution of scrapers
   - Caching mechanism for scraped data
   - Automated data validation

### Medium Priority

4. **Improved Team Name Matching**
   - Fuzzy matching for new teams
   - Auto-detection of team name changes
   - Historical team name mapping

5. **Advanced Poisson Modeling**
   - Double Poisson (separate variance for home/away)
   - Dynamic base rate based on current league avg
   - 3-way odds comparison with bookmakers

6. **Prediction Confidence Enhancement**
   - Model uncertainty quantification
   - Historical accuracy by prediction type
   - Automated edge detection

### Lower Priority

7. **User Interface**
   - Web dashboard for predictions
   - Historical prediction accuracy tracking
   - Mobile notifications

8. **Extended Coverage**
   - Argentine Primera Nacional
   - Copa Libertadores fixtures
   - International friendlies

## Completed Items (March 2026)

- [x] Code modularization and refactoring: `main.py` split into `src/` sub-modules.
- [x] Centralized configuration in `src/config.py`.
- [x] Standardized logging and utility functions.
- [x] FootyStats Scraper: Added `scrape_footystats.py` using Playwright.
- [x] Enhanced Manual Scraper: Updated `scrape_stats_manual.py` with multi-site CDP support.
- [x] Integrated FootyStats into the automated pipeline (`run_model.ps1`).

## Completed Items (March 2026 - Enhanced Evaluation)

- [x] **AI Configuration Analysis**: Deep review of 5 AI products (Claude, Codex, Gemini, OpenCode, Agent)
- [x] **Configuration Harmonization**: Fixed 13 compatibility issues, achieved 97% parity
- [x] **Code Review**: Identified 29 issues (3 critical, 5 high, 12 medium, 9 low)
- [x] **Comprehensive Enhancement Evaluation**: Generated 11 agent recommendations
- [x] **Free-Tier Validation**: Confirmed all recommendations use free tier only ($0 cost)
- [x] **8-Week Implementation Roadmap**: Created detailed week-by-week plan with code examples
- [x] **Documentation**: Created 9 comprehensive documents with navigation guides
- [x] **Quality Assurance**: All changes verified with completion checklist (30+ checkpoints, all passed)

## Completed Items (March 2026)

- [x] Code modularization and refactoring: `main.py` split into `src/` sub-modules.
- [x] Centralized configuration in `src/config.py`.
- [x] Standardized logging and utility functions.
- [x] FootyStats Scraper: Added `scrape_footystats.py` using Playwright.
- [x] Enhanced Manual Scraper: Updated `scrape_stats_manual.py` with multi-site CDP support.
- [x] Integrated FootyStats into the automated pipeline (`run_model.ps1`).

## Next Steps (Updated 2026-03-22)

### Priority 1: Fix Critical Bugs (Week 1) - 8 Hours
1. Fix 3 critical bugs in features.py, pipeline.py, stats_engine.py
2. Add data validation layer
3. Improve scraper resilience
→ See ENHANCEMENT_RECOMMENDATIONS.md Week 1 for details

### Priority 2: Add Testing & Automation (Week 2-4) - 8 Hours
4. Generate integration tests (increase coverage 35% → 65%)
5. Set up GitHub Actions for automated weekly runs
6. Profile and parallelize scrapers (5x speedup)
7. Optimize hyperparameters (+1-2% accuracy)
→ See ENHANCEMENT_RECOMMENDATIONS.md Week 2-4 for details

### Priority 3: Add Monitoring & Polish (Month 2) - 8 Hours
8. Implement accuracy trend tracking (SQLite MCP)
9. Auto-generate documentation
10. Add fuzzy team name matching
11. Feature importance analysis
→ See ENHANCEMENT_RECOMMENDATIONS.md Month 2 for details

### Reference
- Complete 8-week roadmap: ENHANCEMENT_RECOMMENDATIONS.md
- Quick comparison: QUICK_REFERENCE.md
- Executive summary: EVALUATION_SUMMARY.md
