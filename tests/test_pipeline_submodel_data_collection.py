"""
Tests for train_validate submodel data collection in src/pipeline.py.

train_validate returns: (model, cv_acc, cv_ll, submodel_data_df, naive_ll, bookie_ll)
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch
from src.pipeline import train_validate
from src.config import RESULT_ENCODING, MODEL_TYPE


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


@patch('src.pipeline.create_model', return_value=MockModel())
def test_train_validate_collects_submodel_data(mock_create_model):
    """
    train_validate collects validation fold data for sub-model training.
    Returns 6-tuple: (model, cv_acc, cv_ll, submodel_data_df, naive_ll, bookie_ll)
    """
    data = {
        'Home_GF': [1, 2, 0, 3, 1, 2, 0, 1, 3, 2],
        'Away_GF': [1, 1, 0, 1, 0, 1, 2, 1, 1, 0],
        'FullTimeResult': [
            RESULT_ENCODING['D'], RESULT_ENCODING['H'], RESULT_ENCODING['D'],
            RESULT_ENCODING['H'], RESULT_ENCODING['H'], RESULT_ENCODING['H'],
            RESULT_ENCODING['A'], RESULT_ENCODING['D'], RESULT_ENCODING['H'],
            RESULT_ENCODING['H']
        ],
        'Expected_Home_Goals': [1.1, 2.0, 0.7, 2.5, 1.5, 1.8, 0.9, 1.3, 2.8, 2.1],
        'Expected_Away_Goals': [0.9, 1.0, 0.7, 1.2, 0.8, 1.1, 1.5, 1.0, 1.4, 0.9],
        'Feature_1': np.random.rand(10),
        'Feature_2': np.random.rand(10),
        'Date': pd.to_datetime([
            '2025-01-01', '2025-01-08', '2025-01-15', '2025-01-22',
            '2025-01-29', '2025-02-05', '2025-02-12', '2025-02-19',
            '2025-02-26', '2025-03-05'
        ])
    }
    df = pd.DataFrame(data).sort_values('Date').reset_index(drop=True)
    features = ['Expected_Home_Goals', 'Expected_Away_Goals', 'Feature_1', 'Feature_2']

    result = train_validate(df, features, model_type=MODEL_TYPE, n_splits=2)

    # Current signature returns 6 values
    assert len(result) == 6, f"Expected 6 return values, got {len(result)}"
    model, cv_acc, cv_ll, submodel_data_df, naive_ll, bookie_ll = result

    assert isinstance(submodel_data_df, pd.DataFrame)
    # TimeSeriesSplit(2) on 10 rows produces validation sets of varying size
    # depending on dropna() results. Just verify it's non-empty and < total rows.
    assert len(submodel_data_df) > 0
    assert len(submodel_data_df) < len(df)

    expected_cols = ['exp_h', 'exp_a', 'ml_pred', 'p_h', 'p_d', 'p_a']
    for col in expected_cols:
        assert col in submodel_data_df.columns, f"Missing column: {col}"

    # Mock model always predicts draw (1)
    assert np.allclose(submodel_data_df['ml_pred'], 1)
    assert np.allclose(submodel_data_df['p_h'], 0.2)
    assert np.allclose(submodel_data_df['p_d'], 0.6)
