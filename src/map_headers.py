"""
Header normalization & mapping utility

Provides:
- normalize_header(header: str) -> str
- map_header(header: str, provider: Optional[str] = None, overrides: Optional[dict] = None) -> dict
  returns provenance record:
    {
      "original": <original header>,
      "normalized": <normalized header>,
      "canonical": <canonical key or None>,
      "mapping_source": "provider"|"general"|"fuzzy"|"override"|None,
      "confidence": float (0.0-1.0),
      "notes": str
    }
- map_headers(headers: List[str], provider: Optional[str] = None, overrides: Optional[dict] = None)
  returns (mapped_dict, log_list)
    - mapped_dict: { canonical_key: [original_header, ...] } (note: if unmapped, canonical_key is None under 'UNMAPPED')
    - log_list: list of provenance records

By default uses an embedded general mapping and small football-data / fbref overrides.
You can pass your own overrides dict to extend/replace mappings.

Author: Assistant (2026)
"""

from typing import Optional, Dict, List, Tuple
import re
import math

# Optional dependency: Levenshtein for faster ratio. If not present, fallback to pure python.
try:
    import Levenshtein  # type: ignore
    def _ratio(a: str, b: str) -> float:
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        return Levenshtein.ratio(a, b)
except Exception:
    # Pure-Python fallback (simple Levenshtein ratio)
    def _levenshtein(s1: str, s2: str) -> int:
        if s1 == s2:
            return 0
        len1, len2 = len(s1), len(s2)
        if len1 == 0:
            return len2
        if len2 == 0:
            return len1
        prev_row = list(range(len2 + 1))
        for i, c1 in enumerate(s1, start=1):
            cur_row = [i] + [0] * len2
            for j, c2 in enumerate(s2, start=1):
                insert_cost = cur_row[j - 1] + 1
                delete_cost = prev_row[j] + 1
                replace_cost = prev_row[j - 1] + (0 if c1 == c2 else 1)
                cur_row[j] = min(insert_cost, delete_cost, replace_cost)
            prev_row = cur_row
        return prev_row[-1]

    def _ratio(a: str, b: str) -> float:
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        dist = _levenshtein(a, b)
        # ratio = 1 - (distance / max_len)
        max_len = max(len(a), len(b))
        return 1.0 - (dist / max_len)

# -------------------------
# General mapping (normalized form -> canonical key)
# Compact selection from the Markdown mapping produced earlier.
# All keys here should be normalized the same way used in normalize_header().
# -------------------------
_GENERAL_MAP: Dict[str, str] = {
    # standings & basic
    "rk": "Rk",
    "pos": "Rk",
    "position": "Rk",
    "rank": "Rk",
    "mp": "MP",
    "pld": "MP",
    "played": "MP",
    "matches": "MP",
    "matchesplayed": "MP",
    "gp": "MP",
    "w": "W",
    "won": "W",
    "wins": "W",
    "d": "D",
    "draw": "D",
    "draws": "D",
    "t": "D",
    "l": "L",
    "loss": "L",
    "losses": "L",
    "gf": "GF",
    "f": "GF",
    "goalsfor": "GF",
    "for": "GF",
    "ga": "GA",
    "a": "GA",
    "goalsagainst": "GA",
    "against": "GA",
    "gd": "GD",
    "goaldiff": "GD",
    "goaldifference": "GD",
    "gdiff": "GD",
    "plusminus": "GD",
    "pts": "Pts",
    "points": "Pts",
    "p": "Pts",
    "pt": "Pts",
    "ptspermatch": "Pts/MP",
    "pointspermatch": "Pts/MP",
    "ppm": "Pts/MP",
    "last5": "Last5",
    "last5matches": "Last5",
    "form": "Last5",
    "attendance": "Attendance",
    "att": "Attendance",
    # players & minutes
    "starts": "Starts",
    "gs": "Starts",
    "min": "Min",
    "minutes": "Min",
    "mins": "Min",
    "timeplayed": "Min",
    "90s": "90s",
    "90splayed": "90s",
    "90m": "90s",
    # basic performance
    "gls": "Gls",
    "goals": "Gls",
    "g": "Gls",
    "scored": "Gls",
    "ast": "Ast",
    "assists": "Ast",
    "gplusa": "GplusA",
    "gplus_a": "GplusA",
    "goalsplusassists": "GplusA",
    "gminuspk": "GminusPK",
    "nonpkgoals": "GminusPK",
    "pk": "PK",
    "pen": "PK",
    "pens": "PK",
    "penalties": "PK",
    "pkatt": "PKatt",
    "penatt": "PKatt",
    "penaltyattempts": "PKatt",
    "crdy": "CrdY",
    "yellow": "CrdY",
    "yc": "CrdY",
    "crdr": "CrdR",
    "red": "CrdR",
    "rc": "CrdR",
    # xG family
    "xg": "xG",
    "expg": "xG",
    "xg90": "xG_90",
    "xg/90": "xG_90",
    "xga": "xGA",
    "xgallowed": "xGA",
    "xgd": "xGD",
    "xgdiff": "xGD",
    "npxg": "npxG",
    "nonpenxg": "npxG",
    "npxg90": "npxG_90",
    "xa": "xAG",
    "xag": "xAG",
    "expectedassists": "xAG",
    "npxgxag": "npxG_xAG",
    # progression
    "prgp": "PrgP",
    "progp": "PrgP",
    "prgc": "PrgC",
    "progc": "PrgC",
    # shots & finishing
    "shots": "Shots",
    "sh": "Shots",
    "sot": "SoT",
    "shotsontarget": "SoT",
    "sota": "SoTA",
    "shotsontargetagainst": "SoTA",
    "shotconv": "ShotConv",
    "shot%": "ShotConv",
    "goalspershot": "ShotConv",
    "psxg": "PSxG",
    "postshotxg": "PSxG",
    # passing & creativity
    "passes": "Passes",
    "pass": "Passes",
    "passacc": "PassAcc",
    "passpct": "PassAcc",
    "passcompletionpct": "PassAcc",
    "keypasses": "KeyPasses",
    "kp": "KeyPasses",
    "keypass": "KeyPasses",
    "passinto3rd": "PassInto3rd",
    "passintobox": "PassIntoBox",
    "ppda": "PPDA",
    # creating actions
    "sca": "SCA",
    "gca": "GCA",
    # defensive
    "tackles": "Tackles",
    "tkl": "Tackles",
    "interceptions": "Interceptions",
    "int": "Interceptions",
    "blocks": "Blocks",
    "blk": "Blocks",
    "clearances": "Clearances",
    "clr": "Clearances",
    "aerialwon": "AerialWon",
    "recoveries": "Recoveries",
    "recov": "Recoveries",
    "errorstoshot": "ErrorsToShot",
    # goalkeeper
    "goalkeeper": "Goalkeeper",
    "gk": "Goalkeeper",
    "cs": "CS",
    "cleansheets": "CS",
    "cspct": "CSpct",
    "savepct": "SavePct",
    "save%": "SavePct",
    "pksv": "PKsv",
    "pka": "PKA",
    "pkm": "PKm",
    "distacc": "DistAcc",
    "sweeperactions": "SweeperActions",
    # minutes/efficiency
    "minpergoal": "MinutesPerGoal",
    "mpg": "MinutesPerGoal",
    "minperassist": "MinutesPerAssist",
    # expected points & meta
    "xp": "xP",
    "expectedpoints": "xP",
    "rankpercentile": "RankPercentile",
    "rankpct": "RankPercentile",
}

# -------------------------
# Provider-specific overrides (normalized form -> canonical)
# Add/extend keys here for football-data, fbref, sofascore, etc.
# -------------------------
_PROVIDER_MAPS: Dict[str, Dict[str, str]] = {
    "football-data": {
        # match-level common columns
        "date": "Date",
        "time": "Time",
        "hometeam": "HomeTeam",
        "awayteam": "AwayTeam",
        "home": "HomeTeam",
        "away": "AwayTeam",
        "fthg": "Home_GF",
        "hg": "Home_GF",
        "ftag": "Away_GF",
        "ag": "Away_GF",
        "ftr": "FullTimeResult",
        "res": "FullTimeResult",
        "hthg": "HT_Home_GF",
        "htag": "HT_Away_GF",
        "htr": "HalfTimeResult",
        # common odds prefixes (B365 -> Odds_b365_H/D/A)
        "b365h": "Odds_b365_H",
        "b365d": "Odds_b365_D",
        "b365a": "Odds_b365_A",
    },
    "fbref": {
        # fbref-specific naming
        "xg": "xG",
        "npxg": "npxG",
        "xg90": "xG_90",
        "npxg90": "npxG_90",
        "xa": "xAG",
        "xag": "xAG",
        "sca": "SCA",
        "gca": "GCA",
    },
    "sofascore": {
        "rating": "Rating",
        "player_rating": "Rating",
        "minutes": "Min",
        "min": "Min",
        "subs_on": "SubsOn",
    },
}

# Common bookmaker prefixes (normalized) -> canonical odds group prefix
_BOOKIE_PREFIXES = {
    "b365": "b365",
    "ps": "pinnacle",
    "bw": "betandwin",
    "iw": "interwetten",
    "wh": "williamhill",
    "vc": "vcbet",
    "gb": "gamebookers",
    "bs": "bluesquare",
    "lb": "ladbrokes",
    "sj": "stanjames",
    "max": "max",
    "avg": "avg",
    "bfe": "betfair",
}

# -------------------------
# Utility functions
# -------------------------
def normalize_header(header: str) -> str:
    """
    Normalize a header string for lookup:
    - lowercase
    - replace % -> pct, + -> plus, - -> minus (to preserve meaning)
    - remove any non-alphanumeric characters
    """
    if header is None:
        return ""
    s = header.lower()
    s = s.replace("%", "pct").replace("+", "plus").replace("-", "minus")
    # allow alphanumeric only
    s = re.sub(r"[^a-z0-9]", "", s)
    return s

def _detect_provider_from_filename_or_header(headers: List[str]) -> Optional[str]:
    """
    Simple heuristic to guess provider if not given.
    Checks for headers typical of football-data or fbref.
    Returns provider key or None.
    """
    set_norm = {normalize_header(h) for h in headers}
    # HG/AG/Res or FTHG/FTAG/FTR or B365H are strong signals for football-data
    if any(k in set_norm for k in ["fthg", "ftag", "b365h", "hg", "ag", "res"]):
        return "football-data"
    if "xg" in set_norm and "npxg" in set_norm:
        return "fbref"
    if "rating" in set_norm and "minutes" in set_norm:
        return "sofascore"
    return None

def _try_direct_lookup(norm: str, provider: Optional[str], overrides: Optional[Dict[str, str]]) -> Tuple[Optional[str], Optional[str]]:
    """
    Try provider override, then user overrides, then general map.
    Returns (canonical, source) where source ∈ {"provider","override","general"} or (None,None).
    """
    # 1) Provider specific mapping
    if provider:
        pmap = _PROVIDER_MAPS.get(provider, {})
        if norm in pmap:
            return pmap[norm], "provider"
            
        # pattern for bookmaker odds: e.g., b365h, b365d, b365a or similar
        # Only trigger if prefix is a known bookie to avoid false positives with metrics like xA, SoTA
        m = re.match(r"([a-z0-9]+)(h|d|a)$", norm)
        if m:
            prefix, outcome = m.group(1), m.group(2)
            if prefix in _BOOKIE_PREFIXES:
                bookie = _BOOKIE_PREFIXES[prefix]
                outcome_map = {"h": "H", "d": "D", "a": "A"}
                return f"Odds_{bookie}_{outcome_map[outcome]}", "provider-pattern"
                
    # 2) User overrides
    if overrides:
        if norm in overrides:
            return overrides[norm], "override"
            
    # 3) General mapping
    if norm in _GENERAL_MAP:
        return _GENERAL_MAP[norm], "general"
        
    return None, None

def _fuzzy_lookup(norm: str, max_candidates: int = 5) -> Tuple[Optional[str], float]:
    """
    Attempt fuzzy matching against general map keys and provider maps.
    Returns best (canonical, score) or (None, 0.0)
    Score is the similarity ratio (0.0-1.0).
    Conservative threshold recommended by caller.
    """
    best_key = None
    best_score = 0.0
    # search general map
    for k in _GENERAL_MAP.keys():
        score = _ratio(norm, k)
        if score > best_score:
            best_score = score
            best_key = k
    # search provider maps too (flattened)
    for provider, pmap in _PROVIDER_MAPS.items():
        for k in pmap.keys():
            score = _ratio(norm, k)
            if score > best_score:
                best_score = score
                best_key = k
    if best_key and best_score > 0.79:  # conservative threshold
        # determine canonical from whichever map contains best_key
        if best_key in _GENERAL_MAP:
            return _GENERAL_MAP[best_key], best_score
        for provider, pmap in _PROVIDER_MAPS.items():
            if best_key in pmap:
                return pmap[best_key], best_score
    return None, 0.0

# -------------------------
# Public mapping functions
# -------------------------
def map_header(header: str, provider: Optional[str] = None, overrides: Optional[Dict[str, str]] = None) -> Dict:
    """
    Map a single header to a canonical key and return a provenance record.

    Parameters:
      - header: raw header string from CSV/JSON/etc.
      - provider: optional provider key (e.g., 'football-data', 'fbref', 'sofascore')
      - overrides: optional dict of normalized_header -> canonical to override/extend mappings

    Returns provenance record:
      {
        "original": <original header>,
        "normalized": <normalized>,
        "canonical": <canonical key or None>,
        "mapping_source": one of {"provider","provider-pattern","override","general","fuzzy", None},
        "confidence": float,  # 1.0 exact, 0.8+ fuzzy, 0.0 unmapped
        "notes": str
      }
    """
    orig = header
    norm = normalize_header(header or "")
    record = {
        "original": orig,
        "normalized": norm,
        "canonical": None,
        "mapping_source": None,
        "confidence": 0.0,
        "notes": "",
    }
    if norm == "":
        record["notes"] = "Empty header after normalization"
        return record

    # 1) try direct lookup (provider-aware)
    canonical, source = _try_direct_lookup(norm, provider, overrides)
    if canonical:
        record["canonical"] = canonical
        record["mapping_source"] = source
        record["confidence"] = 1.0
        return record

    # 2) try general map without provider
    if not provider:
        canonical, source = _try_direct_lookup(norm, None, overrides)
        if canonical:
            record["canonical"] = canonical
            record["mapping_source"] = source
            record["confidence"] = 1.0
            return record

    # 3) fuzzy fallback
    canonical, score = _fuzzy_lookup(norm)
    if canonical:
        record["canonical"] = canonical
        record["mapping_source"] = "fuzzy"
        record["confidence"] = round(float(score), 3)
        record["notes"] = "Fuzzy match; verify correctness"
        return record

    # 4) attempt to detect and parse common football-data bookmaker or match patterns generically
    # e.g., b365h -> Odds_b365_H or fthg -> Home_GF
    # try a few heuristics:
    # bookmaker-like: prefix+H/D/A
    m = re.match(r"([a-z0-9]+)(h|d|a)$", norm)
    if m:
        prefix, outcome = m.group(1), m.group(2)
        bookie = _BOOKIE_PREFIXES.get(prefix, prefix)
        outcome_map = {"h": "H", "d": "D", "a": "A"}
        record["canonical"] = f"Odds_{bookie}_{outcome_map[outcome]}"
        record["mapping_source"] = "heuristic-odds"
        record["confidence"] = 0.8
        record["notes"] = "Heuristic bookmaker mapping"
        return record

    # unmatched
    record["notes"] = "Unmapped header; consider adding to overrides"
    return record

def map_headers(headers: List[str], provider: Optional[str] = None, overrides: Optional[Dict[str, str]] = None) -> Tuple[Dict[str, List[str]], List[Dict]]:
    """
    Map a list of headers. Returns:
      - mapped_dict: canonical_key -> list of original headers that mapped to it
          Note: unmapped headers grouped under key 'UNMAPPED'
      - log_list: list of provenance records (one per input header, order preserved)
    """
    if provider is None:
        # try heuristics to detect provider from headers
        guessed = _detect_provider_from_filename_or_header(headers)
        provider = guessed

    mapped: Dict[str, List[str]] = {}
    log: List[Dict] = []
    for h in headers:
        rec = map_header(h, provider=provider, overrides=overrides)
        log.append(rec)
        can = rec["canonical"] if rec["canonical"] else "UNMAPPED"
        mapped.setdefault(can, []).append(rec["original"])
    return mapped, log

# -------------------------
# Example usage & quick test
# -------------------------
if __name__ == "__main__":
    sample_headers = [
        "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
        "B365H", "B365D", "B365A", "xG", "npxG", "xG/90", "xA",
        "G", "A", "Min", "SoT", "SoTA", "Pass%", "SCA", "GCA",
        "Rating", "subs_on", "unknown_col"
    ]
    mapped, log = map_headers(sample_headers)
    print("Detected provider (heuristic):", _detect_provider_from_filename_or_header(sample_headers))
    print("\nMapped keys summary:")
    for k, originals in mapped.items():
        print(f"  {k}: {originals}")
    print("\nProvenance log:")
    for rec in log:
        print(rec)
