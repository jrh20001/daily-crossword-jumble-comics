#!/usr/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
export PATH="$HOME/.local/bin:$PATH"

echo "=== Step 1/6: clean todays-input ==="
rm -f todays-input/*.jpg todays-input/*.png todays-input/*.gif

echo "=== Step 1b/6: clean todays-output (keep disk usage flat) ==="
rm -f todays-output/comics-*.html todays-output/comics-*.pdf

# GoComics started rate-limiting (HTTP 403) around 2026-10-10: more than ~3
# rapid requests from one IP get blocked, which killed `dosage @` mid-run and,
# via set -e, aborted the script before the email step. Fetch each comic
# individually, spacing GoComics requests out, and continue past failures.
echo "=== Step 2/6: dosage (spaced; GoComics rate-limits bursts) ==="
ok=0
fail=0
for dir in Comics/*/; do
  provider="$(basename "$dir")"
  for comic in "$dir"*/; do
    name="$provider/$(basename "$comic")"
    if dosage "$name"; then
      ok=$((ok + 1))
    else
      echo "WARN: fetch failed for $name (continuing)" >&2
      fail=$((fail + 1))
    fi
    if [ "$provider" = "GoComics" ]; then
      sleep 90  # stay under GoComics' burst limit
    fi
  done
done
echo "Fetched $ok strips, $fail failures"
if [ "$ok" -eq 0 ]; then
  echo "ERROR: no comics downloaded at all; aborting before email" >&2
  exit 1
fi

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
