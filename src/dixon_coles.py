"""
src/dixon_coles.py
Phase 2.0 — Dixon-Coles Goal-Based Model

Two-stage generative approach:
  Stage 1: Predict λ_home and λ_away from a minimal, non-redundant feature set
           using independent Poisson regression (log link, GLM).
  Stage 2: Derive P(Away), P(Draw), P(Home) analytically by summing the joint
           Poisson grid over the three outcome regions.

DESIGN CHOICES
--------------
1. PoissonRegressor (sklearn) uses a log link natively — predict() returns
   λ directly (expected goals), NOT log(λ). No exp() call needed.

2. Dixon-Coles low-score correction (Dixon & Coles, 1997):
   Adjusts the joint probability for scorelines (0,0), (1,0), (0,1), (1,1)
   using parameter ρ. The standard correction factor τ(i,j,λ,μ,ρ) is:
     τ(0,0) = 1 - λμρ
     τ(1,0) = 1 + μρ
     τ(0,1) = 1 + λρ
     τ(1,1) = 1 - ρ
     τ(i,j) = 1  for i>1 or j>1
   This preserves marginal Poisson distributions while adjusting the
   joint for the known draw inflation at (0,0) and (1,1).

3. ρ is estimated by MLE on the training fold. Falls back to 0.0 (independent
   Poisson) if optimisation fails. Typical value for Argentine football: 0.05-0.12.

4. Minimal, non-redundant feature set (no Poisson or Shin columns):
   - Elo_Diff          (strength signal)
   - Home_Avg_GF       (home recent attack)
   - Away_Avg_GA       (away recent defence = home attack context)
   - Away_Avg_GF       (away recent attack)
   - Home_Avg_GA       (home recent defence = away attack context)
   - Home_Form         (home points-per-game last 8)
   - Away_Form         (away points-per-game last 8)
   Home-side model uses all 7; Away-side model uses the mirror.

5. Warm-up filter: rows with NaN in any model feature are excluded (same as
   baseline — these are the first ~8 matches of each team's career).

CLASS ENCODING: 0=Away, 1=Draw, 2=Home (matches harness convention).

BRIER CONVENTION: multiclass SSE mean over OOF rows (range [0, 2]).
"""

from __future__ import annotations

import warnings
from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize_scalar
from scipy.stats import poisson
from sklearn.linear_model import PoissonRegressor
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import TimeSeriesSplit

MAX_GOALS = 8         # upper bound for grid summation
CLASSES = [0, 1, 2]  # 0=Away, 1=Draw, 2=Home

# Phase 2.0 features — venue-MIXED trailing averages (baseline mode)
HOME_FEATURES = [
    "Elo_Diff",
    "Home_Avg_GF",
    "Away_Avg_GA",
    "Home_Form",
]
AWAY_FEATURES = [
    "Elo_Diff",
    "Away_Avg_GF",
    "Home_Avg_GA",
    "Away_Form",
]
ALL_FEATURES = sorted(set(HOME_FEATURES + AWAY_FEATURES))

# Phase 2.0.2 features — venue-SPLIT raw trailing averages (raw mode)
# These come from src/dc_features.build_dc_features() which separates
# home-venue and away-venue history so Stage 1 models learn the home
# intercept from the data rather than inheriting a baked-in 0.33 λ gap.
HOME_FEATURES_RAW = ["DC_Home_Att", "DC_Away_Def", "Elo_Diff"]
AWAY_FEATURES_RAW = ["DC_Away_Att", "DC_Home_Def", "Elo_Diff"]
ALL_FEATURES_RAW = sorted(set(HOME_FEATURES_RAW + AWAY_FEATURES_RAW))


# ---------------------------------------------------------------------------
# Stage 1: Poisson regression for expected goals
# ---------------------------------------------------------------------------

def _fit_poisson(X: np.ndarray, y: np.ndarray) -> PoissonRegressor:
    """Fit a Poisson GLM. Returns the fitted model."""
    model = PoissonRegressor(alpha=0.01, max_iter=300, fit_intercept=True)
    model.fit(X, y)
    return model


# ---------------------------------------------------------------------------
# Stage 2: Bivariate Poisson grid + Dixon-Coles correction
# ---------------------------------------------------------------------------

def _dc_tau(i: int, j: int, lh: float, la: float, rho: float) -> float:
    """Dixon-Coles low-score correction factor τ(i, j)."""
    if i == 0 and j == 0:
        return 1.0 - lh * la * rho
    if i == 1 and j == 0:
        return 1.0 + la * rho
    if i == 0 and j == 1:
        return 1.0 + lh * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def _score_grid(lh: float, la: float, rho: float) -> np.ndarray:
    """
    Return normalised (MAX_GOALS+1)×(MAX_GOALS+1) joint probability grid.
    grid[i, j] = P(home_goals=i, away_goals=j).
    """
    lh = max(lh, 1e-6)
    la = max(la, 1e-6)
    goals = np.arange(MAX_GOALS + 1)
    ph = poisson.pmf(goals, lh)
    pa = poisson.pmf(goals, la)
    grid = np.outer(ph, pa)

    # Apply DC correction on low-score cells
    for i in range(2):
        for j in range(2):
            tau = _dc_tau(i, j, lh, la, rho)
            grid[i, j] *= tau

    # Normalise — DC correction changes the sum slightly
    total = grid.sum()
    if total > 1e-12:
        grid /= total
    return grid


def grid_to_3class(grid: np.ndarray) -> tuple[float, float, float]:
    """
    Sum grid over outcome regions.
    Returns (p_away, p_draw, p_home) matching class encoding 0/1/2.
    """
    p_home = float(np.triu(grid, k=1).sum())   # i > j
    p_draw = float(np.diag(grid).sum())         # i == j
    p_away = float(np.tril(grid, k=-1).sum())   # i < j
    total = p_home + p_draw + p_away
    if total < 1e-12:
        return 1 / 3, 1 / 3, 1 / 3
    return p_away / total, p_draw / total, p_home / total


# ---------------------------------------------------------------------------
# ρ estimation via MLE on training data
# ---------------------------------------------------------------------------

def _neg_log_likelihood(rho: float, lh_arr: np.ndarray, la_arr: np.ndarray,
                        hg: np.ndarray, ag: np.ndarray) -> float:
    """Negative log-likelihood of observed goals under DC model with given ρ."""
    eps = 1e-15
    ll = 0.0
    for lh, la, h, a in zip(lh_arr, la_arr, hg, ag):
        lh = max(lh, eps)
        la = max(la, eps)
        p = poisson.pmf(h, lh) * poisson.pmf(a, la) * _dc_tau(h, a, lh, la, rho)
        ll += np.log(max(p, eps))
    return -ll


def estimate_rho(lh_arr: np.ndarray, la_arr: np.ndarray,
                 hg: np.ndarray, ag: np.ndarray) -> float:
    """Estimate ρ by 1-D optimisation (bounded search over [-0.3, 0.3])."""
    try:
        result = minimize_scalar(
            _neg_log_likelihood,
            bounds=(-0.3, 0.3),
            method="bounded",
            args=(lh_arr, la_arr, hg, ag),
            options={"xatol": 1e-4, "maxiter": 200},
        )
        return float(result.x)
    except Exception:
        return 0.0


# ---------------------------------------------------------------------------
# Cross-validated OOF evaluation
# ---------------------------------------------------------------------------

def brier_multiclass(y_true: np.ndarray, proba: np.ndarray) -> float:
    """Mean SSE Brier score over rows, range [0, 2]."""
    onehot = np.eye(3)[y_true.astype(int)]
    return float(np.mean(np.sum((proba - onehot) ** 2, axis=1)))


def run_cv(
    df: pd.DataFrame,
    n_splits: int = 5,
    estimate_rho_flag: bool = True,
    rho_fixed: float = 0.0,
    verbose: bool = True,
    feature_mode: str = "mixed",
) -> dict:
    """
    TimeSeriesSplit(n_splits) CV on the Dixon-Coles model.

    Parameters
    ----------
    df : DataFrame after build_features(), must contain the required features
         + HG + AG + Res.
    n_splits : number of CV folds (must match baseline = 5).
    estimate_rho_flag : if True, estimate ρ from training fold; else use rho_fixed.
    rho_fixed : fallback ρ when estimation is disabled.
    verbose : print per-fold diagnostics.
    feature_mode : 'mixed' (Phase 2.0 — venue-mixed, Home_Avg_GF etc.) or
                   'raw'   (Phase 2.0.2 — venue-split, DC_Home_Att etc.)

    Returns
    -------
    dict with OOF predictions, per-fold metrics, aggregate metrics.
    """
    if feature_mode == "raw":
        h_feats = HOME_FEATURES_RAW
        a_feats = AWAY_FEATURES_RAW
    else:
        h_feats = HOME_FEATURES
        a_feats = AWAY_FEATURES

    tscv = TimeSeriesSplit(n_splits=n_splits)
    n = len(df)
    oof_proba = np.full((n, 3), np.nan)
    oof_fold = np.full(n, -1, dtype=int)

    y_all = df["Res"].values.astype(int)
    hg_all = df["HG"].values.astype(int)
    ag_all = df["AG"].values.astype(int)

    per_fold = []
    rho_values = []

    for fold, (t_idx, v_idx) in enumerate(tscv.split(df), 1):
        df_tr = df.iloc[t_idx]
        df_val = df.iloc[v_idx]

        X_home_tr = df_tr[h_feats].values
        X_away_tr = df_tr[a_feats].values
        hg_tr = hg_all[t_idx]
        ag_tr = ag_all[t_idx]

        # Fit Stage 1 models
        home_mod = _fit_poisson(X_home_tr, hg_tr)
        away_mod = _fit_poisson(X_away_tr, ag_tr)

        # Predict λ on training fold for ρ estimation
        lh_tr = home_mod.predict(X_home_tr)
        la_tr = away_mod.predict(X_away_tr)

        # Estimate ρ
        if estimate_rho_flag:
            rho = estimate_rho(lh_tr, la_tr, hg_tr, ag_tr)
        else:
            rho = rho_fixed
        rho_values.append(rho)

        # Predict λ on validation fold
        lh_val = home_mod.predict(df_val[h_feats].values)
        la_val = away_mod.predict(df_val[a_feats].values)

        # Stage 2: derive 3-class probabilities
        proba_fold = np.zeros((len(v_idx), 3))
        for i, (lh, la) in enumerate(zip(lh_val, la_val)):
            grid = _score_grid(lh, la, rho)
            p_away, p_draw, p_home = grid_to_3class(grid)
            proba_fold[i] = [p_away, p_draw, p_home]

        oof_proba[v_idx] = proba_fold
        oof_fold[v_idx] = fold

        # Per-fold metrics
        y_f = y_all[v_idx]
        acc_f = float(accuracy_score(y_f, np.argmax(proba_fold, axis=1)))
        ll_f = float(log_loss(y_f, proba_fold, labels=CLASSES))
        brier_f = brier_multiclass(y_f, proba_fold)
        draw_pred_f = int((np.argmax(proba_fold, axis=1) == 1).sum())
        draw_true_f = int((y_f == 1).sum())
        draw_tp_f = int(((np.argmax(proba_fold, axis=1) == 1) & (y_f == 1)).sum())
        draw_recall_f = draw_tp_f / draw_true_f if draw_true_f > 0 else 0.0

        per_fold.append({
            "fold": fold,
            "n_train": int(len(t_idx)),
            "n_val": int(len(v_idx)),
            "rho": round(rho, 5),
            "accuracy": round(acc_f, 5),
            "log_loss": round(ll_f, 5),
            "brier": round(brier_f, 5),
            "draw_pred": draw_pred_f,
            "draw_true": draw_true_f,
            "draw_recall": round(draw_recall_f, 4),
        })
        if verbose:
            print(f"  Fold {fold}: n_train={len(t_idx)}, n_val={len(v_idx)}, "
                  f"ρ={rho:.4f}, acc={acc_f:.4f}, LL={ll_f:.4f}, "
                  f"Brier={brier_f:.4f}, draw_recall={draw_recall_f:.3f} "
                  f"({draw_tp_f}/{draw_true_f})")

    # Aggregate OOF metrics
    mask = oof_fold >= 0
    y_oof = y_all[mask]
    p_oof = oof_proba[mask]
    pred_oof = np.argmax(p_oof, axis=1)

    oof_acc = float(accuracy_score(y_oof, pred_oof))
    oof_ll = float(log_loss(y_oof, p_oof, labels=CLASSES))
    oof_brier = brier_multiclass(y_oof, p_oof)
    draw_true = int((y_oof == 1).sum())
    draw_pred = int((pred_oof == 1).sum())
    draw_tp = int(((pred_oof == 1) & (y_oof == 1)).sum())
    draw_recall = draw_tp / draw_true if draw_true > 0 else 0.0

    from sklearn.metrics import confusion_matrix
    cm = confusion_matrix(y_oof, pred_oof, labels=CLASSES).tolist()

    return {
        "oof_n": int(mask.sum()),
        "oof_proba": oof_proba,        # full (n, 3) array, NaN outside folds
        "oof_fold": oof_fold,
        "y_all": y_all,
        "per_fold": per_fold,
        "rho_values": [round(r, 5) for r in rho_values],
        "mean_rho": round(float(np.mean(rho_values)), 5),
        "aggregate": {
            "oof_n": int(mask.sum()),
            "oof_accuracy": round(oof_acc, 6),
            "mean_accuracy": round(float(np.mean([f["accuracy"] for f in per_fold])), 6),
            "std_accuracy": round(float(np.std([f["accuracy"] for f in per_fold])), 6),
            "oof_log_loss": round(oof_ll, 6),
            "mean_log_loss": round(float(np.mean([f["log_loss"] for f in per_fold])), 6),
            "std_log_loss": round(float(np.std([f["log_loss"] for f in per_fold])), 6),
            "brier_multiclass": round(oof_brier, 6),
            "mean_brier": round(float(np.mean([f["brier"] for f in per_fold])), 6),
            "draw_true": draw_true,
            "draw_pred": draw_pred,
            "draw_recall": round(draw_recall, 4),
            "confusion_matrix": cm,
        },
    }
