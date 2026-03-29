# -*- coding: utf-8 -*-
"""
Enhanced web scraping utility for Liga Argentina statistics tables.

Purpose:
- Extract tables from FBref Liga Argentina statistics page using browser automation
- Detect and handle anti-bot protections (Cloudflare, reCAPTCHA, hCaptcha, Turnstile)
- Save tables as CSV files compatible with the ML_Predictor workflow
- Automatically clean team names and normalize data formats

Requirements:
    pip install selenium pandas beautifulsoup4 lxml

Usage:
    python scrape_stats_enhanced.py [--table-index 0] [--headless] [--timeout 60] [--force-continue-after-solve]

The URL and output directory are fixed:
- URL: https://fbref.com/en/comps/21/Liga-Profesional-Argentina-Stats
- Output directory: src/
- Backup of original: scrape_stats_backup.py

New Features:
- Browser automation with Selenium
- Anti-bot detection (Cloudflare, reCAPTCHA, hCaptcha, Turnstile)
- Manual intervention prompts for CAPTCHAs
- Configurable timeouts and headless mode
- Automatic WebDriver management
- Optional flag --force-continue-after-solve to continue once URL changes after manual solve
"""

import os
import re
import shutil
import sys
import time
from datetime import datetime
from io import StringIO

import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.scraper_utils import (
    CaptchaDetectedException,
    detect_captcha_in_content,
    get_health_monitor,
    resilient_scraper,
)
from src.utils import log_error, log_info, log_ok, log_warning

# Try to import webdriver-manager for automatic driver management
try:
    from webdriver_manager.chrome import ChromeDriverManager

    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

# Try to import fake-useragent for dynamic User-Agent
try:
    import fake_useragent

    FAKE_USERAGENT_AVAILABLE = True
except ImportError:
    FAKE_USERAGENT_AVAILABLE = False


def log_warning(message):
    """Log a warning message using a simple ASCII prefix."""
    print(f"[WARNING] {message}")


def backup_original_script():
    """Create a backup of the original scrape_stats.py if it exists."""
    original = "scrape_stats.py"
    backup = "scrape_stats_backup.py"

    if os.path.exists(original) and not os.path.exists(backup):
        try:
            shutil.copy2(original, backup)
            log_ok(f"Backup created: {backup}")
        except Exception as e:
            log_warning(f"Could not create backup: {e}")
    elif os.path.exists(backup):
        log_info(f"Backup already exists: {backup}")


def is_page_ready(driver, page_source):
    """Check if the page is actually ready for scraping (has content we expect).

    Returns True if page appears to be the actual stats page, False if it's a challenge page.
    """
    page_lower = page_source.lower()

    # Positive signals: content that indicates we're on the actual stats page
    positive_markers = [
        "goals for",
        "gf",
        "goals against",
        "ga",
        "matches played",
        "mp",
        "squad",
        "team",
        "liga profesional",
        "argentina stats",
        "fbref.com",
        "stats table",
    ]

    # Check for tables in DOM
    try:
        tables = driver.find_elements(By.TAG_NAME, "table")
        if tables and len(tables) > 0:
            # If we have tables AND positive markers, page is ready
            if any(marker in page_lower for marker in positive_markers):
                return True
    except Exception:
        pass

    # If we have strong positive markers, assume ready even without tables yet
    strong_markers = ["goals for", "matches played", "liga profesional argentina"]
    if any(marker in page_lower for marker in strong_markers):
        return True

    return False


def detect_anti_bot_protection(driver, page_source):
    """Detect various anti-bot protections on the page.

    Returns tuple: (protection_type: str, detected: bool)
    Protection types: 'cloudflare_ddos', 'cloudflare_turnstile', 'recaptcha', 'hcaptcha', 'generic', None

    Note: This function is conservative - it only detects active challenges, not residual markers.
    """
    # First check if page is actually ready - if so, don't detect protection
    if is_page_ready(driver, page_source):
        return None, False

    page_lower = page_source.lower()

    # Cloudflare DDoS Protection (challenge page) - only if we see the actual challenge text
    if "checking your browser" in page_lower and "please wait" in page_lower:
        log_warning("Detected: Cloudflare DDoS Protection (active challenge)")
        return "cloudflare_ddos", True
    if "ddos protection by cloudflare" in page_lower and "just a moment" in page_lower:
        log_warning("Detected: Cloudflare DDoS Protection (active challenge)")
        return "cloudflare_ddos", True

    # Cloudflare Turnstile - only if we see the actual challenge widget
    # Check for visible turnstile iframe or challenge elements
    try:
        turnstile_elements = driver.find_elements(
            By.CSS_SELECTOR,
            'iframe[src*="challenges.cloudflare.com"], iframe[title*="challenge"], .cf-turnstile',
        )
        if turnstile_elements:
            # Check if any are visible
            for elem in turnstile_elements:
                if elem.is_displayed():
                    log_warning("Detected: Cloudflare Turnstile (visible challenge)")
                    return "cloudflare_turnstile", True
    except Exception:
        pass

    # reCAPTCHA - only if we see the actual challenge widget
    try:
        recaptcha_elements = driver.find_elements(
            By.CSS_SELECTOR, '.g-recaptcha, iframe[src*="recaptcha"], #recaptcha'
        )
        if recaptcha_elements:
            for elem in recaptcha_elements:
                if elem.is_displayed():
                    log_warning("Detected: reCAPTCHA (visible challenge)")
                    return "recaptcha", True
    except Exception:
        pass

    # hCaptcha - only if we see the actual challenge widget
    try:
        hcaptcha_elements = driver.find_elements(
            By.CSS_SELECTOR, '.h-captcha, iframe[src*="hcaptcha"], #hcaptcha'
        )
        if hcaptcha_elements:
            for elem in hcaptcha_elements:
                if elem.is_displayed():
                    log_warning("Detected: hCaptcha (visible challenge)")
                    return "hcaptcha", True
    except Exception:
        pass

    # Generic bot detection phrases - only if they appear prominently (not in comments/footer)
    # Check for these in the main content area, not just anywhere
    main_content_indicators = [
        "are you a robot",
        "verify you are human",
        "access denied",
        "unusual traffic from your computer",
    ]

    # Only detect if we see these AND the page is clearly a challenge page (no tables, no stats content)
    for phrase in main_content_indicators:
        if phrase in page_lower:
            # Double-check: if page has stats content, ignore this
            if not is_page_ready(driver, page_source):
                log_warning(f"Detected: Generic bot protection ('{phrase}')")
                return "generic", True

    # Don't check for Ray ID alone - it can be present even after passing the challenge
    # Only use it as a secondary indicator if we already detected other issues

    return None, False


def wait_for_user_captcha_solve(
    driver, protection_type, timeout=300, force_on_url_change=False
):
    """Wait for user to manually solve CAPTCHA.

    Args:
        driver: Selenium WebDriver instance
        protection_type: Type of protection detected
        timeout: Maximum time to wait in seconds (default: 5 minutes)
        force_on_url_change: If True, continue when URL changes after manual captcha solve even if markers remain

    Returns:
        bool: True if page changed (likely solved), False if timeout
    """
    log_warning(f"\n{'='*60}")
    log_warning(f"MANUAL INTERVENTION REQUIRED")
    log_warning(f"{'='*60}")
    log_warning(f"Protection type: {protection_type}")
    log_warning(f"Please solve the CAPTCHA/challenge in the browser window.")
    log_warning(f"You have {timeout} seconds to complete it.")
    log_warning(f"The script will automatically continue once solved.")
    log_warning(f"{'='*60}\n")

    initial_url = driver.current_url
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            # Get fresh page source
            current_source = driver.page_source

            # 1) First priority: Check if page is actually ready (has content we want)
            if is_page_ready(driver, current_source):
                log_ok(
                    "Page is ready for scraping (detected expected content). Continuing..."
                )
                return True

            # 2) Check if protection is still actively blocking (not just residual markers)
            _, still_detected = detect_anti_bot_protection(driver, current_source)
            if not still_detected:
                # Protection not detected, but double-check page is ready
                if is_page_ready(driver, current_source):
                    log_ok("Protection cleared and page is ready. Continuing...")
                    return True
                else:
                    # Protection cleared but page not ready yet - wait a bit more
                    log_info("Protection cleared, waiting for page content to load...")
                    time.sleep(3)
                    continue

            # 3) URL change sometimes indicates navigation after solve
            if driver.current_url != initial_url:
                # URL changed - check if page is ready now
                time.sleep(2)  # Give page a moment to load
                if is_page_ready(driver, driver.page_source):
                    log_ok(
                        "Page navigation detected and content is ready. Continuing..."
                    )
                    return True
                elif force_on_url_change:
                    log_ok(
                        "Page navigation detected and --force-continue-after-solve enabled. Continuing..."
                    )
                    return True

            time.sleep(2)  # Check every 2 seconds

        except Exception as e:
            log_warning(f"Error while waiting: {e}")
            time.sleep(2)

    log_error(f"Timeout reached ({timeout}s). CAPTCHA not solved.")
    return False


# Global driver instance for decorator cleanup
_current_driver = None


def close_driver():
    """Cleanup function for resilient_scraper."""
    global _current_driver
    if _current_driver:
        try:
            log_info("Decorator: Closing browser...")
            _current_driver.quit()
        except Exception as e:
            log_error(f"Decorator: Error closing browser: {e}")
        _current_driver = None


def setup_driver(headless=False):
    """Set up and configure Chrome WebDriver with anti-detection measures.

    Args:
        headless: Whether to run in headless mode (not recommended for CAPTCHAs)

    Returns:
        WebDriver instance
    """
    log_info("Setting up Chrome WebDriver...")

    options = Options()

    # Anti-detection measures
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Realistic browser settings
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")

    # User agent - use fake-useragent if available, otherwise fallback to static
    if FAKE_USERAGENT_AVAILABLE:
        try:
            ua = fake_useragent.UserAgent()
            user_agent = ua.random
            log_info(f"Using dynamic User-Agent: {user_agent[:50]}...")
        except Exception:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            log_warning("Failed to generate dynamic User-Agent, using fallback")
    else:
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        log_info("fake-useragent not available, using static User-Agent")

    options.add_argument(f"user-agent={user_agent}")

    # Language
    options.add_argument("--lang=es-AR")

    if headless:
        options.add_argument("--headless=new")
        log_warning("Running in headless mode - CAPTCHA solving will not be possible!")

    try:
        # Try using webdriver-manager first (automatic driver installation)
        if WEBDRIVER_MANAGER_AVAILABLE:
            log_info(
                "Using webdriver-manager for automatic ChromeDriver installation..."
            )
            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            log_warning("webdriver-manager not available, using system ChromeDriver...")
            log_info(
                "To enable automatic driver management: pip install webdriver-manager"
            )
            driver = webdriver.Chrome(options=options)

        # Remove webdriver property (anti-detection)
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

        log_ok("WebDriver initialized successfully")
        return driver

    except WebDriverException as e:
        error_msg = str(e)

        if "ChromeDriver only supports Chrome version" in error_msg:
            log_error("ChromeDriver version mismatch!")
            log_error(error_msg)
            log_info("\nTo fix this issue:")
            log_info("1. Install webdriver-manager: pip install webdriver-manager")
            log_info("2. Re-run this script (it will auto-download the correct driver)")
            log_info("\nAlternatively:")
            log_info("1. Check your Chrome version: chrome://version")
            log_info("2. Download matching ChromeDriver from:")
            log_info("   https://googlechromelabs.github.io/chrome-for-testing/")
            log_info("3. Add to PATH or place in script directory")
        else:
            log_error(f"Failed to initialize WebDriver: {e}")
            log_info("\nTroubleshooting steps:")
            log_info("1. Make sure Chrome browser is installed")
            log_info("2. Install webdriver-manager: pip install webdriver-manager")
            log_info(
                "3. Or manually download ChromeDriver matching your Chrome version"
            )

        raise


def fetch_page_with_selenium(
    url, headless=False, page_timeout=60, force_continue_after_solve=False
):
    """Placeholder for the real implementation to be wrapped by the decorator."""
    return _fetch_page_with_selenium_impl(
        url, headless, page_timeout, force_continue_after_solve
    )


def _fetch_page_with_selenium_impl(
    url, headless=False, page_timeout=60, force_continue_after_solve=False
):
    """Internal implementation of page fetching."""
    global _current_driver
    _current_driver = setup_driver(headless=headless)
    driver = _current_driver

    try:
        log_info(f"Navigating to: {url}")
        driver.set_page_load_timeout(page_timeout)
        driver.get(url)

        # Explicit wait for page to be ready (better than fixed sleep)
        try:
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            log_info("Page loaded and ready")
        except TimeoutException:
            log_warning("Page load may not be complete, continuing anyway")

        # Get initial page source
        page_source = driver.page_source

        # CAPTCHA Detection
        if detect_captcha_in_content(page_source):
            log_warning("CAPTCHA detected in initial page source")
            # If not headless, we might want to try to solve it instead of just raising
            if headless:
                raise CaptchaDetectedException("CAPTCHA detected in headless mode")

        # First check: Is the page already ready? (no protection needed)
        if is_page_ready(driver, page_source):
            log_ok("Page loaded successfully and is ready for scraping")
        else:
            # Check for anti-bot protection
            protection_type, detected = detect_anti_bot_protection(driver, page_source)

            if detected:
                if headless:
                    log_error("Anti-bot protection detected in headless mode!")
                    log_error("Re-run without --headless to solve CAPTCHAs manually.")
                    if _current_driver:
                        _current_driver.quit()
                        _current_driver = None
                    return None, None

                # Wait for user to solve CAPTCHA (may force on URL change)
                solved = wait_for_user_captcha_solve(
                    driver,
                    protection_type,
                    timeout=300,
                    force_on_url_change=force_continue_after_solve,
                )

                if not solved:
                    log_error("Could not bypass protection")
                    if _current_driver:
                        _current_driver.quit()
                        _current_driver = None
                    return None, None

                # After solve, verify page is ready (wait_for_user_captcha_solve should have confirmed this)
                # But do a final check to be sure
                time.sleep(2)
                page_source = driver.page_source
                if not is_page_ready(driver, page_source):
                    log_warning(
                        "Page may not be fully ready after CAPTCHA solve, but continuing..."
                    )
                else:
                    log_ok("Page confirmed ready after CAPTCHA solve")

        # Final verification: Ensure page is ready before proceeding
        if not is_page_ready(driver, page_source):
            log_warning(
                "Page may not have expected content, but attempting to proceed..."
            )
            # Check again for captcha
            if detect_captcha_in_content(page_source):
                raise CaptchaDetectedException(
                    "CAPTCHA detected after manual solve/navigation"
                )

        # Wait for tables to load (with timeout)
        try:
            log_info("Waiting for tables to load...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            log_ok("Tables detected on page")
        except TimeoutException:
            log_warning("No tables found within timeout period")

        # Final page source
        page_source = driver.page_source
        log_ok("Page fetched successfully")

        return page_source, driver

    except CaptchaDetectedException:
        if _current_driver:
            _current_driver.quit()
            _current_driver = None
        raise
    except TimeoutException:
        log_error(f"Page load timeout ({page_timeout}s)")
        if _current_driver:
            _current_driver.quit()
            _current_driver = None
        return None, None

    except Exception as e:
        log_error(f"Error fetching page: {e}")
        if _current_driver:
            _current_driver.quit()
            _current_driver = None
        return None, None


# Wrap the implementation with the resilient decorator
# Note: Since driver is returned, we need to be careful with resource_cleanup
# If it fails, the decorator calls resource_cleanup.
@resilient_scraper(
    max_retries=3, backoff_factor=2, timeout=60, fallback_source="footystats"
)
def fetch_page_with_selenium(
    url, headless=False, page_timeout=60, force_continue_after_solve=False
):
    return _fetch_page_with_selenium_impl(
        url, headless, page_timeout, force_continue_after_solve
    )


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


def normalize_team_name(name):
    """Normalize team names for consistent merging (matches main.py logic)."""
    return (
        str(name).strip().upper().replace(".", "").replace("-", " ").replace("  ", " ")
    )


def extract_tables_from_html(html_content):
    """Extract all tables from HTML content.

    Returns a list of pandas DataFrames, one for each table found.
    """
    # Use pd.read_html on entire HTML at once (more efficient than per-table)
    try:
        all_tables = pd.read_html(html_content)
        dataframes = []

        for df in all_tables:
            try:
                # Clean column names
                df.columns = [clean_team_name(str(col)) for col in df.columns]
                dataframes.append(df)
            except Exception as e:
                log_info(f"Skipping table due to column cleaning error: {e}")
                continue

        log_info(f"Extracted {len(dataframes)} tables using consolidated read_html")
        return dataframes

    except Exception as e:
        log_info(f"pd.read_html failed, falling back to BeautifulSoup: {e}")
        # Fallback to original BeautifulSoup approach
        soup = BeautifulSoup(html_content, "lxml")
        tables = soup.find_all("table")

        dataframes = []
        for table in tables:
            try:
                df = pd.read_html(StringIO(str(table)), header=0)[0]
                df.columns = [clean_team_name(str(col)) for col in df.columns]
                dataframes.append(df)
            except Exception as te:
                log_info(f"Skipping table due to parsing error: {te}")
                continue

        return dataframes


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
                1
                for v in sample_values
                if not str(v).replace(".", "").replace("-", "").isdigit()
            ) / len(sample_values)
            if text_ratio > 0.6:
                return first_col

    return None


def clean_dataframe(df, squad_column=None):
    """Clean and prepare dataframe for ML_Predictor compatibility."""
    df = df.copy()

    # Remove duplicate header rows (rows where ALL values match column names)
    # This is different from checking if a value contains header keywords
    if len(df) > 0:
        first_col = df.iloc[:, 0]
        # Only consider it a duplicate header if the value EXACTLY matches the column name
        # (not just contains keywords like 'Club')
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


def save_table(df, output_dir="src/", prefix="results", table_index=0):
    """Save dataframe as CSV with timestamp-based filename."""
    os.makedirs(output_dir, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    filename = f"{prefix}{today}_{table_index}.csv"
    filepath = os.path.join(output_dir, filename)

    df.to_csv(filepath, index=False, encoding="utf-8")
    log_ok(f"Table saved to: {filepath}")
    log_info(f"Table shape: {df.shape[0]} rows x {df.shape[1]} columns")

    return filepath


def main():
    """Main function to scrape tables from FBref Liga Argentina stats page."""
    # Create backup first
    backup_original_script()

    # Fixed configuration
    url = "https://fbref.com/en/comps/21/Liga-Profesional-Argentina-Stats"
    output_dir = "src/"
    table_index = 0
    headless = False
    page_timeout = 60
    force_continue_after_solve = False

    # Parse command line arguments
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--table-index" and i + 1 < len(sys.argv):
            table_index = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--headless":
            headless = True
            i += 1
        elif sys.argv[i] == "--timeout" and i + 1 < len(sys.argv):
            page_timeout = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--force-continue-after-solve":
            force_continue_after_solve = True
            i += 1
        elif sys.argv[i] in ["-h", "--help"]:
            print(__doc__)
            print("\nOptional arguments:")
            print(
                "  --table-index N    Save table index N (default: 0 = first stats table)"
            )
            print("                    Use -1 to save all tables with Squad columns")
            print("                    Use N > 0 to save specific table by HTML index")
            print("  --headless         Run browser in headless mode (no GUI)")
            print("                    WARNING: Cannot solve CAPTCHAs in headless mode")
            print("  --timeout N        Page load timeout in seconds (default: 60)")
            print("  --force-continue-after-solve")
            print(
                "                    Continue when URL changes after manual captcha solve even if markers remain"
            )
            print("\nFixed settings:")
            print(f"  URL: {url}")
            print(f"  Output directory: {output_dir}")
            print("\nAnti-bot protections handled:")
            print("  - Cloudflare DDoS Protection")
            print("  - Cloudflare Turnstile")
            print("  - reCAPTCHA (Google)")
            print("  - hCaptcha")
            print("  - Generic bot verification")
            sys.exit(0)
        else:
            log_error(f"Unknown argument: {sys.argv[i]}")
            log_info("Use --help for usage information")
            sys.exit(1)

    log_info(f"Fetching page: {url}")
    log_info(f"Headless mode: {headless}")
    log_info(f"Page timeout: {page_timeout}s")
    log_info(f"Force continue after solve: {force_continue_after_solve}")

    driver = None
    try:
        # Fetch page with Selenium (pass the force flag so wait routine can use it)
        page_source, driver = fetch_page_with_selenium(
            url,
            headless=headless,
            page_timeout=page_timeout,
            force_continue_after_solve=force_continue_after_solve,
        )

        if page_source is None:
            log_error("Failed to fetch page")
            sys.exit(1)

        # Extract tables
        log_info("Extracting tables from page...")
        tables = extract_tables_from_html(page_source)

        if not tables:
            log_error("No tables found on the page")
            sys.exit(1)

        log_info(f"Found {len(tables)} table(s)")

        # Process and save tables
        saved_count = 0
        stats_table_count = 0
        for idx, df in enumerate(tables):
            log_info(f"\nProcessing table {idx + 1}/{len(tables)}...")

            if df.empty or len(df) == 0:
                log_info("Skipping empty table (empty)")
                continue

            df_cleaned = clean_dataframe(df)

            if df_cleaned.empty or len(df_cleaned) == 0:
                log_info("Skipping table (empty after cleaning)")
                continue

            # Check if this table has a Squad column (indicates it's a stats table)
            has_squad = "Squad" in df_cleaned.columns
            if not has_squad:
                log_info(f"Skipping table {idx} (no Squad column)")
                continue

            log_info("Sample of extracted data:")
            print(df_cleaned.head())

            # Determine prefix based on columns
            table_cols = [str(col).upper() for col in df_cleaned.columns]
            is_main_table = (
                any("MP" in col or "MATCHES PLAYED" in col for col in table_cols)
                and any("GF" in col or "GOALS FOR" in col for col in table_cols)
                and any("GA" in col or "GOALS AGAINST" in col for col in table_cols)
            )

            prefix = "results" if is_main_table else "stats"

            # When --table-index is specified (not -1), only save that specific table
            # When --table-index is -1, save all stats tables
            # Default (--table-index 0) now means save the first valid stats table
            if table_index == -1:
                # Save all stats tables
                save_table(
                    df_cleaned, output_dir, prefix=prefix, table_index=stats_table_count
                )
                saved_count += 1
                stats_table_count += 1
            elif table_index == 0 and stats_table_count == 0:
                # Save only the first stats table when default index is used
                save_table(
                    df_cleaned, output_dir, prefix=prefix, table_index=stats_table_count
                )
                saved_count += 1
                stats_table_count += 1
            elif table_index > 0 and idx == table_index:
                # Save specific table index from HTML
                save_table(
                    df_cleaned, output_dir, prefix=prefix, table_index=stats_table_count
                )
                saved_count += 1
                stats_table_count += 1
            else:
                log_info(
                    f"Skipping table {idx} (index mismatch with --table-index {table_index})"
                )

        log_info(f"\nTotal tables saved: {saved_count}")
        log_ok("Scraping completed successfully")

    except Exception as e:
        log_error(f"Error during scraping: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Log health report
        monitor = get_health_monitor()
        log_info(monitor.generate_report())

        if driver is not None:
            try:
                driver.quit()
                log_info("Browser closed")
            except Exception as e:
                log_warning(f"Error closing browser: {e}")


if __name__ == "__main__":
    main()
