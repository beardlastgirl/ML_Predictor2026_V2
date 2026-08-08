# Tournament-aware time-series cross-validation

from typing import Iterator, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit


def find_season_boundaries(seasons: pd.Series) -> List[int]:
    """Return row indices where the season/tournament changes."""
    boundaries = [0]
    values = seasons.fillna("unknown").astype(str).values
    for i in range(1, len(values)):
        if values[i] != values[i - 1]:
            boundaries.append(i)
    boundaries.append(len(values))
    return boundaries


def tournament_aware_cv_splits(
    n_samples: int,
    seasons: pd.Series,
    n_splits: int = 5,
) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """
    Yield train/validation indices with fold cuts snapped to season transitions.

    Prefers validation windows that start at tournament boundaries. Falls back
    to sklearn TimeSeriesSplit when there are fewer season segments than folds.
    """
    boundaries = find_season_boundaries(seasons)
    segment_starts = boundaries[:-1]
    segment_ends = boundaries[1:]

    if len(segment_starts) <= n_splits:
        yield from TimeSeriesSplit(n_splits=n_splits).split(np.arange(n_samples))
        return

    # Use the last n_splits season segments as validation blocks
    val_segments = list(zip(segment_starts, segment_ends))[-n_splits:]
    for val_start, val_end in val_segments:
        if val_start == 0:
            continue
        train_idx = np.arange(0, val_start)
        val_idx = np.arange(val_start, val_end)
        if len(train_idx) == 0 or len(val_idx) == 0:
            continue
        yield train_idx, val_idx
