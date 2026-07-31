#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Step 1/6: clean todays-input ==="
rm -f todays-input/*.jpg todays-input/*.png todays-input/*.gif

echo "=== Step 2/6: dosage @"
dosage @

echo "=== Step 3/6: harvest.py ==="
uv run harvest.py

echo "=== Step 4/6: aggregate.py ==="
uv run aggregate.py

echo "=== Step 5/6: to-pdf.py ==="
uv run to-pdf.py

if [ -n "${COMICS_PASS:-}" ]; then
  echo "=== Step 6/6: email-comics.py ==="
  uv run email-comics.py "$COMICS_PASS"
else
  echo "=== Step 6/6: email-comics.py (skipped — set COMICS_PASS env var) ==="
fi

echo ""
echo "Done. Output in todays-output/"
ls -lh todays-output/comics-*.html todays-output/comics-*.pdf 2>/dev/null
