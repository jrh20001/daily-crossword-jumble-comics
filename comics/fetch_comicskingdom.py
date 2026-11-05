#!/usr/bin/env python3
"""Fetch ComicsKingdom strips for a given date via their public WordPress API.

Replaces `dosage ComicsKingdom/...`, which was one of the two rate-limited /
markup-dependent scrapers in get-comics.sh.

Usage:
    uv run fetch_comicskingdom.py [--date YYYY-MM-DD] [--root Comics] [--dry-run]
"""
import argparse
import pathlib
import sys
from datetime import date

import requests

from comics_sources import COMICSKINGDOM

API = "https://wp.comicskingdom.com/wp-json/wp/v2/ck_comic"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )
}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=date.today().isoformat(), help="YYYY-MM-DD")
    ap.add_argument("--root", default="Comics", help="comics root directory")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def find_strip(session: requests.Session, slug: str, want: str) -> str | None:
    """Return the image URL for the strip published on `want`."""
    params = {
        "ck_feature": slug,
        "per_page": "100",
        "_fields": "date,assets,link",
    }
    r = session.get(API, params=params, headers=HEADERS, timeout=45)
    r.raise_for_status()
    for item in r.json():
        if not str(item.get("date", "")).startswith(want):
            continue
        assets = item.get("assets") or {}
        for key in ("single", "featured"):
            url = (assets.get(key) or {}).get("url")
            if url:
                return url
    return None


def main() -> int:
    args = parse_args()
    root = pathlib.Path(args.root)
    session = requests.Session()
    ok = fail = 0

    for name, slug in COMICSKINGDOM.items():
        dest_dir = root / "ComicsKingdom" / name
        dest = dest_dir / f"{slug}_{args.date}.jpg"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"SKIP {dest} (already present)")
            ok += 1
            continue
        try:
            url = find_strip(session, slug, args.date)
            if not url:
                print(f"FAIL ComicsKingdom/{name}: no comic dated {args.date}", file=sys.stderr)
                fail += 1
                continue
            if args.dry_run:
                print(f"DRY  ComicsKingdom/{name} -> {url}")
                ok += 1
                continue
            img = session.get(url, headers=HEADERS, timeout=60)
            img.raise_for_status()
            if not img.content:
                raise RuntimeError("empty image")
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(img.content)
            print(f"OK   ComicsKingdom/{name} ({len(img.content) // 1024} KB) -> {dest.name}")
            ok += 1
        except Exception as e:  # noqa: BLE001 - one failure must not kill the run
            print(f"FAIL ComicsKingdom/{name}: {type(e).__name__}: {e}", file=sys.stderr)
            fail += 1

    print(f"\nComicsKingdom: {ok} ok, {fail} failed (date {args.date})")
    if ok == 0:
        return 1
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
