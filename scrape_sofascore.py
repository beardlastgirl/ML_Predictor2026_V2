"""
scrape_sofascore.py - Sofascore Statistics Scraper

Uses Playwright to connect to an existing Chrome session (CDP)
to extract team statistics from Sofascore's Liga Profesional Argentina page.

Usage:
    # First, launch Chrome with debugging port:
    # "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebug"

    python scrape_sofascore.py
    python scrape_sofascore.py --output src/sofascore_stats.json
"""

import os
import sys
import json
import argparse
import re
from datetime import datetime
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.data_processing import normalize_team_name, load_glossary


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Scrape Sofascore statistics")
    parser.add_argument("--output", "-o", default="src/sofascore_stats.json", help="Output file path")
    parser.add_argument("--port", "-p", type=int, default=9222, help="Chrome debugging port")
    parser.add_argument("--timeout", "-t", type=int, default=30, help="Page timeout in seconds")
    parser.add_argument("--glossary", "-g", default="Glossary.txt", help="Path to Glossary.txt")
    return parser.parse_args()


def extract_data_from_page(page, glossary=None):
    """Extract data from the currently loaded page."""
    teams = []
    standings = []

    try:
        # Get page content
        content = page.content()

        # Look for team data in the page
        # Try to find standings table
        table = page.locator('table').first
        if table.is_visible():
            rows = table.locator('tbody tr, tr').all()

            for row in rows:
                try:
                    cells = row.locator('td').all()
                    if len(cells) >= 7:
                        # Get team name from link
                        team_link = row.locator('a[href*="/team/"]').first
                        if team_link.is_visible():
                            team_name = team_link.text_content().strip()

                            # Get stats
                            pos = cells[0].text_content().strip() if len(cells) > 0 else ""
                            played = cells[2].text_content().strip() if len(cells) > 2 else "0"
                            won = cells[3].text_content().strip() if len(cells) > 3 else "0"
                            drawn = cells[4].text_content().strip() if len(cells) > 4 else "0"
                            lost = cells[5].text_content().strip() if len(cells) > 5 else "0"
                            goals = cells[6].text_content().strip() if len(cells) > 6 else "0-0"

                            # Parse goals
                            if '-' in goals:
                                gf, ga = goals.split('-')
                            else:
                                gf, ga = goals, "0"

                            # Get team URL for ID
                            href = team_link.get_attribute('href') or ""
                            team_id_match = re.search(r'/team/[^/]+/(\d+)', href)
                            team_id = team_id_match.group(1) if team_id_match else ""
                            
                            normalized = normalize_team_name(team_name, glossary)

                            standings.append({
                                'position': pos,
                                'team': team_name,
                                'normalized': normalized,
                                'sofascore_id': team_id,
                                'played': int(played) if played.isdigit() else 0,
                                'won': int(won) if won.isdigit() else 0,
                                'drawn': int(drawn) if drawn.isdigit() else 0,
                                'lost': int(lost) if lost.isdigit() else 0,
                                'goals_for': gf.strip(),
                                'goals_against': ga.strip(),
                            })

                            teams.append({
                                'name': team_name,
                                'normalized': normalized,
                                'sofascore_id': team_id,
                            })
                except Exception:
                    continue

    except Exception as e:
        print(f"[WARNING] Error extracting table data: {e}")

    # Remove duplicate teams
    seen = set()
    unique_teams = []
    for team in teams:
        if team['sofascore_id'] and team['sofascore_id'] not in seen:
            seen.add(team['sofascore_id'])
            unique_teams.append(team)

    print(f"[INFO] Found {len(unique_teams)} teams in standings")
    return unique_teams, standings


def save_results(teams, standings, output_path):
    """Save scraped data to JSON file."""
    # Create output directory if needed
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Merge team data with standings
    team_data = {}
    for team in teams:
        team_data[team['sofascore_id']] = team

    for stand in standings:
        sid = stand.get('sofascore_id')
        if sid and sid in team_data:
            team_data[sid].update(stand)

    result = {
        'scraped_at': datetime.now().isoformat(),
        'source': 'sofascore',
        'url': 'https://www.sofascore.com/football/tournament/argentina/liga-profesional-de-futbol/155',
        'teams': list(team_data.values()),
        'standings': standings
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[OK] Data saved to {output_path}")
    return result


def main():
    """Main scraper function."""
    args = parse_arguments()

    print("=" * 60)
    print("Sofascore Statistics Scraper - Liga Profesional Argentina")
    print("=" * 60)
    
    glossary = load_glossary(args.glossary)

    print()
    print("INSTRUCTIONS:")
    print("1. Close all Chrome windows")
    print("2. Launch Chrome with debugging port:")
    print('   "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"')
    print('   --remote-debugging-port=9222 --user-data-dir="C:\\ChromeDebug"')
    print("3. Navigate to:")
    print("   https://www.sofascore.com/football/tournament/argentina/liga-profesional-de-futbol/155")
    print("4. Click on 'Standings' tab to see the table")
    print("5. Press Enter in this terminal to continue...")
    print()

    input("Press Enter when ready...")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[ERROR] playwright not installed. Run: pip install playwright")
        sys.exit(1)

    with sync_playwright() as p:
        try:
            # Connect to existing Chrome session
            print(f"[INFO] Connecting to Chrome on port {args.port}...")
            browser = p.chromium.connect_over_cdp(f"http://localhost:{args.port}")
            print("[OK] Connected to Chrome")

            # Get the first context
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()

            # Check current URL
            current_url = page.url
            print(f"[INFO] Current page: {current_url}")

            if "sofascore" not in current_url.lower():
                print("[WARNING] Not on Sofascore. Please navigate to the correct page.")
                print("[INFO] Navigate to: https://www.sofascore.com/football/tournament/argentina/liga-profesional-de-futbol/155")
                print("[INFO] Then click on 'Standings' tab")
                input("Press Enter when ready...")

            # Extract data
            teams, standings = extract_data_from_page(page, glossary)

            if teams or standings:
                save_results(teams, standings, args.output)
            else:
                print("[WARNING] No data extracted. Try scrolling to the standings table.")

            browser.close()

        except Exception as e:
            print(f"[ERROR] Failed to connect: {e}")
            print("\nMake sure Chrome is running with debugging port:")
            print('  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"')
            print('  --remote-debugging-port=9222 --user-data-dir="C:\\ChromeDebug"')
            sys.exit(1)

    print("\n[OK] Done!")


if __name__ == "__main__":
    main()
