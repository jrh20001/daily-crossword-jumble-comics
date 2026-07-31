#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"

echo "==> Fetching today's Jumble..."
uv run --directory "$DIR" python jumble.py

pdffile="$DIR/output/jumble-puzzle.pdf"

if [ ! -f "$pdffile" ]; then
  echo "ERROR: $pdffile not found" >&2
  exit 1
fi

# Print to Brother MFC-7840W
if command -v lp &>/dev/null; then
  echo "==> Printing..."
  lp -d Brother-MFC-7840W "$pdffile" 2>/dev/null && echo "     sent to Brother-MFC-7840W"
fi