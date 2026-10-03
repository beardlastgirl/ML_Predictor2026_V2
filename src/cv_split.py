"""
Tournament-aware temporal cross-validation splits.

Provides CV splitting that respects tournament/season boundaries to prevent
lookahead leakage. Falls back to standard TimeSeriesSplit with warning
when insufficient segment boundaries exist.
"""

import warnings
import numpy as np
import pandas as pd
from typing import List, Tuple, Optional
from sklearn.model_selection import TimeSeriesSplit


def get_tournament_boundaries(matches_df: pd.DataFrame, date_col: str = "Date") -> List[int]:
    """
    Identify tournament/season boundary indices in a sorted match DataFrame.
    
    Args:
        matches_df: DataFrame sorted by date
        date_col: Column name for match dates
        
    Returns:
        List of row indices where new tournaments/seasons begin
    """
    if matches_df.empty:
        return []
    
    dates = pd.to_datetime(matches_df[date_col])
    boundaries = [0]  # First match is always a boundary
    
    # Detect season boundaries by large gaps in dates (>60 days)
    date_diffs = dates.diff().dt.days
    season_starts = date_diffs[date_diffs > 60].index.tolist()
    
    # Also detect explicit season column if present
    if "Season" in matches_df.columns:
        season_changes = matches_df["Season"].ne(matches_df["Season"].shift()).cumsum()
        season_boundaries = matches_df[season_changes != season_changes.shift()].index.tolist()
        boundaries.extend([b for b in season_boundaries if b not in boundaries])
    
    boundaries.extend([b for b in season_starts if b not in boundaries])
    boundaries = sorted(set(boundaries))
    
    return boundaries


def tournament_aware_split(
    n_samples: int,
    boundaries: List[int],
    n_splits: int = 5,
    test_size: Optional[int] = None,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Generate CV splits that respect tournament boundaries.
    
    Each fold's test set is a contiguous block of matches within a single
    tournament/season. Training set includes all prior matches.
    
    Args:
        n_samples: Total number of samples
        boundaries: List of tournament start indices
        n_splits: Desired number of CV folds
        test_size: Optional fixed test set size
        
    Returns:
        List of (train_indices, test_indices) tuples
    """
    if not boundaries or len(boundaries) < 2:
        # Not enough boundaries, fall back to standard TimeSeriesSplit
        warnings.warn(
            f"Insufficient tournament boundaries ({len(boundaries)}). "
            f"Falling back to standard TimeSeriesSplit. "
            f"Season boundaries will not be respected.",
            UserWarning,
            stacklevel=2
        )
        tscv = TimeSeriesSplit(n_splits=n_splits, test_size=test_size)
        return list(tscv.split(np.arange(n_samples)))
    
    # Ensure boundaries are within range
    boundaries = [b for b in boundaries if 0 <= b < n_samples]
    boundaries = sorted(set(boundaries))
    
    # If still not enough boundaries, fall back
    if len(boundaries) < 2:
        warnings.warn(
            f"Insufficient valid tournament boundaries ({len(boundaries)}). "
            f"Falling back to standard TimeSeriesSplit.",
            UserWarning,
            stacklevel=2
        )
        tscv = TimeSeriesSplit(n_splits=n_splits, test_size=test_size)
        return list(tscv.split(np.arange(n_samples)))
    
    # Create segments between boundaries
    segments = []
    for i, start in enumerate(boundaries):
        end = boundaries[i + 1] if i + 1 < len(boundaries) else n_samples
        if end > start:
            segments.append((start, end))
    
    # If fewer segments than n_splits, adjust n_splits
    n_splits = min(n_splits, max(2, len(segments)))
    
    if len(segments) <= 1:
        warnings.warn(
            f"Only {len(segments)} tournament segment(s) found. "
            f"Cannot create {n_splits} folds respecting boundaries. "
            f"Falling back to TimeSeriesSplit.",
            UserWarning,
            stacklevel=2
        )
        tscv = TimeSeriesSplit(n_splits=n_splits, test_size=test_size)
        return list(tscv.split(np.arange(n_samples)))
    
    # Distribute segments across folds
    splits = []
    segment_per_fold = max(1, len(segments) // n_splits)
    
    for fold in range(n_splits):
        test_start_idx = fold * segment_per_fold
        test_end_idx = min(test_start_idx + segment_per_fold, len(segments))
        
        if test_start_idx >= len(segments):
            break
            
        # Test set: segments for this fold
        test_indices = []
        for seg_idx in range(test_start_idx, test_end_idx):
            seg_start, seg_end = segments[seg_idx]
            test_indices.extend(range(seg_start, seg_end))
        
        # Train set: all segments before test segments
        train_indices = []
        for seg_idx in range(0, test_start_idx):
            seg_start, seg_end = segments[seg_idx]
            train_indices.extend(range(seg_start, seg_end))
        
        if train_indices and test_indices:
            splits.append((np.array(train_indices), np.array(test_indices)))
    
    # Ensure we have at least 2 splits
    if len(splits) < 2:
        warnings.warn(
            f"Could only create {len(splits)} valid fold(s). "
            f"Falling back to TimeSeriesSplit.",
            UserWarning,
            stacklevel=2
        )
        tscv = TimeSeriesSplit(n_splits=n_splits, test_size=test_size)
        return list(tscv.split(np.arange(n_samples)))
    
    return splits


def make_tournament_aware_cv(
    matches_df: pd.DataFrame,
    n_splits: int = 5,
    date_col: str = "Date",
    test_size: Optional[int] = None,
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Convenience function to create tournament-aware CV splits from match DataFrame.
    
    Args:
        matches_df: DataFrame with match data (must be sorted by date)
        n_splits: Desired number of CV folds
        date_col: Column name for match dates
        test_size: Optional fixed test set size
        
    Returns:
        List of (train_indices, test_indices) tuples
    """
    boundaries = get_tournament_boundaries(matches_df, date_col)
    return tournament_aware_split(len(matches_df), boundaries, n_splits, test_size)


class TournamentAwareTimeSeriesSplit:
    """
    Scikit-learn compatible CV splitter that respects tournament boundaries.
    
    Usage:
        cv = TournamentAwareTimeSeriesSplit(n_splits=5)
        for train_idx, test_idx in cv.split(X, y, groups=dates):
            ...
    """
    
    def __init__(self, n_splits: int = 5, test_size: Optional[int] = None):
        self.n_splits = n_splits
        self.test_size = test_size
    
    def get_n_splits(self, X=None, y=None, groups=None) -> int:
        return self.n_splits
    
    def split(self, X, y=None, groups=None):
        """
        Generate tournament-aware splits.
        
        Args:
            X: Feature matrix (ignored, uses shape only)
            y: Target (ignored)
            groups: Optional array of tournament/season identifiers.
                   If provided, boundaries are detected from group changes.
                   If not provided, boundaries are detected from date gaps.
        """
        n_samples = X.shape[0] if hasattr(X, 'shape') else len(X)
        
        if groups is not None:
            # Detect boundaries from group changes
            groups = np.asarray(groups)
            boundaries = [0]
            changes = np.where(groups[1:] != groups[:-1])[0] + 1
            boundaries.extend(changes.tolist())
            boundaries = sorted(set(boundaries))
        else:
            # Need dates from somewhere - can't do without matches_df
            # Fall back to standard TimeSeriesSplit
            warnings.warn(
                "No tournament groups provided and no date column available. "
                "Falling back to standard TimeSeriesSplit.",
                UserWarning,
                stacklevel=2
            )
            tscv = TimeSeriesSplit(n_splits=self.n_splits, test_size=self.test_size)
            yield from tscv.split(X)
            return
        
        splits = tournament_aware_split(n_samples, boundaries, self.n_splits, self.test_size)
        yield from splits


if __name__ == "__main__":
    # Quick demo/test
    import pandas as pd
    
    # Create dummy match data with two seasons
    dates = pd.date_range("2023-01-01", periods=100, freq="3D")
    dates2 = pd.date_range("2023-09-01", periods=100, freq="3D")
    all_dates = dates.tolist() + dates2.tolist()
    
    df = pd.DataFrame({
        "Date": all_dates,
        "Home": ["TeamA"] * 200,
        "Away": ["TeamB"] * 200,
    })
    
    print("Testing tournament boundary detection...")
    boundaries = get_tournament_boundaries(df)
    print(f"Boundaries found at indices: {boundaries}")
    
    print("\nTesting tournament-aware splits...")
    splits = make_tournament_aware_cv(df, n_splits=5)
    print(f"Created {len(splits)} splits:")
    for i, (train, test) in enumerate(splits):
        print(f"  Fold {i+1}: train={len(train)}, test={len(test)}, "
              f"train range=[{train[0]}-{train[-1]}], test range=[{test[0]}-{test[-1]}]")