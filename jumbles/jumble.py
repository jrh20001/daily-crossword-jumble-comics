#!/usr/bin/env python3
"""jumble: fetch today's Jumble puzzle, save cartoon + printable HTML."""
import json, os, sys, urllib.request
from datetime import datetime as dt
from client import JumbleClient

OUTPUT_DIR = 'output'
DATE_FILE = os.path.join(OUTPUT_DIR, 'jumble-date.txt')
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

# exit codes consumed by get-jumble.sh
EXIT_NO_PUZZLE_TODAY = 3
EXIT_STALE_PUZZLE = 4


def fetch():
    """Fetch today's puzzle only. Never fall back to an older puzzle:
    printing a previous day's Jumble as if it were today's is a bug."""
    jc = JumbleClient()
    try:
        return jc.get_jumble(dt.today())
    except Exception as e:
        print(f"No Jumble published for today ({e})")
        return None


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


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Never let a previous run's artifacts reach the printer.
    for stale in ('jumble-puzzle.pdf', 'jumble-print.html', 'jumble-date.txt'):
        p = os.path.join(OUTPUT_DIR, stale)
        if os.path.exists(p):
            os.remove(p)

    print('Fetching puzzle...')
    puzzle = fetch()
    if puzzle is None:
        print('Nothing published today - not printing.')
        return EXIT_NO_PUZZLE_TODAY

    try:
        published = dt.strptime(puzzle['date'], '%m/%d/%Y').date()
    except (KeyError, ValueError):
        print(f"ERROR: unparseable puzzle date {puzzle.get('date')!r}", file=sys.stderr)
        return EXIT_STALE_PUZZLE

    print(f'  date: {puzzle["date"]}')
    for c in puzzle['clues']:
        print(f'  {c["jumbled"]} -> {c["answer"]}  circles: {c["circles"]}')
    print(f'  caption: {puzzle["caption"]}')
    print(f'  layout: {puzzle["layout"]}')
    print(f'  answer: {puzzle["answer"]}')

    # Only today's puzzle is printable.
    if published != dt.today().date():
        print(f'ERROR: puzzle is dated {puzzle["date"]}, not today - not printing', file=sys.stderr)
        return EXIT_STALE_PUZZLE

    print('\nDownloading cartoon...')
    cartoon_path = os.path.join(OUTPUT_DIR, 'cartoon.png')
    download_image(puzzle['image'], cartoon_path)

    print('\nBuilding HTML...')
    html_path = os.path.join(OUTPUT_DIR, 'jumble-print.html')
    html = build_html(puzzle)
    with open(html_path, 'w') as f:
        f.write(html)
    print(f'  html -> {html_path}')

    with open(DATE_FILE, 'w') as f:
        f.write(puzzle['date'])
    print(f'  date marker -> {DATE_FILE} ({puzzle["date"]})')

    print(f'\nDone! Files in {OUTPUT_DIR}/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
