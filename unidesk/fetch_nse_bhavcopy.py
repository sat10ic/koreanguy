"""Fetch today's/most-recent NSE bhavcopy straight from the official NSE
archives (archives.nseindia.com) — public, no credentials, per the project's
NSE-public-files policy (D9 / Phase 0 spec).

Writes sec_bhavdata_full_<DDMMYYYY>.csv into data/bhavcopy/ so the existing
ingest/scan path picks it up untouched. This is only an EXTRACT; the
available-at timestamp convention (18:00 IST session day) is enforced by the
ingestor at load time."""
from __future__ import annotations

import sys
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "data" / "bhavcopy"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) research-eod"}

MONTHS = {1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN",
          7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"}


def try_url(url: str, timeout: int = 45) -> bytes | None:
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as exc:
        print(f"  HTTP {exc.code} for {url}")
    except Exception as exc:
        print(f"  failed {url}: {exc}")
    return None


def fetch_for(d: date) -> bool:
    dd = f"{d.day:02d}"
    mm = f"{d.month:02d}"
    mmm = MONTHS[d.month]
    yyyy = str(d.year)
    out = OUT_DIR / f"sec_bhavdata_full_{dd}{mm}{yyyy}.csv"
    if out.exists() and out.stat().st_size > 100_000:
        print(f"  already present: {out.name}")
        return True

    # 1) NSE full bhavcopy (sec_bhavdata_full, matches our 15-col schema)
    url1 = (f"https://archives.nseindia.com/products/content/"
            f"sec_bhavdata_full_{dd}{mm}{yyyy}.csv")
    print(f"  trying NSE archives: {url1}")
    data = try_url(url1)
    if data and len(data) > 100_000:
        out.write_bytes(data)
        print(f"  -> saved {out.name} ({len(data):,} bytes)")
        return True

    # 2) NSE historical bhavcopy zip (cm-DD-MMM-YYYY)
    url2 = (f"https://archives.nseindia.com/content/historical/EQUITIES/"
            f"{yyyy}/{mmm}/cm{dd}{mmm}{yyyy}bhav.csv.zip")
    print(f"  trying NSE historical zip: {url2}")
    data = try_url(url2)
    if data and len(data) > 10_000:
        import io, zipfile
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
            name = z.namelist()[0]
            csv_bytes = z.read(name)
        except Exception as exc:
            print(f"  zip parse failed: {exc}")
            return False
        # Convert cm format (SYMBOL,SERIES,...) to sec_bhavdata_full name but
        # the cm schema differs slightly (SYMBOL,SERIES,DATE1,... is the same
        # 15-col; both parse with our _COLUMNS map). Save under the cm name
        # so ingest dedupe (seen set, sorted order) still works.
        out_cm = OUT_DIR / name
        out_cm.write_bytes(csv_bytes)
        print(f"  -> saved {out_cm.name} ({len(csv_bytes):,} bytes)")
        return True

    print("  NSE archive had neither file — may still be unpublished")
    return False


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    print(f"Targeting today (system clock): {today}")
    ok_today = fetch_for(today)
    if not ok_today:
        # last weekday
        d = today
        tried = []
        for _ in range(7):
            d = d - timedelta(days=1)
            if d.weekday() < 5:
                tried.append(d)
                print(f"Falling back to last weekday {d}:")
                if fetch_for(d):
                    ok_today = True
                    break
        if not ok_today:
            print("No file obtainable for the last few weekdays.")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())