#!/usr/bin/env python3
"""Analyze aspect ratios of all files in todays-input/."""

from pathlib import Path
from PIL import Image

INPUT_DIR = Path(__file__).resolve().parent / "todays-input"

files = sorted(INPUT_DIR.iterdir())
for f in files:
    if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.gif', '.png'):
        img = Image.open(f)
        w, h = img.size
        ratio = w / h
        print(f"{ratio:5.2f}  {w:4d}x{h:<4d}  {f.name}")
