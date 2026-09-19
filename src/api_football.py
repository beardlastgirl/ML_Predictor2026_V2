import os
import requests
from typing import Optional
try:
    from src.utils import log_info, log_error
except ImportError:
    def log_info(m): print(f"[INFO] {m}")
    def log_error(m): print(f"[ERROR] {m}")


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