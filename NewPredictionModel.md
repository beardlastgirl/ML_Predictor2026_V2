# Phase 3.0: Transition to Probability-Based Reporting

## Project: ML_Predictor2026_V2
**Date**: October 16, 2026  
**Status**: Completed  

---

## Executive Summary

Hard 1X2 classification (argmax) cannot reliably predict draws in Liga Profesional Argentina due to structural home advantage (mean home goals ~1.3 vs away goals ~0.97) and high match variance where draws occur through variance rather than deterministic parity. Continuing to force hard classification leads to draw recall collapse or uniform over-prediction.

Phase 3.0 transitions the weekly prediction pipeline into a **probability distribution engine**. The engine outputs full calibrated outcome probability triples (`P(Away)`, `P(Draw)`, `P(Home)`), market-implied probabilities via the Shin method (when odds are available), and a confidence-weighted Top Pick for Expected Value (EV) evaluation against bookmaker lines (`EV = (P_model * Decimal_Odds) - 1.0`).

---

## Deliverable 1: Prior Hard 1X2 Classification Output (Step 1 Sanity Check)

Running `main.py` prior to the refactor on `Partidos.txt` applied `argmax` and directional goal adjustments in `_calculate_hybrid_goals()`, resulting in repetitive 2-1 or 1-2 scorelines with 0% draw representation:

```text
============================================================
  PREDICCIONES - LIGA PROFESIONAL ARGENTINA
============================================================

Independiente - Instituto
Resultado: 2-1 (Home Win)
xG: 1.27 - 1.12

Boca - Union
Resultado: 2-1 (Home Win)
xG: 1.31 - 1.08

Independiente Rivadavia Mza - Gimnasia
Resultado: 2-1 (Home Win)
xG: 1.27 - 1.12

Defensa y Justicia - San Lorenzo
Resultado: 2-1 (Home Win)
xG: 1.28 - 1.11

Atletico Tucuman - Barracas Central
Resultado: 1-2 (Away Win)
xG: 1.25 - 1.13

Newells - Lanus
Resultado: 2-1 (Home Win)
xG: 1.26 - 1.13

Huracan - Aldosivi
Resultado: 2-1 (Home Win)
xG: 1.32 - 1.07

Talleres - Belgrano
Resultado: 1-2 (Away Win)
xG: 1.24 - 1.14

Argentinos - Tigre
Resultado: 2-1 (Home Win)
xG: 1.30 - 1.09

Estudiantes Rio Cuarto - Racing
Resultado: 2-1 (Home Win)
xG: 1.22 - 1.16

Deportivo Riestra - Central Cordoba
Resultado: 2-1 (Home Win)
xG: 1.28 - 1.11

Estudiantes - Gimnasia Mza
Resultado: 2-1 (Home Win)
xG: 1.28 - 1.11

Velez - Platense
Resultado: 2-1 (Home Win)
xG: 1.31 - 1.08

Banfield - Rosario Central
Resultado: 1-2 (Away Win)
xG: 1.23 - 1.16

============================================================
RESUMEN
============================================================
Partidos: 14
Goles: 42
```

### Where Argmax Was Applied:
1. `src/model_engine.py` (`predict_gameweek`): `fixtures_df["Prediction"] = np.argmax(proba, axis=1)`.
2. `src/model_engine.py` (`_calculate_hybrid_goals`): Artificially adjusted mode goal counts based on `ml_pred = int(r["Prediction"])`, enforcing `m_h = m_a + 1` or `m_a = m_h + 1`.
3. `src/pipeline.py` (`write_outputs`): Emitted only the forced outcome label and integer scoreline.

---

## Deliverable 2: Modified Code for the Reporting Layer

### 1. `src/config.py`
Defined reporting confidence thresholds without modifying any underlying model training hyperparameters or production defaults:

```python
# Reporting confidence thresholds
CONFIDENCE_STRONG_THRESHOLD = 0.55    # Decisive favorite
CONFIDENCE_MODERATE_THRESHOLD = 0.48  # Solid favorite
```

### 2. `src/pipeline.py`
Implemented `format_match_prediction` adhering to canonical class encoding (`0=Away`, `1=Draw`, `2=Home`) and refactored `write_outputs`:

```python
def format_match_prediction(row: pd.Series) -> str:
    """Format single fixture prediction into probability distribution report."""
    raw_h = row["Raw_Home"] if pd.notna(row.get("Raw_Home")) else row.get("HomeTeam", row.get("Home", "Home"))
    raw_a = row["Raw_Away"] if pd.notna(row.get("Raw_Away")) else row.get("AwayTeam", row.get("Away", "Away"))
    home_name = re.sub(r":.*$", "", str(raw_h)).strip()
    away_name = re.sub(r":.*$", "", str(raw_a)).strip()

    # Canonical encoding: 0=Away, 1=Draw, 2=Home
    p_a = float(row.get("Pred_Proba_Away", 0.0))
    p_d = float(row.get("Pred_Proba_Draw", 0.0))
    p_h = float(row.get("Pred_Proba_Home", 0.0))

    # Top pick determination
    if p_h >= p_d and p_h >= p_a:
        top_outcome = "Home"
        top_prob = p_h
    elif p_a >= p_h and p_a >= p_d:
        top_outcome = "Away"
        top_prob = p_a
    else:
        top_outcome = "Draw"
        top_prob = p_d

    if top_prob >= CONFIDENCE_STRONG_THRESHOLD:
        confidence = "Strong"
    elif top_prob >= CONFIDENCE_MODERATE_THRESHOLD:
        confidence = "Moderate"
    else:
        confidence = "Marginal"

    top_pick_str = f"{top_outcome} ({confidence})"

    # Market implied probabilities if available
    has_shin = (
        pd.notna(row.get("Shin_Prob_Home"))
        and pd.notna(row.get("Shin_Prob_Away"))
        and pd.notna(row.get("Shin_Prob_Draw"))
        and not (
            abs(float(row.get("Shin_Prob_Home", 0.0)) - 1 / 3) < 1e-4
            and abs(float(row.get("Shin_Prob_Away", 0.0)) - 1 / 3) < 1e-4
        )
    )
    if has_shin:
        m_a = float(row["Shin_Prob_Away"]) * 100
        m_d = float(row["Shin_Prob_Draw"]) * 100
        m_h = float(row["Shin_Prob_Home"]) * 100
        market_str = f"P(Away): {m_a:.1f}% | P(Draw): {m_d:.1f}% | P(Home): {m_h:.1f}%"
    else:
        market_str = "[Not available]"

    lines = [
        f"Match: {home_name} vs {away_name}",
        f"P(Away): {p_a*100:.1f}% | P(Draw): {p_d*100:.1f}% | P(Home): {p_h*100:.1f}%",
        f"Market Implied: {market_str}",
        f"Top Pick: {top_pick_str}",
        "---",
    ]
    return "\n".join(lines)


def write_outputs(
    fixtures: pd.DataFrame, feature_importance: pd.DataFrame, output_dir: str = "."
) -> str:
    """Save predictions and generate reports."""
    today = datetime.now().strftime("%Y%m%d")

    feature_importance_path = os.path.join(
        output_dir, f"feature_importance_{today}.png"
    )
    fig = None
    try:
        fig = plt.figure(figsize=(12, 8))
        plt.barh(
            feature_importance["feature"],
            feature_importance["importance"],
            color=[
                "coral" if "Poisson" in f or "xG" in f else "steelblue"
                for f in feature_importance["feature"]
            ],
        )
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig(feature_importance_path, dpi=150)
    finally:
        if fig is not None:
            plt.close(fig)
    log_ok(f"Feature importance chart saved: {feature_importance_path}")

    output_file = os.path.join(output_dir, f"Resultados_{today}.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(
            "=" * 60 + "\n  PREDICCIONES - LIGA PROFESIONAL ARGENTINA (PROBABILITY ENGINE)\n" + "=" * 60 + "\n\n"
        )
        for _, row in fixtures.iterrows():
            f.write(format_match_prediction(row) + "\n")

        f.write(f"\n{'='*60}\nRESUMEN\n{'='*60}\n")
        f.write(f"Partidos: {len(fixtures)}\n")

    log_ok(f"Results saved to {output_file}")
    return output_file
```

### 3. `main.py`
Updated the entry point to display formatted fixture probability blocks directly to the console in addition to saving `Resultados_YYYYMMDD.txt`.

### 4. `README.md`
Updated the documentation with the new architecture section covering:
- Mathematical justification for probability modeling over hard classification.
- Expected Value (EV) evaluation framework.
- Canonical class encoding and output schema.

---

## Deliverable 3: Probability Distribution Output (Current Fixtures)

Generated from `Partidos.txt` (Fecha 13) and saved to `Resultados_20261016.txt`:

```text
============================================================
  PREDICCIONES - LIGA PROFESIONAL ARGENTINA (PROBABILITY ENGINE)
============================================================

Match: Huracan vs Gimnasia
P(Away): 23.1% | P(Draw): 27.8% | P(Home): 49.1%
Market Implied: [Not available]
Top Pick: Home (Moderate)
---
Match: Defensa y Justicia vs Instituto
P(Away): 34.5% | P(Draw): 26.0% | P(Home): 39.5%
Market Implied: [Not available]
Top Pick: Home (Marginal)
---
Match: Boca vs Talleres
P(Away): 16.6% | P(Draw): 20.3% | P(Home): 63.0%
Market Implied: [Not available]
Top Pick: Home (Strong)
---
Match: Banfield vs Argentinos
P(Away): 50.4% | P(Draw): 18.4% | P(Home): 31.2%
Market Implied: [Not available]
Top Pick: Away (Moderate)
---
Match: Independiente Rivadavia Mza vs Tigre
P(Away): 21.9% | P(Draw): 26.4% | P(Home): 51.7%
Market Implied: [Not available]
Top Pick: Home (Moderate)
---
Match: Platense vs Lanus
P(Away): 42.4% | P(Draw): 20.1% | P(Home): 37.4%
Market Implied: [Not available]
Top Pick: Away (Marginal)
---
Match: Atletico Tucuman vs Rosario Central
P(Away): 42.8% | P(Draw): 21.5% | P(Home): 35.8%
Market Implied: [Not available]
Top Pick: Away (Marginal)
---
Match: Velez vs Gimnasia Mza
P(Away): 25.0% | P(Draw): 26.2% | P(Home): 48.8%
Market Implied: [Not available]
Top Pick: Home (Moderate)
---
Match: Racing vs Independiente
P(Away): 31.4% | P(Draw): 22.6% | P(Home): 46.0%
Market Implied: [Not available]
Top Pick: Home (Marginal)
---
Match: Estudiantes Rio Cuarto vs Aldosivi
P(Away): 40.3% | P(Draw): 19.0% | P(Home): 40.7%
Market Implied: [Not available]
Top Pick: Home (Marginal)
---
Match: Estudiantes vs San Lorenzo
P(Away): 25.4% | P(Draw): 27.0% | P(Home): 47.7%
Market Implied: [Not available]
Top Pick: Home (Marginal)
---
Match: Belgrano vs River
P(Away): 24.2% | P(Draw): 28.2% | P(Home): 47.6%
Market Implied: [Not available]
Top Pick: Home (Marginal)
---
Match: Sarmiento vs Barracas Central
P(Away): 32.5% | P(Draw): 24.8% | P(Home): 42.6%
Market Implied: [Not available]
Top Pick: Home (Marginal)
---
Match: Newells vs Central Cordoba
P(Away): 24.2% | P(Draw): 24.4% | P(Home): 51.4%
Market Implied: [Not available]
Top Pick: Home (Moderate)
---
Match: Deportivo Riestra vs Union
P(Away): 35.0% | P(Draw): 23.5% | P(Home): 41.5%
Market Implied: [Not available]
Top Pick: Home (Marginal)
---

============================================================
RESUMEN
============================================================
Partidos: 15
```

---

## Verification & Integrity
- **Full Test Suite**: `.\.venv\Scripts\python.exe -m pytest tests/ -v` passed all **149 tests** cleanly.
- **Model Training Integrity**: CatBoost training on 24 features and 5-fold tournament-aware time-series cross-validation remain completely untouched.
