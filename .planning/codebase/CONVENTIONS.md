# Coding Conventions

**Analysis Date:** 2026-03-15

## Naming Patterns

**Files:**
- snake_case for Python files: `main.py`, `scrape_stats_enhanced.py`, `data_processing.py`
- Prefix convention: `scrape_*` for scrapers, `*_engine.py` for core modules
- PowerShell: PascalCase: `run_model.ps1`, `setup_venv.ps1`

**Functions:**
- snake_case: `calculate_expected_goals`, `normalize_team_name`, `create_model`
- Descriptive verb-first: `load_data`, `build_features`, `predict_fixtures`
- Private helpers: No leading underscore (Python convention relaxed)

**Variables:**
- snake_case: `elo_ratings`, `cv_accuracies`, `feature_importance`
- DataFrames: `df`, `matches_df`, `fixtures_df`, `traildf`
- Loop variables: `idx`, `row`, `t_idx`, `v_idx`

**Types/Classes:**
- PascalCase: `PipelineResult` (only class in codebase)
- Dict keys: PascalCase for sports terms (`Home_Elo`, `Away_Form`)

## Code Style

**Formatting:**
- No auto-formatter configured (no `.prettierrc`, `black`, etc.)
- Consistent 4-space indentation
- Line length: ~100 characters (some files exceed)

**Linting:**
- No ESLint or flake8 configuration
- No type checking (mypy) configured

## Import Organization

**Order:**
1. Standard library: `import os`, `import sys`, `import json`
2. Third-party: `import pandas as pd`, `import numpy as np`
3. First-party: `from src.config import ...`, `from src.utils import ...`

**Path Aliases:**
- No path aliases configured
- Relative imports: `from src.pipeline import run_pipeline`
- sys.path manipulation in test files: `sys.path.insert(0, os.path.dirname(...))`

## Error Handling

**Patterns:**
- Try/except with custom logging:
  ```python
  try:
      data = json.load(f)
  except Exception as e:
      log_error(f"Error reading Sofascore data: {e}")
  ```
- Fail-fast: Raise after logging
- Graceful degradation: Return empty dict/list on file not found
- Validation: `pd.to_numeric(errors="coerce")` for data cleaning

**Custom Exceptions:**
- Standard Python exceptions: `ValueError`, `TimeoutError`, `ConnectionError`
- No custom exception classes

## Logging

**Framework:** Custom utilities in `src/utils.py`

**Patterns:**
- Four levels: `log_info`, `log_ok`, `log_error`, `log_warning`
- Plain ASCII prefixes: `[INFO]`, `[OK]`, `[ERROR]`, `[WARNING]`
- No ANSI colors (per project guidelines in CLAUDE.md)
- Console output only (no file logging)

**Usage:**
```python
from src.utils import log_info, log_ok, log_error

log_info("Loading data...")
log_ok(f"Loaded {len(data)} records")
log_error(f"Failed: {e}")
```

## Comments

**When to Comment:**
- Module docstrings explain purpose
- Complex math has inline comments
- Function docstrings for public APIs

**Docstrings:**
- Google-style for functions:
  ```python
  def calculate_expected_goals(...):
      """Calculate expected goals for each team."""
  ```
- Args/Returns documented in longer functions:
  ```python
  Args:
      elo_team: Current Elo rating
      elo_opp: Opponent Elo rating
  Returns:
      float: Expected score
  ```

## Function Design

**Size:**
- Small utilities: 10-30 lines (`src/utils.py`)
- Medium functions: 30-60 lines (`stats_engine` functions)
- Large functions: 60-100 lines (`pipeline.py` functions)

**Parameters:**
- Explicit parameters preferred over **kwargs
- Default values for optional: `window=8`, `headless=False`
- Config from `src/config.py` not passed as parameters

**Return Values:**
- Single value for simple functions
- Dict for multiple related values: `calculate_poisson_features` returns 9 keys
- Tuple for unrelated multiple returns: `return elo_ratings, elo_history`
- Class for complex results: `PipelineResult`

## Module Design

**Exports:**
- No `__all__` declarations
- Direct imports from modules: `from src.stats_engine import calculate_poisson_features`

**Barrel Files:**
- `src/__init__.py` is empty (package marker only)
- No re-exports from `__init__.py`

**Coupling:**
- `pipeline.py` imports from all other modules
- `model_engine.py` imports `stats_engine` and `features`
- `stats_engine.py` and `features.py` are leaf modules (no internal imports)

## Class Design

**PipelineResult:**
- Purpose: Data container for pipeline outputs
- Pattern: Simple data class (no inheritance)
- Attributes typed with annotations: `cv_accuracies: List[float]`

## Anti-Patterns Observed

**Magic Numbers:**
- Some hardcoded values in functions (mitigated by `config.py`)
- Sample weight value `0.7` for draws in `pipeline.py`

**Long Functions:**
- `predict_gameweek` in `model_engine.py`: ~190 lines
- `fetch_page_with_selenium` in `scrape_stats_enhanced.py`: ~90 lines

**Code Duplication:**
- Team name normalization logic duplicated across scrapers
- Logging functions duplicated in each scraper

---

*Convention analysis: 2026-03-15*
