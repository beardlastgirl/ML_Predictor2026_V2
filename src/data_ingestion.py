"""
Data ingestion: auto-download ARG.csv and enrich with API-Football xG/possession stats.
"""

import os
import re
import difflib
import pandas as pd
from datetime import datetime, timedelta
from src.api_football import APIFootballClient
from src.utils import log_info, log_ok, log_warning, log_error
import requests


# ---------------------------------------------------------------------------
# Curated API-Football → canonical team name map
# Covers known mismatches that fuzzy matching gets wrong.
# Add new entries here when a team name changes or a new team is promoted.
# NOTE: This is separate from data_processing.py's INTERNAL_MAPPING because:
# - This maps API-Football names → canonical (ARG.csv) names
# - That maps internal variations (nicknames, abbreviations) → canonical
# Both serve different purposes and should NOT be merged.
# ---------------------------------------------------------------------------
_API_NAME_MAP_RAW = {
    "Argentinos JRS":              "ARGENTINOS JUNIORS",
    "Atletico Tucuman":            "ATL TUCUMAN",
    "Belgrano Cordoba":            "BELGRANO",
    "Central Cordoba de Santiago": "CENTRAL CORDOBA",
    "Deportivo Riestra":           "DEP RIESTRA",
    "Estudiantes L.P.":            "ESTUDIANTES LP",
    "Gimnasia L.P.":               "GIMNASIA LP",
    "Independ. Rivadavia":         "IND RIVADAVIA",
    "Instituto Cordoba":           "INSTITUTO",
    "Union Santa Fe":              "UNION DE SANTA FE",
}


def _normalize_for_match(name: str) -> str:
    """Normalize a team name for fuzzy comparison. Matches _canonicalize_name in data_processing.py."""
    if name is None:
        return ""
    try:
        if pd.isna(name):
            return ""
    except (TypeError, ValueError):
        pass
    s = str(name).upper().strip()
    s = s.replace(".", " ").replace("-", " ").replace("–", " ").replace("—", " ")
    # Remove accents
    mapping = str.maketrans({
        "Á": "A", "É": "E", "Í": "I", "Ó": "O", "Ú": "U", "Ü": "U", "Ñ": "N",
        "á": "A", "é": "E", "í": "I", "ó": "O", "ú": "U", "ü": "U", "ñ": "N"
    })
    s = s.translate(mapping)
    s = re.sub(r"[^A-Z0-9\s]+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def build_api_to_canonical_map(canonical_teams: list) -> dict:
    """
    Build a mapping from API-Football team names to canonical ARG.csv names.

    Uses curated overrides first, then exact normalized match, then fuzzy
    match with a high cutoff (0.75) as a last resort.

    Args:
        canonical_teams: List of canonical team names from ARG.csv

    Returns:
        Dict mapping API name -> canonical name
    """
    canonical_norm = {_normalize_for_match(c): c for c in canonical_teams}
    result = {}

    # Start with curated overrides (highest confidence)
    for api_name, canonical in _API_NAME_MAP_RAW.items():
        result[api_name] = canonical

    # For any API name not in curated map, try exact then fuzzy
    # (This handles new teams added mid-season)
    # We don't know all API names upfront, so this is called per-fixture
    return result


def _resolve_api_name(api_name: str, curated_map: dict, canonical_norm: dict) -> str:
    """Resolve a single API team name to its canonical equivalent."""
    # 1. Curated override
    if api_name in curated_map:
        return curated_map[api_name]

    # 2. Exact normalized match
    norm = _normalize_for_match(api_name)
    if norm in canonical_norm:
        return canonical_norm[norm]

    # 3. Fuzzy match (conservative cutoff to avoid wrong matches)
    candidates = list(canonical_norm.keys())
    matches = difflib.get_close_matches(norm, candidates, n=1, cutoff=0.75)
    if matches:
        return canonical_norm[matches[0]]

    return None  # Unresolved


class DataIngestor:
    """Consolidates data from football-data.co.uk and API-Football."""

    CSV_URL = "https://www.football-data.co.uk/new/ARG.csv"

    def __init__(self, data_path="data/ARG.csv"):
        self.data_path = data_path
        self.api_client = APIFootballClient()

    def update_base_data(self) -> bool:
        """Downloads the latest ARG.csv from football-data.co.uk if newer."""
        try:
            log_info(f"Checking for updates at {self.CSV_URL}...")
            response = requests.get(self.CSV_URL, timeout=30)
            response.raise_for_status()

            if os.path.exists(self.data_path):
                current_size = os.path.getsize(self.data_path)
                if len(response.content) == current_size:
                    log_info("Local ARG.csv size matches remote. Skipping download.")
                    return False

            with open(self.data_path, "wb") as f:
                f.write(response.content)
            log_ok(f"Updated base data: {self.data_path}")
            return True
        except Exception as e:
            log_error(f"Failed to update base data: {e}")
            return False

    def enrich_with_api_stats(self, days_back: int = 14) -> int:
        """
        Fetch xG and possession stats from API-Football for recent matches
        and merge them into ARG.csv as HxG, AxG, HPoss, APoss columns.

        Only processes matches within the last `days_back` days that are
        already in ARG.csv but missing xG data.

        Args:
            days_back: How many days back to look for matches to enrich

        Returns:
            Number of rows enriched (0 if nothing updated or API unavailable)

        Limitations:
            - Free API plan only covers seasons up to 2024.
            - API quota: 100 requests/day. Each fixture stats call = 1 request.
            - Enrichment is best-effort; pipeline runs fine without it.
        """
        if not self.api_client.api_key:
            log_warning("enrich_with_api_stats: no API key, skipping")
            return 0

        # Load local CSV
        try:
            df = pd.read_csv(self.data_path)
        except Exception as e:
            log_error(f"enrich_with_api_stats: cannot read {self.data_path}: {e}")
            return 0

        # Ensure xG columns exist
        for col in ["HxG", "AxG", "HPoss", "APoss"]:
            if col not in df.columns:
                df[col] = None

        # Parse dates
        df["Date"] = pd.to_datetime(df.get("Date", df.get("date", None)),
                                    dayfirst=True, errors="coerce")

        cutoff = pd.Timestamp.now() - timedelta(days=days_back)
        recent_missing = df[
            (df["Date"] >= cutoff) &
            (df["HxG"].isna() | (df["HxG"] == ""))
        ]

        if recent_missing.empty:
            log_info("enrich_with_api_stats: no recent rows missing xG data")
            return 0

        log_info(f"enrich_with_api_stats: {len(recent_missing)} rows to enrich")

        # Determine season from dates
        seasons = recent_missing["Date"].dt.year.unique().tolist()

        # Build canonical team list for name resolution
        home_col = "HomeTeam" if "HomeTeam" in df.columns else "Home"
        away_col = "AwayTeam" if "AwayTeam" in df.columns else "Away"
        canonical_teams = sorted(
            set(df[home_col].dropna().tolist() + df[away_col].dropna().tolist())
        )
        canonical_norm = {_normalize_for_match(c): c for c in canonical_teams}
        curated_map = build_api_to_canonical_map(canonical_teams)

        # Fetch fixtures from API for relevant seasons
        api_fixtures = []
        for season in seasons:
            if season > 2024:
                log_warning(f"enrich_with_api_stats: season {season} not available on free plan (max 2024)")
                continue
            from_date = (pd.Timestamp.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
            to_date = pd.Timestamp.now().strftime("%Y-%m-%d")
            try:
                r = requests.get(
                    f"{self.api_client.BASE_URL}/fixtures",
                    headers=self.api_client.headers,
                    params={"league": self.api_client.ARG_LEAGUE_ID,
                            "season": season,
                            "from": from_date,
                            "to": to_date},
                    timeout=30,
                )
                r.raise_for_status()
                api_fixtures.extend(r.json().get("response", []))
            except Exception as e:
                log_error(f"enrich_with_api_stats: API fetch failed for season {season}: {e}")

        if not api_fixtures:
            log_warning("enrich_with_api_stats: no API fixtures returned")
            return 0

        log_info(f"enrich_with_api_stats: {len(api_fixtures)} API fixtures to process")

        # Pre-compute normalized columns once before loop (efficiency)
        home_norm_all = df[home_col].apply(_normalize_for_match)
        away_norm_all = df[away_col].apply(_normalize_for_match)

        enriched = 0
        api_requests_used = 0
        MAX_REQUESTS = 80  # Leave buffer from 100/day quota

        for fix in api_fixtures:
            if api_requests_used >= MAX_REQUESTS:
                log_warning(f"enrich_with_api_stats: API quota limit reached ({MAX_REQUESTS} requests), stopping")
                break

            fixture_info = fix.get("fixture", {})
            teams = fix.get("teams", {})
            goals = fix.get("goals", {})

            api_home = teams.get("home", {}).get("name", "")
            api_away = teams.get("away", {}).get("name", "")
            api_date = pd.to_datetime(fixture_info.get("date", "")[:10], errors="coerce")
            fixture_id = fixture_info.get("id")

            if not api_home or not api_away or pd.isna(api_date) or not fixture_id:
                continue

            # Resolve API names to canonical
            canonical_home = _resolve_api_name(api_home, curated_map, canonical_norm)
            canonical_away = _resolve_api_name(api_away, curated_map, canonical_norm)

            if not canonical_home or not canonical_away:
                log_warning(f"enrich_with_api_stats: cannot resolve '{api_home}' or '{api_away}', skipping")
                continue

            # Find matching row in ARG.csv (match on date ±1 day and team names)
            # Normalize both sides for comparison since raw ARG.csv names differ from canonical
            # NOTE: home_norm/away_norm pre-computed once before loop (efficiency)
            date_mask = (df["Date"] - api_date).abs() <= timedelta(days=1)
            home_mask = home_norm_all == _normalize_for_match(canonical_home)
            away_mask = away_norm_all == _normalize_for_match(canonical_away)
            row_mask = date_mask & home_mask & away_mask

            if not row_mask.any():
                continue  # Match not in ARG.csv yet (results lag)

            # Skip if already enriched
            if df.loc[row_mask, "HxG"].notna().all():
                continue

            # Fetch fixture stats (1 API request)
            try:
                import time
                time.sleep(0.5)  # Free plan rate limit: ~2 req/sec
                stats_r = requests.get(
                    f"{self.api_client.BASE_URL}/fixtures/statistics",
                    headers=self.api_client.headers,
                    params={"fixture": fixture_id},
                    timeout=30,
                )
                stats_r.raise_for_status()
                stats_data = stats_r.json().get("response", [])
                api_requests_used += 1
            except Exception as e:
                log_error(f"enrich_with_api_stats: stats fetch failed for fixture {fixture_id}: {e}")
                continue

            # Parse stats for home and away
            xg_home = xg_away = poss_home = poss_away = None
            for team_stats in stats_data:
                team_name = team_stats.get("team", {}).get("name", "")
                stats = {s["type"]: s["value"] for s in team_stats.get("statistics", [])}

                xg_val = stats.get("expected_goals") or stats.get("Expected Goals")
                poss_val = stats.get("Ball Possession", "")

                # Parse possession percentage string ("45%" → 45.0)
                poss_float = None
                if poss_val and isinstance(poss_val, str):
                    try:
                        poss_float = float(poss_val.replace("%", "").strip())
                    except ValueError:
                        pass

                # Determine if this is home or away team
                resolved = _resolve_api_name(team_name, curated_map, canonical_norm)
                if resolved == canonical_home:
                    xg_home = xg_val
                    poss_home = poss_float
                elif resolved == canonical_away:
                    xg_away = xg_val
                    poss_away = poss_float

            if xg_home is None and xg_away is None:
                continue

            # Write to DataFrame
            df.loc[row_mask, "HxG"] = xg_home
            df.loc[row_mask, "AxG"] = xg_away
            df.loc[row_mask, "HPoss"] = poss_home
            df.loc[row_mask, "APoss"] = poss_away
            enriched += 1

        if enriched > 0:
            df.to_csv(self.data_path, index=False)
            log_ok(f"enrich_with_api_stats: enriched {enriched} rows, used {api_requests_used} API requests")
        else:
            log_info(f"enrich_with_api_stats: 0 rows enriched (used {api_requests_used} API requests)")

        return enriched


if __name__ == "__main__":
    ingestor = DataIngestor()
    ingestor.update_base_data()
    ingestor.enrich_with_api_stats(days_back=30)
