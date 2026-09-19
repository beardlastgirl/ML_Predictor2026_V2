"""
Fold-aware leakage tests: the fold-aware path of train_validate must rebuild
features per fold from raw matches only, so validation rows never absorb
future outcomes (these tests were written first, before the feature-wiring
change in run_pipeline / pipeline.py).
"""
import numpy as np
import pandas as pd
import pytest
from unittest.mock import patch

from src.pipeline import _build_fold_features, build_features, train_validate, FEATURE_COLUMNS
from src.config import MODEL_TYPE


def _make_raw_matches(n_rows=24, seed=0):
    """Deterministic synthetic historical frame with odds, goals and a season."""
    rng = np.random.default_rng(seed)
    teams = [f"Team{i}" for i in range(6)]
    dates = pd.date_range("2025-01-01", periods=n_rows, freq="7D")
    rows = []
    for i in range(n_rows):
        h, a = rng.choice(6, size=2, replace=False)
        rows.append({
            "Date": dates[i],
            "HomeTeam": teams[h],
            "AwayTeam": teams[a],
            "FullTimeResult": int(rng.integers(0, 3)),
            "Home_GF": int(rng.integers(0, 4)),
            "Away_GF": int(rng.integers(0, 4)),
            "Season": "2024-25",
            "Odds_b365_H": 2.1,
            "Odds_b365_D": 3.3,
            "Odds_b365_A": 3.6,
        })
    return pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)


LEAK_PRONE_COLUMNS = [
    "Home_Elo", "Away_Elo", "Elo_Diff",
    "Home_Avg_GF", "Away_Avg_GF", "Home_Avg_GA", "Away_Avg_GA",
    "Home_Form", "Away_Form", "Attack_Balance", "Def_Balance", "Form_Balance",
    "xG_home", "xG_away", "xG_diff",
    "Poisson_Home_Win", "Poisson_Draw", "Poisson_Away_Win",
    "Expected_Home_Goals", "Expected_Away_Goals", "Expected_Total_Goals",
    "poisson_xg_home_meta", "poisson_xg_away_meta",
]


def test_fold_features_do_not_change_with_future_outcomes():
    """Keeps 24 matches; flipping results/odds after row 10 must leave the
    features of the first 10 rows bit-identical."""
    raw = _make_raw_matches(24)
    mutated = raw.copy()
    mutated.loc[10:, "FullTimeResult"] = (mutated.loc[10:, "FullTimeResult"] + 1) % 3
    mutated.loc[10:, "Odds_b365_H"] = 5.0

    base = _build_fold_features(raw, until_row=10, elo_ratings={}, window=8)
    other = _build_fold_features(mutated, until_row=10, elo_ratings={}, window=8)

    pd.testing.assert_frame_equal(
        base[LEAK_PRONE_COLUMNS].reset_index(drop=True),
        other[LEAK_PRONE_COLUMNS].reset_index(drop=True),
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )
    # Shin is a per-match market feature; mutated odds are outside the prefix,
    # so the prefix Shin probabilities must match too.
    pd.testing.assert_frame_equal(
        base[["Shin_Prob_H", "Shin_Prob_D", "Shin_Prob_A"]].reset_index(drop=True),
        other[["Shin_Prob_H", "Shin_Prob_D", "Shin_Prob_A"]].reset_index(drop=True),
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )


def test_fold_features_equivalent_to_prefix_only_build():
    """Features for the first k rows computed via the fold-aware helper must
    equal build_features() run on the k-row prefix alone."""
    raw = _make_raw_matches(24)
    k = 10

    fold_feats = _build_fold_features(raw, until_row=k, elo_ratings={}, window=8)
    prefix = raw.iloc[:k].copy().sort_values("Date").reset_index(drop=True)
    prefix_feats, _ = build_features(prefix)

    pd.testing.assert_frame_equal(
        fold_feats[LEAK_PRONE_COLUMNS].reset_index(drop=True),
        prefix_feats[LEAK_PRONE_COLUMNS].reset_index(drop=True),
        check_exact=False,
        rtol=1e-12,
        atol=1e-12,
    )


class MockModel:
    def fit(self, X, y, sample_weight=None):
        pass

    def predict(self, X):
        return np.ones(len(X), dtype=int)  # always predict draw (1)

    def predict_proba(self, X):
        return np.array([[0.2, 0.6, 0.2]] * len(X))

    @property
    def feature_importances_(self):
        return np.ones(4)


@patch("src.pipeline.create_model", return_value=MockModel())
def test_train_validate_fold_aware_runs(mock_create_model):
    """Regression test for the fold-aware branch (was: NameError on
    val_features at sub-model data collection, and unwired in production)."""
    raw = _make_raw_matches(30)
    feats, _ = build_features(raw)
    df = feats.dropna(subset=FEATURE_COLUMNS).copy()

    result = train_validate(
        df, FEATURE_COLUMNS, model_type=MODEL_TYPE, n_splits=2, raw_matches=raw
    )
    assert len(result) == 5
    model, cv_acc, cv_ll, naive_ll, bookie_ll = result
    assert len(cv_acc) == 2
    assert len(cv_ll) == 2