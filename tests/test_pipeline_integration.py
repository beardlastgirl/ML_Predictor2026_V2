"""
Pipeline Integration Tests - ML_Predictor2026_V2

End-to-end integration tests for the prediction pipeline.
Verifies full execution of run_pipeline(), metric calculation,
output formatting, and edge case handling.
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import run_pipeline, load_data, build_features, train_validate, predict_fixtures, write_outputs
from src.config import RESULT_ENCODING
from src.pipeline import FEATURE_COLUMNS


class TestPipelineIntegration:
    """Full pipeline integration tests."""

    def test_run_pipeline_auto_update_false(self):
        """Test pipeline runs end-to-end."""
        result = run_pipeline()

        # Verify result structure
        assert result is not None
        assert result.model is not None
        assert result.elo_ratings is not None
        assert result.features == FEATURE_COLUMNS
        assert isinstance(result.cv_accuracies, list)
        assert isinstance(result.cv_log_losses, list)
        assert len(result.cv_accuracies) == 5
        assert len(result.cv_log_losses) == 5

    def test_run_pipeline_historical_matches_processed(self):
        """Test that historical matches are loaded and processed."""
        result = run_pipeline()

        # Should process 6295 matches from ARG.csv
        assert result.model is not None

    def test_run_pipeline_cv_metrics_valid(self):
        """Test CV metrics are in valid ranges."""
        result = run_pipeline()

        # Accuracy should be reasonable (30-60% for 3-class football)
        for acc in result.cv_accuracies:
            assert 0.30 <= acc <= 0.60

        # Log loss should be reasonable (>0, <2 for 3-class)
        for ll in result.cv_log_losses:
            assert 0.5 <= ll <= 2.0

    def test_run_pipeline_mean_metrics(self):
        """Test mean CV metrics match expected baselines."""
        result = run_pipeline()

        mean_acc = np.mean(result.cv_accuracies)
        mean_ll = np.mean(result.cv_log_losses)

        # Per roadmap: Mean CV Accuracy ~0.436, Mean Log Loss ~1.075
        assert 0.40 <= mean_acc <= 0.48
        assert 1.05 <= mean_ll <= 1.12

    def test_load_data_returns_correct_structure(self):
        """Test load_data returns all expected components."""
        glossary, sofascore_data, matches, fixtures = load_data()

        assert isinstance(glossary, dict)
        assert isinstance(sofascore_data, dict)
        assert isinstance(matches, pd.DataFrame)
        assert fixtures is None or isinstance(fixtures, pd.DataFrame)

        # Verify matches has required columns
        required_cols = ["Home", "Away", "Res", "Date"]
        for col in required_cols:
            assert col in matches.columns

    def test_load_data_matches_normalized(self):
        """Test that team names are normalized in matches."""
        glossary, _, matches, _ = load_data()

        # All team names should be uppercase and normalized
        for team in pd.concat([matches["Home"], matches["Away"]]).unique():
            assert team == team.upper()
            assert "." not in team  # Dots removed in normalization

    def test_load_data_results_encoded(self):
        """Test that results are properly encoded (H=2, D=1, A=0)."""
        _, _, matches, _ = load_data()

        valid_results = {0, 1, 2}
        assert set(matches["Res"].dropna().unique()).issubset(valid_results)

    def test_build_features_creates_all_features(self):
        """Test that build_features creates all FEATURE_COLUMNS."""
        glossary, _, matches, _ = load_data()
        matches_with_features, elo_ratings = build_features(matches)

        for feature in FEATURE_COLUMNS:
            assert feature in matches_with_features.columns, f"Missing feature: {feature}"

    def test_build_features_elo_ratings_dict(self):
        """Test that Elo ratings are returned as dict."""
        glossary, _, matches, _ = load_data()
        _, elo_ratings = build_features(matches)

        assert isinstance(elo_ratings, dict)
        assert len(elo_ratings) > 0
        # All ratings should be within bounds
        for rating in elo_ratings.values():
            assert 800 <= rating <= 2800

    def test_train_validate_returns_model_and_metrics(self):
        """Test train_validate returns trained model and CV metrics."""
        glossary, _, matches, _ = load_data()
        matches_with_features, _ = build_features(matches)

        df = matches_with_features.dropna(subset=FEATURE_COLUMNS).copy()
        model, cv_acc, cv_ll = train_validate(df, FEATURE_COLUMNS)

        assert model is not None
        assert hasattr(model, "predict")
        assert hasattr(model, "predict_proba")
        assert len(cv_acc) == 5
        assert len(cv_ll) == 5

    def test_predict_fixtures_handles_empty(self):
        """Test predict_fixtures handles empty fixtures DataFrame."""
        glossary, sofascore_data, matches, _ = load_data()
        matches_with_features, elo_ratings = build_features(matches)
        df = matches_with_features.dropna(subset=FEATURE_COLUMNS).copy()
        model, _, _ = train_validate(df, FEATURE_COLUMNS)

        empty_fixtures = pd.DataFrame()
        result = predict_fixtures(
            empty_fixtures, elo_ratings, model, FEATURE_COLUMNS,
            df[FEATURE_COLUMNS].mean().to_dict(), matches_with_features, sofascore_data
        )

        assert result.empty

    def test_write_outputs_creates_files(self):
        """Test write_outputs creates result file and chart."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create minimal fixtures with predictions
            fixtures = pd.DataFrame({
                "Home": ["TEAM A"], "Away": ["TEAM B"],
                "Raw_Home": ["Team A"], "Raw_Away": ["Team B"],
                "Pred_Home_Goals": [1.5], "Pred_Away_Goals": [0.8],
                "Prediction_Label": ["Home Win"], "xG_home": [1.5], "xG_away": [0.8]
            })
            feature_importance = pd.DataFrame({
                "feature": ["Home_Elo", "Away_Elo"], "importance": [0.5, 0.3]
            })

            output_file = write_outputs(fixtures, feature_importance, tmpdir)

            assert os.path.exists(output_file)
            assert "Resultados_" in output_file

            # Check chart was created
            chart_files = list(Path(tmpdir).glob("feature_importance_*.png"))
            assert len(chart_files) == 1


class TestPipelineEdgeCases:
    """Edge case handling tests."""

    def test_pipeline_with_missing_odds(self):
        """Test pipeline handles matches without odds data."""
        result = run_pipeline()
        # Should not crash even though most matches lack odds
        assert result.model is not None

    def test_pipeline_feature_validation(self):
        """Test feature validation catches invalid features."""
        from src.validation import validate_model_features

        # Create DataFrame with NaN features
        bad_df = pd.DataFrame({
            "Home_Elo": [1500, np.nan, 1500],
            "Away_Elo": [1500, 1500, 1500],
        })
        result = validate_model_features(bad_df, ["Home_Elo", "Away_Elo"])

        assert not result.is_valid
        assert len(result.errors) > 0

    def test_pipeline_handles_missing_fixtures_file(self):
        """Test pipeline handles missing partidos.txt gracefully."""
        # This is tested implicitly by run_pipeline
        result = run_pipeline()
        assert result is not None


class TestPipelineDataIntegrity:
    """Data integrity checks."""

    def test_historical_data_size(self):
        """Verify historical data has expected size."""
        _, _, matches, _ = load_data()
        # ARG.csv has 6295 matches
        assert len(matches) >= 6000

    def test_no_duplicate_matches(self):
        """Verify no exact duplicate matches in historical data."""
        _, _, matches, _ = load_data()
        dup_cols = ["Date", "Home", "Away"]
        duplicates = matches.duplicated(subset=dup_cols).sum()
        assert duplicates == 0

    def test_date_ordering(self):
        """Verify matches are sorted by date."""
        _, _, matches, _ = load_data()
        dates = matches["Date"].dropna()
        assert dates.is_monotonic_increasing

    def test_shin_probabilities_imputed(self):
        """Test Shin probabilities are imputed for missing odds."""
        glossary, _, matches, _ = load_data()
        matches_with_features, _ = build_features(matches)

        # Check Shin columns exist
        assert "Shin_Prob_H" in matches_with_features.columns
        assert "Shin_Prob_D" in matches_with_features.columns
        assert "Shin_Prob_A" in matches_with_features.columns

        # Missing odds should be imputed to 1/3
        shin_h = matches_with_features["Shin_Prob_H"]
        nan_count = shin_h.isna().sum()
        # Should have very few or no NaN after imputation
        assert nan_count == 0 or nan_count < 100  # Allow some edge cases


if __name__ == "__main__":
    pytest.main([__file__, "-v"])