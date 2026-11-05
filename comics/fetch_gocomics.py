# /// script
# requires-python = ">=3.12"
# ///
"""Fetch GoComics strips over plain HTTP - no browser, no proof-of-work.

Why this is simple again (2026-11-05):

    GoComics' Bunny Shield rejects every request that has no ``Accept-Language``
    header. That is the whole check - a browser UA, cookies, JS execution and a
    solved proof-of-work change nothing; adding ``Accept-Language`` to ``curl``
    turns a 403 into a 200. Plain HTTP clients (dosage, requests, curl, wget)
    simply never sent that header.

    The shield also only guards the *dated* routes (``/{slug}/{date}``) and the
    Next.js RSC data route. The feature landing page ``/{slug}`` is served
    normally and embeds the current strip in its JSON-LD (an ``ImageObject``
    with ``representativeOfPage: true``), and strip files on
    ``featureassets.gocomics.com`` are open. So each strip needs exactly two
    plain GETs: the landing page, then the image.

    Consequence: this source only ever yields the *newest* strip. A backfill date
    is reported as unavailable and left to fetch_arcamax.py (which mirrors 13 of
    the 20 GoComics strips).

Rate limiting, and why the budget exists:

    One landing page per strip, and GoComics starts answering 403/429 after about
    six to nine feature-page requests from one host in a window (roughly 20
    minutes); the default --budget of 6 stays under it.
    The seven strips arcamax does not mirror are therefore fetched *first*, and
    --budget (default 6) stops the run before the wall; fetch_arcamax.py then
    fills in the eleven that remain. Raise --budget with --cooldown if you want
    GoComics originals for every strip instead of arcamax's upscaled copies.

Layout and naming are unchanged from the dosage era:
Comics/GoComics/<Name>/<slug>_<YYYYMMDD>.<ext>, so harvest.py needs no changes.

Usage:
    uv run fetch_gocomics.py [--date YYYY-MM-DD] [--root Comics]
                             [--sleep SECONDS] [--only Name,Name] [--dry-run]

Exit codes: 0 all ok, 2 partial (some strips unavailable or failed), 1 nothing
fetched and at least one real error.
"""

import argparse
import http.cookiejar
import json
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date as date_cls
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from comics_sources import ARCAMAX, GOCOMICS  # noqa: E402

BASE = "https://www.gocomics.com"

# Accept-Language is the header that gets us past Bunny Shield. Do not drop it.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

LDJSON_RE = re.compile(
    r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.S
)
# Fallback for the inline Next.js payload: {"url":"...","isRerun":...,"date":"..."}
RSC_PAIR_RE = re.compile(
    r'"url":"(https://featureassets\.gocomics\.com/assets/[a-f0-9]+)"[^}]{0,400}?"date":"(\d{4}-\d{2}-\d{2})T'
)
BLOCK_STATUSES = (403, 429)


class Blocked(Exception):
    """GoComics refused the request (403 shield / 429 throttle)."""

    def __init__(self, status: int) -> None:
        super().__init__(f"HTTP {status}")
        self.status = status


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date_cls.today().isoformat(), help="YYYY-MM-DD")
    ap.add_argument("--root", default="Comics", help="comics root directory")
    ap.add_argument("--sleep", type=float, default=3.0, help="seconds between strips")
    ap.add_argument("--only", default="", help="comma separated strip names")
    ap.add_argument("--budget", type=int, default=6,
                    help="max feature-page requests per run (0 = unlimited); GoComics throttles after 6-9")
    ap.add_argument("--cooldown", type=float, default=0.0,
                    help="seconds to wait after a 403/429 before giving up (default: give up at once)")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def log(msg: str) -> None:
    print(msg, flush=True)


def err(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def opener() -> urllib.request.OpenerDirector:
    """One per run: keeps the bunny_shield_id cookie across requests."""
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )


def http_get(op: urllib.request.OpenerDirector, url: str, timeout: int = 45) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with op.open(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        if e.code in BLOCK_STATUSES:
            raise Blocked(e.code) from None
        return e.code, b""


def parse_published(value: str) -> str | None:
    """'November 5, 2026' or ISO -> 'YYYY-MM-DD'."""
    value = (value or "").strip()
    if not value:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}", value):
        return value[:10]
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def strip_from_landing(html: str) -> tuple[str | None, str | None, str]:
    """Return (image_url, published_date, how) from a GoComics feature page."""
    for raw in LDJSON_RE.findall(html):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for obj in _walk(data):
            if obj.get("@type") != "ImageObject" or not obj.get("representativeOfPage"):
                continue
            url = obj.get("url") or obj.get("contentUrl")
            if isinstance(url, str) and "featureassets" in url:
                return url, parse_published(obj.get("datePublished", "")), "ld+json"
    pairs = RSC_PAIR_RE.findall(html)
    if pairs:
        return pairs[0][0], pairs[0][1], "rsc-inline"
    return None, None, "none"


def sniff_ext(body: bytes, url: str) -> str:
    """Name the file after the real bytes, not the (extension-less) CDN path."""
    if body[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if body[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if body[:2] == b"\xff\xd8":
        return ".jpg"
    ext = Path(urlparse(url).path).suffix.lower()
    return ext if ext in (".jpg", ".jpeg", ".gif", ".png") else ".jpg"


def main() -> int:
    args = parse_args()
    try:
        want = date_cls.fromisoformat(args.date).isoformat()
    except ValueError:
        err(f"bad --date {args.date!r}; expected YYYY-MM-DD")
        return 1
    root = Path(args.root)
    stamp = want.replace("-", "")

    wanted = GOCOMICS
    if args.only:
        names = [n.strip() for n in args.only.split(",") if n.strip()]
        unknown = [n for n in names if n not in GOCOMICS]
        if unknown:
            err(f"unknown strip(s): {unknown}")
            return 1
        wanted = {n: GOCOMICS[n] for n in names}

    todo: list[tuple[str, str]] = []
    for name, slug in wanted.items():
        if any((root / "GoComics" / name).glob(f"{slug}_{stamp}.*")):
            log(f"SKIP GoComics/{name} (already present)")
            continue
        todo.append((name, slug))
    # Spend the request budget on strips arcamax cannot replace; the rest are
    # mirrored there and get filled in by fetch_arcamax.py.
    todo.sort(key=lambda item: (item[0] in ARCAMAX, item[0]))

    ok = len(wanted) - len(todo)
    fail = unavailable = 0
    if not todo:
        log(f"\nGoComics: nothing to do for {want}")
        return 0

    op = opener()
    blocked_streak = 0
    budget_hit = False
    requests = 0  # landing pages fetched this run; the throttle counts these
    for idx, (name, slug) in enumerate(todo, start=1):
        if args.budget and requests >= args.budget:
            log(f"     stopping at --budget {args.budget} requests; "
                f"{len(todo) - idx + 1} strip(s) left for fetch_arcamax.py")
            budget_hit = True
            break
        try:
            requests += 1
            status, body = http_get(op, f"{BASE}/{slug}")
            if status != 200:
                err(f"FAIL GoComics/{name}: landing page status {status}")
                fail += 1
                continue
            img_url, published, how = strip_from_landing(body.decode("utf-8", "replace"))
            if not img_url:
                err(f"FAIL GoComics/{name}: no strip in landing page ({len(body)}B)")
                fail += 1
                continue
            if published and published != want:
                err(f"SKIP GoComics/{name}: page shows {published}, not {want}")
                unavailable += 1
                continue
            if args.dry_run:
                log(f"DRY  GoComics/{name} -> {img_url} ({how}, page date {published})")
                ok += 1
                continue
            img_status, img = http_get(op, img_url)
            if img_status != 200 or not img:
                err(f"FAIL GoComics/{name}: image status {img_status} ({img_url[-24:]})")
                fail += 1
                continue
            dest = root / "GoComics" / name / f"{slug}_{stamp}{sniff_ext(img, img_url)}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(img)
            log(f"OK   GoComics/{name} ({len(img) // 1024} KB, {how}) -> {dest.name}")
            ok += 1
            blocked_streak = 0
        except Blocked as e:
            err(f"FAIL GoComics/{name}: {e} (GoComics is throttling this host)")
            fail += 1
            blocked_streak += 1
            if blocked_streak >= 3 or not args.cooldown:
                err("ERROR: GoComics is blocking this host; stopping run")
                break
            err(f"     cooling down {args.cooldown:.0f}s")
            time.sleep(args.cooldown)
            blocked_streak = 0
        except Exception as e:  # noqa: BLE001 - one strip must not kill the run
            err(f"FAIL GoComics/{name}: {type(e).__name__}: {e}")
            fail += 1

        if idx < len(todo):
            pause = args.sleep + random.uniform(0, 4)
            log(f"     waiting {pause:.0f}s")
            time.sleep(pause)

    log(f"\nGoComics: {ok} ok, {fail} failed, {unavailable} not available for {want}"
        f" (older dates come from fetch_arcamax.py)")
    if budget_hit:
        return 2
    if ok == 0 and fail == 0:
        return 2
    if ok == 0:
        return 1
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
