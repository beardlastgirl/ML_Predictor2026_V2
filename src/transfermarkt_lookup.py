"""Look up Transfermarkt club profile URLs for Liga Profesional Argentina clubs.

Provides quick resolution from club names to Transfermarkt profile URLs and IDs.
Data sourced from transfermarkt_urls.txt, extracted from the competition page.
"""

import re
from pathlib import Path
from typing import Optional, Tuple


# Project-relative path to the URLs file
_URLS_FILE = Path(__file__).resolve().parent.parent / "transfermarkt_urls.txt"


def _load_urls() -> dict:
    """Load the club name → (URL, club_id) mapping from transfermarkt_urls.txt.

    Returns:
        Dictionary mapping canonical club names to (url, club_id) tuples.
        Club names are canonicalized (uppercase, accent-stripped) for matching.
    """
    mapping: dict = {}
    if not _URLS_FILE.exists():
        return mapping

    # Build a reverse map: normalized name -> (url, club_id)
    with open(_URLS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            # Support format: "Club Name -> URL (ID)" or "Club Name -> URL"
            # The club name may contain -> inside it (e.g., "Boca Juniors -> ...")
            # but our format uses "->" as the separator, so we split on the last "->"
            if "->" in line:
                # Split on the first "->" only - everything before is the name,
                # everything after is the URL (which may contain spaces)
                name_part, rest = line.split("->", 1)
                name_raw = name_part.strip()
                rest = rest.strip()

                # Extract URL and optional club ID in parentheses at the end
                # Pattern: URL (ID) or just URL
                url_match = re.match(r"(https?://\S+)\s*\((\d+)\)?$", rest)
                if url_match:
                    url = url_match.group(1)
                    club_id = int(url_match.group(2)) if url_match.group(2) else None
                else:
                    # No parentheses with ID
                    url = rest
                    club_id = None

                # Canonicalize the name for matching
                from src.normalization import canonicalize_name
                name_canonical = canonicalize_name(name_raw)

                mapping[name_canonical] = (url, club_id)

    return mapping


# Pre-loaded lookup table
_urls_cache: Optional[dict] = None


def get_club_url(club_name: str) -> Optional[Tuple[str, int]]:
    """Get the Transfermarkt profile URL and club ID for a given club name.

    Args:
        club_name: Raw club name (e.g., "Boca Juniors", "Racing Club", "Gimnasia LP")

    Returns:
        Tuple of (url, club_id) if found, or None if the club is not in the database.
        club_id will be -1 if present in URL but could not be parsed as int.
    """
    global _urls_cache
    if _urls_cache is None:
        _urls_cache = _load_urls()

    # Canonicalize the input name for matching
    from src.normalization import canonicalize_name
    name_canonical = canonicalize_name(club_name)

    result = _urls_cache.get(name_canonical)
    if result is None:
        return None

    url, club_id = result
    # Ensure club_id is int; default to -1 if missing
    if club_id is None:
        club_id = -1
    return url, club_id


def get_club_id(club_name: str) -> Optional[int]:
    """Get just the club ID for a given club name.

    Args:
        club_name: Raw club name

    Returns:
        Club ID as int, or None if not found.
    """
    result = get_club_url(club_name)
    if result is None:
        return None
    url, club_id = result
    if club_id < 0:
        return None
    return club_id


if __name__ == "__main__":
    # Quick CLI demo
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m src.transfermarkt_lookup \"Club Name\"")
        print("Examples:")
        for name in ["Boca Juniors", "River Plate", "Racing Club", "Estudiantes LP"]:
            result = get_club_url(name)
            if result:
                url, cid = result
                print(f"  {name:30s} -> ID={cid:5d}  URL={url}")
            else:
                print(f"  {name:30s} -> NOT FOUND")
        sys.exit(0)

    name = " ".join(sys.argv[1:])
    result = get_club_url(name)
    if result:
        url, cid = result
        print(f"{name} -> ID={cid}  URL={url}")
    else:
        print(f"Club '{name}' not found in database.")