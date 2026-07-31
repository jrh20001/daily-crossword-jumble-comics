#!/usr/bin/env python3
"""Aggregate today's comics from todays-input/ into a smart-layout HTML page in todays-output/."""

import base64
from datetime import date
from pathlib import Path
from PIL import Image


SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / "todays-input"
OUTPUT_DIR = SCRIPT_DIR / "todays-output"
TODAY = date.today().strftime("%Y-%m-%d")



def img_to_data_uri(path):
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = Path(path).suffix.lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "gif": "gif", "png": "png"}.get(ext, "jpeg")
    return f"data:image/{mime};base64,{data}"

def strip_name(filename):
    """Extract readable strip name from filename like ComicsKingdom_Bizarro_bizarro_2026-06-29.jpg"""
    stem = Path(filename).stem
    parts = stem.split("_")
    # Remove source prefix and date suffix
    name_parts = []
    for p in parts[1:]:
        if len(p) == 10 and p[4] == "-" and p[7] == "-":  # looks like 2026-06-29
            break
        if len(p) == 8 and p.isdigit():  # looks like 20260629
            break
        name_parts.append(p)
    return " ".join(name_parts).title() or stem

def layout(comics):
    """Return each comic as its own row. No side-by-side arrangement."""
    return [[(name, img_to_data_uri(path), w, h)] for name, path, w, h in comics]


def generate_html(rows):
    items = ""
    for row in rows:
        name, data_uri, w, h = row[0]
        items += f'  <div class="row">\n'
        items += f'    <div class="comic">\n'
        items += f'      <div class="label">{name}</div>\n'
        items += f'      <img src="{data_uri}" alt="{name}" loading="lazy">\n'
        items += f'    </div>\n'
        items += f'  </div>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Daily Comics — {TODAY}</title>
<style>
  @page {{
    margin: 0;
  }}
  body {{
    font-family: system-ui, sans-serif;
    background: #fff;
    margin: 0;
    padding: 5px;
    color: #333;
  }}
  h1 {{
    text-align: center;
    color: #333;
    margin-bottom: 24px;
    font-size: 1.4em;
    letter-spacing: 0.05em;
  }}
  .row {{
    display: grid;
    grid-template-columns: 1fr;
    gap: 12px;
    margin-bottom: 12px;
  }}

  .comic {{
    background: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    overflow: hidden;
    page-break-inside: avoid;
  }}
  .comic img {{
    width: 100%;
    height: auto;
    display: block;
  }}
  .label {{
    font-size: 0.75em;
    color: #666;
    padding: 6px 10px 2px;
  }}
</style>
</head>
<body>
<h1>Daily Comics — {TODAY}</h1>
{items}
</body>
</html>"""

def main():
    files = sorted(INPUT_DIR.iterdir())
    comics = []
    for f in files:
        if f.is_file() and f.suffix.lower() in ('.jpg', '.jpeg', '.gif', '.png'):
            img = Image.open(f)
            w, h = img.size
            name = strip_name(f.name)
            comics.append((name, str(f), w, h))

    if not comics:
        print(f"No comics found in {INPUT_DIR}")
        return

    print(f"Found {len(comics)} comics.")
    rows = layout(comics)
    print(f"  Layout: {len(rows)} rows")

    OUTPUT_DIR.mkdir(exist_ok=True)
    html = generate_html(rows)
    out_path = OUTPUT_DIR / f"comics-{TODAY}.html"
    out_path.write_text(html)
    print(f"\nWrote: {out_path} ({out_path.stat().st_size / 1024 / 1024:.1f} MB)")

if __name__ == "__main__":
    main()
