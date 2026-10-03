"""
parse_reporte_pdfs.py - Extract match results from PDF reports

Purpose:
- Parse PDF files from Reporte/{year}/ folder (format: Resumen F{round}.pdf)
- Extract "Resultados de la fecha" table from pages 5-6
- Parse match results and optionally append to data/ARG.csv

Inputs:
- Reporte/{year}/Resumen F{round}.pdf files
- Glossary.txt for team name normalization

Outputs:
- Console logs showing extracted matches
- Optionally appends to data/ARG.csv (if --update-history flag is used)
"""

import os
import re
import glob
import argparse
from datetime import datetime
import pandas as pd

try:
    import pdfplumber
except ImportError:
    print("[ERROR] pdfplumber not installed. Install with: pip install pdfplumber")
    exit(1)

# Use centralized logging from src
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import log_info, log_ok, log_error, log_warning


def load_glossary(filepath='Glossary.txt'):
    """Load team name mappings from Glossary.txt."""
    glossary = {}
    
    if not os.path.exists(filepath):
        log_warning(f"Glossary file not found: {filepath}")
        return glossary
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Support formats: "Source -> Target", "Source = Target", "Source : Target"
            for sep in ['->', '=', ':']:
                if sep in line:
                    parts = line.split(sep, 1)
                    if len(parts) == 2:
                        source = parts[0].strip().upper()
                        target = parts[1].strip().upper()
                        glossary[source] = target
                        break
    
    log_info(f"Loaded {len(glossary)} team name mappings from glossary")
    return glossary


def normalize_team_name(name, glossary):
    """Normalize team name using glossary, with fallback."""
    if not name:
        return name
    
    name_upper = name.strip().upper()
    
    # Check glossary first
    if name_upper in glossary:
        return glossary[name_upper]
    
    # Try partial matches (for variations like "Gimnasia (Mza.)" -> "GIMNASIA LA PLATA")
    for key, value in glossary.items():
        if key in name_upper or name_upper in key:
            return value
    
    # Return uppercase version if no match found
    return name_upper


def parse_date_range(date_str):
    """
    Parse date range from header like "FECHA 1 - 22 AL 25/01/2026"
    Returns the end date (most recent date) as DD/MM/YYYY
    """
    # Extract the date part: "25/01/2026"
    date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
    if date_match:
        day, month, year = date_match.groups()
        return f"{day.zfill(2)}/{month.zfill(2)}/{year}"
    
    # Fallback: try to extract just the date without "AL"
    date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', date_str)
    if date_match:
        day, month, year = date_match.groups()
        return f"{day.zfill(2)}/{month.zfill(2)}/{year}"
    
    return None


def parse_match_line(line, glossary):
    """
    Parse a match line like: "Central Córdoba - Unión 1 - 0 / 0 / 0 / L"
    Returns dict with Date, Home, Away, HG, AG, Res or None if invalid
    """
    line = line.strip()
    if not line:
        return None
    
    # Skip summary lines
    if any(keyword in line.lower() for keyword in ['cantidad', 'total', 'resumen', 'fecha']):
        return None
    
    # Pattern: "Home Team - Away Team Score1 - Score2 / Pn / Ex / LEV"
    # Extract the score and result parts first
    match_parts = re.split(r'\s*/\s*', line)
    if len(match_parts) < 4:
        return None
    
    # Last part should be L/E/V
    result_code = match_parts[-1].strip().upper()
    if result_code not in ['L', 'E', 'V']:
        return None
    
    # Extract scores from first part: "Home Team - Away Team Score1 - Score2"
    first_part = match_parts[0].strip()
    
    # Find score pattern: "1 - 0" or "2-1"
    score_match = re.search(r'(\d+)\s*[-–]\s*(\d+)', first_part)
    if not score_match:
        return None
    
    home_score = int(score_match.group(1))
    away_score = int(score_match.group(2))
    
    # Remove score from first part to get team names
    team_part = re.sub(r'\d+\s*[-–]\s*\d+', '', first_part).strip()
    
    # Split teams by dash
    team_parts = re.split(r'\s*[-–]\s*', team_part)
    if len(team_parts) != 2:
        return None
    
    home_raw = team_parts[0].strip()
    away_raw = team_parts[1].strip()
    
    # Normalize team names
    home = normalize_team_name(home_raw, glossary)
    away = normalize_team_name(away_raw, glossary)
    
    # Convert result code: L=H (Home), E=D (Draw), V=A (Away)
    result_map = {'L': 'H', 'E': 'D', 'V': 'A'}
    result = result_map.get(result_code, 'D')
    
    return {
        'Home': home,
        'Away': away,
        'HG': home_score,
        'AG': away_score,
        'Res': result,
        'Home_Raw': home_raw,
        'Away_Raw': away_raw
    }


def extract_results_from_pdf(pdf_path, glossary):
    """
    Extract match results from a PDF report.
    Returns list of match dicts and the date string.
    """
    matches = []
    date_str = None
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            log_info(f"Processing PDF: {os.path.basename(pdf_path)} ({len(pdf.pages)} pages)")
            
            # Check pages 5 and 6 (index 4 and 5, 0-indexed)
            pages_to_check = [4, 5] if len(pdf.pages) > 5 else list(range(len(pdf.pages)))
            
            for page_idx in pages_to_check:
                if page_idx >= len(pdf.pages):
                    continue
                
                page = pdf.pages[page_idx]
                text = page.extract_text()
                
                if not text:
                    continue
                
                lines = text.split('\n')
                
                # Look for "Resultados de la fecha" header
                header_found = False
                for i, line in enumerate(lines):
                    if 'resultados de la fecha' in line.lower():
                        header_found = True
                        log_info(f"Found results table on page {page_idx + 1}")
                        
                        # Next line should be the date header: "FECHA 1 - 22 AL 25/01/2026 Score / Pn / Ex / LEV"
                        if i + 1 < len(lines):
                            date_header = lines[i + 1]
                            date_str = parse_date_range(date_header)
                            if date_str:
                                log_info(f"Extracted date: {date_str}")
                        
                        # Parse subsequent lines until we hit a summary or end
                        for j in range(i + 2, len(lines)):
                            match_line = lines[j].strip()
                            if not match_line:
                                continue
                            
                            # Stop if we hit summary lines
                            if any(keyword in match_line.lower() for keyword in ['cantidad de', 'total', 'pos', 'participante']):
                                break
                            
                            match_data = parse_match_line(match_line, glossary)
                            if match_data:
                                matches.append(match_data)
                        
                        break
                
                if header_found:
                    break
    
    except Exception as e:
        log_error(f"Error processing PDF {pdf_path}: {e}")
        return None, None
    
    return matches, date_str


def process_all_pdfs(reporte_dir, glossary, year=None, skip_parsed=True):
    """
    Process all PDF files in Reporte/{year}/ directory.
    Skips files that start with "Parsed_" if skip_parsed is True.
    Returns dict mapping round number to (matches, date, pdf_path) tuples.
    """
    if year is None:
        year = datetime.now().year
    
    pdf_dir = os.path.join(reporte_dir, str(year))
    if not os.path.exists(pdf_dir):
        log_error(f"Reporte directory not found: {pdf_dir}")
        return {}
    
    # Find all PDFs matching pattern "Resumen F{round}.pdf" (skip already parsed ones)
    pdf_pattern = os.path.join(pdf_dir, "Resumen F*.pdf")
    pdf_files = glob.glob(pdf_pattern)
    
    # Filter out already parsed files
    if skip_parsed:
        pdf_files = [f for f in pdf_files if not os.path.basename(f).startswith("Parsed_")]
    
    if not pdf_files:
        log_warning(f"No unprocessed PDF files found matching pattern: {pdf_pattern}")
        return {}
    
    log_info(f"Found {len(pdf_files)} unprocessed PDF files")
    
    results = {}
    for pdf_path in sorted(pdf_files):
        # Extract round number from filename
        filename = os.path.basename(pdf_path)
        round_match = re.search(r'F(\d+)', filename)
        if not round_match:
            log_warning(f"Could not extract round number from: {filename}")
            continue
        
        round_num = int(round_match.group(1))
        matches, date_str = extract_results_from_pdf(pdf_path, glossary)
        
        if matches:
            results[round_num] = (matches, date_str, pdf_path)
            log_ok(f"Round {round_num}: Extracted {len(matches)} matches (date: {date_str})")
        else:
            log_warning(f"Round {round_num}: No matches extracted")
    
    return results


def append_to_arg_csv(matches_with_dates, csv_path='data/ARG.csv'):
    """
    Append extracted matches to ARG.csv.
    Matches are added with the date from the PDF header.
    Returns list of PDF paths that were successfully processed.
    """
    if not matches_with_dates:
        log_warning("No matches to append")
        return []
    
    # Load existing CSV
    if os.path.exists(csv_path):
        try:
            df_existing = pd.read_csv(csv_path)
            log_info(f"Loaded existing ARG.csv with {len(df_existing)} rows")
        except Exception as e:
            log_error(f"Error reading existing CSV: {e}")
            return []
    else:
        log_warning(f"ARG.csv not found at {csv_path}, creating new file")
        df_existing = pd.DataFrame()
    
    # Prepare new rows
    new_rows = []
    processed_pdfs = []
    
    for round_num, match_data in sorted(matches_with_dates.items()):
        # Handle both old format (matches, date_str) and new format (matches, date_str, pdf_path)
        if len(match_data) == 3:
            matches, date_str, pdf_path = match_data
        else:
            matches, date_str = match_data
            pdf_path = None
        
        if not date_str:
            log_warning(f"Round {round_num}: No date available, skipping")
            continue
        
        round_has_new_matches = False
        for match in matches:
            # Format date as DD/MM/YYYY
            new_row = {
                'Date': date_str,
                'Home': match['Home'],
                'Away': match['Away'],
                'HG': match['HG'],
                'AG': match['AG'],
                'Res': match['Res']
            }
            
            # Check if this match already exists (avoid duplicates)
            if not df_existing.empty:
                existing = df_existing[
                    (df_existing['Date'] == date_str) &
                    (df_existing['Home'] == match['Home']) &
                    (df_existing['Away'] == match['Away'])
                ]
                if not existing.empty:
                    log_info(f"Skipping duplicate: {match['Home']} vs {match['Away']} on {date_str}")
                    continue
            
            new_rows.append(new_row)
            round_has_new_matches = True
        
        # Track PDFs that contributed new matches
        if round_has_new_matches and pdf_path:
            processed_pdfs.append(pdf_path)
    
    if not new_rows:
        log_info("No new matches to add (all duplicates)")
        return []
    
    # Create DataFrame for new rows
    df_new = pd.DataFrame(new_rows)
    
    # Ensure both DataFrames have the same columns before concatenation
    if df_existing.empty:
        # If existing is empty, use df_new as is
        df_combined = df_new.copy()
    else:
        # Preserve column order from existing CSV, add new columns at the end
        existing_cols = list(df_existing.columns)
        new_cols = [col for col in df_new.columns if col not in existing_cols]
        all_columns = existing_cols + new_cols
        
        # Ensure both DataFrames have the same columns (fill missing with None)
        df_existing_aligned = df_existing.reindex(columns=all_columns, fill_value=None)
        df_new_aligned = df_new.reindex(columns=all_columns, fill_value=None)
        
        # Append and save - use sort=False to preserve column order
        df_combined = pd.concat([df_existing_aligned, df_new_aligned], ignore_index=True, sort=False)
    
    # Sort by date
    df_combined['Date'] = pd.to_datetime(df_combined['Date'], dayfirst=True, errors='coerce')
    df_combined = df_combined.sort_values('Date')
    df_combined['Date'] = df_combined['Date'].dt.strftime('%d/%m/%Y')
    
    try:
        df_combined.to_csv(csv_path, index=False)
        log_ok(f"Appended {len(new_rows)} new matches to {csv_path}")
        log_info(f"Total rows in CSV: {len(df_combined)}")
    except Exception as e:
        log_error(f"Error writing to CSV: {e}")
        return []
    
    return processed_pdfs


def rename_processed_pdf(pdf_path):
    """
    Rename a PDF file to indicate it has been processed.
    Example: "Resumen F04.pdf" -> "Parsed_Resumen F04.pdf"
    """
    if not os.path.exists(pdf_path):
        log_warning(f"PDF file not found: {pdf_path}")
        return False
    
    directory = os.path.dirname(pdf_path)
    filename = os.path.basename(pdf_path)
    
    # Skip if already renamed
    if filename.startswith("Parsed_"):
        return True
    
    new_filename = f"Parsed_{filename}"
    new_path = os.path.join(directory, new_filename)
    
    try:
        os.rename(pdf_path, new_path)
        log_info(f"Renamed: {filename} -> {new_filename}")
        return True
    except Exception as e:
        log_error(f"Error renaming {pdf_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Extract match results from PDF reports')
    parser.add_argument('--reporte-dir', default='Reporte', help='Directory containing PDF reports')
    parser.add_argument('--year', type=int, help='Year to process (default: current year)')
    parser.add_argument('--update-history', action='store_true', 
                       help='Append extracted matches to data/ARG.csv')
    parser.add_argument('--round', type=int, help='Process only a specific round number')
    
    args = parser.parse_args()
    
    # Load glossary
    glossary = load_glossary()
    
    # Process PDFs
    if args.round:
        # Process single round
        year = args.year or datetime.now().year
        pdf_path = os.path.join(args.reporte_dir, str(year), f"Resumen F{args.round:02d}.pdf")
        if not os.path.exists(pdf_path):
            log_error(f"PDF not found: {pdf_path}")
            return
        
        matches, date_str = extract_results_from_pdf(pdf_path, glossary)
        if matches:
            log_ok(f"Extracted {len(matches)} matches from Round {args.round}")
            for match in matches:
                print(f"  {match['Home_Raw']} {match['HG']}-{match['AG']} {match['Away_Raw']} ({match['Res']})")
        else:
            log_warning(f"No matches extracted from Round {args.round}")
    else:
        # Process all PDFs
        skip_parsed = args.update_history  # Skip already parsed files when updating history
        results = process_all_pdfs(args.reporte_dir, glossary, args.year, skip_parsed=skip_parsed)
        
        if results:
            log_ok(f"Successfully processed {len(results)} rounds")
            
            # Show summary
            total_matches = 0
            for match_data in results.values():
                if len(match_data) >= 1:
                    matches = match_data[0]
                    total_matches += len(matches)
            log_info(f"Total matches extracted: {total_matches}")
            
            # Append to CSV if requested
            if args.update_history:
                processed_pdfs = append_to_arg_csv(results)
                
                # Rename successfully processed PDFs
                if processed_pdfs:
                    log_info(f"Renaming {len(processed_pdfs)} processed PDF files...")
                    for pdf_path in processed_pdfs:
                        rename_processed_pdf(pdf_path)
                    log_ok("PDF files renamed successfully")
        else:
            log_warning("No results extracted from PDFs")


if __name__ == '__main__':
    main()
