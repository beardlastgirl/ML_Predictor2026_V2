# ML_Predictor2026_V2 - Project Guidelines

## Core Principles & Development Invariants

1. **Plain ASCII Output Only**:
   - Do NOT emit ANSI escape color sequences, icons, or emojis in terminal output or log files.
   - Use standard text prefixes: `[INFO]`, `[OK]`, `[WARNING]`, `[ERROR]`, `[SEASON CHECK]`.

2. **Centralized Hyperparameters**:
   - All model hyperparameters, weights, thresholds, and form parameters must reside in `src/config.py`.
   - Never hardcode numbers or tuning parameters inside feature calculations or model engine functions.

3. **Module Execution Protocol**:
   - Always run Python as modules from the project root: `python -m src.<module_name>`.
   - This prevents path resolution errors with `src.paths` and ensures uniform import behavior.
   - Use the virtual environment Python interpreter at `.venv\Scripts\python.exe`.

4. **Dynamic Model Identification**:
   - Report model types dynamically in logs and summaries using `type(result.model).__name__` rather than hardcoding "CatBoost" or "LightGBM".

5. **Probability Distribution Standard (Phase 3.0+)**:
   - The primary prediction output is a three-class probability distribution: `P(Away)`, `P(Draw)`, `P(Home)`.
   - Probabilities must sum to 1.0 (within ±0.01 tolerance).
   - Hard argmax classification is secondary and must not override probability calibration.
