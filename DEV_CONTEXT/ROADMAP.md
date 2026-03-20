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

## Completed Items (February 2026)

- [x] Poisson distribution integration for goal modeling
- [x] Menu-driven run_model.ps1 with individual script execution
- [x] Apify-based Sofascore scraper integration
- [x] Dual format Sofascore data loading
- [x] Bug fixes for xG calculations
- [x] Sofascore features in prediction model

## Next Steps

1. Integrate FootyStats features (xG, PPG) into the feature engineering pipeline (`src/features.py`).
2. Run full pipeline (option 8) and validate predictions.
3. Compare predicted vs actual results for accuracy assessment.
4. Fine-tune Poisson parameters based on historical accuracy.
