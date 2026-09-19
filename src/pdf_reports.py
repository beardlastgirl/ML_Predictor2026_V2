"""Shared pdfplumber helpers for Reporte/ PDFs — single pdf-discovery implementation.

Consumers: src/summary_validator.py (averages fallback) and the root
parse_reporte_pdfs.py manual tool (match-results extraction).
"""
import glob
import os
import re


def list_report_pdfs(reporte_dir: str):
    """All ``Resumen F*.pdf`` files in reporte_dir, newest round first."""
    files = glob.glob(os.path.join(reporte_dir, "Resumen F*.pdf"))
    if not files:
        return []
    files.sort(
        key=lambda x: [int(c) for c in re.findall(r"\d+", os.path.basename(x))][-1],
        reverse=True,
    )
    return files


def find_latest_report_pdf(reporte_dir: str):
    """Path of the most recent report PDF, or None."""
    files = list_report_pdfs(reporte_dir)
    return files[0] if files else None