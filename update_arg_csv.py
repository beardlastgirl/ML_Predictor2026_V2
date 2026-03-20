"""
update_arg_csv.py - Update ARG.csv from football-data.co.uk

Purpose:
- Check the "Last updated" timestamp from
  https://www.football-data.co.uk/argentina.php
- Download and overwrite data/ARG.csv only if the web version is newer than
  local file
- Verify the update with confirmation message and file properties

Target: C:\\Scripts\\ML_Predictor2026_V2\\data\\ARG.csv
Source: https://www.football-data.co.uk/new/ARG.csv
"""

import os
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup


def log_info(message):
    """Log an informational message."""
    print(f"[INFO] {message}")


def log_ok(message):
    """Log a success message."""
    print(f"[OK] {message}")


def log_warning(message):
    """Log a warning message."""
    print(f"[WARNING] {message}")


def log_error(message):
    """Log an error message."""
    print(f"[ERROR] {message}")


def parse_date_string(date_str):
    """Parse date string like '17/02/26' or '17/02/2026' to datetime.
        Returns datetime object or None if parsing fails.
    """
    # Try DD/MM/YY format first
    for fmt in ['%d/%m/%y', '%d/%m/%Y', '%d-%m-%y', '%d-%m-%Y']:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def get_web_last_updated():

    """Scrape the 'Last updated' timestamp from the Argentina.php page.

    Returns datetime object or None if not found.
    """
    url = "https://www.football-data.co.uk/argentina.php"

    try:
        log_info(f"Fetching last updated timestamp from {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for "Last updated" text in the page
        # Common patterns: "Last updated: 17/02/26" or "Last updated 17/02/26"
        text = soup.get_text()

        # Try to find date patterns near "Last updated" or "updated"
        patterns = [
            r'Last updated[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            r'updated[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            # Fallback: any date-like pattern
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Take the first match that looks like a recent date
                for match in matches:
                    parsed_date = parse_date_string(match)
                    if parsed_date:
                        log_info(
                            f"Found timestamp: {match} -> "
                            f"{parsed_date.strftime('%Y-%m-%d')}"
                        )
                        return parsed_date

        log_warning("Could not find 'Last updated' timestamp on page")
        return None

    except requests.RequestException as e:
        log_error(f"Failed to fetch page: {e}")
        return None
    except (AttributeError, TypeError, ValueError) as e:
        log_error(f"Error parsing page: {e}")
        return None


def download_arg_csv(target_path):
    """Download ARG.csv from football-data.co.uk and save to target_path.

    Returns True if successful, False otherwise.
    """
    url = "https://www.football-data.co.uk/new/ARG.csv"

    try:
        log_info(f"Downloading ARG.csv from {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()

        # Save to target path
        with open(target_path, 'wb') as f:
            f.write(response.content)

        log_ok(f"Downloaded {len(response.content)} bytes")
        return True

    except requests.RequestException as e:
        log_error(f"Failed to download ARG.csv: {e}")
        return False


def get_file_modification_date(filepath):
    """Get the last modification date of a file.

    Returns datetime object or None if file doesn't exist.
    """
    if not os.path.exists(filepath):
        return None

    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime)
    except OSError as e:
        log_error(f"Error reading file modification date: {e}")
        return None


def main():
    """Main function to check and update ARG.csv if needed."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_path = os.path.join(script_dir, "data", "ARG.csv")

    log_info("=" * 60)
    log_info("ARG.csv Update Check")
    log_info("=" * 60)

    # Get web timestamp
    web_date = get_web_last_updated()
    if web_date is None:
        log_warning("Could not determine web timestamp. Skipping update.")
        return

    # Get local file modification date
    local_date = get_file_modification_date(target_path)

    if local_date is None:
        log_info("Local ARG.csv not found. Downloading...")
        if download_arg_csv(target_path):
            # Verify the download
            new_local_date = get_file_modification_date(target_path)
            if new_local_date:
                file_size = os.path.getsize(target_path)
                log_ok("ARG.csv created successfully")
                log_info(f"File size: {file_size:,} bytes")
                log_info(
                    f"File date: "
                    f"{new_local_date.strftime('%Y-%m-%d %H:%M:%S')}"
                )
        return

    # Compare dates
    log_info(f"Web timestamp: {web_date.strftime('%Y-%m-%d')}")
    log_info(f"Local file date: {local_date.strftime('%Y-%m-%d %H:%M:%S')}")

    if web_date.date() > local_date.date():
        log_info("Web version is newer. Downloading update...")
        if download_arg_csv(target_path):
            # Verify the update
            updated_date = get_file_modification_date(target_path)
            if updated_date:
                file_size = os.path.getsize(target_path)
                log_ok("ARG.csv updated successfully")
                log_info(f"File size: {file_size:,} bytes")
                log_info(
                    f"File date: {updated_date.strftime('%Y-%m-%d %H:%M:%S')}"
                )
    else:
        log_info("Local file is up to date. No update needed.")


if __name__ == "__main__":
    main()
