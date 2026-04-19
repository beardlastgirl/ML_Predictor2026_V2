import os
import pytest
from src.data_processing import normalize_team_name, load_glossary

# Assume Glossary.txt is in the project root for testing
GLOSSARY_FILEPATH = "Glossary.txt"

# Load the glossary once for all tests
@pytest.fixture(scope="module")
def team_glossary():
    """Fixture to load the team glossary."""
    return load_glossary(GLOSSARY_FILEPATH)

def test_normalize_team_name_with_glossary_entries(team_glossary):
    """Test normalization using entries explicitly defined in Glossary.txt."""
    # Test cases from Glossary.txt
    test_cases = [
        ("Boca Jr", "BOCA JUNIORS"),
        ("Boca Jrs", "BOCA JUNIORS"), # Test another variation for Boca
        ("River", "RIVER PLATE"),
        ("CA River Plate", "RIVER PLATE"),
        ("racing avellaneda", "RACING CLUB"), # Case-insensitive
        ("Racing Club de Avellaneda", "RACING CLUB"),
        ("San Lorenzo de Almagro", "SAN LORENZO"),
        ("CA Velez Sarsfield", "VELEZ SARSFIELD"),
        ("newell's old boys", "NEWELLS OLD BOYS"), # From glossary, should override internal if present
        ("Gimnasia y Esgrima La Plata", "GIMNASIA LP"),
        ("Club Atletico Aldosivi", "ALDOSIVI")
    ]

    for raw_name, expected_normalized_name in test_cases:
        actual_normalized_name = normalize_team_name(raw_name, team_glossary)
        assert actual_normalized_name == expected_normalized_name, \
            f"Failed for '{raw_name}': Expected '{expected_normalized_name}', Got '{actual_normalized_name}'"

def test_normalize_team_name_with_internal_mapping(team_glossary):
    """Test normalization using internal mapping for names not in glossary."""
    # These names should be covered by INTERNAL_MAPPING in data_processing.py
    # and NOT explicitly in Glossary.txt (or should be overridden by glossary if present)
    test_cases = [
        ("GIMNASIA", "GIMNASIA LP"), # From internal mapping
        ("INSTITUTO ACC", "INSTITUTO"), # From internal mapping
        ("ROSARIO", "ROSARIO CENTRAL"), # From internal mapping
        ("DEFENSA", "DEFENSA Y JUSTICIA"), # From internal mapping
        ("RIESTRA", "DEP RIESTRA") # Corrected based on Glossary.txt
    ]
    for raw_name, expected_normalized_name in test_cases:
        actual_normalized_name = normalize_team_name(raw_name, team_glossary)
        assert actual_normalized_name == expected_normalized_name, \
            f"Failed for '{raw_name}': Expected '{expected_normalized_name}', Got '{actual_normalized_name}'"

def test_normalize_team_name_without_mapping(team_glossary):
    """Test normalization for names not found in glossary or internal mapping."""
    test_cases = [
        ("My New Team", "MY NEW TEAM"),
        ("A.C. Milan", "A C MILAN"), # Corrected based on _canonicalize_name
        ("FC BARCELONA-2", "FC BARCELONA 2")
    ]
    for raw_name, expected_normalized_name in test_cases:
        actual_normalized_name = normalize_team_name(raw_name, team_glossary)
        assert actual_normalized_name == expected_normalized_name, \
            f"Failed for '{raw_name}': Expected '{expected_normalized_name}', Got '{actual_normalized_name}'"

def test_normalize_team_name_edge_cases(team_glossary):
    """Test edge cases for normalize_team_name."""
    assert normalize_team_name("", team_glossary) == ""
    assert normalize_team_name(None, team_glossary) == ""
    assert normalize_team_name("   ", team_glossary) == ""
    assert normalize_team_name("  Team X  ", team_glossary) == "TEAM X"
    assert normalize_team_name("Team-Y", team_glossary) == "TEAM Y"
    assert normalize_team_name("Team.Z", team_glossary) == "TEAM Z"
    assert normalize_team_name("TEAM ÑUÑÚ", team_glossary) == "TEAM NUNU" # Accents removed
