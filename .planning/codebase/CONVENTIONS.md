# Coding Conventions

**Analysis Date:** 2025-01-20

## Naming Patterns

**Files:**
- Lowercase with underscores: `utils.py`, `data_processing.py`, `stats_engine.py`
- Purpose-driven names reflecting domain: `features.py` (feature engineering), `model_engine.py` (model operations), `pipeline.py` (orchestration)

**Modules:**
- Core modules live in `src/`: `src/config.py`, `src/utils.py`, `src/data_processing.py`, etc.
- Single-word modules for utilities: `utils.py`, `config.py`
- Compound names for domain-specific modules: `data_processing.py`, `model_engine.py`, `stats_engine.py`

**Functions:**
- lowercase with underscores: `normalize_team_name()`, `calculate_expected_goals()`, `get_team_trailing_stats()`
- Verb-first pattern for actions: `load_data()`, `build_features()`, `train_validate()`, `predict_gameweek()`
- Descriptive names reflecting complete action: `calculate_outcome_probabilities()` (not just `probabilities()`)

**Variables:**
- lowercase with underscores: `home_elo`, `expected_result`, `team_history`
- Abbreviated meaningful names acceptable: `xG_home`, `p_home_win`, `gf` (goals for), `ga` (goals against)

**Constants:**
- UPPERCASE with underscores: `BASE_ELO = 1500`, `K_FACTOR = 30`, `MAX_GOALS = 8`
- Located in `src/config.py` module
- Example from `src/config.py`:
  ```python
  BASE_ELO = 1500
  K_FACTOR = 30
  HOME_ADVANTAGE = 65
  ELO_DIVISOR = 400
  BASE_GOAL_RATE = 1.89
  MAX_GOALS = 8
  RESULT_ENCODING = {"H": 2, "D": 1, "A": 0}  # Home Win, Draw, Away Win
  TRAILING_WINDOW = 8
  ```

**Feature Columns:**
- Title_Case_With_Underscores naming convention for all dataframe features
- Examples from `src/pipeline.py` FEATURE_COLUMNS list:
  ```python
  "Home_Elo", "Away_Elo", "Elo_Diff",
  "Home_Avg_GF", "Away_Avg_GF", "Home_Avg_GA", "Away_Avg_GA",
  "Home_Form", "Away_Form",
  "Attack_Balance", "Def_Balance", "Form_Balance",
  "xG_home", "xG_away", "xG_diff",
  "Poisson_Home_Win", "Poisson_Draw", "Poisson_Away_Win",
  "Expected_Home_Goals", "Expected_Away_Goals", "Expected_Total_Goals",
  "Shin_Prob_H", "Shin_Prob_D", "Shin_Prob_A",
  ```
- Prefix with team side: `Home_*`, `Away_*` for team-specific features
- Abbreviated xG notation: `xG_home`, `xG_away`, `xG_diff`
- Probability features: `Poisson_Home_Win`, `Poisson_Draw`, `Poisson_Away_Win`
- Statistical features: `Home_Avg_GF`, `Home_Avg_GA`, `Home_Form`

**Result Encoding:**
- Fixed convention in `src/config.py`:
  ```python
  RESULT_ENCODING = {"H": 2, "D": 1, "A": 0}  # Home Win, Draw, Away Win
  RESULT_DECODING = {2: "Home Win", 1: "Draw", 0: "Away Win"}
  ```
- Home Win = 2, Draw = 1, Away Win = 0 (used throughout pipeline)
- Applied in `src/pipeline.py` line 99: `matches["Res"] = matches["Res"].map(RESULT_ENCODING)`

## Code Style

**Formatting:**
- Python standard: 2-4 spaces per indentation level (consistent within modules)
- Line length: No strict limit observed, but kept under 100 chars in most cases
- No automatic formatter configured (black/autopep8 not in requirements.txt)

**Imports:**
- Standard library first (os, sys, json, re, glob, datetime)
- Third-party libraries next (pandas, numpy, scipy, sklearn, matplotlib, etc.)
- Local imports last (from src import...)
- Example from `src/pipeline.py`:
  ```python
  import os
  from datetime import datetime
  from typing import Dict, List, Optional, Tuple
  
  import matplotlib
  import matplotlib.pyplot as plt
  import numpy as np
  import pandas as pd
  from sklearn.metrics import accuracy_score, log_loss
  from sklearn.model_selection import TimeSeriesSplit
  
  from src.config import BASE_ELO, MODEL_TYPE, TRAILING_WINDOW, RESULT_ENCODING
  from src.utils import log_info, log_ok, log_error, log_warning
  ```

**Linting:**
- No linter configuration detected (no .pylintrc, .flake8, etc.)
- Code follows PEP 8 conventions informally

## Import Organization

**Order:**
1. Standard library: `os`, `sys`, `json`, `re`, `glob`, `datetime`, `typing`
2. Third-party data science: `pandas`, `numpy`, `scipy`, `matplotlib`, `sklearn`
3. Third-party ML: `lightgbm`, `catboost`, `sklearn.metrics`, `sklearn.model_selection`
4. Local imports: `from src.config import`, `from src.utils import`, etc.

**Path Aliases:**
- No aliases configured (no @app or similar patterns)
- Direct relative imports: `from src.config import BASE_ELO`
- Explicit module path for testing: `sys.path.insert(0, os.path.dirname(...))` in `tests/test_main.py` line 20

## Error Handling

**Patterns:**
- Try/Except blocks used for file operations and data loading
- Example from `src/data_processing.py` lines 16-36:
  ```python
  try:
      with open(filepath, "r", encoding="utf-8") as f:
          for line in f:
              # process line
      log_ok(f"Loaded {len(glossary)} team name mappings from glossary")
  except Exception as e:
      log_error(f"Error reading glossary: {e}")
  ```
- File-not-found warnings (non-fatal): `log_warning(f"File not found: {path}")`
- Return empty dict/list on error: `return {}` or `return pd.DataFrame()`
- ValueError for invalid model types: `raise ValueError(f"Unknown model type: {model_type}")` in `src/model_engine.py` line 36
- Pipeline-level exception re-raising with logging: `except Exception as e: log_error(...); raise` in `src/pipeline.py` line 401

## Logging

**Framework:** Custom logging functions from `src/utils.py`

**Functions:**
- `log_info(message)` - General information, prefixed with `[INFO]`
- `log_ok(message)` - Success messages, prefixed with `[OK]`
- `log_warning(message)` - Warning messages, prefixed with `[WARNING]`
- `log_error(message)` - Error messages, prefixed with `[ERROR]`
- All functions use simple print with formatted strings: `print(f"[INFO] {message}")`

**Patterns:**
- Entry point logging: `log_info("Loading data...")` at function start
- Success logging: `log_ok(f"Trailing features computed for {len(result)} matches")` at function end
- State logging: `log_info(f"Precomputed trailing stats for {len(latest_stats)} teams")`
- Data availability logging: `log_ok(f"Loaded Sofascore data for {len(sofascore_data)} teams")`
- Pipeline execution: `log_info("=" * 60)` for section markers
- Used throughout: `src/pipeline.py` (lines 82, 101, 120, 195), `src/features.py` (lines 41, 74)

## Comments

**When to Comment:**
- Algorithm explanation (Shin Method derivation in `src/stats_engine.py` lines 175-179)
- Non-obvious calculations: `# Grid of scoreline probabilities: grid[h, a] = P(home=h, away=a)`
- Configuration rationale: `# Home team scoring boost (calibrated for league average)` in `src/config.py` line 15
- Complex logic: Draw calibration in `src/stats_engine.py` lines 85-98

**JSDoc/TSDoc:**
- Docstrings used for major functions (not all functions have them)
- Triple-quoted docstrings for module and class docstrings
- Example from `src/pipeline.py` lines 65-80:
  ```python
  def load_data(
      glossary_path: str = "Glossary.txt",
      sofascore_path: str = "src/sofascore_stats.json",
      fixtures_path: str = "partidos.txt",
      historical_path: str = "data/ARG.csv"
  ) -> Tuple[Dict, Dict, pd.DataFrame, Optional[pd.DataFrame]]:
      """Load and normalize all input data.
      
      Args:
          glossary_path: Path to team name glossary
          sofascore_path: Path to Sofascore standings JSON
          fixtures_path: Path to fixtures file
          historical_path: Path to historical match data CSV
      
      Returns:
          Tuple of (glossary, sofascore_data, matches_df, fixtures_df)
      """
  ```
- Type hints used consistently in function signatures
- Example from `src/stats_engine.py`:
  ```python
  def calculate_expected_goals(
      elo_home, elo_away, avg_gf_home, avg_gf_away, avg_ga_home, avg_ga_away
  ):
      """Calculate expected goals for each team."""
  ```

## Function Design

**Size:**
- Small focused functions: 5-15 lines typical
- Larger functions: 30-50 lines for complex calculations (`calculate_outcome_probabilities` ~40 lines)
- Maximum in codebase: ~100 lines (`predict_gameweek` in `src/model_engine.py`)

**Parameters:**
- Positional parameters for core data: `df`, `elo_ratings`, `model`
- Optional parameters with defaults: `window=8`, `n_splits=5`, `model_type=MODEL_TYPE`
- Example from `src/features.py` line 7:
  ```python
  def get_team_trailing_stats(history, window):
      """Calculate trailing statistics from team history."""
  ```
- Keyword arguments for configuration: `class_weights=None` in `src/model_engine.py` line 16

**Return Values:**
- Single values: `return elo_ratings`
- Tuples for multiple outputs: `return elo_ratings, elo_history` in `src/stats_engine.py` line 173
- DataFrames for data results: `return pd.DataFrame(trailing_features)`
- Dictionaries for feature results: `return dict of calculated features`
- Type hints used: `-> Tuple[Dict, Dict, pd.DataFrame, Optional[pd.DataFrame]]`

## Module Design

**Exports:**
- All functions at module level (no private/public convention with underscores)
- Helper functions prefixed with underscore when internal: `_extract_sofa_stats()` in `src/data_processing.py` line 114
- Clear module responsibilities:
  - `src/config.py`: Constants and hyperparameters (export constants)
  - `src/utils.py`: Logging and utilities (export helper functions)
  - `src/data_processing.py`: Data loading and normalization (export data functions)
  - `src/features.py`: Feature engineering (export feature functions)
  - `src/stats_engine.py`: Elo and Poisson calculations (export statistical functions)
  - `src/model_engine.py`: ML model operations (export model functions)
  - `src/pipeline.py`: Orchestration (export pipeline functions and PipelineResult class)

**Class Usage:**
- Container class for pipeline results: `PipelineResult` in `src/pipeline.py` lines 51-62
  ```python
  class PipelineResult:
      """Container for pipeline execution results."""
      def __init__(self):
          self.model = None
          self.elo_ratings: Dict = {}
          self.features: List[str] = []
          self.cv_accuracies: List[float] = []
          self.cv_log_losses: List[float] = []
          self.fixtures: Optional[pd.DataFrame] = None
          self.output_file: Optional[str] = None
          self.feature_importance: Optional[pd.DataFrame] = None
  ```
- No class hierarchies or inheritance patterns
- Dataclasses not used (no @dataclass decorators)

**Barrel Files:**
- No barrel file pattern (no `__init__.py` re-exports)
- `src/__init__.py` is empty
- Direct imports from modules: `from src.config import BASE_ELO`

## Common Patterns

**Data Pipeline Pattern:**
Functions follow load → transform → compute → return flow:
1. Load data with validation
2. Normalize/transform data
3. Compute features/results
4. Return results with logging

Example from `src/features.py` lines 39-75 (compute_trailing_features):
```python
def compute_trailing_features(matches_df, window=8):
    """Compute trailing-average features for each team chronologically."""
    log_info(f"Computing trailing features with window={window}...")
    team_history = {}
    trailing_features = []
    for idx, row in matches_df.iterrows():
        # compute
        trailing_features.append({...})
    traildf = pd.DataFrame(trailing_features)
    # merge
    log_ok(f"Trailing features computed for {len(result)} matches")
    return result
```

**Calculation Pattern:**
Functions extract inputs → calculate → format output:
```python
def update_elo(home_elo, away_elo, result):
    """Update Elo ratings given match result (2=Home win, 1=Draw, 0=Away win)."""
    exp_home = expected_result(home_elo + HOME_ADVANTAGE, away_elo)
    exp_away = 1 - exp_home
    
    if result == 2:
        home_score, away_score = 1, 0
    # ... calculate
    home_elo_new = home_elo + K_FACTOR * (home_score - exp_home)
    away_elo_new = away_elo + K_FACTOR * (away_score - exp_away)
    return home_elo_new, away_elo_new
```

## Configuration Management

**Approach:**
- Centralized configuration in `src/config.py`
- All hyperparameters and constants defined there
- Environment variable support: `MODEL_TYPE = os.environ.get("ML_PREDICTOR_MODEL", "catboost").strip().lower()`
- Config imported at module level: `from src.config import BASE_ELO, K_FACTOR, ...`

**Parameter Organization:**
- Elo parameters (lines 5-10)
- Poisson parameters (lines 12-19)
- Probability calibration (lines 21-22)
- Result encoding (lines 24-26)
- Prediction thresholds (lines 28-32)
- Trailing window (line 34)
- Model selection (lines 36-40)
- Model hyperparameters by type (lines 42-64):
  ```python
  MODEL_PARAMS = {
      "lightgbm": {...},
      "catboost": {...}
  }
  ```

**Usage Pattern:**
Import specific constants needed:
```python
from src.config import (
    HOME_ADVANTAGE, K_FACTOR, MAX_GOALS, BASE_GOAL_RATE,
    ELO_DIVISOR, ELO_FACTOR_DENOM, HOME_BOOST,
    GOAL_WEIGHT_ATTACK, GOAL_WEIGHT_DEFENSE, XG_MIN, XG_MAX,
    BASE_ELO, POISSON_DRAW_ADJUSTMENT
)
```

## Type Hints

**Usage:**
- Function parameters: `def load_data(glossary_path: str = "Glossary.txt", ...) -> Tuple[...]:`
- Return types always specified for public functions
- Complex types from typing module: `Dict`, `List`, `Optional`, `Tuple`
- Example from `src/pipeline.py`:
  ```python
  def train_validate(
      df: pd.DataFrame,
      features: List[str],
      model_type: str = MODEL_TYPE,
      n_splits: int = 5,
  ) -> Tuple[any, List[float], List[float]]:
  ```

---

*Convention analysis: 2025-01-20*
