---
name: gameweek-pipeline
description: End-to-end execution workflow for weekly Argentine Liga Profesional match predictions. Validates ARG.csv freshness, checks Partidos.txt, computes temporal batch features, executes the Dixon-Coles + CatBoost model, and formats calibrated probability distributions and EV outputs.
---

# Gameweek Prediction Pipeline Skill

This skill guides the complete operational execution of the weekly prediction cycle for Liga Profesional Argentina in `ML_Predictor2026_V2`.

## Execution Overview

The pipeline executes five core stages:
1. **Pre-flight & Data Ingestion**: Verifies dataset freshness (`ARG.csv`), updates from `football-data.co.uk` if >5 days old, and confirms `.venv` activation.
2. **Fixture Parsing & Glossary Check**: Reads `Partidos.txt` and normalizes team names via `Glossary.txt`.
3. **Temporal Batching**: Computes Dixon-Coles parameters, Elo ratings, and rolling form features via `src/batched_features.py` (preserving zero lookahead bias).
4. **Model Inference**: Generates calibrated three-class probability distributions: $P(\text{Home})$, $P(\text{Draw})$, $P(\text{Away})$.
5. **Report & Output Formatting**: Saves results to `Resultados_YYYYMMDD.txt` and updates `feature_importance_YYYYMMDD.png`.

---

## Step-by-Step Runbook

### Step 1: Pre-flight Verification

Run the preflight check script:
```powershell
.\.venv\Scripts\python.exe .agents/scripts/preflight_check.py
```

If `data/ARG.csv` is older than 5 days or missing, download the latest version:
```powershell
Invoke-WebRequest -Uri "https://football-data.co.uk/new/ARG.csv" -OutFile "data/ARG.csv" -UseBasicParsing
```

### Step 2: Fixture Preparation (`Partidos.txt`)

Ensure `Partidos.txt` (or `partidos.txt`) contains the upcoming round's matches formatted as:
```text
Home Team - Away Team
```
Example:
```text
Boca Juniors - River Plate
Racing Club - Independiente
San Lorenzo - Huracan
```

Run a quick dry-run check to verify all teams exist in `Glossary.txt`:
```powershell
.\.venv\Scripts\python.exe -c "from src.data_processing import load_glossary, parse_fixtures; g = load_glossary('Glossary.txt'); f = parse_fixtures('Partidos.txt'); print(f'[OK] {len(f)} fixtures parsed successfully')"
```

### Step 3: Fast Regression Gate

Before executing the full pipeline, verify mathematical and temporal invariants:
```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_golden_math.py tests/test_temporal_ordering.py tests/test_leakage.py -q
```
*Requirement*: All 26 fast tests must pass.

### Step 4: Run the Prediction Pipeline

Execute the main entry point:
```powershell
.\.venv\Scripts\python.exe main.py
```

To switch models, set the `ML_PREDICTOR_MODEL` environment variable:
```powershell
# Default: CatBoost
$env:ML_PREDICTOR_MODEL = "catboost"
.\.venv\Scripts\python.exe main.py

# Alternative: LightGBM
$env:ML_PREDICTOR_MODEL = "lightgbm"
.\.venv\Scripts\python.exe main.py
```

### Step 5: Validate Output & Expected Value (EV)

1. Verify that the output file was generated:
   ```powershell
   Get-ChildItem -Filter "Resultados_*.txt" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
   ```
2. Verify probability calibration:
   - For every fixture, confirm:
     $$|P(\text{Home}) + P(\text{Draw}) + P(\text{Away}) - 1.0| < 0.01$$
3. EV Calculation vs Market Odds:
   If decimal bookmaker odds are available:
   $$\text{EV} = (P_{\text{model}} \times \text{Decimal\_Odds}) - 1.0$$
   - Flag matches where $\text{EV} > +0.05$ (5% positive expected value) as value recommendations.

---

## Troubleshooting & Diagnostics

- **Unmapped Team Warning**: If `[SEASON CHECK]` or `KeyError` appears during parsing, trigger the `team-glossary-auditor` skill to resolve missing aliases.
- **Missing Date/Time**: Missing or malformed times in `ARG.csv` are safely handled by `src/batched_features.py` as conservative day-batches.
- **CatBoost Info Directory**: Delete temporary `catboost_info/` directory after testing if disk space is needed.
