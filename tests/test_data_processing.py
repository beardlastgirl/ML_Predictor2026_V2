import pytest
import os
import pandas as pd
from src.data_processing import load_glossary, normalize_team_name

# Define a temporary glossary file for testing
@pytest.fixture
def temp_glossary_file(tmp_path):
    content = """
# Team Name Glossary for Liga Profesional Argentina
# Last updated: 2026-04-17

Boca Jr -> BOCA JUNIORS
CA Boca Juniors = BOCA JUNIORS
River : RIVER PLATE
Racing Club de Avellaneda -> RACING CLUB
Huracán -> HURACAN
Vélez Sarsfield -> VELEZ SARSFIELD
Atlético Tucumán -> ATL TUCUMAN
Independiente Rivadavia -> IND RIVADAVIA
Central Córdoba Santiago -> CENTRAL CORDOBA
"""
    filepath = tmp_path / "Glossary.txt"
    filepath.write_text(content, encoding="utf-8")
    return filepath

# Test for load_glossary function
def test_load_glossary(temp_glossary_file):
    glossary = load_glossary(temp_glossary_file)
    assert len(glossary) == 9
    assert glossary["BOCA JR"] == "BOCA JUNIORS"
    assert glossary["CA BOCA JUNIORS"] == "BOCA JUNIORS"
    assert glossary["RIVER"] == "RIVER PLATE"
    assert glossary["RACING CLUB DE AVELLANEDA"] == "RACING CLUB"
    assert glossary["HURACAN"] == "HURACAN"
    assert glossary["VELEZ SARSFIELD"] == "VELEZ SARSFIELD"
    assert glossary["ATLETICO TUCUMAN"] == "ATL TUCUMAN"
    assert glossary["INDEPENDIENTE RIVADAVIA"] == "IND RIVADAVIA"
    assert glossary["CENTRAL CORDOBA SANTIAGO"] == "CENTRAL CORDOBA"

def test_load_glossary_file_not_found():
    glossary = load_glossary("non_existent_glossary.txt")
    assert len(glossary) == 0

# Test for normalize_team_name function
@pytest.mark.parametrize("input_name, expected_name, glossary_enabled", [
    # Test cases for internal mapping
    ("Central Cordoba (Sgo)", "CENTRAL CORDOBA", False),
    ("Estudiantes", "ESTUDIANTES LP", False),
    ("Newells", "NEWELLS OLD BOYS", False),
    ("Nob", "NEWELLS OLD BOYS", False),
    ("DyJ", "DEFENSA Y JUSTICIA", False),
    ("Atl Tuc", "ATL TUCUMAN", False),
    ("Ind Riv", "INDEPENDIENTE RIVADAVIA", False),
    ("Dep Riestra", "DEPORTIVO RIESTRA", False),
    ("Barracas", "BARRACAS CENTRAL", False),
    ("Sarmiento (J)", "SARMIENTO JUNIN", False),

    # Test cases for glossary mapping (when glossary_enabled is True)
    ("Boca Jr", "BOCA JUNIORS", True),
    ("CA Boca Juniors", "BOCA JUNIORS", True),
    ("River", "RIVER PLATE", True),
    ("Racing Club de Avellaneda", "RACING CLUB", True),
    ("Huracan", "HURACAN", True), # Accent removed by normalize_team_name
    ("Velez Sarsfield", "VELEZ SARSFIELD", True), # Accent removed by normalize_team_name
    ("Atletico Tucuman", "ATL TUCUMAN", True), # Accent removed by normalize_team_name
    ("Independiente Rivadavia", "IND RIVADAVIA", True),
    ("Central Cordoba Santiago", "CENTRAL CORDOBA", True),

    # Test cases for general normalization (accents, special chars, spacing)
    ("Boca.Juniors-", "BOCA JUNIORS", False),
    ("   River   Plate", "RIVER PLATE", False),
    ("Racing--Club", "RACING CLUB", False),
    ("San Lorenzo de Almagro", "SAN LORENZO DE ALMAGRO", False), # Not in internal/test glossary
    ("Vélez-Sarsfield.", "VELEZ SARSFIELD", False), # Accent and special chars handled

    # Test cases for mixed internal and glossary behavior
    ("Estudiantes", "ESTUDIANTES LP", True), # Should use internal mapping
    ("Huracán", "HURACAN", True), # Glossary has it, but internal mapping handles accents too

    # Test cases for empty or NaN inputs
    ("", "", False),
    (None, "", False),
    (pd.NA, "", False),
])
def test_normalize_team_name(input_name, expected_name, glossary_enabled, temp_glossary_file):
    if glossary_enabled:
        glossary = load_glossary(temp_glossary_file)
    else:
        glossary = None # Do not pass glossary to test internal mapping and general normalization

    if glossary_enabled: # For glossary-enabled tests, apply glossary
        assert normalize_team_name(input_name, glossary) == expected_name
    else: # For other tests, ensure glossary is not influencing
        assert normalize_team_name(input_name, None) == expected_name

# Test that glossary takes precedence over internal mapping
def test_normalize_team_name_glossary_precedence(tmp_path):
    content = """
    Estudiantes -> ESTUDIANTES CUSTOM
    """
    filepath = tmp_path / "Glossary.txt"
    filepath.write_text(content, encoding="utf-8")
    custom_glossary = load_glossary(filepath)

    # "Estudiantes" has an internal mapping to "ESTUDIANTES LP"
    # But custom glossary should override it to "ESTUDIANTES CUSTOM"
    assert normalize_team_name("Estudiantes", custom_glossary) == "ESTUDIANTES CUSTOM"
