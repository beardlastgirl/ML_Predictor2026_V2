# ML_Predictor2026_V2 Documentation Index

**Generated:** 2026-03-21
**Location:** `I:\Scripts\ML_Predictor2026_V2\DEV_CONTEXT\`

---

## 📋 Documentation Files

### 🏗️ CODEBASE_MAP.md (37.3 KB) - **START HERE**
**Complete architectural and technical documentation**

**Contents:**
1. Architecture Overview - System pattern, data pipeline flow
2. Component Relationships - How scrapers, pipeline, models interact
3. Key Modules - Detailed responsibility & code flow for each module
4. Data Scrapers - All collection layer integration points
5. Configuration System - All hyperparameters and settings
6. Dependencies & Integrations - External services and packages
7. Entry Points - How to run the system
8. File Structure - Complete directory organization
9. Key Algorithms - Elo, xG, Poisson, Shin method formulas
10. Testing Strategy - 21 test cases coverage
11. Known Constants - All tuning parameters
12. Data Quality & Validation - Input requirements
13. Performance Characteristics - Time/space complexity
14. Error Handling & Logging - Exception strategy
15. Development Guidelines - How to add features
16. Future Enhancements - Potential improvements
17. Summary - Quick recap of the system

**Use when:**
- Understanding the full architecture
- Identifying where to add new features
- Debugging complex issues
- Making design decisions

---

### ⚡ QUICK_REFERENCE.md (9.6 KB) - **QUICK START**
**Fast lookup guide for common tasks**

**Contents:**
- One-minute overview
- Critical files reference table
- Data pipeline diagram
- 24 features breakdown
- Key algorithms (condensed)
- Configuration quick view
- Common tasks (run, debug, test)
- Output file descriptions
- Directory essentials
- Debugging tips
- Constants cheat sheet
- Model architecture summary

**Use when:**
- Running the pipeline
- Quick lookup of file purposes
- Common tasks (scrape, train, predict)
- Debugging quick issues
- Referencing constants

---

## 🔑 Key Sections by Use Case

### "I want to understand the system"
**→ Read:** CODEBASE_MAP sections 1-3

**Time:** 15 minutes
**Learn:** Overall architecture, data flow, component responsibilities

---

### "I want to run predictions"
**→ Read:** QUICK_REFERENCE "Common Tasks"

**Time:** 2 minutes
**Learn:** Commands to execute, what to expect

---

### "I want to add a new feature"
**→ Read:** CODEBASE_MAP section 15 + QUICK_REFERENCE "Key Constants"

**Time:** 10 minutes
**Learn:** Feature engineering pattern, configuration locations

---

### "Predictions look wrong"
**→ Read:** QUICK_REFERENCE "Debugging Tips" + CODEBASE_MAP section 9

**Time:** 5 minutes
**Learn:** Common issues, check Elo/Poisson formulas

---

### "I want to tune the model"
**→ Read:** CODEBASE_MAP section 11 + QUICK_REFERENCE "Configuration"

**Time:** 10 minutes
**Learn:** All tuning parameters, what each affects

---

### "I need to integrate external data"
**→ Read:** CODEBASE_MAP sections 4, 5, 6

**Time:** 20 minutes
**Learn:** Scraper architecture, data loading patterns, config integration

---

## 🎯 Critical Files (from System)

| File | Purpose | When to Read |
|------|---------|---|
| `src/config.py` | All hyperparameters | Tuning model |
| `src/pipeline.py` | Main orchestration | Understanding flow |
| `src/stats_engine.py` | Elo + Poisson math | Understanding predictions |
| `src/model_engine.py` | ML + ensemble | Debugging predictions |
| `src/features.py` | Trailing stats | Feature engineering |
| `main.py` | Entry point | Running system |
| `tests/test_main.py` | Unit tests | After changes |

**See CODEBASE_MAP Section 3 for full code details**

---

## 📊 System Architecture (TL;DR)

```
Raw Data Sources (Weekly)
    ↓
[Data Scrapers] → partidos.txt, fbref_*.csv, sofascore_stats.json
    ↓
[Pipeline: Load Data]
    → Normalize team names via Glossary.txt
    → Parse dates and results
    ↓
[Build Features: 24 total]
    → Elo ratings (dynamic team strength)
    → Trailing stats (last 8 matches)
    → Expected goals (xG) from Elo + stats
    → Poisson probabilities from xG
    → Shin method from betting odds
    ↓
[Train Model: CatBoost]
    → Time-series 5-fold CV (prevent leakage)
    → 500 trees, learning rate 0.04
    → Sample weight for imbalance
    ↓
[Ensemble: 60% ML + 40% Poisson]
    → Blend model probabilities with Poisson
    → Determine scoreline from expected goals
    ↓
[Output]
    → Resultados_YYYYMMDD.txt (predictions)
    → feature_importance_YYYYMMDD.png (chart)
```

---

## 🧮 The Three Core Systems

### 1. Elo Rating System
**File:** `src/stats_engine.py` lines 14-32
**What:** Dynamic team strength ratings

**Formula:**
```
New_Elo = Old_Elo + 30 × (Actual - Expected)
Expected = 1 / (1 + 10^((opp_elo - your_elo + 65) / 400))
```

**Key insight:** Accumulates over match history, self-normalizing

---

### 2. Expected Goals (xG) Calculation
**File:** `src/stats_engine.py` lines 34-56
**What:** Quantifies offensive/defensive quality

**Formula:**
```
xG_home = (0.6×GF + 0.4×oppGA) × 1.22 × (1 + elo_diff/5000)
Clamp: [0.3, 2.5]
```

**Key insight:** Combines attack stats, defense stats, Elo, home advantage

---

### 3. Poisson Goal Modeling
**File:** `src/stats_engine.py` lines 58-123
**What:** Realistic probability distributions

**Formula:**
```
P(k goals) = (λ^k × e^-λ) / k!
Create 9×9 scoreline grid, calibrate to league averages
```

**Key insight:** Mathematically sound, but needs calibration for draw bias

---

## 🔧 Quick Configuration Changes

**Want higher Elo volatility?**
```python
# In src/config.py
K_FACTOR = 40  # Default: 30
```

**Want home teams to score more in xG?**
```python
# In src/config.py
HOME_BOOST = 1.30  # Default: 1.22
```

**Want to use LightGBM instead of CatBoost?**
```bash
# Environment variable
export ML_PREDICTOR_MODEL=lightgbm  # Default: catboost
```

**Want to change prediction blend?**
```python
# In src/model_engine.py line 107
ensemble_alpha = 0.70  # Default: 0.60 (was 60% ML / 40% Poisson)
```

---

## 📈 Data Pipeline Diagram

```
SOURCES
  ↓
football-data.co.uk ──→ data/ARG.csv (manual download)
TyC Sports ──→ scrape_tyc.py ──→ partidos.txt
FBref ──→ scrape_stats_enhanced.py ──→ src/fbref_*.csv
Sofascore ──→ scrape_sofascore_apify.py ──→ src/sofascore_stats.json
Footystats ──→ scrape_footystats.py ──→ src/footystats_*.csv
Glossary.txt ──[Manual] ──→ User mappings

PIPELINE (main.py)
  ├─ load_data()
  │  └─ Normalize + parse all sources
  ├─ build_features()
  │  ├─ calculate_all_elo_ratings()
  │  ├─ compute_trailing_features()
  │  ├─ calculate_poisson_features()
  │  └─ shin_method() from odds
  ├─ train_validate()
  │  └─ CatBoost with 5-fold TimeSeriesSplit
  └─ predict_fixtures()
     └─ Blend ML + Poisson

OUTPUT
  ├─ Resultados_YYYYMMDD.txt
  └─ feature_importance_YYYYMMDD.png
```

---

## 🧪 Testing Quick Reference

**Run all tests:**
```bash
pytest tests/test_main.py -v
```

**What's tested (21 test cases):**
- Team name normalization (3)
- Elo calculations (5)
- Poisson distributions (7)
- Trailing features (4)
- Integration tests (2)

**Run specific test:**
```bash
pytest tests/test_main.py::test_elo_update_home_win -v
```

**See CODEBASE_MAP Section 10 for full test details**

---

## 📍 Key Locations in Code

| Task | File | Lines |
|------|------|-------|
| Understand pipeline flow | `src/pipeline.py` | 65-108 (load_data) |
| | | 111-176 (build_features) |
| | | 178-231 (train_validate) |
| Understand Elo system | `src/stats_engine.py` | 14-32 |
| Understand Poisson | `src/stats_engine.py` | 58-143 |
| Understand prediction | `src/model_engine.py` | 38-193 |
| Understand features | `src/features.py` | 39-100 |
| Change hyperparameters | `src/config.py` | 1-65 |
| Debug normalization | `src/data_processing.py` | 39-61 |

---

## ✅ Before Running `python main.py`

Checklist:
- [ ] `.venv` virtual environment activated
- [ ] Requirements installed: `pip install -r requirements.txt`
- [ ] `data/ARG.csv` exists and has historical data
- [ ] `Glossary.txt` exists (optional but recommended)
- [ ] `partidos.txt` exists (from `python scrape_tyc.py`)
- [ ] `src/sofascore_stats.json` exists (from `python scrape_sofascore_apify.py`)

**Typical pre-run sequence:**
```bash
# Activate environment
.\.venv\Scripts\Activate.ps1

# Update data (5 min)
python scrape_tyc.py                    # Fixtures
python scrape_sofascore_apify.py        # Standings

# Run pipeline (2 min)
python main.py

# Results in:
# - Resultados_20250321.txt
# - feature_importance_20250321.png
```

---

## 🚀 Common Operations

### Add a new feature to the model
**See:** CODEBASE_MAP Section 15

### Change model type (LightGBM vs CatBoost)
**See:** QUICK_REFERENCE "Key Constants Cheat Sheet"

### Debug why predictions are all draws
**See:** QUICK_REFERENCE "Debugging Tips"

### Understand feature engineering
**See:** CODEBASE_MAP Section 9 (Algorithms)

### Add new data source
**See:** CODEBASE_MAP Section 4 (Data Scrapers)

### Tune Elo sensitivity
**See:** CODEBASE_MAP Section 11 (Known Constants)

---

## 📞 Documentation Navigation

**For Architecture Questions:**
→ CODEBASE_MAP Sections 1-3, 8

**For Algorithm Questions:**
→ CODEBASE_MAP Section 9, QUICK_REFERENCE "Key Algorithms"

**For Code Location Questions:**
→ CODEBASE_MAP Section 8 (File Structure), QUICK_REFERENCE "File Reference"

**For Running/Executing Questions:**
→ QUICK_REFERENCE "Common Tasks"

**For Configuration Questions:**
→ CODEBASE_MAP Section 5, QUICK_REFERENCE "Configuration"

**For Debugging Questions:**
→ QUICK_REFERENCE "Debugging Tips", CODEBASE_MAP Section 14

**For Extending/Adding Features:**
→ CODEBASE_MAP Section 15, QUICK_REFERENCE "Key Constants"

---

## 📊 Quick Stats

| Metric | Value |
|--------|-------|
| Total Python files (src) | 8 |
| Total lines of core code | ~1200 |
| Machine Learning features | 24 |
| Test coverage | 21 test cases |
| Supported models | 2 (CatBoost, LightGBM) |
| Data sources | 6+ |
| Prediction latency | <100ms per match |
| Model training time | ~5 seconds (5-fold CV) |

---

## 🎓 Learning Path (Recommended)

**Day 1: Basics (30 min)**
1. Read QUICK_REFERENCE (5 min)
2. Run `python main.py` (5 min)
3. Read CODEBASE_MAP Section 1-3 (20 min)

**Day 2: Deep Dive (1 hour)**
1. Read CODEBASE_MAP Section 9 (Algorithms) - 20 min
2. Read CODEBASE_MAP Section 3 (Key Modules) - 30 min
3. Look at `src/stats_engine.py` and `src/model_engine.py` - 10 min

**Day 3: Running & Extending (45 min)**
1. Read CODEBASE_MAP Section 15 (Development) - 15 min
2. Run full scraping workflow - 10 min
3. Try adding a test case - 20 min

---

## 📝 Note

Both documentation files are **generated from codebase analysis** and describe the current state of the system. They are:

- ✅ Implementation-focused (not aspirational)
- ✅ Detailed with actual line numbers and code paths
- ✅ Self-contained (no external references needed)
- ✅ Indexed and cross-referenced
- ✅ Ready for other developers or future reference

---

**Documentation Generated:** 2026-03-21
**System:** ML_Predictor2026_V2
**Target:** Liga Profesional Argentina Football Predictions
