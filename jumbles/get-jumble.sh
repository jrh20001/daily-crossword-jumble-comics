#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
export PATH="$HOME/.local/bin:$PATH"

OUTDIR="$DIR/output"
htmlfile="$OUTDIR/jumble-print.html"
pdffile="$OUTDIR/jumble-puzzle.pdf"
datefile="$OUTDIR/jumble-date.txt"
TODAY=$(date +%m/%d/%Y)

# Clear previous artifacts first: a stale PDF left on disk used to be re-printed
# every day whenever rendering failed (bug 2026-10-14..10-22).
rm -f "$pdffile" "$htmlfile" "$datefile"

echo "==> Fetching today's Jumble..."
rc=0
uv run python jumble.py || rc=$?
if [ "$rc" -eq 3 ]; then
  echo "     no Jumble published for today - skipping print"
  exit 0
fi
if [ "$rc" -ne 0 ]; then
  echo "ERROR: jumble fetch failed (exit $rc) - nothing printed" >&2
  exit 1
fi

# Belt and braces: only print a puzzle that really is dated today.
if [ ! -f "$datefile" ]; then
  echo "ERROR: no puzzle date marker, nothing printed" >&2
  exit 1
fi
puzzledate=$(cat "$datefile")
if [ "$puzzledate" != "$TODAY" ]; then
  echo "ERROR: puzzle dated $puzzledate but today is $TODAY - skipping print" >&2
  exit 0
fi

echo "==> Converting to PDF..."
# Snap chromium cannot run from a cron job: "is not a snap cgroup for tag
# snap.chromium.chromium" -> exits 1 without writing a file. Playwright's
# bundled headless chromium works under cron (same renderer as crosswords).
attempt=0
while [ ! -s "$pdffile" ] && [ "$attempt" -lt 3 ]; do
  attempt=$((attempt+1))
  timeout 180 uv run "$DIR/render_pdf.py" "$htmlfile" "$pdffile" 2>&1 || true
  if [ ! -s "$pdffile" ]; then
    echo "     PDF attempt $attempt: no output, retrying..." >&2
    sleep 5
  fi
done
if [ ! -s "$pdffile" ]; then
  echo "ERROR: PDF not created after $attempt attempts - nothing printed" >&2
  exit 1
fi
echo "     saved: $pdffile"

# Print to Brother MFC-7840W
if command -v lp &>/dev/null; then
  echo "==> Printing..."
  lp -d Brother-MFC-7840W "$pdffile" 2>/dev/null && echo "     sent to Brother-MFC-7840W"
fi
