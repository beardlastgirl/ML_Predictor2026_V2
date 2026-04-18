import os
import requests
import json
from dotenv import load_dotenv
from src.utils import log_info, log_error, log_ok

def test_api_connection():
    """Diagnostic script to verify API-Football connection."""
    # Try to load .env with override to ensure it takes precedence
    load_dotenv(override=True)
    
    api_key = os.environ.get("API_FOOTBALL_KEY")
    
    if not api_key:
        log_error("API_FOOTBALL_KEY not found in environment or .env file.")
        return

    # Diagnostic info
    key_len = len(api_key)
    log_info(f"Key found: {api_key[:5]}...{api_key[-5:]} (Length: {key_len})")

    # Determine Provider
    # RapidAPI keys are usually 50 chars, Direct keys are 32 chars.
    is_direct = key_len == 32 or "v3.football.api-sports.io" in api_key
    
    if is_direct:
        log_info("Detected potential Direct API-Sports key. Testing Direct endpoint...")
        url = "https://v3.football.api-sports.io/timezone"
        headers = {"x-apisports-key": api_key}
    else:
        log_info("Detected potential RapidAPI key. Testing RapidAPI endpoint...")
        url = "https://api-football-v1.p.rapidapi.com/v3/timezone"
        headers = {
            "x-rapidapi-host": "api-football-v1.p.rapidapi.com",
            "x-rapidapi-key": api_key
        }

    try:
        log_info(f"Connecting to: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("errors"):
                log_error(f"API Error: {data['errors']}")
                if "plan" in str(data['errors']).lower():
                    log_error("Check if you have subscribed to the API (even the free tier).")
            else:
                log_ok("Connection Successful!")
                log_info(f"Remaining requests today: {response.headers.get('x-ratelimit-requests-remaining', 'unknown')}")
        else:
            log_error(f"HTTP {response.status_code}: {response.text}")
            
    except Exception as e:
        log_error(f"Request failed: {str(e)}")

if __name__ == "__main__":
    test_api_connection()
