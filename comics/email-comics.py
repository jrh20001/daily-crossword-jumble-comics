#!/usr/bin/env python3
"""Email today's comics PDF via Gmail SMTP using an app password.

One-time setup: https://myaccount.google.com/apppasswords
Generate a 16-char app password, then:

    uv run email-comics.py <app-password>
"""

import smtplib
import subprocess
import sys
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "todays-output"
# backfill runs pass COMICS_DATE so filenames/subject match the strip date
TODAY = os.environ.get("COMICS_DATE") or date.today().strftime("%Y-%m-%d")

FROM = "jerryrhinson@gmail.com"
TO = "rahinson58@gmail.com, jerryrhinson@gmail.com, sjhinson@gmail.com, rhinson2010@gmail.com"
# COMICS_SUBJECT_SUFFIX marks a re-send, e.g. " (corrected — all 27 strips)"
SUBJECT = f"Daily Comics — {TODAY}" + os.environ.get("COMICS_SUBJECT_SUFFIX", "")

def main():
    if len(sys.argv) < 2:
        print("Usage: uv run email-comics.py <gmail-app-password>")
        sys.exit(1)

    app_password = sys.argv[1]

    pdf_path = OUTPUT_DIR / f"comics-{TODAY}.pdf"
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        sys.exit(1)

    msg = MIMEMultipart()
    msg["From"] = FROM
    msg["To"] = TO
    msg["Subject"] = SUBJECT
    body = f"Today's comics ({TODAY}) attached."
    missing_file = OUTPUT_DIR / "missing-strips.txt"
    if missing_file.exists():
        missing = [line.strip() for line in missing_file.read_text().splitlines() if line.strip()]
        if missing:
            body += (
                f"\n\nWARNING: {len(missing)} of 27 strips are missing from this PDF:\n  "
                + "\n  ".join(missing)
                + "\n\nGoComics is currently serving a bot-challenge page instead of the strips"
                  " (their side); ComicsKingdom strips are complete. The missing strips will be"
                  " retried on the next run."
            )
    msg.attach(MIMEText(body, "plain"))

    # ponytail: gs compresses 28MB->~4MB, fits under Gmail's 25MB limit
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        subprocess.run([
            "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/ebook", "-dNOPAUSE", "-dQUIET", "-dBATCH",
            f"-sOutputFile={tmp.name}", str(pdf_path),
        ], check=True)
        with open(tmp.name, "rb") as f:
            part = MIMEBase("application", "pdf")
            part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f"attachment; filename=comics-{TODAY}.pdf")
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(FROM, app_password)
        server.send_message(msg)

    print(f"Sent {pdf_path.name} to {TO}")

if __name__ == "__main__":
    main()
