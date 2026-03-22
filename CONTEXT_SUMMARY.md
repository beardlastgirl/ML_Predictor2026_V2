# Repository Context Summary - ML_Predictor2026_V2

**Last Updated**: 2026-03-21  
**Repository**: I:\Scripts\ML_Predictor2026_V2  
**Primary Storage**: DEV_CONTEXT/ (for all findings and analysis)

---

## 📚 Essential Reading for New Sessions

### START HERE (In Order)
1. **DEV_CONTEXT/00_README.md** - Overview of this folder
2. **DEV_CONTEXT/SYSTEM_KNOWLEDGE.md** - Technical details
3. **DEV_CONTEXT/CODE_REVIEW_2026_03_21.md** - Latest findings (29 issues)
4. **.github/copilot-instructions.md** - Development guide

### Project Files
- **Readme.md** - Setup and usage instructions
- **CLAUDE.md** - AI-focused project context
- **main.py** - Entry point for prediction pipeline

---

## 🔍 Latest Analysis (2026-03-21)

### Code Review Summary
- **Total Issues**: 29
- **Critical**: 3 (division by zero, unsafe conversions)
- **High**: 5 (memory leaks, data misalignment)
- **Medium**: 12 (bounds checking, exception handling)
- **Low**: 9 (code quality, tech debt)

### Key Files with Issues
1. `src/features.py:30` - Division by zero
2. `src/pipeline.py:316` - Integer conversion without bounds
3. `src/stats_engine.py:107-110` - Probability normalization
4. `src/model_engine.py:52-74` - String methods, DataFrame alignment
5. `scrape_sofascore_apify.py` - Resource cleanup

### Production-Ready Fixes
All 10 priority fixes are in **DEV_CONTEXT/FIXES_EXAMPLES.md** with before/after code ready to apply.

---

## 🏗️ Architecture Quick Reference

### Entry Points
- `main.py` - Orchestrates full pipeline
- `run_model.ps1` - PowerShell menu for interactive execution
- `.\.venv\Scripts\Activate.ps1` - Activate virtual environment

### Core Pipeline Stages
1. **Load Data** - `src/pipeline.py:load_data()`
2. **Build Features** - `src/pipeline.py:build_features()`
3. **Train Model** - `src/pipeline.py:train_validate()`
4. **Predict Fixtures** - `src/model_engine.py:predict_gameweek()`
5. **Write Outputs** - `src/pipeline.py:write_outputs()`

### Key Modules
- `src/stats_engine.py` - Elo + Poisson math
- `src/features.py` - Trailing feature computation
- `src/model_engine.py` - ML model creation and predictions
- `src/data_processing.py` - Data normalization and loading
- `src/config.py` - All hyperparameters

### Data Files
- `data/ARG.csv` - Historical matches (6049 samples)
- `partidos.txt` - Upcoming fixtures
- `src/sofascore_stats.json` - Current standings
- `Glossary.txt` - Team name mappings

---

## 🧪 Testing

```powershell
# Run all tests
python -m pytest tests/test_main.py -v

# Run specific test
python -m pytest tests/test_main.py::test_normalize_team_name

# Run with coverage
python -m pytest tests/test_main.py --cov=src --cov-report=html
```

---

## 🚀 Development Workflow

### Before Starting Work
1. ✅ Read DEV_CONTEXT/00_README.md
2. ✅ Check DEV_CONTEXT/CODE_REVIEW_2026_03_21.md for known issues
3. ✅ Review DEV_CONTEXT/SYSTEM_KNOWLEDGE.md for technical details
4. ✅ Check DEV_CONTEXT/BUG_TRACKING.md for related bugs

### When Making Changes
1. ✅ Reference issue ID: `CR-2026-03-21-XXX` (from CODE_REVIEW)
2. ✅ Use code from FIXES_EXAMPLES.md when applicable
3. ✅ Update BUG_TRACKING.md status to "In Progress" → "Fixed"
4. ✅ Run tests: `python -m pytest tests/test_main.py`

### When Adding Features
1. ✅ Document in DEV_CONTEXT/ROADMAP.md
2. ✅ Add tests before implementation
3. ✅ Update SYSTEM_KNOWLEDGE.md if adding new concepts
4. ✅ Commit with clear message referencing DEV_CONTEXT files

---

## 📊 Key Metrics

### Model Performance
- **CV Accuracy**: 0.421 (+/- 0.014)
- **Log-Loss**: 1.090
- **Features Used**: 21 (including 10 Poisson-derived)
- **Training Samples**: 6049 matches

### Poisson Parameters
- **BASE_GOAL_RATE**: 1.89 (Liga Profesional Argentina average)
- **HOME_BOOST**: 1.22
- **POISSON_DRAW_ADJUSTMENT**: 0.85
- **MAX_GOALS**: 8 (in calculation)

### Elo Parameters
- **BASE_ELO**: 1500
- **K_FACTOR**: 30
- **HOME_ADVANTAGE**: 65 points

---

## 🔧 Common Commands

```powershell
# Activate environment
.\.venv\Scripts\Activate.ps1

# Run prediction pipeline
python main.py

# Run with menu
.\run_model.ps1 -Option 7  # Prediction only
.\run_model.ps1 -Option 8  # All scrapers + prediction

# Update dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/test_main.py

# Scrape data
python scrape_sofascore_apify.py    # Sofascore standings
python scrape_tyc.py                # TyC Sports fixtures
python scrape_stats_enhanced.py     # FBref stats
```

---

## ⚠️ Known Issues & Workarounds

### Issue: "No files match pattern src/results*.csv"
**Workaround**: Run scraper: `python scrape_stats_enhanced.py`

### Issue: Team names don't merge with historical data
**Workaround**: Update `Glossary.txt` with new team name mappings

### Issue: Model accuracy drops after scraper updates
**Workaround**: Verify features computed chronologically (check `TimeSeriesSplit` active)

See DEV_CONTEXT/SYSTEM_KNOWLEDGE.md for more technical details.

---

## 📝 Important Conventions

### Naming
- Modules: `snake_case.py` (e.g., `stats_engine.py`)
- Functions: `snake_case` (e.g., `calculate_poisson_features`)
- Feature Columns: `Title_Case_With_Underscores` (e.g., `Home_Elo`)

### Logging
- Use `log_info()`, `log_ok()`, `log_warning()`, `log_error()` from `src/utils.py`
- **NO ANSI colors** or emoji (ASCII only)
- **NO bare print() statements** (use logging functions)

### Results Encoding
- `H` (Home) → `2`
- `D` (Draw) → `1`
- `A` (Away) → `0`

---

## 🎯 Next Priority Actions

### This Week (Critical Fixes)
- [ ] Fix division by zero in form calculation (src/features.py:30)
- [ ] Add integer conversion bounds (src/pipeline.py:316)
- [ ] Protect probability normalization (src/stats_engine.py:107-110)

### Next Week (High-Priority Fixes)
- [ ] Implement try-finally for matplotlib cleanup
- [ ] Add DataFrame alignment assertions
- [ ] Fix string method safety checks

### This Sprint
- [ ] Add CSV result code validation
- [ ] Implement scraper resource cleanup
- [ ] Improve exception logging context

See DEV_CONTEXT/CODE_REVIEW_2026_03_21.md for full details with code examples.

---

## 📞 Questions?

1. **About code**: Check SYSTEM_KNOWLEDGE.md or the relevant source file
2. **About architecture**: Read copilot-instructions.md or CLAUDE.md
3. **About issues**: Check CODE_REVIEW_2026_03_21.md
4. **About fixes**: Read FIXES_EXAMPLES.md
5. **About progress**: Update BUG_TRACKING.md

---

*All findings, analysis, and context are centralized in DEV_CONTEXT/ for easy access and continuity.*
