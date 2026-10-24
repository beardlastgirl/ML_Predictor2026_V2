"""Verify Phase 1 goal model evaluation."""
import numpy as np
import sys
sys.path.insert(0, ".")

from src.pipeline import load_data, build_features
from src.goal_model import run_minimal_evaluation
from sklearn.model_selection import TimeSeriesSplit

result = load_data()
print("result type:", type(result))
print("result length:", len(result))
print("result[2] type:", type(result[2]))
matches, features_dict = build_features(result[2])  # historical matches is index 2

print("matches type after build_features:", type(matches))
print("matches shape:", matches.shape)
print("matches columns:", list(matches.columns)[:10])
print("features_dict keys:", list(features_dict.keys())[:5])
print("Res column value_counts:", matches["Res"].value_counts().to_dict())
print("Number of rows:", len(matches))

tscv = TimeSeriesSplit(n_splits=5)
splits = list(tscv.split(matches))
print(f"Number of TSSCV splits: {len(splits)}")
for i, (t, v) in enumerate(splits):
    print(f"  Fold {i}: train_n={len(t)}, test_n={len(v)}")

results = run_minimal_evaluation(matches, tscv)

print(f"\nMean Accuracy: {results['mean_accuracy']:.4f}")
print(f"Mean Log Loss: {results['mean_log_loss']:.4f}")
print(f"Mean Brier:    {results['mean_brier_score']:.4f}")
print(f"Per-fold accs: {results['cv_accuracies']}")
print(f"Per-fold LLs:  {results['cv_log_losses']}")
print(f"Per-fold Briers: {results['cv_brier_scores']}")