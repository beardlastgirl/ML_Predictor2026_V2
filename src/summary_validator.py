import os
import re
import glob
import pdfplumber
import math
from src.utils import log_info, log_ok, log_warning, log_error

class PDFStatsExtractor:
    """Extends the pipeline with PDF report analysis for summary stats."""
    
    def __init__(self, reporte_dir="Reporte/2026_2"):
        self.reporte_dir = reporte_dir

    def get_latest_pdf(self):
        """Find the most recent PDF in the directory."""
        files = glob.glob(os.path.join(self.reporte_dir, "Resumen F*.pdf"))
        if not files:
            return None
        # Sort by round number (Resumen F11.pdf > Resumen F08.pdf)
        files.sort(key=lambda x: [int(c) for c in re.findall(r'\d+', os.path.basename(x))][-1], reverse=True)
        return files[0]

    def extract_averages(self):
        """
        Extract 'Promedios' from page 4 of the latest PDF.
        Returns (penalties, red_cards, goals) as rounded integers.
        """
        pdf_path = self.get_latest_pdf()
        if not pdf_path:
            log_warning("No PDF reports found in 2026. Using default fallbacks.")
            return 4, 3, 30

        log_info(f"Extracting fallback averages from latest report: {os.path.basename(pdf_path)}")
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if len(pdf.pages) < 4:
                    log_warning(f"PDF {os.path.basename(pdf_path)} has fewer than 4 pages.")
                    return 4, 3, 30
                
                page_text = pdf.pages[3].extract_text()
                
                # Regex for: Promedios: 3.40 penales, 2.90 expulsados y 29.60 goles por fecha.
                pattern = r"Promedios:\s*([\d\.]+)\s*penales,\s*([\d\.]+)\s*expulsados\s*y\s*([\d\.]+)\s*goles"
                match = re.search(pattern, page_text, re.IGNORECASE)
                
                if match:
                    penalties = math.ceil(float(match.group(1)))
                    red_cards = math.ceil(float(match.group(2)))
                    goals = math.ceil(float(match.group(3)))
                    log_ok(f"Extracted averages: {penalties} pen, {red_cards} reds, {goals} goals")
                    return penalties, red_cards, goals
                else:
                    log_warning("Could not find 'Promedios' line on page 4. Using defaults.")
                    return 4, 3, 30
        except Exception as e:
            log_error(f"Error parsing PDF stats: {e}")
            return 4, 3, 30

def validate_and_fix_summary(penalties, red_cards, goals):
    """
    If values are 0, use the PDF extractor to find averages.
    """
    if penalties == 0 or red_cards == 0:
        log_info("Summary stats are missing (0). Attempting PDF fallback...")
        extractor = PDFStatsExtractor()
        avg_pen, avg_red, avg_goals = extractor.extract_averages()
        
        # Only replace if current is 0
        final_pen = penalties if penalties > 0 else avg_pen
        final_red = red_cards if red_cards > 0 else avg_red
        # We don't replace goals if they are > 0 (they come from model predictions)
        return final_pen, final_red, goals
    
    return penalties, red_cards, goals

if __name__ == "__main__":
    p, r, g = validate_and_fix_summary(0, 0, 35)
    print(f"Final Validation: Penales={p}, Expulsados={r}, Goles={g}")
