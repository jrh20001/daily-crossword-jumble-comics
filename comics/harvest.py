#!/usr/bin/env python3
"""Harvest: move newest file from each Comics/ subdir into todays-input/, delete the rest."""

import os
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
COMICS_DIR = SCRIPT_DIR / "Comics"
INPUT_DIR = SCRIPT_DIR / "todays-input"
INPUT_DIR.mkdir(exist_ok=True)

for dirpath, dirnames, filenames in os.walk(COMICS_DIR):
    files = [Path(dirpath) / f for f in filenames]
    if not files:
        continue

    # newest by modification time
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    newest = files[0]
    rest = files[1:]

    # unique name: source/strip
    rel = newest.relative_to(COMICS_DIR)
    dest_name = str(rel).replace("/", "_")
    dest = INPUT_DIR / dest_name

    shutil.move(str(newest), str(dest))
    print(f"  {rel} -> {dest_name}")

    for old in rest:
        old.unlink()
        print(f"  DEL {old.relative_to(COMICS_DIR)}")

print(f"\nDone. {len(list(INPUT_DIR.iterdir()))} files in todays-input/")
