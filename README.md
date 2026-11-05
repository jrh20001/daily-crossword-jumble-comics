# Daily Crossword, Jumble, and Comics

Automated daily downloads of LA Times crossword puzzles, jumble word puzzles, and comic strips.

## What it does

Every day this tool downloads:

- **LA Times Crossword** — `.puz` format (Across Lite), `.pdf`, and `.html` versions
- **Jumble** — Daily jumble word puzzle from the Chicago Tribune
- **Comics** — 27 comic strips: 20 from gocomics.com, 7 from ComicsKingdom
  (arcamax.com mirrors 13 of the GoComics strips as a fallback)

All outputs are saved to organized directories under `daily-crossword-jumble-comics/`.

## Delivery (current settings)

| Item | Delivered how | Recipient(s) | Schedule |
|---|---|---|---|
| Comics | Emailed PDF (`comics/email-comics.py`) | rahinson58, jerryrhinson, sjhinson, rhinson2010 @gmail.com | daily 07:00 |
| Crossword | **Printing suspended** — downloaded and rendered to PDF only, nothing sent to the printer | — | daily 07:05 |
| Jumble | Emailed PDF (`jumbles/email-jumble.py`); **never printed** | rahinson58@gmail.com only | Mon–Sat 07:10 |

- Email is sent from `jerryrhinson@gmail.com` via Gmail SMTP (SSL, port 465) using the app password in `COMICS_PASS` (set in crontab and `comics/.env`).
- Crossword printing is controlled by `CROSSWORD_PRINT`: unset or `0` = no printing (current). To resume printing, add `CROSSWORD_PRINT=1` to the crossword cron line.
- Jumble printing was retired on 2026-10-29; `get-jumble.sh` only emails.
- No puzzle is ever delivered if today's puzzle is missing or stale: both scripts exit before email/print in that case.

## How it works

```
Daily cron ──▶ get-crossword.sh ──▶ xword-dl ──▶ .puz / .pdf / .html   (no print)
              ├── get-jumble.sh ──▶ jumble.py ──▶ PDF ──▶ email-jumble.py ──▶ email
              └── get-comics.sh ──▶ fetch_comicskingdom.py ──┐
                                    fetch_gocomics.py ──────┼─▶ Comics/<Provider>/<Name>/
                                    fetch_arcamax.py ───────┘        │
                                                       harvest.py ───┴─▶ todays-input/ ──▶ aggregate.py ──▶ to-pdf.py ──▶ email-comics.py ──▶ email
```

Three independent shell scripts, each triggered by cron at specific times each morning.

## Directory structure

```
daily-crossword-jumble-comics/
├── crosswords/
│   ├── get-crossword.sh      # Downloads LA Times crossword (printing gated by CROSSWORD_PRINT)
│   ├── render_pdf.py         # Playwright headless-chromium HTML→PDF renderer
│   ├── output/               # Daily .puz, .pdf, .html files
│   ├── puzpy/                # puzpy library for .puz file handling
│   └── xword-dl-main/        # xword-dl crossword downloader tool
├── jumbles/
│   ├── get-jumble.sh         # Downloads daily jumble, renders PDF, emails it
│   ├── email-jumble.py       # Emails jumble PDF to rahinson58@gmail.com
│   ├── jumble.py             # Solves/processes jumble puzzles
│   ├── client.py             # Jumble API client
│   └── output/               # jumble-print.html, jumble-puzzle.pdf, cartoon.png
└── comics/
    ├── get-comics.sh         # Runs the whole comics pipeline and emails the PDF
    ├── comics_sources.py     # Strip inventory: name -> slug per provider (COMICSKINGDOM/GOCOMICS/ARCAMAX)
    ├── fetch_comicskingdom.py# ComicsKingdom strips via their public JSON API
    ├── fetch_gocomics.py     # GoComics strips over plain HTTP (see comics/README.md)
    ├── fetch_arcamax.py      # arcamax.com mirror, fills GoComics gaps
    ├── harvest.py            # Moves the target date's file per strip into todays-input/
    ├── aggregate.py          # Compiles comics into an HTML page
    ├── analyze.py            # Comic analysis tools
    ├── to-pdf.py             # Converts comics to PDF
    ├── email-comics.py       # Emails comics PDF to the four recipients
    ├── README.md             # Comics pipeline + GoComics notes
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

Nothing is printed unless `CROSSWORD_PRINT=1` is set:

```bash
CROSSWORD_PRINT=1 ./get-crossword.sh   # also sends the PDF to Brother-MFC-7840W
```

### Download and email today's jumble

```bash
cd jumbles
export COMICS_PASS='<gmail-app-password>'
./get-jumble.sh
```

`get-jumble.sh` fetches the puzzle, renders `output/jumble-puzzle.pdf`, and emails it to
`rahinson58@gmail.com`. Without `COMICS_PASS` it still fetches and renders, logs
`Email skipped - COMICS_PASS not set`, and exits.

To re-send an already-rendered PDF without re-fetching:

```bash
cd jumbles
uv run email-jumble.py            # reads COMICS_PASS from the environment
# or: uv run email-jumble.py '<app-password>'
```

### Download comic strips

```bash
cd comics
bash get-comics.sh              # today
bash get-comics.sh 2026-11-03   # backfill a date (or COMICS_DATE=2026-11-03 bash get-comics.sh)
```

The strip list is not a config file — it is the `COMICSKINGDOM` / `GOCOMICS` /
`ARCAMAX` tables in `comics/comics_sources.py`. Steps, per-source scripts and the
GoComics bot-wall details are documented in [`comics/README.md`](comics/README.md).

### Email comics as PDF

```bash
cd comics
uv run email-comics.py '<app-password>'
```

### Automate with cron

Current crontab (`crontab -l`):

```cron
COMICS_PASS='<gmail-app-password>'

# Comics: daily fetch + email at 7:00 AM
0 7 * * * cd /home/ubuntu/daily-crossword-jumble-comics/comics && bash get-comics.sh >> /home/ubuntu/daily-crossword-jumble-comics/comics/cron.log 2>&1

# Crosswords: daily fetch at 7:05 AM (printing suspended; CROSSWORD_PRINT=1 re-enables)
5 7 * * * cd /home/ubuntu/daily-crossword-jumble-comics/crosswords && bash get-crossword.sh >> /home/ubuntu/daily-crossword-jumble-comics/crosswords/cron.log 2>&1

# Jumbles: fetch + email at 7:10 AM (Mon-Sat; none published on Sundays)
10 7 * * 1-6 cd /home/ubuntu/daily-crossword-jumble-comics/jumbles && bash get-jumble.sh >> /home/ubuntu/daily-crossword-jumble-comics/jumbles/cron.log 2>&1
```

`COMICS_PASS` is inherited by all cron jobs. Logs are in each module's `cron.log`.

## Comic strip configuration

Strips come from three sources, all listed in `comics/comics_sources.py`:

```python
COMICSKINGDOM = {"Bizarro": "bizarro", "Mutts": "mutts", ...}     # 7 strips
GOCOMICS      = {"Pickles": "pickles", "Garfield": "garfield", ...} # 20 strips
ARCAMAX       = {"Pickles": "pickles", ...}                        # 13 of the 20, as a fallback
```

Slugs are the path component from the provider's site (e.g. `gocomics.com/pickles`).
Add a strip to both the GoComics table and (if arcamax carries it) the ARCAMAX table,
then `mkdir -p Comics/GoComics/<Name>`; `harvest.py` walks whatever directories exist.

### Known breakages and how they were fixed

| Date | Symptom | Cause / fix |
|---|---|---|
| 2026-10-29 | no puzzle printed | printing retired; `CROSSWORD_PRINT=1` re-enables |
| 2026-11-03 | comics email dropped to 7 of 27 | GoComics put Bunny Shield in front of its pages; `dosage` got 403 on every strip. Replaced with per-provider fetch scripts |
| 2026-11-05 | GoComics strips still missing | **the shield only rejects requests with no `Accept-Language` header.** `fetch_gocomics.py` rewritten to plain HTTP: feature landing pages (not shield-gated) + open `featureassets` CDN |

`comics/summary-comics-2026-11-04.md` holds the full investigation and its resolution.

### GoComics rate limit (important)

GoComics answers 403/429 after roughly six to nine feature-page requests per host, then
clears after ~20 minutes. So `get-comics.sh` is layered on purpose:

1. ComicsKingdom (their own API, no limit)
2. GoComics with `--budget 6`, spent on the 7 strips arcamax does not carry
3. arcamax, which fills every GoComics strip it mirrors
4. if GoComics reported incomplete, one retry after 10 minutes picks up the tail

Budget the requests, not the minutes: raising `--budget` only gets you throttled sooner.
