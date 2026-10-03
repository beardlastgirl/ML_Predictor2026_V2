"""Bayesian shrinkage for cold-start xG estimates early in a tournament."""

from src.config import BAYESIAN_SHRINKAGE_C, LEAGUE_MEAN_XG


def calculate_bayesian_shrunk_xg(observed_xg, matchday, league_mean=None, shrinkage_c=None):
    """Shrink an observed/estimated xG toward the league mean.

    Empirical-Bayes-style composite estimate: early in a tournament (low
    matchday), the estimate is pulled heavily toward the league mean; as
    matchday grows, the observed value dominates.

        shrunk = (observed * matchday + league_mean * C) / (matchday + C)

    Args:
        observed_xg: raw/estimated xG value for the team.
        matchday: matches played so far in the current tournament (>= 0).
            matchday=0 or 1 gives maximum shrinkage toward league_mean.
        league_mean: prior mean xG (defaults to config.LEAGUE_MEAN_XG).
        shrinkage_c: prior pseudo-count strength (defaults to
            config.BAYESIAN_SHRINKAGE_C); higher = more shrinkage.

    Returns:
        Shrunk xG estimate (float).
    """
    if league_mean is None:
        league_mean = LEAGUE_MEAN_XG
    if shrinkage_c is None:
        shrinkage_c = BAYESIAN_SHRINKAGE_C

    matchday = max(0, matchday)
    return (observed_xg * matchday + league_mean * shrinkage_c) / (matchday + shrinkage_c)
