v# jumble-master

Fetch today's Jumble puzzle from the Tribune Content Agency, save the cartoon image and a printable PDF.

## Requirements

- Python >= 3.11
- Google Chrome (for PDF generation)
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Quick Start

```bash
uv sync
uv run python jumble.py
```

This creates an `output/` directory containing:

- `cartoon.png` -- the daily cartoon image
- `jumble-print.html` -- printable HTML layout
- `jumble-puzzle.pdf` -- single-page PDF ready to print

## How It Works

1. Fetches today's puzzle data from the Tribune Content Agency API
2. Falls back to previous days if today's isn't available (e.g. Sundays)
3. Downloads the cartoon image
4. Generates an HTML page with the scrambled words, answer grids (with circles), caption, and bonus answer blanks
5. Renders the HTML to PDF using headless Chrome