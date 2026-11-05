# comics

Download, harvest, and aggregate daily comic strips into HTML/PDF, then email the PDF.

## Requirements

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Google Chrome (for PDF generation)

`dosage` is no longer used: GoComics locked it out in Nov 2026 and both providers are
fetched by the scripts below.

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
bash get-comics.sh            # today
bash get-comics.sh 2026-11-03 # backfill a date
```

Steps:

1. `fetch_comicskingdom.py` -- the 7 ComicsKingdom strips, via their public WordPress JSON API
2. `fetch_gocomics.py` -- GoComics strips, via the feature landing pages (see below)
3. `fetch_arcamax.py` -- arcamax.com mirror, fills every GoComics strip it carries (13 of 20)
4. `harvest.py` -- move the file for the target date from each `Comics/` subdirectory into `todays-input/`, delete older ones
5. `aggregate.py` -- generate an HTML page with smart layout (wide=full row, tall+square paired)
6. `to-pdf.py` -- convert HTML to PDF via headless Chrome
7. `email-comics.py` -- send the PDF to the recipients (skipped if `COMICS_PASS` not set)

Output goes to `todays-output/`; a missing-strips list is written to
`todays-output/missing-strips.txt` and named in the email body.

## Per-script

```bash
uv run fetch_comicskingdom.py --date 2026-11-05
uv run fetch_gocomics.py --date 2026-11-05
uv run fetch_arcamax.py --date 2026-11-05
uv run harvest.py --date 2026-11-05   # collect that date from Comics/ -> todays-input/
uv run aggregate.py                   # todays-input/ -> todays-output/comics-YYYY-MM-DD.html
uv run to-pdf.py                      # HTML -> PDF
uv run email-comics.py                # email the PDF
```

## GoComics notes (Nov 2026)

Bunny Shield fronts www.gocomics.com. What actually matters:

- **`Accept-Language` is the whole bot check.** Any request without that header gets
  HTTP 403 "Establishing a secure connection" no matter how browser-like the UA, cookies,
  JS or proof-of-work are. `curl -H 'Accept-Language: en-US,en;q=0.5'` is served fine.
- The shield only guards the **dated routes** (`/<strip>/<date>`) and the Next.js RSC data
  route, and those return an empty app shell even when they answer 200. The **feature
  landing page** `/<strip>` is served normally and embeds that day's strip in its JSON-LD
  (`ImageObject` with `representativeOfPage: true`).
- Strip files on `featureassets.gocomics.com` are open -- no auth, no referer, no cookies.
- **Rate limit:** GoComics answers 403/429 after roughly six to nine feature-page requests
  from one host, then stops throttling after ~20 minutes. `fetch_gocomics.py` therefore
  spends its `--budget` (default 6) on the 7 strips arcamax does *not* mirror, and
  `get-comics.sh` retries once after 10 minutes; arcamax covers the rest.
- A backfill date cannot be fetched from the landing page (it only ever shows the newest
  strip), so older dates come from arcamax. Strips with no arcamax page can only be
  backfilled while they are still the current strip.

Checking it by hand:

```bash
# 200 = not blocked (needs the Accept-Language header)
curl -s -o /dev/null -w '%{http_code}\n' \
  -A 'Mozilla/5.0 (X11; Linux x86_64; rv:158.0) Gecko/20100101 Firefox/158.0' \
  -H 'Accept-Language: en-US,en;q=0.5' https://www.gocomics.com/pickles

uv run fetch_gocomics.py --only TheDuplex --dry-run   # show the image URL it would fetch
```

## Layout

Comics are categorized by aspect ratio:

- **Wide** (>1.5:1) -- full-width row
- **Square** (0.85-1.5) -- side-by-side with tall or other squares
- **Tall** (<0.85) -- paired left with a square or another tall
