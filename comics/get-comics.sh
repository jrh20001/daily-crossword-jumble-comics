#!/usr/bin/bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
export PATH="$HOME/.local/bin:$PATH"

# Optional date argument / COMICS_DATE env: for backfilling a missed day.
#   bash get-comics.sh 2026-11-03      (or) COMICS_DATE=2026-11-03 bash get-comics.sh
export COMICS_DATE="${1:-${COMICS_DATE:-$(date +%F)}}"
echo "=== Target date: $COMICS_DATE ==="

echo "=== Step 1/6: clean todays-input ==="
rm -f todays-input/*

echo "=== Step 1b/6: clean todays-output (keep disk usage flat) ==="
rm -f todays-output/comics-*.html todays-output/comics-*.pdf

# 2026-11-03: GoComics put the site behind Bunny Shield, so `dosage` always got
# HTTP 403 and the email silently dropped to 7 of 27 strips. Both providers are
# fetched directly instead:
#   ComicsKingdom -> public WordPress JSON API (no bot wall)
#   GoComics      -> plain HTTP of the feature landing page (see fetch_gocomics.py)
#
# 2026-11-05: root cause of the 403 found - Bunny Shield rejects any request with
# no `Accept-Language` header (UA/cookies/JS/proof-of-work are irrelevant), and it
# only guards the dated /<strip>/<date> routes and the RSC data route. The landing
# page /<strip> serves fine and embeds that day's strip, so GoComics needs no
# browser at all now. Older dates still come from fetch_arcamax.py.
echo "=== Step 2a/6: ComicsKingdom ==="
ck_rc=0
uv run fetch_comicskingdom.py --date "$COMICS_DATE" || ck_rc=$?

echo "=== Step 2b/6: GoComics ==="
gc_rc=0
uv run fetch_gocomics.py --date "$COMICS_DATE" || gc_rc=$?
# GoComics mirrors on arcamax.com (plain HTML, no bot wall) cover most of the
# GoComics strips, so run that before waiting on GoComics again.
echo "=== Step 2c/6: Arcamax fallback (GoComics mirrors) ==="
ax_rc=0
uv run fetch_arcamax.py --date "$COMICS_DATE" || ax_rc=$?

# GoComics' bot wall throttles this host for a while after a failed challenge.
# One delayed retry catches a transient block; both fetchers skip strips they
# already have, so the retry only costs the gaps.
if [ "$gc_rc" -ne 0 ]; then
  if [ "${SKIP_GC_RETRY:-}" = "1" ]; then
    echo "WARN: GoComics incomplete (rc=$gc_rc); retry skipped (SKIP_GC_RETRY=1)" >&2
  else
    echo "WARN: GoComics incomplete (rc=$gc_rc); retrying once in 10 minutes" >&2
    sleep 600
    gc_rc=0
    uv run fetch_gocomics.py --date "$COMICS_DATE" || gc_rc=$?
  fi
fi

if [ "$ck_rc" -eq 1 ] && [ "$gc_rc" -eq 1 ]; then
  echo "ERROR: nothing downloaded for $COMICS_DATE; aborting before email" >&2
  exit 1
fi

echo "=== Step 3/6: harvest.py ==="
uv run harvest.py --date "$COMICS_DATE"

fetched=$(ls todays-input | wc -l)
echo "Fetched $fetched of 27 strips for $COMICS_DATE (ComicsKingdom rc=$ck_rc, GoComics rc=$gc_rc, Arcamax rc=$ax_rc)"
if [ "$fetched" -lt 27 ]; then
  echo "WARN: only $fetched of 27 strips for $COMICS_DATE" >&2
fi

# Record what is still missing so the email body can name it (recipients were
# previously sent a 7-of-27 PDF that looked complete).
mkdir -p todays-output
uv run python - "$COMICS_DATE" <<'PY'
import sys
from pathlib import Path
from comics_sources import COMICSKINGDOM, GOCOMICS

date = sys.argv[1]
have = {p.name for p in Path("todays-input").iterdir()}
missing = []
for provider, comics in (("ComicsKingdom", COMICSKINGDOM), ("GoComics", GOCOMICS)):
    for name in comics:
        if not any(n.startswith(f"{provider}_{name}_") for n in have):
            missing.append(f"{provider}/{name}")
Path("todays-output/missing-strips.txt").write_text("\n".join(missing))
print(f"missing strips: {len(missing)}" + (f" -> {', '.join(missing)}" if missing else ""))
PY

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
