# Daily Crossword, Jumble, and Comics

Automated daily downloads of LA Times crossword puzzles, jumble word puzzles, and comic strips.

## What it does

Every day this tool downloads:

- **LA Times Crossword** — `.puz` format (Across Lite), `.pdf`, and `.html` versions
- **Jumble** — Daily jumble word puzzle from the Chicago Tribune
- **Comics** — Multiple comic strips from gocomics.com

All outputs are saved to organized directories and can be emailed or printed automatically.

## How it works

```
Daily cron ──▶ get-crossword.sh ──▶ xword-dl ──▶ .puz / .pdf / .html
              ├── get-jumble.sh ──▶ jumble.py ──▶ jumble output
              └── get-comics.sh ──▶ harvest.py ──▶ comic images
```

Three independent shell scripts, each triggered by cron at specific times each morning.

## Directory structure

```
daily-crossword-jumble-comics/
├── crosswords/
│   ├── get-crossword.sh      # Downloads LA Times crossword
│   ├── output/               # Daily .puz, .pdf, .html files
│   ├── puzpy/                # puzpy library for .puz file handling
│   └── xword-dl-main/        # xword-dl crossword downloader tool
├── jumbles/
│   ├── get-jumble.sh         # Downloads daily jumble
│   ├── jumble.py             # Solves/processes jumble puzzles
│   ├── client.py             # Jumble API client
│   └── pi-session-*.html     # Daily jumble output
└── comics/
    ├── get-comics.sh         # Downloads comic strips
    ├── harvest.py            # Comic strip harvester
    ├── aggregate.py          # Compiles comics into collections
    ├── analyze.py            # Comic analysis tools
    ├── email-comics.py       # Emails comics as PDF
    ├── to-pdf.py             # Converts comics to PDF
    └── comics-list.txt       # Configured comic strip list
```

## Installation

### Prerequisites

```bash
sudo apt-get install curl jq python3 python3-pip
pip install puzpy
```

### Comic strip harvester

```bash
cd comics
uv sync  # or: pip install -r requirements.txt
```

### xword-dl (crossword downloader)

```bash
cd crosswords/xword-dl-main
uv sync  # or: pip install .
```

## Usage

### Download today's crossword

```bash
cd crosswords
./get-crossword.sh
```

Output files in `crosswords/output/`:
- `LA Times - YYYYMMDD.puz` — Across Lite format
- `LA Times - YYYYMMDD.pdf` — Printable PDF
- `LA Times - YYYYMMDD.html` — HTML version

### Download today's jumble

```bash
cd jumbles
./get-jumble.sh
```

### Download comic strips

Edit `comics/comics-list.txt` with the comic strip slugs you want, then:

```bash
cd comics
./get-comics.sh
```

### Email comics as PDF

```bash
cd comics
python3 email-comics.py
```

### Automate with cron

```bash
# Add to crontab (runs at 6am daily)
0 6 * * * /path/to/crosswords/get-crossword.sh
5 6 * * * /path/to/jumbles/get-jumble.sh
10 6 * * * /path/to/comics/get-comics.sh
```

## Comic strip configuration

Edit `comics/comics-list.txt` — one comic slug per line:

```
calvinandhobbes
dilbert-classics
garfield
peanuts
foxTrot
```

Comic slugs are the path component from gocomics.com (e.g., `gocomics.com/calvinandhobbes`).