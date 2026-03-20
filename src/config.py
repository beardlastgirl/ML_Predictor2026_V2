# Configuration and Hyperparameters

import os

# Elo parameters
BASE_ELO = 1500
K_FACTOR = 30
HOME_ADVANTAGE = 65
ELO_DIVISOR = 400  # Standard Elo formula constant
ELO_FACTOR_DENOM = 5000  # Elo factor denominator

# Poisson parameters
BASE_GOAL_RATE = 1.89  # Base goals per match in Liga Profesional Argentina
MAX_GOALS = 8  # Maximum goals to consider in Poisson distribution
HOME_BOOST = 1.22  # Home team scoring boost (calibrated for league average)
GOAL_WEIGHT_ATTACK = 0.6  # Weight for attack in xG calculation
GOAL_WEIGHT_DEFENSE = 0.4  # Weight for defense in xG calculation
XG_MIN = 0.3  # Minimum xG clamp
XG_MAX = 2.5  # Maximum xG clamp

# Probability calibration
POISSON_DRAW_ADJUSTMENT = 0.85  # Multiply draw probability to reduce draw bias

# Result encoding
RESULT_ENCODING = {"H": 2, "D": 1, "A": 0}  # Home Win, Draw, Away Win
RESULT_DECODING = {2: "Home Win", 1: "Draw", 0: "Away Win"}

# Prediction thresholds
WIN_PROBABILITY_THRESHOLD = 0.45  # High confidence for home/away win
DRAW_PROBABILITY_THRESHOLD = 0.38  # High confidence for draw (league avg ~33%)
DEFAULT_EXPECTED_GOALS = 1.35  # Fallback for expected goals
MAX_PREDICTED_GOALS = 6  # Maximum goals to predict

# Trailing window for squad features
TRAILING_WINDOW = 8

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
        "iterations": 500,
        "learning_rate": 0.04,
        "depth": 6,
        "l2_leaf_reg": 3,
        "bootstrap_type": "Bernoulli",
        "subsample": 0.8,
        "colsample_bylevel": 0.8,
        "random_state": 42,
        "verbose": False,
    },
}
