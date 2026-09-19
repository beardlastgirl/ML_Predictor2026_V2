"""
Tests for the train_validate contract in src/pipeline.py.

train_validate returns: (model, cv_acc, cv_ll, naive_ll, bookie_ll)
"""
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
def test_train_validate_returns_five_tuple(mock_create_model):
    """
    train_validate returns the 5-tuple
    (model, cv_acc, cv_ll, naive_ll, bookie_ll) and runs 2 CV folds.
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

    assert len(result) == 5, f"Expected 5 return values, got {len(result)}"
    model, cv_acc, cv_ll, naive_ll, bookie_ll = result
    assert len(cv_acc) > 0
    assert len(cv_ll) > 0