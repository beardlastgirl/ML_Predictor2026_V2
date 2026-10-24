"""
scripts/test_afa_pdf_parse.py
Phase 1.6 — PoC: AFA Convocation PDF Parseability Test

PURPOSE:
    Verify whether AFA national team convocation PDFs (2012-2026) are
    machine-readable and yield player names + club affiliations via
    standard Python PDF libraries. This is a RECONNAISSANCE script only.
    Do not integrate into production pipeline.

USAGE:
    python scripts/test_afa_pdf_parse.py <path_to_pdf>
    python scripts/test_afa_pdf_parse.py --demo   # runs against any PDF in Reporte/

DEPENDENCIES:
    pdfplumber (preferred)  -- pip install pdfplumber
    pypdf (fallback)        -- already in requirements.txt

EXIT CODES:
    0  -- text extracted, structure assessed
    1  -- PDF not readable (scanned/image-only or not found)
    2  -- dependency missing
"""

import sys
import re
import os
from pathlib import Path


def _try_pdfplumber(pdf_path: str) -> tuple[bool, str, list[dict]]:
    """Attempt extraction with pdfplumber. Returns (success, raw_text, parsed_rows)."""
    try:
        import pdfplumber
    except ImportError:
        return False, "pdfplumber not installed", []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            raw = "\n".join(pages)
        if not raw.strip():
            return False, "PDF opened but no text extracted (likely scanned/image)", []
        return True, raw, []
    except Exception as e:
        return False, f"pdfplumber error: {e}", []


def _try_pypdf(pdf_path: str) -> tuple[bool, str, list[dict]]:
    """Fallback extraction with pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # older alias
        except ImportError:
            return False, "pypdf not installed", []

    try:
        reader = PdfReader(pdf_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        raw = "\n".join(pages)
        if not raw.strip():
            return False, "PDF opened but no text extracted (likely scanned/image)", []
        return True, raw, []
    except Exception as e:
        return False, f"pypdf error: {e}", []


# ---------------------------------------------------------------------------
# Regex patterns expected in AFA convocation lists
# ---------------------------------------------------------------------------
# AFA lists typically look like:
#   GK  Franco ARMANI          River Plate
#   DF  Nicolás OTAMENDI       Manchester City
# or in older formats:
#   Arqueros: Franco Armani (River Plate), Sergio Romero (Sampdoria)
#
# We try two patterns: structured (position + name + club) and inline.
PATTERN_STRUCTURED = re.compile(
    r"(?P<pos>GK|DF|MF|FW|Arquero|Defensor|Mediocampista|Delantero)"
    r"[\s\t]+(?P<name>[A-ZÁÉÍÓÚÑ][a-záéíóúñA-ZÁÉÍÓÚÑ\s\-\'\.]{3,40})"
    r"[\s\t]+(?P<club>[A-Za-záéíóúñÁÉÍÓÚÑ\s\.\-\'&]{3,50})",
    re.IGNORECASE,
)

PATTERN_INLINE = re.compile(
    r"(?P<name>[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+)"
    r"\s*\((?P<club>[^)]{3,50})\)"
)

# FIFA window months — used to cross-check document dates
FIFA_WINDOW_MONTHS = {3, 6, 9, 10, 11}


def parse_convocation(raw_text: str) -> dict:
    """
    Attempt to extract player names and clubs from raw PDF text.
    Returns a dict with assessment results.
    """
    result = {
        "total_chars": len(raw_text),
        "total_lines": raw_text.count("\n"),
        "structured_matches": [],
        "inline_matches": [],
        "machine_readable": len(raw_text.strip()) > 200,
        "has_player_names": False,
        "has_club_names": False,
        "structure": "unknown",
        "notes": [],
    }

    # Try structured pattern
    for m in PATTERN_STRUCTURED.finditer(raw_text):
        result["structured_matches"].append({
            "pos": m.group("pos").strip(),
            "name": m.group("name").strip(),
            "club": m.group("club").strip(),
        })

    # Try inline pattern
    for m in PATTERN_INLINE.finditer(raw_text):
        result["inline_matches"].append({
            "name": m.group("name").strip(),
            "club": m.group("club").strip(),
        })

    best_matches = result["structured_matches"] or result["inline_matches"]
    result["has_player_names"] = len(best_matches) >= 3
    result["has_club_names"] = any(r.get("club") for r in best_matches)

    if result["structured_matches"]:
        result["structure"] = "structured (position + name + club)"
    elif result["inline_matches"]:
        result["structure"] = "inline (name + club in parentheses)"
    elif result["machine_readable"]:
        result["structure"] = "text present but pattern unmatched — manual review needed"
        result["notes"].append(
            "PDF contains text but no player patterns matched. "
            "AFA may use a different layout. Inspect raw text manually."
        )
    else:
        result["structure"] = "not machine-readable"
        result["notes"].append("Likely scanned/image PDF — OCR required.")

    return result


def assess_pdf(pdf_path: str) -> None:
    print(f"\nAFA PDF Parse PoC")
    print(f"{'='*60}")
    print(f"File: {pdf_path}")

    if not os.path.exists(pdf_path):
        print(f"ERROR: File not found: {pdf_path}")
        sys.exit(1)

    # Try pdfplumber first, then pypdf
    success, raw, _ = _try_pdfplumber(pdf_path)
    if not success:
        print(f"pdfplumber: {raw}")
        success, raw, _ = _try_pypdf(pdf_path)
        if not success:
            print(f"pypdf: {raw}")
            print("\nRESULT: NOT PARSEABLE — both libraries failed.")
            print("Recommendation: PDF is likely scanned/image-only or encrypted.")
            sys.exit(1)
        else:
            print("pdfplumber failed; pypdf succeeded.")
    else:
        print("Extraction library: pdfplumber")

    result = parse_convocation(raw)

    print(f"\nRaw text: {result['total_chars']} chars, {result['total_lines']} lines")
    print(f"Machine-readable: {result['machine_readable']}")
    print(f"Structure detected: {result['structure']}")
    print(f"Structured matches (pos+name+club): {len(result['structured_matches'])}")
    print(f"Inline matches (name+club): {len(result['inline_matches'])}")

    best = result["structured_matches"] or result["inline_matches"]
    if best:
        print(f"\nSample extracted entries (first 5):")
        for row in best[:5]:
            print(f"  {row}")

    if result["notes"]:
        print(f"\nNotes:")
        for note in result["notes"]:
            print(f"  - {note}")

    # Final verdict
    print(f"\n{'='*60}")
    if result["has_player_names"] and result["has_club_names"]:
        print("VERDICT: PARSEABLE — player names and clubs extracted successfully.")
        print("         Regex extraction is viable. Club mapping to ARG.csv glossary required.")
        print("         Recommend testing 5-10 PDFs across 2012-2026 to confirm consistency.")
    elif result["machine_readable"]:
        print("VERDICT: PARTIALLY PARSEABLE — text present but patterns unmatched.")
        print("         Inspect raw_text snippet below and adjust regex.")
        print("\nFirst 500 chars of raw text:")
        print(raw[:500])
    else:
        print("VERDICT: NOT PARSEABLE — no text layer found.")
        print("         OCR (pytesseract) would be required. High engineering cost.")
        sys.exit(1)


def find_demo_pdf() -> str | None:
    """Find any PDF in Reporte/ for demo mode."""
    for root, _, files in os.walk("Reporte"):
        for f in files:
            if f.lower().endswith(".pdf"):
                return os.path.join(root, f)
    return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_afa_pdf_parse.py <path_to_pdf>")
        print("       python scripts/test_afa_pdf_parse.py --demo")
        sys.exit(0)

    if sys.argv[1] == "--demo":
        pdf = find_demo_pdf()
        if not pdf:
            print("No PDF found in Reporte/. Provide a path explicitly.")
            sys.exit(1)
        print(f"Demo mode: using {pdf}")
        assess_pdf(pdf)
    else:
        assess_pdf(sys.argv[1])
