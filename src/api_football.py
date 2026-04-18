import os
import requests
from typing import Dict, List, Optional
try:
    from src.utils import log_info, log_error, log_ok
except ImportError:
    def log_info(m): print(f"[INFO] {m}")
    def log_error(m): print(f"[ERROR] {m}")
    def log_ok(m): print(f"[OK] {m}")

class APIFootballClient:
    """
    Client for API-Football (Direct API-Sports version).
    Endpoint: https://v3.football.api-sports.io
    """
    
    BASE_URL = "https://v3.football.api-sports.io"
    ARG_LEAGUE_ID = 128  # Liga Profesional Argentina
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("API_FOOTBALL_KEY")
        if not self.api_key:
            log_error("API_FOOTBALL_KEY not found in environment variables.")
        
        self.headers = {
            "x-apisports-key": self.api_key
        }

    def get_standings(self, season: int = 2024) -> List[Dict]:
        """Fetch current league standings."""
        url = f"{self.BASE_URL}/standings"
        params = {"league": self.ARG_LEAGUE_ID, "season": season}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            resp = data.get("response", [])
            return resp[0].get("league", {}).get("standings", [[]])[0] if resp else []
        except Exception as e:
            log_error(f"Failed to fetch standings: {e}")
            return []

    def get_fixtures(self, season: int = 2024, next_n: int = 10) -> List[Dict]:
        """Fetch upcoming fixtures."""
        url = f"{self.BASE_URL}/fixtures"
        params = {"league": self.ARG_LEAGUE_ID, "season": season, "next": next_n}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("response", [])
        except Exception as e:
            log_error(f"Failed to fetch fixtures: {e}")
            return []

    def get_fixture_stats(self, fixture_id: int) -> List[Dict]:
        """
        Fetch detailed stats for a specific match (xG, Shots, Possession).
        Crucial for enriching ARG.csv.
        """
        url = f"{self.BASE_URL}/fixtures/statistics"
        params = {"fixture": fixture_id}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("response", [])
        except Exception as e:
            log_error(f"Failed to fetch stats for fixture {fixture_id}: {e}")
            return []

    def get_last_results(self, last_n: int = 20) -> List[Dict]:
        """Fetch the last N results to update historical data."""
        url = f"{self.BASE_URL}/fixtures"
        params = {"league": self.ARG_LEAGUE_ID, "last": last_n}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("response", [])
        except Exception as e:
            log_error(f"Failed to fetch last results: {e}")
            return []
