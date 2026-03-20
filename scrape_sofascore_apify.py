"""
scrape_sofascore_apify.py - Apify-based Sofascore Scraper

Uses Apify's Sofascore scraper to fetch tournament data.
This is a more reliable alternative to direct web scraping.

Usage:
    python scrape_sofascore_apify.py

Requirements:
    pip install apify-client
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

try:
    from apify_client import ApifyClient
except ImportError:
    print("[ERROR] apify-client not installed.")
    print("         Run: pip install apify-client")
    sys.exit(1)


# Configuration
DATASET_ID = "FGVhnJN8KMHeYbQYQ"
STORE_ID = "aI50qNLcEHTtQ5Fu1"
API_TOKEN = os.getenv("APIFY_API_TOKEN")


def normalize_team_name(name):
    """Normalize team name for consistency with other data sources."""
    if not name:
        return ""

    # Remove accents
    name = name.replace("á", "a").replace("é", "e").replace("í", "i")
    name = name.replace("ó", "o").replace("ú", "u").replace("ñ", "n")

    # Common mappings
    mappings = {
        "Boca Juniors": "BOCA JUNIORS",
        "River Plate": "RIVER PLATE",
        "Estudiantes de La Plata": "ESTUDIANTES LP",
        "Independiente Rivadavia": "INDEPENDIENTE RIVADAVIA",
        "Club Atlético Independiente": "INDEPENDIENTE",
        "San Lorenzo de Almagro": "SAN LORENZO",
        "Vélez Sarsfield": "VELEZ SARSFIELD",
        "Rosario Central": "ROSARIO CENTRAL",
        "Talleres de Córdoba": "TALLERES CORDOBA",
        "Banfield": "BANFIELD",
        "Lanús": "LANUS",
        "Argentinos Juniors": "ARGENTINOS JUNIORS",
        "Defensa y Justicia": "DEFENSA Y JUSTICIA",
        "Huracán": "HURACAN",
        "Tigre": "TIGRE",
        "Instituto": "INSTITUTO",
        "Central Córdoba": "CENTRAL CORDOBA",
        "Unión de Santa Fe": "UNION",
        "Platense": "PLATENSE",
        "Barracas Central": "BARRACAS CENTRAL",
        "Newell's Old Boys": "NEWELLS OLD BOYS",
        "Gimnasia y Esgrima": "GIMNASIA",
        "Deportivo Riestra": "DEPORTIVO RIESTRA",
        "Belgrano": "BELGRANO",
        "Sarmiento": "SARMIENTO JUNIN",
        "Atlético Tucumán": "ATLETICO TUCUMAN",
        "Aldosivi": "ALDOSIVI",
    }

    for original, normalized in mappings.items():
        if original.lower() in name.lower():
            return normalized

    return name.upper().strip()


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Scrape Sofascore via Apify")
    parser.add_argument("--output", "-o", default="src/sofascore_stats.json", help="Output file path")
    parser.add_argument("--dataset-id", "-d", default=DATASET_ID, help="Apify dataset ID")
    parser.add_argument("--store-id", "-s", default=STORE_ID, help="Apify store ID")
    return parser.parse_args()


def run_apify_scraper():
    """Run the Apify scraper to fetch fresh data."""
    print("[INFO] Initializing Apify client...")

    if not API_TOKEN:
        print("[ERROR] APIFY_API_TOKEN is not set. Set it in your environment before running.")
        return None

    client = ApifyClient(API_TOKEN)

    # Prepare Actor input
    run_input = {
        "startUrls": [
            "https://www.sofascore.com/football/tournament/argentina/liga-profesional-de-futbol/155#tab:standings",
        ]
    }

    print("[INFO] Running Apify scraper (this may take a minute)...")

    # Run the Actor
    try:
        run = client.actor("azzouzana/sofascore-scraper-pro").call(run_input=run_input)
        print(f"[OK] Scraper finished. Run ID: {run.get('id')}")

        # Get dataset ID
        dataset_id = run.get("defaultDatasetId")
        print(f"[INFO] Dataset ID: {dataset_id}")

        return dataset_id

    except Exception as e:
        print(f"[ERROR] Failed to run scraper: {e}")
        return None


def fetch_from_dataset(dataset_id):
    """Fetch data from Apify dataset."""
    if not dataset_id:
        return []

    if not API_TOKEN:
        print("[ERROR] APIFY_API_TOKEN is not set. Set it in your environment before running.")
        return []

    client = ApifyClient(API_TOKEN)

    print("[INFO] Fetching data from dataset...")

    items = []
    try:
        for item in client.dataset(dataset_id).iterate_items():
            items.append(item)
        print(f"[OK] Retrieved {len(items)} items")
    except Exception as e:
        print(f"[ERROR] Failed to fetch data: {e}")

    return items


def fetch_from_store():
    """Fetch data from Apify key-value store."""
    if not API_TOKEN:
        print("[ERROR] APIFY_API_TOKEN is not set. Set it in your environment before running.")
        return None

    client = ApifyClient(API_TOKEN)

    print("[INFO] Fetching data from key-value store...")

    try:
        store = client.key_value_store(STORE_ID)
        record = store.get_record("STANDINGS")

        if record:
            print("[OK] Retrieved standings data")
            return record.get("value")
        else:
            print("[WARNING] No STANDINGS record found in store")
            return None
    except Exception as e:
        print(f"[ERROR] Failed to fetch from store: {e}")
        return None


def process_standings_data(data):
    """Process raw standings data into structured format."""
    teams = []
    standings = []

    if not data:
        return teams, standings

    print(f"[INFO] Processing {len(data) if isinstance(data, list) else 1} records...")

    # Handle different data structures
    if isinstance(data, list):
        for item in data:
            teams.extend(process_item(item))
    else:
        teams = process_item(data)

    # Normalize team names
    for team in teams:
        team['normalized'] = normalize_team_name(team.get('name', ''))

        # Add to standings
        standings.append({
            'team': team.get('name', ''),
            'normalized': team.get('normalized', ''),
            'played': team.get('played', 0),
            'won': team.get('won', 0),
            'drawn': team.get('drawn', 0),
            'lost': team.get('lost', 0),
            'goals_for': team.get('goalsFor', 0),
            'goals_against': team.get('goalsAgainst', 0),
            'goal_difference': team.get('goalDifference', 0),
            'points': team.get('points', 0),
            'position': team.get('position', 0),
        })

    return teams, standings


def process_item(item):
    """Process a single item from the dataset."""
    teams = []

    # Try different possible structures
    if isinstance(item, dict):
        # Check for standings in different locations
        if 'standings' in item:
            data = item['standings']
        elif 'table' in item:
            data = item['table']
        elif 'teams' in item:
            data = item['teams']
        elif 'data' in item:
            data = item['data']
        else:
            data = [item]

        if isinstance(data, list):
            teams.extend(data)
        else:
            teams.append(data)

    return teams


def save_results(teams, standings, output_path):
    """Save processed data to JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    result = {
        'scraped_at': datetime.now().isoformat(),
        'source': 'sofascore',
        'source_type': 'apify',
        'url': 'https://www.sofascore.com/football/tournament/argentina/liga-profesional-de-futbol/155',
        'teams': teams,
        'standings': standings
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[OK] Data saved to {output_path}")
    return result


def main():
    """Main function."""
    args = parse_arguments()

    print("=" * 60)
    print("Sofascore Scraper - Apify Edition")
    print("=" * 60)

    # Try to get data
    raw_data = None

    # Option 1: Try fetching from key-value store first
    raw_data = fetch_from_store()

    # Option 2: If no store data, run the scraper
    if not raw_data:
        print("[INFO] No cached data found. Running scraper...")
        dataset_id = run_apify_scraper()
        if dataset_id:
            raw_data = fetch_from_dataset(dataset_id)

    # Process and save
    if raw_data:
        teams, standings = process_standings_data(raw_data)

        if teams:
            save_results(teams, standings, args.output)
        else:
            print("[WARNING] No team data found in response")
            print("[INFO] Raw data sample:")
            if isinstance(raw_data, list) and len(raw_data) > 0:
                print(json.dumps(raw_data[0], indent=2)[:500])
            elif isinstance(raw_data, dict):
                print(json.dumps(raw_data, indent=2)[:500])
    else:
        print("[ERROR] Could not fetch any data from Apify")

    print("\n[OK] Done!")


if __name__ == "__main__":
    main()
