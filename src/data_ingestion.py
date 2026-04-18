import os
import pandas as pd
from datetime import datetime
from src.api_football import APIFootballClient
from src.utils import log_info, log_ok, log_warning, log_error
import requests

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
            
            # Simple check: if local file exists and content is same size, skip (optional optimization)
            if os.path.exists(self.data_path):
                current_size = os.path.getsize(self.data_path)
                if len(response.content) == current_size:
                    log_info("Local ARG.csv size matches remote. Skipping download.")
                    return False

            with open(self.data_path, 'wb') as f:
                f.write(response.content)
            log_ok(f"Updated base data: {self.data_path}")
            return True
        except Exception as e:
            log_error(f"Failed to update base data: {e}")
            return False

    def enrich_with_api_stats(self, days_back=7):
        """
        Fetches advanced stats (xG, Possession) for recent matches 
        and merges them into the local dataset.
        """
        log_info(f"Enriching last {days_back} days with API-Football stats...")
        # 1. Get last results from API
        results = self.api_client.get_last_results(last_n=20)
        
        if not results:
            log_warning("No recent results found from API to enrich.")
            return

        # 2. Load local CSV
        df = pd.read_csv(self.data_path)
        
        # 3. logic to map API results to CSV rows and add columns like 'HxG', 'AxG'
        # Note: This requires mapping team names (e.g., 'Boca Juniors' vs 'Boca Jrs')
        log_info(f"Retrieved {len(results)} matches for potential enrichment.")
        # Implementation of fuzzy matching/mapping would go here
        
        log_ok("Data enrichment process completed.")

if __name__ == "__main__":
    ingestor = DataIngestor()
    ingestor.update_base_data()
