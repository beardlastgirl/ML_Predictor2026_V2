#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TyC Sports scraper for Liga Profesional Argentina fixtures and results.

This script scrapes fixture and result data from TyC Sports website
and processes it for the ML predictor system.
"""

import sys
import os
import re
import json
import time
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.data_processing import normalize_team_name, load_glossary
from src.utils import log_info, log_ok, log_error, log_warning
from src.scraper_utils import resilient_scraper, CaptchaDetectedException, detect_captcha_in_content, get_health_monitor


# ==============================================
# Logging Utilities
# ==============================================

# Use imported logging utilities from src.utils


# ==============================================
# Web Scraping Functions
# ==============================================

@resilient_scraper(max_retries=3, backoff_factor=2, timeout=30)
def fetch_page(url):
    """Fetch a web page and return its HTML content."""
    try:
        session = requests.Session()
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        html_content = response.text
        
        # CAPTCHA Detection
        if detect_captcha_in_content(html_content):
            raise CaptchaDetectedException("CAPTCHA detected on TyC Sports")
            
        log_ok(f"Successfully fetched: {url}")
        return html_content
        
    except CaptchaDetectedException:
        raise
    except Exception as e:
        log_error(f"Failed to fetch URL: {e}")
        log_info("Note: The site may require browser automation (Selenium/Playwright)")
        raise


def parse_fixtures(html_content, glossary):
    """Parse fixtures and results from HTML content.
    
    NOTE: TyC Sports HTML structure changes frequently. This parser attempts
    to extract match data but may fail if the site structure changes.
    If scraping fails, manually update Partidos.txt with fixture data.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    completed = []
    upcoming = []
    
    # Strategy: Look for common fixture/result patterns in the HTML
    # Pattern 1: Match containers with team names and scores
    match_containers = soup.find_all(['div', 'article', 'section'], class_=re.compile(r'(match|partido|fixture|result)', re.I))
    
    if match_containers:
        log_info(f"Found {len(match_containers)} potential match containers")
        for container in match_containers:
            text = container.get_text(separator=' ', strip=True)
            # Look for score pattern: "Team A 2 - 1 Team B"
            score_match = re.search(r'(.+?)\s+(\d+)\s*[-:]\s*(\d+)\s+(.+)', text)
            if score_match:
                home_name = score_match.group(1).strip()
                home_score = int(score_match.group(2))
                away_score = int(score_match.group(3))
                away_name = score_match.group(4).strip()
                
                # Clean team names
                home_name = re.sub(r"\s*\(.*?\)\s*$", "", home_name)
                away_name = re.sub(r"\s*\(.*?\)\s*$", "", away_name)
                
                if len(home_name) >= 3 and len(away_name) >= 3:
                    home_team = normalize_team_name(home_name, glossary)
                    away_team = normalize_team_name(away_name, glossary)
                    completed.append({
                        'Home': home_team,
                        'Away': away_team,
                        'Home_Score': home_score,
                        'Away_Score': away_score,
                        'Date': 'TBD'
                    })
    
    # Fallback: Parse all text for score patterns (less reliable)
    if not completed:
        log_warning("No match containers found, falling back to text search")
        score_pattern = re.compile(r'(.+?)\s+(\d+)\s*[-:]\s*(\d+)\s+(.+)')
        for element in soup.find_all(string=True):
            match = score_pattern.search(element)
            if match:
                home_name = match.group(1).strip()
                home_score = int(match.group(2))
                away_score = int(match.group(3))
                away_name = match.group(4).strip()
                
                # Skip common false positives
                skip_words = ['fecha', 'hora', 'estadio', 'canal', 'tv', 'ver', 'vivo', 'fixture', 'resultados', 'tyc sports']
                if any(word in home_name.lower() or word in away_name.lower() for word in skip_words):
                    continue
                
                if len(home_name) >= 3 and len(away_name) >= 3:
                    home_team = normalize_team_name(home_name, glossary)
                    away_team = normalize_team_name(away_name, glossary)
                    completed.append({
                        'Home': home_team,
                        'Away': away_team,
                        'Home_Score': home_score,
                        'Away_Score': away_score,
                        'Date': 'TBD'
                    })
    
    log_info(f"Parsed {len(completed)} completed matches and {len(upcoming)} upcoming fixtures")
    return completed, upcoming


def write_partidos_txt(completed, upcoming, fecha_label=None):
    """Write fixtures and results to Partidos.txt file.
    
    Args:
        completed: List of completed match dicts with Home/Away/scores
        upcoming: List of upcoming fixture dicts with Home/Away
        fecha_label: Optional header string e.g. "FECHA 10 - 05 al 08/05/2026"
                     If None, uses today's date as fallback.
    """
    filepath = "Partidos.txt"
    all_matches = completed + upcoming
    
    if not all_matches:
        log_warning("No matches to write to Partidos.txt")
        return
    
    if fecha_label is None:
        fecha_label = f"FECHA XX - {datetime.now().strftime('%d/%m/%Y')}"
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"{fecha_label}\n\n")
            
            for match in all_matches:
                home = match.get('Home', '')
                away = match.get('Away', '')
                if home and away:
                    f.write(f"{home} - {away}:\n")
            
            f.write("\nCantidad de penales cobrados:\n")
            f.write("Cantidad de expulsados:\n")
            f.write("Cantidad de goles convertidos:\n")
        
        log_ok(f"Wrote {len(all_matches)} matches to {filepath}")
        
    except Exception as e:
        log_error(f"Failed to write Partidos.txt: {e}")


# ==============================================
# Main Function
# ==============================================

def main():
    """Main function to scrape TyC Sports and update data files.
    
    Usage:
        python scrape_tyc.py
        python scrape_tyc.py --url "https://www.tycsports.com/..." --fecha "FECHA 10 - 05 al 08/05/2026"
    
    If no URL is provided, you will be prompted to enter one.
    The URL should point to the current season's fixture/results page on TyC Sports.
    """
    import argparse
    parser = argparse.ArgumentParser(description="Scrape TyC Sports fixtures")
    parser.add_argument("--url", type=str, default=None, help="TyC Sports fixture page URL")
    parser.add_argument("--fecha", type=str, default=None, help='Fecha label e.g. "FECHA 10 - 05 al 08/05/2026"')
    args = parser.parse_args()
    
    url = args.url
    if not url:
        print("[INFO] No URL provided.")
        print("[INFO] Find the current season fixture page at: https://www.tycsports.com/liga-profesional")
        url = input("Enter TyC Sports fixture URL (or press Enter to skip scraping): ").strip()
        if not url:
            log_warning("No URL provided. Skipping scrape. Update Partidos.txt manually.")
            return
    
    log_info("Starting TyC Sports scraper...")
    glossary = load_glossary()
    
    try:
        html_content = fetch_page(url)
        completed, upcoming = parse_fixtures(html_content, glossary)
        write_partidos_txt(completed, upcoming, fecha_label=args.fecha)
        
        if not completed and not upcoming:
            log_warning("No matches found. The website structure may have changed.")
            log_warning("Update Partidos.txt manually with the current fixture list.")
        else:
            log_ok(f"Processed {len(completed)} completed and {len(upcoming)} upcoming matches")
    
    except Exception as e:
        log_error(f"Scraping failed: {e}")
        log_warning("Update Partidos.txt manually with the current fixture list.")
    
    finally:
        monitor = get_health_monitor()
        log_info(monitor.generate_report())
    
    log_ok("TyC Sports scraping completed")


if __name__ == '__main__':
    main()
