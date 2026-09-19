"""Unified team-identity layer — single source of truth for canonical names.

Combines the three name maps used across the wired data paths into one
resolver with Glossary.txt precedence:

  * Glossary.txt       -- user-defined canonical mappings (highest)
  * _API_NAME_MAP_RAW  -- API-Football names -> canonical (data_ingestion)
  * INTERNAL_MAPPING   -- nickname/abbreviation variations (data_processing)

Individual consumers may keep using the existing maps; EntityResolver is the
authoritative composition for new code (DataGateway) and for conflict tests.
"""
from src.data_processing import _canonicalize_name, load_glossary, INTERNAL_MAPPING
from src.data_ingestion import _API_NAME_MAP_RAW


class EntityResolver:
    """Resolve arbitrary team-name spellings to a single canonical name."""

    def __init__(self, glossary_path: str = "Glossary.txt"):
        self.glossary = load_glossary(glossary_path)
        self.api_map = {
            _canonicalize_name(k): v for k, v in _API_NAME_MAP_RAW.items()
        }

    def resolve(self, name) -> str:
        """Canonical name for ``name`` (glossary -> API map -> internal map)."""
        canonical = _canonicalize_name(name)
        if canonical in self.glossary:
            return self.glossary[canonical]
        if canonical in self.api_map:
            return self.api_map[canonical]
        return INTERNAL_MAPPING.get(canonical, canonical)