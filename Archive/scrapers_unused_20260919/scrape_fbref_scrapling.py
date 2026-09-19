import os
import time
import random
import pandas as pd
from datetime import datetime
from io import StringIO
from bs4 import BeautifulSoup
import re

# Import Scrapling components
from scrapling.fetchers import StealthyFetcher

from src.scraper_utils import resilient_scraper, CaptchaDetectedException, detect_captcha_in_content, get_health_monitor
from src.utils import log_error, log_info, log_ok, log_warning

# --- Configuration ---
FBREF_URL = "https://fbref.com/en/comps/21/Liga-Profesional-Argentina-Stats"
OUTPUT_DIR = "data/"
USER_DATA_DIR = os.path.join(os.getcwd(), ".scrapling_user_data")  # Persist browser profile

# --- Cleaning functions (unchanged) ---
def clean_team_name(text):
    """Clean team name by removing URLs, images, and extra whitespace."""
    if not text:
        return ""
    text = re.sub(r"https?://[^\s]+", "", str(text))
    text = re.sub(r"<img[^>]*>", "", text)
    text = re.sub(r"cdn\.[^\s]+", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = " ".join(text.split())
    return text.strip()

def identify_squad_column(df):
    """Identify which column contains team/squad names."""
    squad_names = ["Squad", "Team", "Equipo", "Club", "Nombre", "Name", "Squadra"]
    for col in df.columns:
        col_upper = str(col).upper()
        for name in squad_names:
            if name.upper() in col_upper:
                return col
    
    # Check first column if it looks like names
    first_col = df.columns[0]
    if df[first_col].dtype == "object":
        sample_values = df[first_col].dropna().head(5)
        if len(sample_values) > 0:
            text_ratio = sum(
                1 for v in sample_values 
                if not str(v).replace(".", "").replace("-", "").isdigit()
            ) / len(sample_values)
            if text_ratio > 0.6:
                return first_col
    return None

def clean_dataframe(df, squad_column=None):
    """Clean and prepare dataframe for ML_Predictor compatibility."""
    df = df.copy()
    
    # Remove duplicate header rows
    if len(df) > 0:
        first_col = df.iloc[:, 0]
        col_name = str(df.columns[0])
        mask = first_col.astype(str) != col_name
        df = df[mask].reset_index(drop=True)

    if squad_column is None:
        squad_column = identify_squad_column(df)

    if squad_column and squad_column in df.columns:
        df[squad_column] = df[squad_column].apply(clean_team_name)
        if squad_column != "Squad":
            df = df.rename(columns={squad_column: "Squad"})
        
        df = df[df["Squad"].notna()]
        df = df[df["Squad"].astype(str).str.strip() != ""]
        df = df[df["Squad"].astype(str).str.strip() != "nan"]

    # Convert numeric columns
    for col in df.columns:
        if col == "Squad":
            continue
        try:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        except:
            pass

    # Remove empty columns
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
    df = df.dropna(axis=1, how="all")
    
    return df

# Global Scrapling fetcher instance for decorator cleanup
_scrapling_fetcher_instance = None

def close_scrapling_browser():
    """Cleanup function for resilient_scraper to close Scrapling's Playwright browser."""
    global _scrapling_fetcher_instance
    if _scrapling_fetcher_instance:
        try:
            log_info("Decorator: Closing Scrapling Playwright resources...")
            # Scrapling uses Playwright internally. We need to close browser and stop playwright
            if hasattr(_scrapling_fetcher_instance, '_browser') and _scrapling_fetcher_instance._browser:
                _scrapling_fetcher_instance._browser.close()
                log_info("Browser closed.")
            if hasattr(_scrapling_fetcher_instance, '_playwright') and _scrapling_fetcher_instance._playwright:
                _scrapling_fetcher_instance._playwright.stop()
                log_info("Playwright stopped.")
        except Exception as e:
            log_error(f"Decorator: Error closing Scrapling resources: {e}")
        finally:
            _scrapling_fetcher_instance = None

@resilient_scraper(max_retries=3, backoff_factor=2, timeout=90, resource_cleanup=close_scrapling_browser)
def scrape_fbref_with_scrapling(headless=False, output_dir=OUTPUT_DIR, table_index=-1):  # Default headless=False for debugging FBref blocks
    """
    Scrape football statistics from FBref using Scrapling with enhanced stealth.
    """
    log_info(f"Starting FBref scraper with Scrapling for: {FBREF_URL}")
    global _scrapling_fetcher_instance
    
    try:
        # Create user_data_dir if it doesn't exist (helps with persistence)
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        
        # Initialize StealthyFetcher with anti-detection arguments
        # Note: user_data_dir helps maintain cookies/session between runs, reducing 403s
        _scrapling_fetcher_instance = StealthyFetcher(
            headless=headless,
            user_data_dir=USER_DATA_DIR,
            # Extra arguments to help bypass detection
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-web-security',
                '--disable-features=BlockInsecurePrivateNetworkRequests',
            ]
        )
        
        # Human-like random delay before fetch (important for FBref)
        delay = random.uniform(2, 6)
        log_info(f"Adding human-like delay: {delay:.2f}s before request...")
        time.sleep(delay)
        
        # Fetch with networkidle to ensure JS tables load
        response = _scrapling_fetcher_instance.fetch(
            FBREF_URL,
            timeout=80000,
            wait_until='networkidle'
        )
        
        # Check response status immediately
        if response.status == 403:
            log_error("HTTP 403 Forbidden - FBref is blocking this request.")
            raise CaptchaDetectedException("HTTP 403 - Access blocked by FBref/DataDome.")
        elif response.status == 429:
            log_error("HTTP 429 Too Many Requests.")
            raise CaptchaDetectedException("HTTP 429 - Rate limited by FBref.")
        elif response.status != 200:
            raise Exception(f"HTTP {response.status} returned")
            
        html = response.html
        
        # Secondary CAPTCHA/Block detection in content
        if detect_captcha_in_content(html):
            raise CaptchaDetectedException("CAPTCHA detected in page content.")
            
        # Check for block messages in HTML
        lower_html = html.lower()
        if any(block_msg in lower_html for block_msg in ['access denied', 'datadome', 'blocked', 'please verify', 'captcha']):
            raise CaptchaDetectedException("Anti-bot protection detected in page content.")
            
        log_ok(f"Retrieved {len(html)} characters of HTML via Scrapling (Status: {response.status}).")

        # Parse tables
        soup = BeautifulSoup(html, "lxml")
        tables = soup.find_all("table")
        log_info(f"Found {len(tables)} tables on the page.")

        os.makedirs(output_dir, exist_ok=True)
        today = datetime.now().strftime("%Y%m%d")

        saved_count = 0
        stats_table_count = 0
        
        for idx, table in enumerate(tables):
            try:
                df_list = pd.read_html(StringIO(str(table)))
                if not df_list:
                    continue

                df = df_list[0]
                if df.empty or len(df.columns) < 2:
                    continue

                df_cleaned = clean_dataframe(df)
                
                # Only save tables with Squad data (stats tables)
                if "Squad" not in df_cleaned.columns:
                    log_info(f"Skipping table {idx} (no Squad column after cleaning)")
                    continue

                # Determine file prefix based on content
                table_cols = [str(col).upper() for col in df_cleaned.columns]
                is_main_table = (
                    any("MP" in col or "MATCHES PLAYED" in col for col in table_cols)
                    and any("GF" in col or "GOALS FOR" in col for col in table_cols)
                    and any("GA" in col or "GOALS AGAINST" in col for col in table_cols)
                )
                prefix = "fbref_results" if is_main_table else "fbref_stats"

                # Save logic
                if table_index == -1 or table_index == idx:
                    filename = f"{prefix}_{today}_{stats_table_count}.csv"
                    filepath = os.path.join(output_dir, filename)
                    df_cleaned.to_csv(filepath, index=False, encoding="utf-8")
                    log_ok(f"Saved: {filepath} ({len(df_cleaned)} rows)")
                    saved_count += 1
                    stats_table_count += 1
                else:
                    log_info(f"Skipping table {idx} (index mismatch with --table-index {table_index})")

            except (ValueError, KeyError, AttributeError) as te:
                log_warning(f"Error processing table {idx}: {te}")
                continue

        if saved_count == 0:
            log_error("No valid stats tables were found.")
            return False
            
        log_ok(f"Successfully scraped {saved_count} tables.")
        return True

    except CaptchaDetectedException:
        raise  # Re-raise for resilient_scraper to handle retry
    except Exception as e:
        # Convert 403/429 errors to CaptchaDetected so they trigger retry logic
        error_str = str(e).lower()
        if "403" in error_str or "forbidden" in error_str:
            raise CaptchaDetectedException(f"Access blocked (403): {e}")
        elif "429" in error_str or "too many requests" in error_str:
            raise CaptchaDetectedException(f"Rate limited (429): {e}")
        else:
            log_error(f"FBref Scrapling scraper failed: {e}")
            raise

# --- CLI Entry Point ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape FBref Argentina data using Scrapling.")
    parser.add_argument(
        "--headless", action="store_true", default=False, 
        help="Run in headless mode (default: False to see what's happening)"
    )
    parser.add_argument(
        "--output-dir", default=OUTPUT_DIR, 
        help="Directory to save CSV files"
    )
    parser.add_argument(
        "--table-index", type=int, default=-1, 
        help="Specific table index to save (HTML order), -1 for all stats tables"
    )

    args = parser.parse_args()
    
    try:
        success = scrape_fbref_with_scrapling(
            headless=args.headless, 
            output_dir=args.output_dir, 
            table_index=args.table_index
        )
        if not success:
            exit(1)
    except Exception as e:
        log_error(f"FBref Scrapling scraper failed during execution: {e}")
        exit(1)
    finally:
        monitor = get_health_monitor()
        log_info(monitor.generate_report())
