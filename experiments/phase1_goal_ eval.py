"""Verify Phase 1 goal model evaluation."""
import sys
sys.path.insert(0, ".")

import numpy as np
from src.goal_model import run_minimal_evaluation, build_minimal_frame, fit_poisson_models, bivariate_poisson_3class
from src.pipeline import load_data, build_features
from sklearn.model_selection import TimeSeriesSplit

_, _, matches, _ = load_data()
matches = build_features(matches)

tscv = TimeSeriesSplit(n_splits=5)
results = run_minimal_evaluation(matches, tscv)

print(f"Mean Accuracy:  {results['mean_accuracy']:.4f}")
print(f"Mean Log Loss:  {results['mean_log_loss']:.4f}")
print(f"Mean Brier:     {results['mean_brier_score']:.4f}")
print(f"Per-fold accuracies: {results['cv_accuracies']}")
print(f"Per-fold log losses: {results['cv_log_losses']}")
print(f"Per-fold Brier scores: {results['cv_brier_scores']}")