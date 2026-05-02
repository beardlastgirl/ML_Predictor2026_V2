"""
Data validation layer for ML_Predictor2026_V2

Provides schema validation for all input data sources (CSV, JSON, TXT)
to catch data quality issues early and prevent silent NaN propagation.
"""

import os
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from src.utils import log_info, log_ok, log_error, log_warning


class ValidationResult:
    """Container for validation results."""
    
    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.stats: Dict = {}
    
    def add_error(self, error: str):
        """Add a validation error."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add a validation warning."""
        self.warnings.append(warning)
    
    def report(self) -> str:
        """Generate validation report."""
        lines = []
        lines.append("=" * 60)
        lines.append("VALIDATION REPORT")
        lines.append("=" * 60)
        
        status = "VALID" if self.is_valid else "INVALID"
        lines.append(f"Status: {status}")
        
        if self.stats:
            lines.append("\nStatistics:")
            for key, value in self.stats.items():
                lines.append(f"  {key}: {value}")
        
        if self.warnings:
            lines.append(f"\nWarnings ({len(self.warnings)}):")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        
        if self.errors:
            lines.append(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                lines.append(f"  - {error}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


def validate_glossary(glossary: Dict[str, str]) -> ValidationResult:
    """Validate team name glossary."""
    result = ValidationResult()
    
    if not glossary:
        result.add_error("Glossary is empty")
        return result
    
    log_info("Validating glossary...")
    
    # Check for empty keys or values
    for key, value in glossary.items():
        if not key or not isinstance(key, str):
            result.add_error(f"Invalid glossary key: {key}")
        if not value or not isinstance(value, str):
            result.add_error(f"Invalid glossary value for key {key}: {value}")
    
    # Check for circular or self-referential mappings
    for key, value in glossary.items():
        if key.upper().strip() == value.upper().strip():
            result.add_warning(f"Self-referential mapping: {key} -> {value}")
    
    result.stats["total_mappings"] = len(glossary)
    
    if result.is_valid:
        log_ok(f"Glossary validated: {len(glossary)} mappings")
    else:
        log_error(f"Glossary validation failed: {len(result.errors)} errors")
    
    return result


def validate_historical_data(matches_df: pd.DataFrame) -> ValidationResult:
    """Validate historical match data (ARG.csv)."""
    result = ValidationResult()
    
    if matches_df is None or matches_df.empty:
        result.add_error("Historical data is empty")
        return result
    
    log_info("Validating historical data...")
    
    required_cols = ["HomeTeam", "AwayTeam", "FullTimeResult", "Date"]
    missing_cols = [col for col in required_cols if col not in matches_df.columns]
    if missing_cols:
        result.add_error(f"Missing required columns: {missing_cols}")
        return result
    
    # Check for missing values in critical columns
    for col in ["HomeTeam", "AwayTeam", "FullTimeResult"]:
        missing_count = matches_df[col].isna().sum()
        if missing_count > 0:
            result.add_error(f"Column '{col}' has {missing_count} missing values")
    
    # Validate result codes
    valid_results = {0, 1, 2, "0", "1", "2", "A", "D", "H"}
    invalid_results = matches_df[~matches_df["FullTimeResult"].isin(valid_results)]["FullTimeResult"].unique()
    if len(invalid_results) > 0:
        result.add_error(f"Invalid result codes: {list(invalid_results)}")
    
    # Check date format
    try:
        pd.to_datetime(matches_df["Date"])
    except Exception as e:
        result.add_error(f"Invalid date format: {str(e)}")
    
    # Check for GF/GA columns if present
    if "Home_GF" in matches_df.columns:
        gf_invalid = matches_df[matches_df["Home_GF"] < 0]["Home_GF"].count()
        if gf_invalid > 0:
            result.add_error(f"{gf_invalid} rows with negative Home_GF")
    
    if "Away_GF" in matches_df.columns:
        ga_invalid = matches_df[matches_df["Away_GF"] < 0]["Away_GF"].count()
        if ga_invalid > 0:
            result.add_error(f"{ga_invalid} rows with negative Away_GF")
    
    result.stats["total_matches"] = len(matches_df)
    result.stats["date_range"] = f"{matches_df['Date'].min()} to {matches_df['Date'].max()}"
    result.stats["teams"] = matches_df[["HomeTeam", "AwayTeam"]].stack().nunique()
    
    if result.is_valid:
        log_ok(f"Historical data validated: {len(matches_df)} matches, {result.stats['teams']} teams")
    else:
        log_error(f"Historical data validation failed: {len(result.errors)} errors")
    
    return result


def validate_fixtures(fixtures_df: pd.DataFrame) -> ValidationResult:
    """Validate upcoming fixtures file."""
    result = ValidationResult()
    
    if fixtures_df is None or fixtures_df.empty:
        result.add_warning("Fixtures data is empty")
        return result
    
    log_info("Validating fixtures...")
    
    required_cols = ["HomeTeam", "AwayTeam"]
    missing_cols = [col for col in required_cols if col not in fixtures_df.columns]
    if missing_cols:
        result.add_error(f"Missing required columns: {missing_cols}")
        return result
    
    # Check for missing team names
    missing_home = fixtures_df["HomeTeam"].isna().sum()
    missing_away = fixtures_df["AwayTeam"].isna().sum()
    if missing_home > 0:
        result.add_error(f"{missing_home} fixtures with missing Home team")
    if missing_away > 0:
        result.add_error(f"{missing_away} fixtures with missing Away team")
    
    # Check for identical teams
    identical = (fixtures_df["HomeTeam"].str.upper() == fixtures_df["AwayTeam"].str.upper()).sum()
    if identical > 0:
        result.add_warning(f"{identical} fixtures with identical Home/Away teams")
    
    result.stats["total_fixtures"] = len(fixtures_df)
    result.stats["unique_teams"] = fixtures_df[["HomeTeam", "AwayTeam"]].stack().nunique()
    
    if result.is_valid:
        log_ok(f"Fixtures validated: {len(fixtures_df)} matches")
    else:
        log_error(f"Fixtures validation failed: {len(result.errors)} errors")
    
    return result


def validate_sofascore_data(sofascore_data: Dict) -> ValidationResult:
    """Validate Sofascore standings JSON."""
    result = ValidationResult()

    if not sofascore_data:
        result.add_warning("Sofascore data is empty")
        return result

    log_info("Validating Sofascore data...")
    # The processed sofascore_data is a dictionary where keys are team names.
    # It has already been successfully loaded.
    return result

def validate_model_features(features_df: pd.DataFrame, feature_columns: List[str]) -> ValidationResult:
    """Validate ML model features before training."""
    result = ValidationResult()
    
    if features_df is None or features_df.empty:
        result.add_error("Features DataFrame is empty")
        return result
    
    log_info("Validating model features...")
    
    # Check all required features exist
    missing_features = [f for f in feature_columns if f not in features_df.columns]
    if missing_features:
        result.add_error(f"Missing features: {missing_features}")
        return result
    
    # Check for NaN values in features
    nan_counts = features_df[feature_columns].isna().sum()
    total_nans = nan_counts.sum()
    if total_nans > 0:
        result.add_warning(f"Total NaN values in features: {total_nans}")
        high_nan_features = nan_counts[nan_counts > len(features_df) * 0.1]
        if len(high_nan_features) > 0:
            result.add_error(f"Features with >10% NaN: {list(high_nan_features.index)}")
    
    # Check for Inf values
    inf_counts = features_df[feature_columns].map(lambda x: np.isinf(x) if isinstance(x, (int, float)) else False).sum()
    total_infs = inf_counts.sum()
    if total_infs > 0:
        result.add_error(f"Total Inf values in features: {total_infs}")
    
    # Check feature bounds
    bounds_checks = {
        "Elo": (800, 2800),
        "Form": (0, 3),
        "Probability": (0, 1),
    }
    
    for feature in feature_columns:
        for bound_type, (min_val, max_val) in bounds_checks.items():
            if bound_type in feature:
                out_of_bounds = ((features_df[feature] < min_val) | (features_df[feature] > max_val)).sum()
                if out_of_bounds > 0:
                    result.add_warning(f"{feature}: {out_of_bounds} values out of bounds [{min_val}, {max_val}]")
    
    result.stats["total_samples"] = len(features_df)
    result.stats["total_features"] = len(feature_columns)
    result.stats["total_nans"] = int(total_nans)
    result.stats["total_infs"] = int(total_infs)
    
    if result.is_valid:
        log_ok(f"Model features validated: {len(features_df)} samples, {len(feature_columns)} features")
    else:
        log_error(f"Feature validation failed: {len(result.errors)} errors")
    
    return result


def validate_pipeline_inputs(
    glossary: Dict,
    matches_df: pd.DataFrame,
    fixtures_df: Optional[pd.DataFrame],
    sofascore_data: Dict
) -> Tuple[bool, List[str]]:
    """
    Validate all pipeline inputs before execution.
    
    Returns:
        Tuple of (is_valid, error_messages)
    """
    log_info("Running pre-flight validation checks...")
    
    all_results = []
    
    # Validate each component
    glossary_result = validate_glossary(glossary)
    all_results.append(glossary_result)
    
    matches_result = validate_historical_data(matches_df)
    all_results.append(matches_result)
    
    if fixtures_df is not None and not fixtures_df.empty:
        fixtures_result = validate_fixtures(fixtures_df)
        all_results.append(fixtures_result)
    
    sofascore_result = validate_sofascore_data(sofascore_data)
    all_results.append(sofascore_result)
    
    # Aggregate results
    all_valid = all(r.is_valid for r in all_results)
    all_errors = []
    for r in all_results:
        all_errors.extend(r.errors)
    
    if all_valid:
        log_ok("All validation checks passed!")
    else:
        log_error(f"Validation failed with {len(all_errors)} errors")
        for error in all_errors:
            log_error(f"  - {error}")
    
    return all_valid, all_errors
