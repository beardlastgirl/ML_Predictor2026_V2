# Configuration and Hyperparameters

import os

# Elo parameters
BASE_ELO = 1500
K_FACTOR = 30
HOME_ADVANTAGE = 65
ELO_DIVISOR = 400  # Standard Elo formula constant
ELO_FACTOR_DENOM = 5000  # Elo factor denominator

# Poisson parameters
# BASE_GOAL_RATE: Liga Profesional average goals per team per match.
# Used as the NaN fallback in calculate_expected_goals() when a team has no
# trailing stats (e.g. promoted/new teams at season start). It is NOT used
# as a scaling factor in the xG formula — trailing avg_gf/avg_ga drive that.
BASE_GOAL_RATE = 2.22  # Based on actual historical data (1.26 Home + 0.96 Away)
MAX_GOALS = 8  # Maximum goals to consider in Poisson distribution
HOME_BOOST = 1.15  # Refined based on 1.26/0.96 ratio
GOAL_WEIGHT_ATTACK = 0.55  # Slightly adjusted
GOAL_WEIGHT_DEFENSE = 0.45  # Slightly adjusted
XG_MIN = 0.3  # Minimum xG clamp
XG_MAX = 2.5  # Maximum xG clamp

# Probability calibration
POISSON_DRAW_ADJUSTMENT = 1.11   # Calibrated 2026-05-02 against 6171 matches
# Actual: home=43.1%, draw=30.3%, away=26.6%
# Grid search optimal: draw_adj=1.11 + home_boost=0.02 → home=43.0%, draw=30.3%, away=26.6%
# Previous value was 0.85 (reducing draws) — wrong direction for this dataset
HOME_ADVANTAGE_BOOST = 0.02  # Calibrated 2026-05-02: small residual boost after xG home advantage
# xG already encodes home advantage via HOME_BOOST (1.15x) and Elo HOME_ADVANTAGE (+65 pts).
# Grid search: draw_adj=1.11 + home_boost=0.02 → home=43.0%, draw=30.3%, away=26.6% (actual: 43.1/30.3/26.6)
ML_POISSON_BLEND_RATIO = 0.6  # DEPRECATED: ensemble removed; Poisson feeds GBM as features

# Draw Calibration Strategy Documentation:
# ============================================
# Poisson draw/home calibration (stats_engine.py) feeds meta-features into GBM.
# Final probabilities come from the ML model only (no post-hoc Poisson blend).

# Result encoding
RESULT_ENCODING = {"H": 2, "D": 1, "A": 0}  # Home Win, Draw, Away Win
RESULT_DECODING = {2: "Home Win", 1: "Draw", 0: "Away Win"}

# Prediction thresholds
WIN_PROBABILITY_THRESHOLD = 0.45  # High confidence for home/away win
DRAW_PROBABILITY_THRESHOLD = 0.38  # High confidence for draw (league avg ~33%)
DEFAULT_EXPECTED_GOALS = 1.35  # Fallback for expected goals
MAX_PREDICTED_GOALS = 6  # Maximum goals to predict

# Trailing window for squad features (EWMA span; decay handled in features.py)
TRAILING_WINDOW = 8

# Tournament transition: compress prior-season EWMA by this factor at season change
TOURNAMENT_TRANSITION_DECAY = 0.70

# Cold-start Bayesian shrinkage for meta xG features
BAYESIAN_SHRINKAGE_C = 5
LEAGUE_MEAN_XG = 1.15

# Model selection
MODEL_TYPE = os.environ.get("ML_PREDICTOR_MODEL", "catboost").strip().lower()
if MODEL_TYPE not in ("lightgbm", "catboost"):
    MODEL_TYPE = "catboost"

# Model hyperparameters
MODEL_PARAMS = {
    "lightgbm": {
        "n_estimators": 500,
        "learning_rate": 0.04,
        "num_leaves": 32,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "verbose": -1,
    },
    "catboost": {
        "loss_function": "MultiClass",
        "iterations": 800,       # Higher ceiling; early stopping will trim this
        "learning_rate": 0.03,   # Slightly lower LR pairs better with early stopping
        "depth": 6,
        "l2_leaf_reg": 3,
        "bootstrap_type": "Bernoulli",
        "subsample": 0.8,
        "colsample_bylevel": 0.8,
        "early_stopping_rounds": 50,  # Stop if val log-loss doesn't improve for 50 rounds
        "random_state": 42,
        "verbose": False,
    },
}
