#!/usr/bin/env python3
"""Harvest: move the wanted file from each Comics/ subdir into todays-input/.

Default: newest file per directory (daily run).
With --date YYYY-MM-DD: the file for that date (backfill run); older/newer
files in that directory are deleted afterwards, so run backfills oldest-first.
"""

import argparse
import os
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
COMICS_DIR = SCRIPT_DIR / "Comics"
INPUT_DIR = SCRIPT_DIR / "todays-input"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="", help="YYYY-MM-DD (default: newest file)")
    args = ap.parse_args()

    INPUT_DIR.mkdir(exist_ok=True)
    wanted: list[Path] = []
    skipped = 0

    for dirpath, _dirnames, filenames in os.walk(COMICS_DIR):
        files = [Path(dirpath) / f for f in filenames]
        if not files:
            continue

        if args.date:
            stamp_variants = (args.date, args.date.replace("-", ""))
            matching = [f for f in files if any(v in f.name for v in stamp_variants)]
            if not matching:
                skipped += 1
                continue
            pick = max(matching, key=lambda p: p.stat().st_mtime)
        else:
            pick = max(files, key=lambda p: p.stat().st_mtime)

        rest = [f for f in files if f != pick]
        rel = pick.relative_to(COMICS_DIR)
        dest = INPUT_DIR / str(rel).replace("/", "_")
        shutil.move(str(pick), str(dest))
        wanted.append(dest)
        print(f"  {rel} -> {dest.name}")

        for old in rest:
            old.unlink()
            print(f"  DEL {old.relative_to(COMICS_DIR)}")

    print(f"\nDone. {len(wanted)} files in todays-input/ ({skipped} dirs had no strip for {args.date or 'newest'})")
    return 0 if wanted else 1


if __name__ == "__main__":
    raise SystemExit(main())
