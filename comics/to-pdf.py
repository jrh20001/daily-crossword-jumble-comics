#!/usr/bin/env python3
"""Convert HTML to PDF via WeasyPrint. No Chrome needed."""

from pathlib import Path
from datetime import date
from weasyprint import HTML

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "todays-output"
TODAY = date.today().strftime("%Y-%m-%d")
HTML_PATH = OUTPUT_DIR / f"comics-{TODAY}.html"
PDF_PATH = OUTPUT_DIR / f"comics-{TODAY}.pdf"

if __name__ == "__main__":
    if not HTML_PATH.exists():
        print(f"HTML not found: {HTML_PATH}")
        exit(1)

    HTML(str(HTML_PATH)).write_pdf(str(PDF_PATH))
    size_mb = PDF_PATH.stat().st_size / 1024 / 1024
    print(f"Wrote: {PDF_PATH} ({size_mb:.1f} MB)")