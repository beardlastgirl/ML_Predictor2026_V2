# -*- coding: utf-8 -*-
r"""
Manual-browser scraper for Liga Profesional Argentina (FBref & FootyStats).

STRATEGY: Chrome Remote Debugging (CDP)
----------------------------------------
Instead of launching a bot-controlled browser that sites detect and block,
this script connects to YOUR OWN Chrome session via the Chrome DevTools
Protocol (CDP). You open the page yourself (solving any CAPTCHA as a normal
user), then the script reads the already-rendered HTML from your tab and
extracts the tables.

No bot detection is possible because the browser is genuinely yours.

HOW TO USE (step-by-step)
--------------------------
Step 1 - The script can now auto-launch Chrome with CDP enabled!

SIMPLIFIED USAGE (Recommended):
  Just run the script directly:
    python scrape_stats_manual.py

  The script will automatically:
  1. Launch Chrome with remote debugging on port 9222
  2. Wait for you to navigate to the FBref or FootyStats page
  3. Connect and scrape the data

MANUAL USAGE (Optional):
  If you prefer to launch Chrome manually first:

Step 1 - Launch Chrome with remote debugging enabled. Run ONE of these:

  Windows (PowerShell):
    & "C:\Program Files\Google\Chrome\Application\chrome.exe" `
    --remote-debugging-port=9222 --user-data-dir="C:\ChromeDebug" `
    --remote-allow-origins=*

Step 2 - In that Chrome window, navigate manually to:
    FBref: https://fbref.com/en/comps/21/Liga-Profesional-Argentina-Stats
    OR
    FootyStats: https://footystats.org/argentina/primera-division

  Solve any CAPTCHA if prompted. Wait until the full stats table is visible.

Step 3 - Run this script (with the virtual environment active):
    python scrape_stats_manual.py

  The script connects to Chrome on port 9222, finds the relevant tab,
  reads the page HTML, extracts the tables, and saves them to src/.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import threading
from datetime import datetime
from io import StringIO
from typing import Dict, Optional

import pandas as pd
import requests

try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False

# ==============================================
# Logging Utilities
# ==============================================


def log_info(msg):
    print(f"[INFO] {msg}")



def log_ok(msg):
    print(f"[OK] {msg}")



def log_error(msg):
    print(f"[ERROR] {msg}")



def log_warning(msg):
    print(f"[WARNING] {msg}")

# ==============================================
# Targets Configuration
# ==============================================

TARGET_SITES = {
    "FBref": "fbref.com/en/comps/21",
    "FootyStats": "footystats.org/argentina/primera-division"
}

DEFAULT_CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEFAULT_USER_DATA_DIR = r"C:\ChromeDebug"

# ==============================================
# Rate Limiting
# ==============================================


def get_last_scrape_date(output_dir):
    """Get the date of the last successful scrape from the timestamp files."""
    try:
        if not os.path.exists(output_dir):
            return None

        csv_files = [f for f in os.listdir(output_dir) if f.endswith(".csv")]
        if not csv_files:
            return None

        dates = []
        for filename in csv_files:
            match = re.search(r"(\d{8})", filename)
            if match:
                dates.append(match.group(1))

        if dates:
            return max(dates)
    except Exception as e:
        log_warning(f"Error checking last scrape date: {e}")
    return None



def should_scrape_today(output_dir, force=False):
    """Check if we should scrape today based on last scrape date."""
    if force:
        log_info("Force scraping enabled (bypassing rate limit)")
        return True

    today = datetime.now().strftime("%Y%m%d")
    last_scrape = get_last_scrape_date(output_dir)

    if last_scrape == today:
        log_info(
            f"Already scraped today (last scrape: {last_scrape}). "
            "Use --force to override."
        )
        return False

    return True

# ==============================================
# CDP Connection
# ==============================================


def launch_chrome(chrome_path, port, user_data_dir=DEFAULT_USER_DATA_DIR):
    """Start Chrome with remote debugging if it's not already running."""
    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--remote-allow-origins=*",
    ]
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log_info(f"Launched Chrome: {chrome_path} (port {port})")
        return True
    except Exception as e:
        log_error(f"Failed to launch Chrome: {e}")
        return False



def ensure_chrome_cdp(port, timeout, chrome_path=DEFAULT_CHROME_PATH):
    """Ensure Chrome CDP is available; if not, try launching Chrome."""
    try:
        tabs = get_cdp_tabs(port, timeout=min(timeout, 5))
        return tabs
    except Exception:
        log_info(
            f"Chrome not reachable on port {port}. Attempting to start it."
        )
        if not launch_chrome(chrome_path, port):
            raise
        start = time.time()
        while time.time() - start < timeout:
            try:
                return get_cdp_tabs(port, timeout=2)
            except Exception:
                time.sleep(1)
        raise ConnectionError(
            f"Chrome did not become ready on port {port} within {timeout}s."
        )



def get_cdp_tabs(port, timeout=10):
    """Return the list of open tabs from Chrome's CDP endpoint."""
    endpoint = f"http://localhost:{port}/json"
    try:
        resp = requests.get(endpoint, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise ConnectionError(
            f"Could not connect to Chrome on port {port}: {e}"
        )



def find_target_tab(tabs):
    """Return the first tab matching any target site and the site name."""
    for tab in tabs:
        url = tab.get("url", "")
        for name, fragment in TARGET_SITES.items():
            if fragment in url:
                return tab, name
    return None, None



def get_page_html_via_cdp(tab, port):
    """Retrieve fully rendered HTML via CDP WebSocket."""
    if not HAS_WEBSOCKET:
        log_error(
            "websocket-client not installed. "
            "Please run: pip install websocket-client"
        )
        return None

    ws_url = tab.get("webSocketDebuggerUrl")
    if not ws_url:
        tab_id = tab.get("id", "")
        ws_url = f"ws://localhost:{port}/devtools/page/{tab_id}"

    result: Dict[str, Optional[str]] = {"html": None, "error": None}

    def run():
        try:
            ws = websocket.create_connection(
                ws_url,
                timeout=15,
                origin=f"http://localhost:{port}",
            )
            msg_id = 1
            payload = json.dumps(
                {
                    "id": msg_id,
                    "method": "Runtime.evaluate",
                    "params": {
                        "expression": "document.documentElement.outerHTML",
                        "returnByValue": True,
                    },
                }
            )
            ws.send(payload)
            deadline = time.time() + 15
            while time.time() < deadline:
                data = json.loads(ws.recv())
                if data.get("id") == msg_id:
                    result["html"] = data.get("result", {}).get(
                        "result", {}
                    ).get("value")
                    break
            ws.close()
        except Exception as e:
            result["error"] = str(e)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=20)

    if result["error"]:
        log_error(f"CDP WebSocket error: {result['error']}")
    return result["html"]

# ==============================================
# Table Extraction and Cleaning
# ==============================================


def clean_team_name(text):
    """Remove rank prefixes and HTML artifacts from team names."""
    if not text:
        return ""
    text = re.sub(r"^\d+\.\s*", "", str(text))  # FootyStats rank
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s*\([HA]\)$", "", text)  # FootyStats (H)/(A)
    return " ".join(text.split()).strip()



def identify_squad_column(df):
    """Identify the column containing team names."""
    candidates = ["Squad", "Team", "Equipo", "Club", "Name", "Nombre"]
    for col in df.columns:
        if any(c.upper() in str(col).upper() for c in candidates):
            return col
    return df.columns[0] if not df.empty else None



def clean_dataframe(df):
    """Normalize dataframe for ML_Predictor."""
    df = df.copy()

    # Flatten MultiIndex if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [
            str(c[-1]).strip()
            if "Unnamed" not in str(c[-1])
            else str(c[0]).strip()
            for c in df.columns
        ]

    # Deduplicate column names so every access returns a Series
    seen = {}
    deduped = []
    for col in df.columns:
        col_str = str(col)
        if col_str not in seen:
            seen[col_str] = 0
            deduped.append(col_str)
        else:
            seen[col_str] += 1
            deduped.append(f"{col_str}_{seen[col_str]}")
    df.columns = deduped

    squad_col = identify_squad_column(df)
    if squad_col:
        df = df.rename(columns={squad_col: "Squad"})
        df["Squad"] = df["Squad"].apply(clean_team_name)
        df = df[
            df["Squad"].notna()
            & (df["Squad"].astype(str) != "")
            & (df["Squad"].astype(str).str.lower() != "team")
        ]

    for col in df.columns:
        if col != "Squad":
            try:
                # Ensure we are passing a Series to to_numeric
                df[col] = pd.to_numeric(df[col], errors="coerce")
            except Exception as e:
                log_warning(f"Could not convert column {col} to numeric: {e}")

    cols_index = pd.Index(df.columns)
    unnamed_mask = ~cols_index.astype(str).str.contains("^Unnamed")
    return df.loc[:, unnamed_mask].dropna(axis=1, how="all")



def identify_table_type(df):
    """Identify table type (league, stats, etc.)."""
    cols = [str(c).upper() for c in df.columns]
    cols_str = " ".join(cols)
    if "MP" in cols and "GF" in cols and "GA" in cols:
        return "league_table"
    if any(k in cols_str for k in ["XG", "PPG", "GLS", "SH", "GA90"]):
        return "stats_advanced"
    return "other"



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output-dir", default="src/")
    args = parser.parse_args()

    if not should_scrape_today(args.output_dir, args.force):
        sys.exit(0)

    try:
        tabs = ensure_chrome_cdp(args.port, timeout=15)

        # Wait loop for target tab
        tab, site_name = None, None
        log_info("Searching for FBref or FootyStats tab...")

        start_wait = time.time()
        wait_timeout = 60  # Give user 60 seconds to navigate

        while time.time() - start_wait < wait_timeout:
            tabs = get_cdp_tabs(args.port)
            tab, site_name = find_target_tab(tabs)
            if tab:
                break

            # Print status every 5 seconds
            if int(time.time() - start_wait) % 5 == 0:
                remaining = int(wait_timeout - (time.time() - start_wait))
                log_info(
                    "Waiting for you to open FBref or FootyStats... "
                    f"({remaining}s remaining)"
                )
                print("  Target URLs:")
                for name, url in TARGET_SITES.items():
                    print(f"    - {name}: https://{url}")

            time.sleep(2)

        if not tab:
            log_error("No FBref or FootyStats tab found within timeout.")
            log_info("Currently open tabs in your Chrome window:")
            for t in tabs:
                print(f"  - [{t.get('type', '?')}] {t.get('url', '(no url)')}")
            sys.exit(1)
        if not site_name:
            log_error(
                "Target tab found but site name could not be identified."
            )
            sys.exit(1)

        log_ok(f"Found {site_name} tab: {tab.get('url')}")
        html = get_page_html_via_cdp(tab, args.port)
        if not html:
            log_error("Failed to retrieve HTML via CDP.")
            sys.exit(1)

        raw_tables = pd.read_html(StringIO(html))
        log_info(f"Found {len(raw_tables)} tables.")

        today = datetime.now().strftime("%Y%m%d")
        for i, df in enumerate(raw_tables):
            df_clean = clean_dataframe(df)
            if df_clean.empty or len(df_clean.columns) < 2:
                continue

            table_type = identify_table_type(df_clean)
            prefix = f"{site_name.lower()}_{table_type}"
            filename = f"{prefix}_{today}_{i}.csv"
            filepath = os.path.join(args.output_dir, filename)

            df_clean.to_csv(filepath, index=False)
            log_ok(f"Saved: {filepath} ({len(df_clean)} rows)")

    except Exception as e:
        log_error(f"Execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
