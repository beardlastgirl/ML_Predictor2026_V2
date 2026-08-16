"""ML_Predictor2026_V2 - Main Prediction Engine with Poisson Distribution

Entry point for CLI execution. Keeps main() minimal: it invokes
src.pipeline.run_pipeline() and prints a concise summary to stdout.

This module is intentionally small — orchestration and logic live in src.pipeline.
"""

from src.pipeline import run_pipeline
from src.utils import log_info, log_ok


def main():
    """Main prediction pipeline with Poisson integration."""
    log_info("Starting prediction pipeline...")

    result = run_pipeline()

    log_info("=" * 60)
    log_info("Pipeline Summary")
    log_info("=" * 60)
    log_info("Model: CatBoost")
    log_info(f"CV Accuracy: {sum(result.cv_accuracies)/len(result.cv_accuracies):.3f} (+/- {__import__('numpy').std(result.cv_accuracies):.3f})")
    log_info(f"Features: {len(result.features)}")
    if result.fixtures is not None:
        log_info(f"Fixtures predicted: {len(result.fixtures)}")
    if result.output_file:
        log_ok(f"Results written to: {result.output_file}")

    return result.model, result.elo_ratings, result.features


if __name__ == "__main__":
    main()
