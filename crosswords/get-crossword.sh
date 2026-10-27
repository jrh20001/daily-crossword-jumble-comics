#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
export PATH="$HOME/.local/bin:$PATH"

# Guard against concurrent runs (cron has double-fired) racing on output/ files
# ponytail: single flock; fine unless parallel prints are ever wanted.
exec 9>"$DIR/.crossword.lock"
flock -n 9 || { echo "already running, skipping"; exit 0; }

OUTDIR="$DIR/output"
DATE=$(date +%Y%m%d)
mkdir -p "$OUTDIR"

# Clear stale renders so disk usage doesn't accumulate
rm -f "$OUTDIR"/*.pdf "$OUTDIR"/*.html "$OUTDIR"/*.puz

# Download today's LA Times crossword
puzfile="$OUTDIR/LA Times - $DATE.puz"
echo "==> Downloading LA Times crossword ($DATE)..."
uv run --directory "$DIR/xword-dl-main" xword-dl lat -o "$puzfile" 2>&1 || true
if [ ! -f "$puzfile" ]; then
  echo "ERROR: crossword download failed for $DATE" >&2
  exit 1
fi
echo "     saved: $puzfile"

# Render to HTML
htmlfile="$OUTDIR/LA Times - $DATE.html"
echo "==> Rendering HTML..."
uv run --directory "$DIR/puzpy" python puz_viewer.py "$puzfile" -o "$htmlfile"
echo "     saved: $htmlfile"

# Convert to PDF (single letter page)
pdffile="$OUTDIR/LA Times - $DATE.pdf"
echo "==> Converting to PDF..."
# PDF via Playwright's bundled headless chromium (render_pdf.py) - the snap
# chromium was slow (57-103s) and intermittently wrote no PDF under cron on
# this 899MB box (session 10/15). Gate on the PDF existing; retry if needed.
attempt=0
while [ ! -f "$pdffile" ] && [ "$attempt" -lt 3 ]; do
  attempt=$((attempt+1))
  timeout 120 uv run "$DIR/render_pdf.py" "$htmlfile" "$pdffile" 2>&1 || true
  if [ ! -f "$pdffile" ]; then
    echo "     PDF attempt $attempt: no output, retrying..." >&2
    sleep 5
  fi
done
if [ ! -f "$pdffile" ]; then
  echo "ERROR: PDF not created after $attempt attempts" >&2
  exit 1
fi
echo "     saved: $pdffile"

# Print to Brother MFC-7840W
if command -v lp &>/dev/null; then
  echo "==> Printing..."
  lp -d Brother-MFC-7840W "$pdffile" 2>/dev/null && echo "     sent to Brother-MFC-7840W"
fi
