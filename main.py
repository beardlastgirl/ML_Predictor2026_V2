"""
ML_Predictor2026_V2 - Main Prediction Engine with Poisson Distribution

This is the main entry point for the prediction pipeline.
It delegates to the pipeline service for all major operations.
"""

import sys

import numpy as np

from src.pipeline import run_pipeline, format_match_prediction
from src.utils import log_info, log_ok, log_error
from src.config import MODEL_TYPE


def main():
    """Main prediction pipeline with Poisson integration."""
    log_info("Starting prediction pipeline...")

    result = run_pipeline()

    if result.fixtures is not None and not result.fixtures.empty:
        log_info("=" * 60)
        log_info("Fixture Predictions (Probability Engine)")
        log_info("=" * 60)
        for _, row in result.fixtures.iterrows():
            print(format_match_prediction(row))

    log_info("=" * 60)
    log_info("Pipeline Summary")
    log_info("=" * 60)
    model_name = type(result.model).__name__ if result.model else MODEL_TYPE
    log_info(f"Model: {model_name}")
    cv_acc = result.cv_accuracies
    if not cv_acc:
        log_error("No cross-validation accuracies produced; cannot report summary.")
        sys.exit(1)
    log_info(f"CV Accuracy: {sum(cv_acc)/len(cv_acc):.3f} (+/- {np.std(cv_acc):.3f})")
    log_info(f"Features: {len(result.features)}")
    if result.fixtures is not None:
        log_info(f"Fixtures predicted: {len(result.fixtures)}")
    if result.output_file:
        log_ok(f"Results written to: {result.output_file}")

    return result.model, result.elo_ratings, result.features


if __name__ == "__main__":
    main()