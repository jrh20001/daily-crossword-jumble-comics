# Jumble Not Updating — Troubleshooting Report

**Server:** ubuntu@hcontrol.local — `/home/ubuntu/daily-crossword-jumble-comics/jumbles`
**Investigated:** 2026-10-22
**Reported symptom:** since 10/13/2026 the same Jumble is generated and printed every day

## TL;DR

Two independent bugs, both fixed:

1. **Rendering broke on 10/14** — the snap `chromium` binary refuses to run from a cron job
   (`/system.slice/cron.service is not a snap cgroup for tag snap.chromium.chromium`, exit 1,
   no PDF written). It worked until the chromium snap auto-refreshed on the evening of 10/13.
2. **Stale PDF was re-printed** — `get-jumble.sh` only checked *whether* `output/jumble-puzzle.pdf`
   existed, not whether it was new. So each day: fresh puzzle text was fetched, the PDF step
   silently failed, the 10/13 PDF still sat on disk, the check passed, and the old file was
   printed again. This is why the printed page never changed and why the log looked healthy.

The Jumble **data** was never stale; only the PDF and print step were.

## Evidence

### The puzzle data was updating daily

`jumbles/cron.log` shows a new puzzle every run, e.g. 10/19 `EARLYTORISE`, 10/20 `FOODFORTHOUGHT`,
10/21 `EASYASSPY`, 10/22 `RANGEOFTOPICS`. Every entry ends with
`sent to Brother-MFC-7840W` — so the script always claimed success.

### The PDF was frozen at 10/13

```
$ pdfinfo output/jumble-puzzle.pdf
CreationDate:   Tue Oct 13 07:11:00 2026 PDT     <- last PDF actually produced
$ ls -la output/jumble-puzzle.pdf
-rw-rw-r-- 1 ubuntu ubuntu 262675 Oct 13 07:11 jumble-puzzle.pdf
```
Printer jobs 151–162 (10/17–10/22) all printed that same 10/13 file.

### chromium stopped being launched at all

`journalctl` for the 07:10 cron run:

| Date | Result |
|---|---|
| 10/13 07:10 | `Started snap.chromium.chromium-…scope` → PDF written 07:11 |
| 10/14 07:10 | cron session opens 07:10:01, closes 07:10:12 — **no chromium scope, no PDF** |
| 10/22 07:10 | same: 10 s run, no chromium |

The whole job finishing in ~10 s (only the ~5 s API fetch + image download) means chromium exited
immediately and `lp` sent the leftover file.

### What changed on 10/13

`/var/log/syslog.1` shows a **chromium snap auto-refresh on 2026-10-13 ~20:34** (snapd restarts as a
new PID, chromium revisions 3549/3555 mounted). The 10/13 morning run was fine; the first run after
that refresh (10/14 07:10) had no chromium at all. Snapshot now: chromium 155.0.8059.84 (rev 3564),
snapd 2.77.1.

### Reproduced under real cron

A temporary one-shot cron job running the exact render command (crontab restored afterwards):

```
=== Thu Oct 22 10:59:01 PDT 2026
PATH=…:/usr/bin:/bin:/usr/games:/usr/local/games:/snap/bin     <- chromium IS on PATH
/system.slice/cron.service is not a snap cgroup for tag snap.chromium.chromium
chromium exit=1 elapsed=4s
ls: cannot access '…/output/probe2.pdf': No such file or directory
```

So it is **not** a PATH problem. Snap-confine refuses to confine a process whose cgroup is the
`cron.service` system slice instead of a snap-managed/user session scope. The same command run
from an interactive SSH session works fine — which is why hand-testing always succeeded and
under-cron behaviour silently differed.

The same breakage hit the crossword job on 10/14; it was fixed on 10/15 by switching that job to
Playwright's bundled headless chromium (`crosswords/render_pdf.py`). The jumble job was left on
snap chromium and kept failing.

### Why nothing was visible in the log

```bash
timeout 180 chromium … --print-to-pdf="$pdffile" … 2>/dev/null || true
if [ ! -f "$pdffile" ]; then … fi      # old PDF satisfies this forever
```
stderr was discarded, `|| true` swallowed the exit code, and the existence check passed on the
stale file. No `ERROR` line was ever logged.

## Fix (`jumbles/get-jumble.sh`, `jumbles/jumble.py`)

1. **Renderer replaced** — snap chromium → Playwright bundled chromium via
   `jumbles/render_pdf.py` (copied from the crosswords job; proven to work under cron here).
   Up to 3 attempts, gated on a non-empty PDF, stderr no longer discarded.
2. **Stale artifacts deleted first** — `jumble-puzzle.pdf`, `jumble-print.html` and the date marker
   are removed at the start of every run, so a failed render can never hand an old file to `lp`.
3. **Print only a genuinely current Jumble** — `jumble.py` now:
   - fetches **today only** and drops the old "fall back up to 3 days" behaviour
     (that fallback is exactly how an old puzzle could be printed as today's);
   - exits `3` when nothing is published today → script logs
     `no Jumble published for today - skipping print` and prints nothing, exit 0;
   - exits `4` when the API returns a puzzle not dated today → script logs the error and prints
     nothing;
   - writes `output/jumble-date.txt` on success, and the shell re-checks it against `date +%m/%d/%Y`
     before rendering/printing.
4. **Loud failures** — a missing PDF now logs `ERROR: … nothing printed` and exits 1 instead of
   silently printing yesterday's page.
5. Backups: `get-jumble.sh.bak-20261022`, `jumble.py.bak-20261022`.

## Verification

| Test | Result |
|---|---|
| Real cron run of `get-jumble.sh` (temporary probe job) | fetched 10/22 puzzle, rendered via Playwright, `request id is Brother-MFC-7840W-163` — PDF `CreationDate: Thu Oct 22 2026`, text confirms `Jumble — Thursday, October 22, 2026` |
| Puzzle is dated yesterday (mocked client, `10/21/2026`) | `ERROR: puzzle is dated 10/21/2026, not today - not printing`, exit 4, no PDF produced |
| No puzzle published (mocked `None`) | `Nothing published today - not printing`, exit 3, no PDF produced |
| PDF / HTML / date marker after failures | removed, nothing printed |

Crontab was restored to its original contents (the temporary probe entries are gone).

**Side effect to be aware of:** the verification cron probe fired once a minute for four minutes,
so today's (correct) Jumble was printed about four times — jobs `163`–`166`. No other days were
reprinted; 10/14–10/22 were already printed with the stale 10/13 page.

## Notes / follow-ups

- `jumbles` is on a Raspberry Pi (6.8.0-raspi, ~899 MB RAM). Playwright uses one process and is
  fast; the snap chromium path was slow (57–103 s) even when it worked.
- If snap chromium is ever wanted again under cron it must be launched inside a managed scope
  (`systemd-run --scope --user …`), not directly from the crontab; simplest is to keep Playwright.
- The next real cron run is 07:10 tomorrow (Mon–Sat, 1-6 — the Jumble is not published Sundays),
  falling back to "no Jumble published for today - skipping print" on any unpublished day.

## Note on crontab during this investigation

To observe the real cron environment, temporary probe jobs were added to the ubuntu crontab and then
removed. During that process the crontab was briefly replaced with a near-empty file; it has been
restored to its original 4 entries (comics 07:00, crosswords 07:05, jumbles 07:10 Mon–Sat, music
server @reboot), and the `COMICS_PASS` value was verified unchanged (hash match). No scheduled job
was missed: nothing is scheduled outside 07:00–07:11 and @reboot, and the disruption was ~11:00.
