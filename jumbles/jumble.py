#!/usr/bin/env python3
"""jumble: fetch today's Jumble puzzle, save cartoon + printable PDF."""
import json, os, subprocess, sys, urllib.request
from datetime import datetime as dt
from client import JumbleClient

OUTPUT_DIR = 'output'
CSS = """  @page { margin: 0.25in; size: letter; }
  body { font-family: 'Courier New', Courier, monospace; font-size: 9pt; max-width: 8in; margin: 0 auto; padding: 0; }
  .topline { font-size: 16pt; font-weight: bold; text-align: center; margin: 0 0 4px 0; }
  .cartoon { text-align: center; margin: 0 0 3px 0; }
  .cartoon img { max-width: 80%; max-height: 5in; width: auto; height: auto; }
  .instructions { font-size: 12pt; text-align: center; margin: 4px 0 12px 0; color: #222; }
  .clue { margin-bottom: 8px; display: flex; align-items: center; justify-content: center; gap: 16px; }
  .grid { display: flex; gap: 3px; flex-shrink: 0; }
  .cell { width: 40px; height: 40px; border: 2px solid #333; display: flex; align-items: center; justify-content: center; font-size: 16pt; font-weight: bold; background: white; box-sizing: border-box; }
  .cell.circled { border-radius: 50%; }
  .jumbled { font-size: 22pt; letter-spacing: 6px; font-weight: bold; }
  .caption { font-size: 16pt; font-weight: bold; font-style: italic; margin: 14px 0 8px 0; text-align: center; color: #000; }
  .bonus-label { font-size: 13pt; text-align: center; margin: 8px 0 8px 0; color: #111; }
  .bonus-grid { display: flex; gap: 14px; flex-wrap: wrap; justify-content: center; }
  .bonus-group .grid { margin: 0 auto; }
  .footer { text-align: center; font-size: 7pt; color: #999; margin-top: 10px; border-top: 1px solid #ccc; padding-top: 4px; }"""


def fetch():
    """Fetch puzzle data; fall back to previous day if today's isn't available."""
    jc = JumbleClient()
    today = dt.today()
    for offset in range(4):  # ponytail: try today then up to 3 days back
        from datetime import timedelta
        date = today - timedelta(days=offset)
        try:
            puzzle = jc.get_jumble(date)
            return puzzle
        except Exception as e:
            if offset == 0:
                print(f"Today's puzzle not available ({e}), trying previous day...")
    raise RuntimeError('No puzzle available for today or recent days')


def download_image(url, path):
    urllib.request.urlretrieve(url, path)
    print(f'  cartoon -> {path} ({os.path.getsize(path)} bytes)')


def build_html(puzzle):
    """Generate jumble-print.html from puzzle data."""
    clues_html = []
    for clue in puzzle['clues']:
        word = clue['jumbled']
        circles = set(clue['circles'])
        n = len(word)
        cells = ''.join(
            '<div class="cell circled"></div>' if i + 1 in circles else '<div class="cell"></div>'
            for i in range(n)
        )
        jumbled = ' '.join(word)
        clues_html.append(
            f'<div class="clue">\n'
            f'    <div class="grid">{cells}</div>\n'
            f'    <div class="jumbled">{jumbled}</div>\n'
            f'  </div>'
        )

    # bonus answer layout groups
    solutions = _get_solutions(puzzle)
    groups_parts = []
    for w in solutions:
        cells_str = '<div class="cell"></div>' * len(w)
        groups_parts.append(
            f'<div class="bonus-group">\n'
            f'      <div class="grid">{cells_str}</div>\n'
            f'    </div>'
        )
    groups_html = ''.join(groups_parts)

    date_str = puzzle['date']
    try:
        date_obj = dt.strptime(date_str, '%m/%d/%Y')
        date_nice = date_obj.strftime('%A, %B %d, %Y')
    except ValueError:
        date_nice = date_str

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{CSS}
</style>
</head>
<body>

<div class="topline">Jumble &mdash; {date_nice}</div>

<div class="cartoon">
  <img src="cartoon.png" alt="Jumble cartoon">
</div>

<div class="instructions">Unscramble the Jumbles, one letter to each square or circle to form ordinary words.</div>

{chr(10).join(clues_html)}

<div class="caption">{puzzle['caption']} &mdash;</div>

<div class="bonus-label">Arrange the circled letters to form the bonus answer:</div>

<div class="bonus-grid">
{groups_html}
</div>

<div class="footer">&copy; Tribune Content Agency, LLC &bull; Jumble Daily</div>

</body>
</html>"""


def _get_solutions(puzzle):
    """Extract word groups from the raw layout answer. Fallback: use client's answer."""
    # The API returns the full answer as a concatenated string
    # and layout like '"___" ___'. Parse layout to get word lengths.
    import re
    words = []
    layout = puzzle.get('layout', '')
    # Count underscores in each group
    for part in re.findall(r'_+', layout):
        words.append(part)
    if not words:
        # fallback: split answer into guessed word lengths
        ans = puzzle.get('answer', '')
        # common jumble patterns: 3+7, 3+8, 4+6, etc.
        # ponytail: simple heuristic for common bonus layouts
        total = len(ans)
        if total <= 11:
            words = ['_' * 3, '_' * (total - 3)]
        else:
            words = ['_' * 4, '_' * (total - 4)]
    return words


def build_pdf(html_path, pdf_path):
    """Render HTML to PDF via headless Chrome."""
    chrome = '/opt/google/chrome/chrome'
    if not os.path.exists(chrome):
        print('Warning: Chrome not found at /opt/google/chrome/chrome, skipping PDF')
        return False
    cmd = [chrome, '--headless', '--no-sandbox', '--disable-gpu',
           f'--print-to-pdf={pdf_path}', '--no-margins',
           f'file://{html_path}']
    result = subprocess.run(cmd, capture_output=True, timeout=20)
    return result.returncode == 0


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('Fetching puzzle...')
    puzzle = fetch()
    print(f'  date: {puzzle["date"]}')
    for c in puzzle['clues']:
        print(f'  {c["jumbled"]} -> {c["answer"]}  circles: {c["circles"]}')
    print(f'  caption: {puzzle["caption"]}')
    print(f'  layout: {puzzle["layout"]}')
    print(f'  answer: {puzzle["answer"]}')

    print('\nDownloading cartoon...')
    cartoon_path = os.path.join(OUTPUT_DIR, 'cartoon.png')
    download_image(puzzle['image'], cartoon_path)

    print('\nBuilding HTML...')
    html_path = os.path.join(OUTPUT_DIR, 'jumble-print.html')
    html = build_html(puzzle)
    with open(html_path, 'w') as f:
        f.write(html)
    print(f'  html -> {html_path}')

    print('Building PDF...')
    pdf_path = os.path.join(OUTPUT_DIR, 'jumble-puzzle.pdf')
    pdf_path_abs = os.path.abspath(pdf_path)
    html_path_abs = os.path.abspath(html_path)
    ok = build_pdf(html_path_abs, pdf_path_abs)
    if ok:
        print(f'  pdf -> {pdf_path} ({os.path.getsize(pdf_path)} bytes)')
    else:
        print('  PDF generation failed (Chrome not available). HTML is ready.')

    print(f'\nDone! Files in {OUTPUT_DIR}/')


if __name__ == '__main__':
    main()