# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright"]
# ///
"""Render an HTML file to PDF using Playwright's bundled headless Chromium.

Lighter than the system snap chromium: no GPU, no extensions, single process.
Usage: render_pdf.py INPUT.html OUTPUT.pdf
"""
import os
import pathlib
import sys

from playwright.sync_api import sync_playwright

# libasound is the one system lib the headless shell needs that this box lacks
# (no sudo to apt-install it); borrow the copy bundled in the gnome-46 snap.
_ALSA_DIR = pathlib.Path("/snap/gnome-46-2404/current/usr/lib/aarch64-linux-gnu")
if _ALSA_DIR.is_dir():
    os.environ["LD_LIBRARY_PATH"] = (
        f"{_ALSA_DIR}:{os.environ.get('LD_LIBRARY_PATH', '')}".rstrip(":")
    )


def main() -> int:
    if len(sys.argv) != 3:
        print(f"usage: {sys.argv[0]} INPUT.html OUTPUT.pdf", file=sys.stderr)
        return 2
    src = pathlib.Path(sys.argv[1]).resolve()
    dst = pathlib.Path(sys.argv[2]).resolve()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--single-process",
                "--renderer-process-limit=1",
            ]
        )
        page = browser.new_page()
        page.goto(src.as_uri(), wait_until="networkidle")
        page.pdf(path=str(dst), format="Letter", print_background=True)
        browser.close()

    if not dst.is_file() or dst.stat().st_size == 0:
        print(f"error: no PDF written to {dst}", file=sys.stderr)
        return 1
    print(dst)
    return 0


if __name__ == "__main__":
    sys.exit(main())
