import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from src.pipeline import train_validate
from src.config import RESULT_ENCODING, MODEL_TYPE

# Mock model and its methods
class MockModel:
    def fit(self, X, y, sample_weight=None):
        pass
    def predict(self, X):
        # Return dummy predictions: 0 for away, 1 for draw, 2 for home
        # For simplicity, let's say it always predicts draw (1)
        return pd.Series(np.ones(len(X))).astype(int)
    def predict_proba(self, X):
        # Return dummy probabilities: away, draw, home
        # For simplicity, say 0.2, 0.6, 0.2
        return np.array([[0.2, 0.6, 0.2]] * len(X))

# Mock create_model function to return our MockModel
@patch('src.pipeline.create_model', return_value=MockModel())
def test_train_validate_collects_submodel_data(mock_create_model):
    """
    Test that train_validate function correctly collects data needed for
    the hybrid goals sub-model training.
    """
    # Create dummy DataFrame with necessary columns
    # This DataFrame needs to simulate the output of build_features
    data = {
        'HomeTeamGoals': [1, 2, 0, 3, 1, 2, 0, 1, 3, 2],
        'AwayTeamGoals': [1, 1, 0, 1, 0, 1, 2, 1, 1, 0],
        'FullTimeResult': [RESULT_ENCODING['D'], RESULT_ENCODING['H'], RESULT_ENCODING['D'],
                           RESULT_ENCODING['H'], RESULT_ENCODING['H'], RESULT_ENCODING['H'],
                           RESULT_ENCODING['A'], RESULT_ENCODING['D'], RESULT_ENCODING['H'],
                           RESULT_ENCODING['H']],
        'Expected_Home_Goals': [1.1, 2.0, 0.7, 2.5, 1.5, 1.8, 0.9, 1.3, 2.8, 2.1],
        'Expected_Away_Goals': [0.9, 1.0, 0.7, 1.2, 0.8, 1.1, 1.5, 1.0, 1.4, 0.9],
        'Feature_1': np.random.rand(10),
        'Feature_2': np.random.rand(10),
        'Date': pd.to_datetime(['2025-01-01', '2025-01-08', '2025-01-15', '2025-01-22',
                                '2025-01-29', '2025-02-05', '2025-02-12', '2025-02-19',
                                '2025-02-26', '2025-03-05'])
    }
    df = pd.DataFrame(data).sort_values('Date').reset_index(drop=True)

    # Define features for the model (including some dummy ones)
    features = ['Expected_Home_Goals', 'Expected_Away_Goals', 'Feature_1', 'Feature_2']

    # Call train_validate (this will be the function we modify)
    model, cv_acc, cv_ll, submodel_data_df = train_validate(df, features, model_type=MODEL_TYPE, n_splits=2)

    # Assertions
    assert isinstance(submodel_data_df, pd.DataFrame)
    # With 2 splits, and 10 rows, first split might have train=5, val=5; second train=7, val=3; total val rows = 5+3=8
    # However, TimeSeriesSplit uses growing window.
    # Split 1: train_idx = 0-4, val_idx = 5-9 (5 rows)
    # Split 2: train_idx = 0-7, val_idx = 8-9 (2 rows)
    # So total validation rows are 5 + 2 = 7.
    assert len(submodel_data_df) == 7, "Expected submodel_data_df to contain all validation rows from CV splits."

    expected_cols = [
        'exp_h', 'exp_a', 'ml_pred', 'p_h', 'p_d', 'p_a',
        'actual_home_goals', 'actual_away_goals'
    ]
    for col in expected_cols:
        assert col in submodel_data_df.columns, f"Missing expected column: {col}"

    # Verify a few values (e.g., first row of first validation split)
    # Based on dummy data and mock model, for first split's validation rows (index 5-9)
    # For row at original index 5 (first validation row in first split):
    # exp_h = 1.8, exp_a = 1.1, ml_pred = 1 (draw), p_h = 0.2, p_d = 0.6, p_a = 0.2
    # actual_home_goals = 2, actual_away_goals = 1

    # Find the row corresponding to original index 5 in the submodel_data_df
    # Since TimeSeriesSplit changes indices, we need to map back or rely on structure
    # With `result_type="expand"` for apply, need to verify carefully.
    # For now, just check column existence and length. Detailed value checks can be added once structure is stable.

    # Check some basic properties
    assert np.allclose(submodel_data_df['ml_pred'], 1) # All dummy predictions are 1
    assert np.allclose(submodel_data_df['p_h'], 0.2) # All dummy p_h are 0.2

