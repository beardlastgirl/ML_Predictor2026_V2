"""Canonical header mapping for multi-source scraped/loaded data.

Maps arbitrary source-specific column headers (FBref, FootyStats, Sofascore,
football-data.co.uk, TyC) to canonical internal names.
"""

from src.normalization import canonicalize_name

# canonicalize_name(raw_header) -> canonical internal column name
CANONICAL_HEADER_MAP = {
    "DATE": "Date", "FECHA": "Date",
    "HOME": "Home", "HOMETEAM": "HomeTeam", "HOME TEAM": "HomeTeam", "LOCAL": "HomeTeam",
    "AWAY": "Away", "AWAYTEAM": "AwayTeam", "AWAY TEAM": "AwayTeam", "VISITANTE": "AwayTeam",
    "RES": "Res", "RESULT": "Res", "FTR": "Res", "FULLTIMERESULT": "FullTimeResult",
    "HG": "HG", "FTHG": "HG", "HOME GOALS": "HG",
    "AG": "AG", "FTAG": "AG", "AWAY GOALS": "AG",
    "B365CH": "B365CH", "B365CD": "B365CD", "B365CA": "B365CA",
    "XG": "xG", "XG HOME": "xG_home", "XG AWAY": "xG_away",
    "PPG": "PPG", "POSITION": "Position", "POS": "Position",
    "POINTS": "Points", "PTS": "Points",
}

# Provider-specific overrides, keyed by canonicalized raw header, checked
# before the generic map above. Populate as source-specific quirks surface.
PROVIDER_OVERRIDES = {
    "fbref": {},
    "footystats": {},
    "sofascore": {},
    "tyc": {},
}


def map_headers(headers, provider=None):
    """Map a list of raw column headers to canonical names.

    Args:
        headers: list of raw header strings from a scraped/loaded source.
        provider: optional source identifier ("fbref", "footystats",
            "sofascore", "tyc") to apply provider-specific overrides before
            the generic lookup.

    Returns:
        (mapped, log):
            mapped: {original_header: canonical_name_or_None}
            log: list of {"original", "canonical", "provider"} records,
                 in the same order as `headers`. "canonical" is None for
                 headers with no known mapping.
    """
    overrides = PROVIDER_OVERRIDES.get(provider, {}) if provider else {}

    mapped = {}
    log = []
    for h in headers:
        key = canonicalize_name(h)
        canonical = overrides.get(key) or CANONICAL_HEADER_MAP.get(key)
        mapped[h] = canonical
        log.append({"original": h, "canonical": canonical, "provider": provider})

    return mapped, log
