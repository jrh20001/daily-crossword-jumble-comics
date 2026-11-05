# Daily Comics — Missing GoComics Strips (11/3 & 11/4) — Troubleshooting Report

**Server:** ubuntu@hcontrol.local — `/home/ubuntu/daily-crossword-jumble-comics/comics`
**Investigated:** 2026-11-04 (evening)
**Reported symptom:** the daily comics email went out on 11/3 and 11/4, but fewer than half the strips were in it.

> Note: the request mentioned the `crosswords` directory; this job is in `comics/` (the only one that
> generates and emails comics). Crosswords only downloads and prints one LA Times puzzle, and that
> job completed normally on both days (`crosswords/output/LA Times - 20261103.pdf`, `…20261104.pdf`).

## TL;DR

**GoComics put its comic pages behind a Bunny Shield JS proof-of-work bot wall around 2026-11-02/03.**
`dosage` — the scraper the job used — is a plain HTTP client, so all 20 GoComics strips started
failing on 11/3. The 7 ComicsKingdom strips kept working, and the email was still sent, so each
"daily comics" PDF since then contains only 7 of 27 strips.

The job also reported success the whole time: `dosage` logged the failures but exited **0**, so
`get-comics.sh` printed `Fetched 27 strips, 0 failures` and never aborted.

## Evidence

### 11/3 is the first bad day (11/2 was complete)

`comics/cron.log`:

| Run | GoComics `Saved` | GoComics `ERROR` | Email sent |
|---|---|---|---|
| 2026-11-02 | 20 | 0 | `Sent comics-2026-11-02.pdf …` |
| 2026-11-03 | 0 | 20 | `Sent comics-2026-11-03.pdf …` |
| 2026-11-04 | 0 | 20 | `Sent comics-2026-11-04.pdf …` |

Every failing strip logs the same thing (truncated in the log):

```
GoComics/Garfield> Retrieving 1 strip
GoComics/Garfield> ERROR: XPath //div[contains(@class, "__showComicViewer__comic")]
                  //script[@type="application/ld+json"]/text() not found at URL
                  https://www.gocomics.com/garfield.
```

`todays-input/` after the 11/4 run held exactly 7 files, all ComicsKingdom:

```
ComicsKingdom_Bizarro_bizarro_2026-11-04.jpg … ComicsKingdom_Zits_zits_2026-11-04.jpg
```

### Why "27 strips, 0 failures" was logged

`get-comics.sh` counted successes with `if dosage "$name"; then ok=… else fail=… fi`.
On 11/3–11/4 `dosage` printed the ERROR but **exited 0**, so 20 failed strips were counted as
successes. (Re-running `dosage Garfield` today, with the site returning 403, exits 1 — the accounting
was only accidental.)

### The site itself changed

Plain HTTP clients now get a bot wall instead of the page:

```
$ curl -A "<browser UA>" https://www.gocomics.com/garfield
HTTP 403, 2182 bytes
<title>Establishing a secure connection ...</title>
<script src="/.bunny-shield/assets/shield-challenge.js"></script>
```

* The challenge page embeds a proof-of-work (`data-pow="…"`) solved in Web Workers, then POSTs to
  `/.bunny-shield/verify-pow`; success sets a `bunny_shield` cookie.
* `curl`/`requests`/`dosage` can never solve it → permanent 403 for those clients.
* Under repeated probing the same IP gets `429 Too Many Requests` (Bunny CDN) on comic routes, which
  is what happened during this investigation (the homepage keeps returning 200 because it is cached).
* The challenge iframe asset `https://shield-templates-prod.b-cdn.net/33498/challenge.html` returns
  404, so even real browsers can get stuck in the shield loop — a GoComics/Bunny misconfiguration.
* `r.jina.ai` (a third-party browser-based fetcher, different IP) also got the shield page, confirming
  this is server-side and not a local networking problem.
* A headless Chromium (Playwright) **does** solve the PoW — observed the `bunny_shield` cookie being
  issued after ~25–30 s — so a real browser is the viable client.

### Attempted alternative: Camoufox on the Pi (per suggestion)

Installed `camoufox` (v158.0.1-beta.41, `lin.arm64`, 1.3 GB) with `uv tool install camoufox` +
`camoufox fetch`. It does not run on this ARM box:

* `libxul.so` needs a newer NSS than the system provides (`NSS_3.126 not found`); the bundled
  `libnss3.so` can be forced via `LD_LIBRARY_PATH`, but
* Firefox then hangs at Playwright launch/navigation (even `https://example.com` times out), and
* it would not have helped: the site is currently returning 429/403 to every client from this IP,
  including jina.ai's servers.

Playwright's Chromium (already used by the crossword/jumble jobs on this box) stays the renderer.

## Fix (deployed)

`dosage` is no longer used for either provider. Two small fetchers replace it:

| File | Purpose |
|---|---|
| `comics_sources.py` | strip name → provider slug tables (the 7 ComicsKingdom + 20 GoComics strips) |
| `fetch_comicskingdom.py` | ComicsKingdom via their public WordPress JSON API (`wp.comicskingdom.com/wp-json/wp/v2/ck_comic`); `--date` supported |
| `fetch_gocomics.py` | GoComics via headless Chromium: solves the Bunny Shield PoW once, caches cookies in `.gocomics-cookies.json`, then fetches each strip page and reads the JSON-LD image URL |
| `harvest.py` | new `--date` flag (picks the strip for that date instead of "newest"); deletes other dates |
| `aggregate.py`, `to-pdf.py`, `email-comics.py` | honour `COMICS_DATE` so backfills get the right filenames/subject |
| `get-comics.sh` | date argument (`bash get-comics.sh 2026-11-03`), direct fetchers, real file-count check |

Other behaviour changes:

* **Honest accounting.** The step now counts files actually written to `todays-input/` and logs
  `WARN: only N of 27 strips for <date>` instead of trusting the scraper's exit code.
* **No silent partial emails.** If nothing at all is fetched the run aborts before emailing; a partial
  run is still emailed (better than nothing) but flagged in the log.
* **Backfill support.** `COMICS_DATE`/`--date` throughout, so a missed day can be regenerated and
  emailed with the correct date.
* **Pacing.** `fetch_gocomics.py` waits 20–25 s between strips and backs off 5–10 min on 429, so the
  daily run stays under the rate limit (it takes ~8 min, still well before 07:00+).

Backups of everything replaced: `get-comics.sh.bak-20261104`, `harvest.py.bak-20261104`,
`aggregate.py.bak-20261104`, `to-pdf.py.bak-20261104`, `email-comics.py.bak-20261104`.

## Status

* ComicsKingdom backfill **done**: 7/7 strips downloaded for both 2026-11-03 and 2026-11-04.
* GoComics backfill **blocked by the site**: after the initial probing the IP was rate-limited
  (`429`) on comic routes; requests were paused to let the window reset. The fetcher has been shown to
  solve the shield, but a full 20-strip run could not be completed while the throttle was active.
* The 11/3 and 11/4 emails that went out contained 7 strips each; they need to be resent once the
  GoComics strips are fetched.

## Follow-ups

* GoComics changes (new shield, markup changes) will keep breaking plain scrapers; the browser-based
  fetcher is the mitigation, and a `WARN: only N of 27` line in `cron.log` is now the early warning.
* `dosage` is now unused by this job (only `Comics/*/` history references it) and can be removed from
  the box.
* GoComics' own shield template is currently broken (404 on the challenge iframe). If 403s persist for
  the Pi even without hammering, the daily email will keep missing those 20 strips until they fix it —
  worth reporting to GoComics support if it lasts more than a day.

## Final status (2026-11-04 22:35 PST)

* ComicsKingdom: **7/7 strips fetched for 2026-11-03 and 2026-11-04** (`Comics/ComicsKingdom/*/<slug>_<date>.jpg`).
* GoComics: **still refused** — `429 Too Many Requests` from Bunny CDN on every comic route, for
  plain HTTP clients, for headless Chromium after it solves the PoW, for a valid `bunny_shield`
  cookie, and for third-party fetchers (jina.ai). The 15–90 minute quiet windows only reset the
  block to a 403 challenge, after which the next solved request is throttled again. GoComics' own
  challenge template (`shield-templates-prod.b-cdn.net/33498/challenge.html`) is 404, so the shield
  cannot be completed cleanly — this is a fault on GoComics' side, not something the Pi can fix.
* Consequence: the 20 GoComics strips for 11/3 and 11/4 could not be regenerated, so no complete
  PDF exists for those days yet and no corrected email was sent (resending the 7-strip PDF would
  repeat the original complaint).
* Retry path (idempotent, skips files already present):
  ```bash
  cd /home/ubuntu/daily-crossword-jumble-comics/comics
  COMICS_PASS='<app password>' bash get-comics.sh 2026-11-03
  COMICS_PASS='<app password>' bash get-comics.sh 2026-11-04
  ```
  Tomorrow's 07:00 cron does the same for 11/5 automatically; `cron.log` will show
  `WARN: only N of 27 strips` if GoComics is still refusing.

## Camoufox cleanup

`camoufox` (1.3 GB browser + tool env) was installed to test the suggestion but does not run on this
ARM box (NSS version mismatch, Firefox hangs at launch). Remove with:

```bash
camoufox remove --all && ~/.local/bin/uv tool uninstall camoufox
```

## 2026-11-05 run (follow-up)

`cron.log` for the 07:00 run:

```
ComicsKingdom: 7 ok, 0 failed (date 2026-11-05)
=== Step 2b/6: GoComics ===
     challenged (attempt 1); running proof-of-work...
     rate limited (429) by GoComics
FAIL GoComics/AdamAtHome: page status 429
... 3 strips ...
ERROR: GoComics is blocking this host; aborting run
Fetched 7 of 27 strips for 2026-11-05 (ComicsKingdom rc=0, GoComics rc=1)
WARN: only 7 of 27 strips for 2026-11-05
Sent comics-2026-11-05.pdf ...
```

The header/trace of a live attempt shows what actually happens:

```
RESP 403  https://www.gocomics.com/pickles/2026/11/05   cdn-cache: MISS
RESP 200  https://www.gocomics.com/.bunny-shield/assets/shield-worker.js
RESP 200  https://www.gocomics.com/.bunny-shield/verify-pow       <- PoW accepted…
RESP 403  https://www.gocomics.com/pickles/2026/11/05             <- …cookie still refused
   (x5, then)
title: 429 Too Many Requests
```

* The shield's challenge iframe is **404 for everyone** (`shield-templates-prod.b-cdn.net/33498/challenge.html`,
  from both the Pi and another network, with or without a GoComics Referer/Origin).
* `verify-pow` keeps returning 200, a `bunny_shield` cookie is set, and the very next request to the
  strip URL is still 403. After ~5 rounds the edge answers 429.
* Conclusion: **GoComics' bot-wall deployment is broken**. No client-side change can fix it: a plain
  scraper gets 403, a real headless Chromium gets 403 after solving, jina.ai's browsers (other IPs)
  get 403, and the challenge's own template is missing. This needs GoComics/Andrews McMeel to fix.

## Two pipeline changes added (2026-11-05)

1. **The email now says what is missing.** `get-comics.sh` writes `todays-output/missing-strips.txt`
   and `email-comics.py` puts a `WARNING: N of 27 strips are missing` block naming them into the mail
   body, so a 7-of-27 PDF no longer looks complete. Verified with a fake SMTP transport (nothing sent).
2. **One delayed retry.** If the GoComics fetch fails, `get-comics.sh` sleeps 10 minutes and retries
   once (already-downloaded strips are skipped), catching a transient block without a second email.

## Camoufox: installed, but cannot work on this box

* `uv tool install camoufox` + `camoufox fetch` succeeded (v158.0.1-beta.41, `lin.arm64`, 1.3 GB).
* The browser binary only starts with `LD_LIBRARY_PATH` pointing at its own directory (bundled
  `libnss3.so`; the system NSS is too old: `NSS_3.126 not found`) plus the gnome snap for
  `libasound.so.2`. With that: `Camoufox 158.0.1-beta.41` / `--version` works.
* Driven through Playwright it launches in ~29 s, but **navigation never completes** — even
  `https://example.com` times out after 60 s and the GoComics navigation is interrupted, i.e. the
  embedded Firefox has no working network/TLS path here (unprivileged-userns sandbox is also denied:
  `unshare(CLONE_NEWPID): EPERM`).
* Even if it worked, it would not have helped: the site rejects every solved session (see above), and
  jina.ai's independent browsers get the same 403.

Cleanup if wanted: `camoufox remove --all && uv tool uninstall camoufox`.

## Fix: Arcamax mirror for the GoComics strips (2026-11-05)

No proxy can help (verified: GoComics' homepage returns 200 while every comic route
403s/429s for our IP, and `r.jina.ai` — a different datacenter IP — gets the same
"Establishing a secure connection" shield page, so a fresh IP just hits the same
broken wall). Instead the job now mirrors the GoComics strips from **arcamax.com**,
which publishes most of the same strips as plain HTML with no bot wall.

**`fetch_arcamax.py`** (new) + `ARCAMAX` map in `comics_sources.py`:

* 13 strips have an arcamax page: BabyBlues, DaddysHome, Doonesbury,
  ForBetterOrForWorse, Garfield, GetFuzzy, Luann, NonSequitur, PearlsBeforeSwine,
  Pickles, RoseIsRose, WallaceTheBrave, WizardOfId.
* Strip image is read from the page's share link (`…&media=<img>&description=<Name>
  for M/D/YYYY`), so the date is verified, not guessed. Daddy's Home publishes no
  date in its caption, so the newest strip is accepted only on a same-day run and
  logged as `(date unverified)`; backfills refuse it.
* WizardOfId is stale on arcamax (newest 11/1), so it is reported missing.
* Writes `Comics/GoComics/<Name>/<slug>_<YYYYMMDD>.gif` — same tree as the GoComics
  fetcher, so `harvest.py`/`aggregate.py` (which already handled gif) need no change.
* `get-comics.sh` order: ComicsKingdom → GoComics → **Arcamax fallback** → one
  10-minute GoComics retry for whatever arcamax does not carry (`SKIP_GC_RETRY=1`
  skips that retry, used for manual backfills).

### Results

| date | strips | detail |
|---|---|---|
| 2026-11-05 | **19/27** | 7 ComicsKingdom + 12 arcamax; emailed |
| 2026-11-04 | **18/27** | 7 ComicsKingdom + 11 arcamax; emailed (backfill) |
| 2026-11-03 | 7/27 | arcamax only keeps ~2 days, so no backfill possible |

Still missing every day until GoComics' shield is fixed (no arcamax equivalent):
AdamAtHome, CalvinAndHobbes, FrankAndErnest, JumpStart, Overboard, ShermansLagoon,
TheDuplex (+ WizardOfId, which arcamax stopped updating on 11/1).

Verified in the generated PDFs: arcamax GIFs render correctly (checked pages 2 and 4
of `comics-2026-11-05.pdf`), and both emails carry the `WARNING: N of 27 strips are
missing` list.

### Strip width normalisation (2026-11-05, later)

Arcamax serves 600px-wide strips while the ComicsKingdom assets are 975-1950px and the
GoComics originals were wider still, so the mirrored strips rendered visibly narrower
on the page. `fetch_arcamax.py` now normalises them:

* `normalise()` upscales anything narrower than `--width` (default **1200 px**) with
  LANCZOS, then quantises to a 128-colour palette PNG (`optimize=True`).
  Result per strip: 600x172 GIF 58 KB -> 1200x344 PNG ~142 KB.
* `--width 0` disables it. Files are written as `.png` instead of `.gif`.
* Rebuilt PDFs: 11/5 = 8.1 MB (19 strips), 11/4 = 7.4 MB (18 strips). Verified by
  rendering pages 4-5: the mirrored strips now fill the text column exactly like the
  ComicsKingdom ones.

---

## Resolution (2026-11-05): the shield was a missing header, not a bot wall

Re-diagnosed from the host itself. The "JS proof-of-work wall" was a red herring.

**Root cause:** Bunny Shield rejects any request that does not send `Accept-Language`.
Nothing else matters — UA, cookies, `Sec-Fetch-*`, executing JS and solving the PoW all
change nothing, while adding one header turns 403 into 200:

```
curl -A "<firefox UA>"                       https://www.gocomics.com/pickles/2026-11-05  -> 403
curl -A "<firefox UA>" -H "Accept-Language: en-US,en;q=0.5" ...                        -> 200
```

dosage, requests, curl and wget never sent that header, which is why every plain client
was permanently "challenged". The PoW still exists and still verifies (argon2id, t=2,
m=512 KiB, 32-byte digest, "00" prefix — solvable in ~0.8 s in Python), but it is not
needed.

**Second finding:** even when the dated strip route answers, it returns an empty app shell
(the strip is drawn client-side from a Next.js RSC payload, and the RSC route *is* shield
gated). The **feature landing page** `/<strip>` is not, and embeds the day's strip in its
JSON-LD (`ImageObject`, `representativeOfPage: true`). Strip files on
`featureassets.gocomics.com` are open — no auth, referer or cookies.

**Fix shipped** (`fetch_gocomics.py`, rewritten, ~330 lines -> plain `urllib`, no Playwright,
no PoW):

- one GET `https://www.gocomics.com/<slug>` + one GET for the image, per strip;
- JSON-LD parse with an inline-RSC-payload fallback, and the page date is checked against
  `--date` so a wrong-day image can never be filed;
- file extension now follows the real bytes (GoComics serves GIF/PNG today, not JPEG);
- **rate limit:** 403/429 starts after roughly six to nine feature pages per host, then
  clears in ~20 min. So `--budget` (default 6) is spent on the 7 strips arcamax does not
  mirror, and `get-comics.sh`'s existing 10-minute retry pass picks up the tail;
- backfill dates are reported as unavailable (the landing page only ever shows the newest
  strip) and are left to arcamax, which mirrors 13 of the 20.

**Verified on the host:** full `bash get-comics.sh 2026-11-05` (email suppressed) produced
**27 of 27** strips, `missing strips: 0`, a 10-page PDF, and the PDF page 1 renders the
correct 11/5 strip. Before the fix the same run produced 7 of 27.
