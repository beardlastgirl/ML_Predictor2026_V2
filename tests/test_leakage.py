
import pandas as pd
import numpy as np
import pytest
from src.pipeline import build_features

def test_no_temporal_leakage():
    """
    Verify that changing a match result at time T does not affect 
    the features of a match at time T-1.
    """
    # Create a dummy dataset
    data = {
        "Date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
        "Home": ["Team A", "Team B", "Team C"],
        "Away": ["Team B", "Team C", "Team A"],
        "HG": [1, 1, 1],
        "AG": [0, 0, 0],
        "Res": ["H", "H", "H"],
        "B365CH": [2.0, 2.0, 2.0],
        "B365CD": [3.0, 3.0, 3.0],
        "B365CA": [4.0, 4.0, 4.0],
    }
    df1 = pd.DataFrame(data)
    df2 = pd.DataFrame(data)
    
    # Change the result of the LAST match in df2
    df2.loc[2, "HG"] = 0
    df2.loc[2, "AG"] = 5
    df2.loc[2, "Res"] = "A"
    
    # Build features for both
    res1, _ = build_features(df1)
    res2, _ = build_features(df2)
    
    # Compare features for the FIRST match
    # They should be identical regardless of the outcome of the 3rd match
    first_match_features_1 = res1.iloc[0][["Home_Elo", "Away_Elo", "Home_Form", "Away_Form"]]
    first_match_features_2 = res2.iloc[0][["Home_Elo", "Away_Elo", "Home_Form", "Away_Form"]]
    
    pd.testing.assert_series_equal(first_match_features_1, first_match_features_2, 
                                 obj="Features of match T-1 changed when match T result was modified!")

if __name__ == "__main__":
    pytest.main([__file__])
