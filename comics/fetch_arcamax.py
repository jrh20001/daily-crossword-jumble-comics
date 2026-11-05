#!/usr/bin/env python3
"""Arcamax fallback source for the GoComics strips.

GoComics put its comic pages behind a Bunny Shield proof-of-work wall that no
client can pass (the challenge frame it loads, 33498/challenge.html, is a 404 on
their own CDN), so fetch_gocomics.py fails and 20 of the 27 daily strips go
missing. Arcamax republishes most of the same strips as plain HTML with no bot
wall, so we mirror the ones it carries.

Writes Comics/GoComics/<Name>/<slug>_<YYYYMMDD>.<ext> - the same place
fetch_gocomics.py writes, so harvest.py needs no change. Existing files are
skipped, so this only fills the gaps.

Exit: 0 = everything requested is on disk, 2 = some strips missing,
      1 = nothing downloaded.
"""

import argparse
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests
from PIL import Image

from comics_sources import ARCAMAX
from io import BytesIO

BASE = Path(__file__).resolve().parent
COMICS_DIR = BASE / "Comics" / "GoComics"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/130.0.0.0 Safari/537.36")
PAGE = "https://www.arcamax.com/thefunnies/{slug}/"
# Arcamax serves 600px-wide strips; the GoComics originals (and the
# ComicsKingdom ones, 975-1950px) are wider, so a 600px strip renders visibly
# narrower on the page. Upscale to GoComics-ish width and store as PNG.
TARGET_WIDTH = 1200
# Share links carry the strip for one date: .../pin/create/button/?url=...&media=<img>&description=<Name> for M/D/YYYY
SHARE = re.compile(r'media=(https%3A%2F%2F[^&"]+)&(?:amp;)?description=([^"&]*)')
SUB = re.compile(r"/thefunnies/[a-z0-9-]+/(s-\d+)")
# Some strips (Daddy's Home) share an image without any date in the caption, so
# the page date cannot be verified; the newest s-<id> page is the newest strip.
NEWEST_IMG = re.compile(r'src="(https://resources\.arcamax\.com/newspics/(?!cache/)[^"]+\.(?:gif|jpg|png))"')
DATE_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")


def fetch(url: str, tries: int = 3) -> requests.Response:
    last: Exception | None = None
    for attempt in range(tries):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 200:
                return r
            last = requests.HTTPError(f"{r.status_code} for {url}")
        except requests.RequestException as exc:  # network hiccup
            last = exc
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(str(last))


def share_images(html: str) -> dict[str, str]:
    """{YYYY-MM-DD: image_url} for every dated share link on a page."""
    from urllib.parse import unquote, unquote_plus

    found: dict[str, str] = {}
    for media, desc in SHARE.findall(html):
        m = DATE_RE.search(unquote_plus(desc))
        if not m:
            continue
        month, day, year = m.groups()
        found[f"{year}-{int(month):02d}-{int(day):02d}"] = unquote(media)
    return found


def image_ext(body: bytes, url: str) -> str:
    if body[:3] == b"GIF":
        return "gif"
    if body[:2] == b"\xff\xd8":
        return "jpg"
    if body[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    return Path(url).suffix.lstrip(".") or "gif"


def normalise(body: bytes, ext: str, target: int) -> tuple[bytes, str]:
    """Upscale an undersized strip to `target` px wide; return (bytes, ext).

    LANCZOS resampling of line art is close to lossless for print and keeps the
    strips the same rendered width as the GoComics originals. PNG avoids the
    256-colour dithering of the source GIF.
    """
    if target <= 0:
        return body, ext
    img = Image.open(BytesIO(body))
    if img.width >= target:
        return body, ext
    height = round(img.height * target / img.width)
    resized = img.convert("RGB").resize((target, height), Image.LANCZOS)
    # 128-colour palette keeps the line art clean at ~1/3 the size of truecolour
    resized = resized.quantize(colors=128, method=Image.MEDIANCUT, dither=Image.NONE)
    if resized.height > 8000:  # sanity: never emit an absurdly tall page
        return body, ext
    out = BytesIO()
    resized.save(out, format="PNG", optimize=True)
    return out.getvalue(), "png"


def find_image(slug: str, want: str, allow_undated: bool,
               older_pages: int = 4) -> tuple[str | None, bool]:
    """(image_url, date_verified) for `want` (YYYY-MM-DD).

    Walks the landing page plus the last few dated s-<id> pages, matching the
    date in the share caption. When that caption carries no date at all
    (Daddy's Home) the newest strip is used instead - only allowed for a
    same-day run, never for a backfill - and reported as unverified.
    """
    html = fetch(PAGE.format(slug=slug)).text
    images = share_images(html)
    if want in images:
        return images[want], True

    subs = list(dict.fromkeys(SUB.findall(html)))[:older_pages]
    undated: str | None = None
    for sub in subs:
        page = fetch(PAGE.format(slug=slug) + sub).text
        images = share_images(page)
        if want in images:
            return images[want], True
        if undated is None and not share_images(page):
            hits = NEWEST_IMG.findall(page)
            if hits:
                undated = hits[0]
        time.sleep(1)
    if undated and allow_undated:
        return undated, False
    return None, False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--sleep", type=float, default=2.0, help="pause between strips")
    ap.add_argument("--width", type=int, default=TARGET_WIDTH,
                    help=f"upscale strips narrower than this to it (default {TARGET_WIDTH}, 0 = off)")
    args = ap.parse_args()

    today = date.today().strftime("%Y-%m-%d")
    target = args.date or today
    stamp = target.replace("-", "")
    ok = failed = 0
    failed_names: list[str] = []

    for name, slug in ARCAMAX.items():
        outdir = COMICS_DIR / name
        existing = list(outdir.glob(f"*_{stamp}.*")) if outdir.exists() else []
        if existing:
            print(f"SKIP GoComics/{name}: already have {existing[0].name}")
            ok += 1
            continue

        try:
            url, verified = find_image(slug, target, allow_undated=target == today)
            if not url:
                print(f"MISS GoComics/{name}: arcamax has no strip for {target}")
                failed += 1
                failed_names.append(name)
                time.sleep(args.sleep)
                continue
            body = fetch(url).content
            if len(body) < 8000:
                raise RuntimeError(f"suspiciously small image ({len(body)} bytes)")
            ext = image_ext(body, url)
            body, ext = normalise(body, ext, args.width)
            outdir.mkdir(parents=True, exist_ok=True)
            dest = outdir / f"{slug}_{stamp}.{ext}"
            dest.write_bytes(body)
            note = "" if verified else "  (date unverified: caption has no date)"
            print(f"OK   GoComics/{name} ({len(body) // 1024} KB) -> {dest.name}{note}")
            ok += 1
        except Exception as exc:  # noqa: BLE001 - report and keep going
            print(f"FAIL GoComics/{name}: {exc}")
            failed += 1
            failed_names.append(name)
        time.sleep(args.sleep)

    print(f"\nArcamax: {ok} ok, {failed} failed (date {target})")
    if failed_names:
        print("       missing from arcamax: " + ", ".join(failed_names))
    if ok == 0:
        return 1
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
