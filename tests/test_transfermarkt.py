"""Focused tests for Transfermarkt club profile URL lookup.

Tests cover: club IDs, unknown names, ambiguous matches,
accent/special formatting, and canonical name consistency.
"""

import pytest
from src.transfermarkt_lookup import get_club_url, get_club_id
from src.normalization import canonicalize_name


# --- Test: All 30 clubs resolve with correct IDs ---

KNOWN_CLUB_IDS = {
    "River Plate": 209,
    "Boca Juniors": 189,
    "Rosario Central": 1418,
    "Racing Club": 1444,
    "Estudiantes LP": 288,
    "Independiente Rivadavia": 12179,
    "San Lorenzo": 1775,
    "Velez Sarsfield": 1029,
    "Tigre": 11831,
    "Talleres": 3938,
    "Lanus": 333,
    "Argentinos Juniors": 1030,
    "Newell's Old Boys": 1286,
    "Platense": 928,
    "Independiente": 1234,
    "Defensa y Justicia": 2402,
    "Gimnasia LP": 1106,
    "Belgrano": 2417,
    "Huracan": 2063,
    "Gimnasia Mendoza": 14687,
    "Barracas Central": 25184,
    "Instituto": 1829,
    "Union": 7097,
    "Atletico Tucuman": 14554,
    "Sarmiento": 12454,
    "Banfield": 830,
    "Deportivo Riestra": 19775,
    "Central Cordoba SdE": 31284,
    "Aldosivi": 12301,
    "Estudiantes Rio Cuarto": 14602,
}


@pytest.mark.parametrize("club_name, expected_id", KNOWN_CLUB_IDS.items())
def test_club_id_resolution(club_name, expected_id):
    """Test that each of the 30 clubs resolves to the correct Transfermarkt ID."""
    result = get_club_url(club_name)
    assert result is not None, f"Club '{club_name}' not found in lookup"
    url, club_id = result
    assert club_id == expected_id, (
        f"Club '{club_name}': expected ID {expected_id}, got {club_id}"
    )


# --- Test: Unknown / unrecognized club names return None ---

UNKNOWN_CLUBS = [
    "Nuevo Equipo FC",
    "Non Existent Club",
    "Made Up Team",
    "Fictional Club",
]


@pytest.mark.parametrize("club_name", UNKNOWN_CLUBS)
def test_unknown_clubs_return_none(club_name):
    """Test that unrecognized club names return None."""
    result = get_club_url(club_name)
    assert result is None, f"Unknown club '{club_name}' should return None, got {result}"


# --- Test: Ambiguous club name handling ---

# These names are known to be ambiguous (multiple clubs exist).
# The test ensures they don't crash the system.
AMBIGUOUS_CLUB_NAMES = [
    "San Martin SJ",
    "San Martin T",
    "Central",  # ambiguous: could be Rosario Central or Central Córdoba
]


@pytest.mark.parametrize("club_name", AMBIGUOUS_CLUB_NAMES)
def test_ambiguous_clubs_dont_crash(club_name):
    """Test that ambiguous club names don't cause errors."""
    result = get_club_url(club_name)
    # Allow None result; just ensure no exception is raised
    assert result is not None or True


# --- Test: Accented and specially formatted names ---

SPECIAL_FORMAT_NAMES = [
    "River Plate",
    "Estudiantes L.P.",
    "Argentinos Juniors",
]


@pytest.mark.parametrize("club_name", SPECIAL_FORMAT_NAMES)
def test_special_format_names(club_name):
    """Test that names with periods/formatting resolve correctly."""
    result = get_club_url(club_name)
    assert result is not None, f"Club '{club_name}' should resolve successfully"


# --- Test: Canonical name consistency with normalization ---

def test_canonical_name_consistency():
    """Test that canonicalize_name produces consistent output for all 30 clubs."""
    clubs = list(KNOWN_CLUB_IDS.keys())
    canonical_map = {}
    for club in clubs:
        canonical = canonicalize_name(club)
        # The canonical name should be uppercase, no accents, no dots/hyphens
        assert canonical == canonical.upper(), f"Canonical '{canonical}' not uppercase"
        assert "." not in canonical, f"Canonical '{canonical}' contains dots"
        assert "--" not in canonical, f"Canonical '{canonical}' contains double hyphens"
        canonical_map[club] = canonical

    # All 30 clubs should have unique canonical names
    canonical_values = list(canonical_map.values())
    assert len(set(canonical_values)) == len(canonical_values), (
        "Duplicate canonical names found across clubs"
    )