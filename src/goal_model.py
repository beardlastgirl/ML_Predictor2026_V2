"""Phase 1 — Goal-Based Generative Model (Dixon-Coles / Bivariate Poisson).

Predicts 3-class (Away/Draw/Home) outcomes from a minimal feature set:
  Elo_Diff, xG_diff, Home_Advantage parameter.

Derives P(Away), P(Draw), P(Home) analytically from the
bivariate Poisson distribution with Dixon-Coles correlation
adjustment.

Used as the architectural pivot from the 24-feature CatBoost
outcome classifier.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss


# ---------------------------------------------------------------------------
# Minimal feature extraction
# ---------------------------------------------------------------------------

def build_minimal_frame(matches: pd.DataFrame) -> pd.DataFrame:
    """Create the minimal feature frame for the goal model.

    Requires columns: Home, Away, Elo_Diff, xG_diff (present in the matches
    dataframe from the canonical pipeline feature set).

    Adds regression targets: home_goals (HG), away_goals (AG).
    Adds a constant Home_Advantage parameter.
    """
    df = matches[["Home", "Away", "Elo_Diff", "xG_diff"]].copy()
    df["home_goals"] = matches["HG"].astype(int)
    df["away_goals"] = matches["AG"].astype(int)
    df["home_advantage"] = 0.30  # empirically estimated HA in goals
    return df


# ---------------------------------------------------------------------------
# Poisson regression for expected goals
# ---------------------------------------------------------------------------

def fit_poisson_models(df: pd.DataFrame):
    """Fit separate Poisson regressors for home and away goals.

    Uses the minimal feature set: Elo_Diff, xG_diff, home_advantage.
    Returns the fitted models (not just lambdas) so we can predict per-row.
    """
    # Home goals model: includes home_advantage
    home_x = df[["Elo_Diff", "xG_diff", "home_advantage"]].values
    home_y = df["home_goals"].values
    home_mod = PoissonRegressor(fit_intercept=True)
    home_mod.fit(home_x, home_y)

    # Away goals model: does NOT include home_advantage
    away_x = df[["Elo_Diff", "xG_diff"]].values
    away_y = df["away_goals"].values
    away_mod = PoissonRegressor(fit_intercept=True)
    away_mod.fit(away_x, away_y)

    return home_mod, away_mod


# ---------------------------------------------------------------------------
# Bivariate Poisson → 3-class probabilities (per-row)
# ---------------------------------------------------------------------------

def bivariate_poisson_3class_row(lambda_h: float, lambda_a: float,
                                rho: float = 0.14) -> dict[str, float]:
    """Derive P(Away), P(Draw), P(Home) from the bivariate Poisson.

    For a SINGLE set of lambda parameters, we approximate the full
    distribution by summing the bivariate Poisson probability mass over
    the outcome regions:

      P(Home)   = sum_{i > j}  P(X=i, Y=j)
      P(Draw)   = sum_{i = j}  P(X=i, Y=j)
      P(Away)   = sum_{i < j}  P(X=i, Y=j)

    where X ~ Poisson(lambda_h) and Y ~ Poisson(lambda_a) with correlation
    rho (Dixon-Coles, typical 0.10–0.18 for Argentine league).

    We use a discrete sum over goal pairs (i, j) ∈ [0, MAX_GOALS]^2.
    MAX_GOALS = 8 suffices for Liga Argentina (max observed = 8).

    Returns probabilities that sum to 1.
    """
    MAX_GOALS = 8

    # Unadjusted Poisson pmf tables
    ph = np.array([stats.poisson.pmf(i, lambda_h) for i in range(MAX_GOALS + 1)])
    pa = np.array([stats.poisson.pmf(j, lambda_a) for j in range(MAX_GOALS + 1)])

    # Dixon-Coles correlation adjustment on the joint.
    # The DC constant: 1 + rho for i≠j, 1−2ρ for i=j (preserves marginals
    # approximately and is the standard DC correction for 1X2 probabilities).
    joint = np.outer(ph, pa)  # start independent
    for i in range(MAX_GOALS + 1):
        for j in range(MAX_GOALS + 1):
            if i == j:
                joint[i, j] *= 1.0 - 2.0 * rho
            else:
                joint[i, j] *= 1.0 + rho

    # Normalise
    joint = joint / joint.sum()

    # Sum over outcome regions
    home_prob = float(np.triu(joint, k=1).sum())   # i > j
    draw_prob = float(np.diag(joint).sum())        # i = j
    away_prob = float(np.tril(joint, k=-1).sum())  # i < j

    # Renormalise to 1.0 (numerical rounding)
    s = home_prob + draw_prob + away_prob
    return {
        "Home": home_prob / s,
        "Draw": draw_prob / s,
        "Away": away_prob / s,
    }


# ---------------------------------------------------------------------------
# Full pipeline: fit → predict → evaluate (OOF via TSSCV)
# ---------------------------------------------------------------------------

def run_minimal_evaluation(matches: pd.DataFrame,
                           tscv) -> dict[str, object]:
    """Run the goal-based model evaluation using TimeSeriesSplit.

    For each fold we:
      1. Fit Poisson models on training indices
      2. Predict lambda_home, lambda_away for EACH validation row
      3. Derive 3-class probabilities from bivariate Poisson per row
      4. Collect OOF predictions + true labels for metric computation

    Returns a dict compatible with the experiment harness metric sheet:
      - cv_accuracies: per-fold accuracy
      - cv_log_losses: per-fold log loss
      - cv_brier_scores: per-fold Brier (multiclass, range [0,2])
      - mean_accuracy, mean_log_loss, mean_brier_score
    """
    from src.pipeline import FEATURE_COLUMNS

    accuracies = []
    log_losses = []
    brier_scores = []

    for fold, (t_idx, v_idx) in enumerate(tscv.split(matches), 1):
        df_train = build_minimal_frame(matches.iloc[t_idx])
        df_val = build_minimal_frame(matches.iloc[v_idx])

        # Fit Poisson models on training data
        home_mod, away_mod = fit_poisson_models(df_train)

        # Predict expected goals for EACH validation row
        X_val = df_val[["Elo_Diff", "xG_diff", "home_advantage"]].values

        # Home goals lambdas for each validation row
        lambda_h_arr = home_mod.predict(X_val)  # shape (n_val,)
        # Away goals lambdas for each validation row
        lambda_a_arr = away_mod.predict(
            df_val[["Elo_Diff", "xG_diff"]].values
        )  # shape (n_val,)

        # Derive 3-class probs for each validation row
        n_val = len(df_val)
        P = np.zeros((n_val, 3))  # columns: [p_away, p_draw, p_home] per harness

        for i in range(n_val):
            probs = bivariate_poisson_3class_row(
                float(np.exp(lambda_h_arr[i])),
                float(lambda_a_arr[i]),
                rho=0.14,
            )
            # Harness convention: P[:, 0]=p_away, P[:, 1]=p_draw, P[:, 2]=p_home
            P[i, 0] = float(probs["Away"])
            P[i, 1] = float(probs["Draw"])
            P[i, 2] = float(probs["Home"])

        # True labels: Res column already 0=Away, 1=Draw, 2=Home (harness convention)
        y_idx = matches.iloc[v_idx]["Res"].values.astype(int)

        # Accuracy
        pred_idx = P.argmax(axis=1)
        acc = float(np.mean(pred_idx == y_idx))
        accuracies.append(acc)

        # Log loss (multiclass, labels=[0,1,2])
        ll = float(log_loss(y_idx, P, labels=[0, 1, 2]))
        log_losses.append(ll)

        # Multiclass Brier = mean over rows of sum_k (p_k - t_k)^2
        onehot = np.eye(3)[y_idx]
        brier = float(np.mean(np.sum((P - onehot) ** 2, axis=1)))
        brier_scores.append(brier)

    return {
        "cv_accuracies": accuracies,
        "cv_log_losses": log_losses,
        "cv_brier_scores": brier_scores,
        "mean_accuracy": float(np.mean(accuracies)),
        "mean_log_loss": float(np.mean(log_losses)),
        "mean_brier_score": float(np.mean(brier_scores)),
    }


# ---------------------------------------------------------------------------
# CLI entry point (python -m src.goal_model)
# ---------------------------------------------------------------------------

def _main():
    """CLI entry: run the goal model evaluation on the current data."""
    import sys

    from src.pipeline import load_data, build_features
    from sklearn.model_selection import TimeSeriesSplit

    result = load_data()
    matches = build_features(result[2])  # historical matches is index 2

    tscv = TimeSeriesSplit(n_splits=5)

    results = run_minimal_evaluation(matches, tscv)

    print(f"Phase 1 — Goal-Based Model Evaluation")
    print(f"---------------------------------------")
    print(f"Mean Accuracy:  {results['mean_accuracy']:.4f}")
    print(f"Mean Log Loss:  {results['mean_log_loss']:.4f}")
    print(f"Mean Brier:     {results['mean_brier_score']:.4f}")
    print(f"Per-fold accuracies: {results['cv_accuracies']}")
    print(f"Per-fold log losses: {results['cv_log_losses']}")
    print(f"Per-fold Brier scores: {results['cv_brier_scores']}")


if __name__ == "__main__":
    _main()