# -*- coding: utf-8 -*-
"""
FootyStats scraper for Liga Profesional Argentina using Playwright.

This script uses Playwright to bypass FootyStats' anti-scraping protections
by automating a real browser. It extracts league tables and team statistics.

Usage:
    python scrape_footystats.py [--headless] [--output-dir src/]

Requirements:
    pip install playwright pandas beautifulsoup4
    playwright install chromium
"""

import os
import re
import time
from datetime import datetime
from io import StringIO

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from src.scraper_utils import resilient_scraper, CaptchaDetectedException, detect_captcha_in_content, get_health_monitor
from src.utils import log_error, log_info, log_ok, log_warning

# ==============================================
# Data Cleaning
# ==============================================


def clean_team_name(text):
    """Clean team name by removing rank prefixes and extra whitespace."""
    if not text:
        return ""
    # FootyStats often has things like "1. River Plate" or "River Plate (H)"
    text = re.sub(r"^\d+\.\s*", "", str(text))
    text = re.sub(r"\s*\([HA]\)$", "", text)
    return text.strip()


def clean_dataframe(df):
    """Clean FootyStats dataframe for ML_Predictor compatibility."""
    df = df.copy()

    # Identify squad column (usually first column or contains 'Team')
    squad_col = None
    candidates = ["Team", "Squad", "Club", "Name", "Equipo"]
    for col in df.columns:
        if any(c.upper() in str(col).upper() for c in candidates):
            squad_col = col
            break

    if not squad_col and not df.empty:
        squad_col = df.columns[0]

    if squad_col:
        df = df.rename(columns={squad_col: "Squad"})
        df["Squad"] = df["Squad"].apply(clean_team_name)

    # Drop rows that are likely header repetitions
    if "Squad" in df.columns:
        df = df[~df["Squad"].astype(str).str.lower().isin(["team", "squad", "club"])]

    # Remove unnamed columns
    df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed", na=False)]

    # Convert to numeric where possible
    for col in df.columns:
        if col != "Squad":
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            except ValueError as e:
                log_warning(f"Error converting column {col} to numeric: {e}")

    return df


# ==============================================
# Scraper Logic
# ==============================================

FOOTYSTATS_URL = "https://footystats.org/argentina/primera-division"

# Global browser instance for decorator cleanup
_browser = None


def close_browser():
    """Cleanup function for resilient_scraper."""
    global _browser
    if _browser:
        try:
            log_info("Decorator: Closing browser...")
            _browser.close()
        except Exception as e:
            log_error(f"Decorator: Error closing browser: {e}")
        _browser = None


@resilient_scraper(max_retries=3, backoff_factor=2, timeout=60, fallback_source='fbref', resource_cleanup=close_browser)
def scrape_footystats(headless=True, output_dir="src/"):
    """
    Scrape football statistics from FootyStats for Argentine Primera Division.
    """
    log_info(f"Starting FootyStats scraper for: {FOOTYSTATS_URL}")
    global _browser

    with sync_playwright() as p:
        # Launch browser with a realistic user agent
        _browser = p.chromium.launch(headless=headless)
        try:
            context = _browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()

            log_info("Navigating to FootyStats...")
            # Set a standard desktop viewport
            page.set_viewport_size({"width": 1920, "height": 1080})

            page.goto(FOOTYSTATS_URL, wait_until="domcontentloaded", timeout=60000)

            # Wait for any table to appear
            log_info("Waiting for tables to appear...")
            try:
                page.wait_for_selector("table", timeout=20000)
            except Exception:
                log_warning(
                    "Timeout waiting for 'table' selector. Continuing anyway..."
                )

            # Additional wait for dynamic content
            time.sleep(10)

            # Scroll to trigger lazy-loading
            for _ in range(3):
                page.evaluate("window.scrollBy(0, 500)")
                time.sleep(1)

            html = page.content()
            
            # CAPTCHA Detection
            if detect_captcha_in_content(html):
                raise CaptchaDetectedException("CAPTCHA detected on FootyStats")
                
            log_ok(f"Retrieved {len(html)} characters of HTML.")

            # Use BeautifulSoup to find tables
            soup = BeautifulSoup(html, "lxml")
            tables = soup.find_all("table")
            log_info(f"Found {len(tables)} tables on the page.")

            os.makedirs(output_dir, exist_ok=True)
            today = datetime.now().strftime("%Y%m%d")

            saved_count = 0
            for i, table in enumerate(tables):
                try:
                    # Read table into pandas
                    df_list = pd.read_html(StringIO(str(table)))
                    if not df_list:
                        continue

                    df = df_list[0]
                    if df.empty or len(df.columns) < 2:
                        continue

                    df_clean = clean_dataframe(df)

                    # Determine table type for filename
                    cols_str = " ".join(str(c).upper() for c in df_clean.columns)
                    prefix = "footystats_other"
                    if "MP" in cols_str and "GF" in cols_str and "GA" in cols_str:
                        prefix = "footystats_league"
                    elif "PPG" in cols_str or "XG" in cols_str:
                        prefix = "footystats_metrics"

                    filename = f"{prefix}_{today}_{i}.csv"
                    filepath = os.path.join(output_dir, filename)

                    df_clean.to_csv(filepath, index=False, encoding="utf-8")
                    log_ok(f"Saved: {filepath} ({len(df_clean)} rows)")
                    saved_count += 1

                except (ValueError, KeyError, AttributeError) as te:
                    log_warning(f"Error processing table {i}: {te}")

            if saved_count == 0:
                log_error("No tables were successfully scraped.")
                return False
            else:
                log_ok(f"Successfully scraped {saved_count} tables.")
                return True

        finally:
            if _browser:
                _browser.close()
                _browser = None


# ==============================================
# CLI Entry Point
# ==============================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape FootyStats Argentina data.")
    parser.add_argument(
        "--headless", action="store_true", default=False, help="Run in headless mode"
    )
    parser.add_argument(
        "--output-dir", default="src/", help="Directory to save CSV files"
    )

    args = parser.parse_args()
    try:
        scrape_footystats(headless=args.headless, output_dir=args.output_dir)
    except Exception as e:
        log_error(f"FootyStats scraper failed: {e}")
    finally:
        # Log health report
        monitor = get_health_monitor()
        log_info(monitor.generate_report())
