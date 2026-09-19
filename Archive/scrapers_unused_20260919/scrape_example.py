import os
import time
import pandas as pd
from datetime import datetime
from io import StringIO
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from src.scraper_utils import resilient_scraper, CaptchaDetectedException, detect_captcha_in_content, get_health_monitor
from src.utils import log_error, log_info, log_ok, log_warning

# --- Configuration ---
EXAMPLE_URL = "http://quotes.toscrape.com/" # A simple, public site for demonstration
OUTPUT_DIR = "data/" # Directory to save scraped data

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

@resilient_scraper(max_retries=3, backoff_factor=2, timeout=60, resource_cleanup=close_browser)
def scrape_example_data(headless=True, output_dir=OUTPUT_DIR):
    """
    Scrape example data from a public website using Playwright.
    """
    log_info(f"Starting example scraper for: {EXAMPLE_URL}")
    global _browser

    with sync_playwright() as p:
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

            log_info("Navigating to example site...")
            page.set_viewport_size({"width": 1920, "height": 1080})
            page.goto(EXAMPLE_URL, wait_until="domcontentloaded", timeout=60000)
            
            # Wait for content
            time.sleep(5) 

            html = page.content()
            
            # CAPTCHA Detection (demonstrative, unlikely on quotes.toscrape.com)
            if detect_captcha_in_content(html):
                raise CaptchaDetectedException("CAPTCHA detected on example site")
                
            log_ok(f"Retrieved {len(html)} characters of HTML.")

            soup = BeautifulSoup(html, "lxml")
            
            # --- Extracting data ---
            quotes_data = []
            quotes = soup.find_all("div", class_="quote")
            for quote in quotes:
                text = quote.find("span", class_="text").get_text(strip=True)
                author = quote.find("small", class_="author").get_text(strip=True)
                tags = [tag.get_text(strip=True) for tag in quote.find_all("a", class_="tag")]
                quotes_data.append({"Quote": text, "Author": author, "Tags": ", ".join(tags)})

            df = pd.DataFrame(quotes_data)

            if df.empty:
                log_warning("No data was scraped.")
                return False

            os.makedirs(output_dir, exist_ok=True)
            today = datetime.now().strftime("%Y%m%d")
            filename = f"example_quotes_{today}.csv"
            filepath = os.path.join(output_dir, filename)

            df.to_csv(filepath, index=False, encoding="utf-8")
            log_ok(f"Saved example data: {filepath} ({len(df)} rows)")
            return True

        finally:
            if _browser:
                _browser.close()
                _browser = None

# --- CLI Entry Point ---
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape example data from a public website.")
    parser.add_argument(
        "--headless", action="store_true", default=True, help="Run in headless mode"
    )
    parser.add_argument(
        "--output-dir", default=OUTPUT_DIR, help="Directory to save CSV files"
    )

    args = parser.parse_args()
    try:
        scrape_example_data(headless=args.headless, output_dir=args.output_dir)
    except Exception as e:
        log_error(f"Example scraper failed: {e}")
    finally:
        monitor = get_health_monitor()
        log_info(monitor.generate_report())
