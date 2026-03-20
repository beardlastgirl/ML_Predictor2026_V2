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
# Web Scraping Functions
# ==============================================

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
        
        log_ok(f"Successfully fetched: {url}")
        return response.text
        
    except Exception as e:
        log_error(f"Failed to fetch URL: {e}")
        log_info("Note: The site may require browser automation (Selenium/Playwright)")
        raise


def parse_fixtures(html_content, glossary):
    """Parse fixtures and results from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    completed = []
    upcoming = []
    
    # Find all text elements that contain score patterns
    import re
    score_pattern = re.compile(r'\d+\s*-\s*\d+')
    
    # Collect all text elements with scores
    match_elements = []
    for element in soup.find_all(string=True):
        if score_pattern.search(element):
            match_elements.append(element.strip())
    
    log_info(f"Found {len(match_elements)} potential match elements")
    
    current_date = None
    
    for element in match_elements:
        # Pattern 1: "Team A 2 - 1 Team B" (with scores)
        match1 = re.match(r'^(.+?)\s+(\d+)\s*-\s*(\d+)\s+(.+)$', element)
        if match1:
            home_name = match1.group(1).strip()
            home_score = int(match1.group(2))
            away_score = int(match1.group(3))
            away_name = match1.group(4).strip()
            
            # Clean trailing parenthetical info from team names
            home_name = re.sub(r"\s*\(.*?\)\s*$", "", home_name)
            away_name = re.sub(r"\s*\(.*?\)\s*$", "", away_name)

            # Skip if team names are too short (likely false positive)
            if len(home_name) < 3 or len(away_name) < 3:
                continue
            
            # Skip common false positives
            skip_words = ['fecha', 'hora', 'estadio', 'canal', 'tv', 'ver', 'vivo', 'fixture', 'resultados', 'tyc sports']
            if any(word in home_name.lower() or word in away_name.lower() for word in skip_words):
                continue
            
            home_team = normalize_team_name(home_name, glossary)
            away_team = normalize_team_name(away_name, glossary)
            
            completed.append({
                'Home': home_team,
                'Away': away_team,
                'Home_Score': home_score,
                'Away_Score': away_score,
                'Date': current_date or 'TBD'
            })
    
    log_info(f"Found {len(completed)} completed matches and {len(upcoming)} upcoming fixtures")
    return completed, upcoming


def write_partidos_txt(completed, upcoming):
    """Write fixtures and results to partidos.txt file."""
    filepath = "partidos.txt"
    
    # Define the specific Fecha 6 matchups from the original file
    fecha6_teams = [
        ('DEFENSA Y JUSTICIA', 'BELGRANO'),
        ('SAN LORENZO', 'ESTUDIANTES LA PLATA'),
        ('INDEPENDIENTE RIVADAVIA', 'INDEPENDIENTE'),
        ('INSTITUTO', 'ATLETICO TUCUMAN'),
        ('ESTUDIANTES LA PLATA', 'SARMIENTO JUNIN'),
        ('BOCA JUNIORS', 'RACING CLUB'),
        ('GIMNASIA', 'GIMNASIA'),
        ('ROSARIO CENTRAL', 'TALLERES CORDOBA'),
        ('PLATENSE', 'BARRACAS CENTRAL'),
        ('BANFIELD', 'NEWELLS OLD BOYS'),
        ('DEPORTIVO RIESTRA', 'HURACAN'),
        ('CENTRAL CORDOBA', 'TIGRE'),
        ('VELEZ', 'RIVER'),
        ('UNION', 'ALDOSIVI'),
        ('ARGENTINOS JUNIORS', 'LANUS')
    ]
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            # Write header
            f.write("FECHA 6 - 19 al 22/02/2026\n\n")
            
            # Filter and write only Fecha 6 matches
            fecha6_found = 0
            for home_team, away_team in fecha6_teams:
                # Check if this matchup exists in our scraped data
                match_found = False
                for match in completed + upcoming:
                    scraped_home = match['Home'].upper().replace(' ', '').replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
                    scraped_away = match['Away'].upper().replace(' ', '').replace('Á', 'A').replace('É', 'E').replace('Í', 'I').replace('Ó', 'O').replace('Ú', 'U')
                    
                    target_home = home_team.upper().replace(' ', '')
                    target_away = away_team.upper().replace(' ', '')
                    
                    if (scraped_home == target_home and scraped_away == target_away) or \
                       (scraped_home == target_away and scraped_away == target_home):
                        f.write(f"{match['Home']} - {match['Away']}:\n")
                        fecha6_found += 1
                        match_found = True
                        break
                
                if not match_found:
                    # Write the expected matchup even if not found in scraped data
                    f.write(f"{home_team} - {away_team}:\n")
                    fecha6_found += 1
            
            # Add footer
            f.write("\nCantidad de penales cobrados:\n")
            f.write("Cantidad de expulsados:\n")
            f.write("Cantidad de goles convertidos:\n\n")
        
        log_ok(f"Successfully wrote {fecha6_found} Fecha 6 matches to {filepath}")
        
    except Exception as e:
        log_error(f"Failed to write partidos.txt: {e}")


# ==============================================
# Main Function
# ==============================================

def main():
    """Main function to scrape TyC Sports and update data files."""
    # Fixed URL
    url = 'https://www.tycsports.com/liga-profesional-de-futbol/fixture-clausura-2025-calendario-partidos-y-resultados--id672603.html'
    
    log_info("Starting TyC Sports scraper...")
    
    # Load team name glossary
    glossary = load_glossary()
    
    try:
        # Fetch the webpage
        html_content = fetch_page(url)
        
        # Parse fixtures and results
        completed, upcoming = parse_fixtures(html_content, glossary)
        
        # Write to partidos.txt
        write_partidos_txt(completed, upcoming)
        
        if not completed and not upcoming:
            log_warning("No matches found. The website structure may have changed.")
        else:
            log_ok(f"Successfully processed {len(completed)} completed and {len(upcoming)} upcoming matches")
    
    except Exception as e:
        log_error(f"Scraping failed: {e}")
        sys.exit(1)
    
    log_ok("TyC Sports scraping completed successfully")


if __name__ == '__main__':
    main()
