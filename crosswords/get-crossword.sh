#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
OUTDIR="$DIR/output"
DATE=$(date +%Y%m%d)
mkdir -p "$OUTDIR"

# Download today's LA Times crossword
puzfile="$OUTDIR/LA Times - $DATE.puz"
echo "==> Downloading LA Times crossword ($DATE)..."
uv run --directory "$DIR/xword-dl-main" xword-dl lat -o "$puzfile" 2>/dev/null
echo "     saved: $puzfile"

# Render to HTML
htmlfile="$OUTDIR/LA Times - $DATE.html"
echo "==> Rendering HTML..."
uv run --directory "$DIR/puzpy" python puz_viewer.py "$puzfile" -o "$htmlfile"
echo "     saved: $htmlfile"

# Convert to PDF (single letter page)
pdffile="$OUTDIR/LA Times - $DATE.pdf"
echo "==> Converting to PDF..."
google-chrome --headless --print-to-pdf-no-header --print-to-pdf="$pdffile" "file://$htmlfile" 2>/dev/null
echo "     saved: $pdffile"

# Print to Brother MFC-7840W
if command -v lp &>/dev/null; then
  echo "==> Printing..."
  lp -d Brother-MFC-7840W "$pdffile" 2>/dev/null && echo "     sent to Brother-MFC-7840W"
fi