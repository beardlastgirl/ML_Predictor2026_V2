# Technology Stack

**Project:** ML_Predictor2026_V2
**Researched:** 2026-03-19
**Overall Confidence:** HIGH

## Recommended Stack

### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.12+ | Primary Language | Standard for 2026, improved performance, and ecosystem compatibility. |
| CatBoost | Latest (v1.2+) | Primary ML Model | Best-in-class categorical feature handling (Team IDs, Leagues) without manual encoding. |
| LightGBM | Latest | Secondary ML Model | Extreme speed for rapid iteration and ensemble diversity. |
| TabPFN-v2 | Latest | Baseline/Small Data | State-of-the-art for "in-context" learning on small tabular datasets (useful for early-season predictions). |
| scikit-learn | 1.4+ | Calibration & Meta-learning | Essential for `CalibratedClassifierCV` and meta-learner (Logistic Regression). |

### Statistical Engine
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| statsmodels | Latest | Poisson Regression | Robust implementation of GLMs for Attack/Defense rating estimation. |
| penaltyblog | Latest | Dixon-Coles Modeling | Specialized football library for Bivariate Poisson and time-decay adjustments. |
| scipy | Latest | Distribution Math | Access to Poisson PMF and optimization routines for model fitting. |

### Data & Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| DuckDB | Latest | Analytics & In-memory DB | Extremely fast processing of tabular data (CSVs, Parquet) for feature engineering. |
| Playwright | Latest | Web Scraping | Successor to Selenium/Puppeteer; handles dynamic/JS-heavy sports & betting sites reliably. |
| PostgreSQL (Neon) | 16+ | Persistent Storage | Relational storage for historical matches and team metadata; JSONB for flexible event data. |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | 2.2+ | Data Manipulation | Core data processing and cleaning. |
| Polars | Latest | Fast Feature Engineering | Use when pandas becomes a bottleneck for large historical datasets. |
| MLflow | Latest | Experiment Tracking | Tracking model versions, hyperparameters, and calibration metrics. |
| Optuna | Latest | Hyperparameter Tuning | Automating the search for optimal boosting parameters. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Scraping | Playwright | BeautifulSoup | BS4 fails on JS-rendered content (Sofascore, Betting odds). |
| Data Processing | DuckDB / Polars | Native Pandas | Pandas is slower on large datasets and lacks DuckDB's SQL efficiency for complex joins. |
| Model Type | GBDTs (CatBoost) | Deep Learning (MLP) | Tabular data in 2026 still favors tree-based models for accuracy and interpretability. |
| ML Model | CatBoost | XGBoost | CatBoost handles the project's categorical nature (teams, venues) more natively than XGBoost. |

## Installation

```bash
# Core ML & Stats
pip install catboost lightgbm tabpfn scikit-learn statsmodels penaltyblog scipy

# Data & Scraping
pip install duckdb polars pandas playwright
playwright install chromium

# Experiment Tracking
pip install mlflow optuna
```

## Integration into Architecture

To integrate this stack into the current modular architecture:
1. **Calibration Layer**: Implement a new module `src/calibration.py` that wraps model outputs with `CalibratedClassifierCV`.
2. **Feature Store**: Use **DuckDB** in `src/data_processing.py` to accelerate the creation of rolling averages and Elo ratings.
3. **Hybrid Engine**: Use **TabPFN** as a "cold start" model for teams with limited data, switching to the **CatBoost/LightGBM Ensemble** as more match data is collected.
4. **Agent Orchestration**: Utilize a Coordinator-Worker pattern where a "Coordinator Agent" manages scraping tasks (via Playwright) and feeds data to "Model Workers."

## Sources

- [Google Search: Standard 2026 stack high-performance football match prediction](https://www.google.com/search?q=standard+2026+stack+high-performance+football+match+prediction) (Verified via multiple sources)
- [penaltyblog Documentation](https://pena.lt/) (Official source for Dixon-Coles implementation)
- [TabPFN-v2 Benchmarks](https://github.com/automl/TabPFN) (Research on small-data tabular performance)
- [DuckDB for Sports Analytics](https://duckdb.org/) (High-performance analytical patterns)
