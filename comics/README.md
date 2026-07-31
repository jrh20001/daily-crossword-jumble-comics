# comics

Download, harvest, and aggregate daily comic strips into HTML/PDF, then email the PDF.

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Google Chrome (for PDF generation)
- [dosage](https://github.com/webcomics/dosage) -- `uv tool install dosage`

## Setup

```bash
uv sync
```

To enable emailing: generate a [Gmail app password](https://myaccount.google.com/apppasswords) and add to `~/.bashrc`:

```bash
export COMICS_PASS="abcd efgh ijkl mnop"
```

## Usage

```bash
bash get-comics.sh
```

Runs 5 steps:

1. `dosage @` -- download today's comics into `Comics/`
2. `harvest.py` -- move the newest file from each subdirectory into `todays-input/`, delete old files
3. `aggregate.py` -- generate an HTML page with smart layout (wide=full row, tall+square paired)
4. `to-pdf.py` -- convert HTML to PDF via headless Chrome
5. `email-comics.py` -- send the PDF to the recipient (skipped if `COMICS_PASS` not set)

Output goes to `todays-output/`.

## Per-script

```bash
uv run harvest.py        # collect newest from Comics/ -> todays-input/
uv run aggregate.py      # todays-input/ -> todays-output/comics-YYYY-MM-DD.html
uv run to-pdf.py         # HTML -> PDF
uv run email-comics.py   # email the PDF
```

## Layout

Comics are categorized by aspect ratio:

- **Wide** (>1.5:1) -- full-width row
- **Square** (0.85-1.5) -- side-by-side with tall or other squares
- **Tall** (<0.85) -- paired left with a square or another tall

Adapts to whatever mix arrives each day.