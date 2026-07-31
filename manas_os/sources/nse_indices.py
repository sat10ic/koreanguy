"""Nightly NSE index-close ingest — keeps EVERY index in sector_index_prices
current, including "NIFTY 50" and "India VIX" (which nothing else in the
nightly pipeline was writing).

Gap this closes: ``ingest_mars`` (regime/mars_ingest.py) only writes the MARS
benchmark + the 15 sector indices it iterates (regime.sectors.SECTOR_INDICES);
"NIFTY 50" and "India VIX" were only ever populated by a one-off/manual run of
``scripts/import_nse_index_history.py`` against a *different* on-disk db
(manas_backtest_2y.db), so on the live manas.db those two rows silently went
stale — first surfaced by vol_har.py's HAR-RV forecaster (regime/vol_har.py),
which reads both series and had to add a whole staleness-tolerance mechanism
(MAX_STALENESS_DAYS / nifty_data_asof) to cope with a feed nobody was
refreshing.

Source of truth: NSE's own daily "all index closes" archive —
``https://nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv``
— the same file scripts/import_nse_index_history.py already fetches for
historical backfill. That script writes to manas_backtest_2y.db and is a
one-off/manual tool; this module is the single nightly writer against the
live manas.db, registered as the ``ingest_nse_indices`` pipeline stage (run
right before ``ingest_mars`` in cli/__init__.py's stage list) and reuses the
identical parse logic (parse_float / CSV shape) so there is exactly one
place that understands the NSE index-close CSV format.

NSE's raw "Index Name" column doesn't match the canonical uppercase Fyers-
style symbols the rest of the codebase already uses for some indices (e.g.
CSV says "Nifty Bank", DB/mars_ingest/vol_har expect "NIFTY BANK"). ALIASES
below renames exactly those already-in-use symbols so this stage lands on
the SAME row ingest_mars / vol_har read, instead of creating a duplicate
differently-cased symbol. Any index NOT in ALIASES is written verbatim
under its raw NSE name (matching scripts/import_nse_index_history.py's
existing behavior for the long tail of indices nothing else consumes).
"""
from __future__ import annotations

import csv
import io
import time
from datetime import date

import requests

STAGE = "ingest_nse_indices"
SOURCE = "nse_index_archive"
ARCHIVE_URL = "https://nsearchives.nseindia.com/content/indices/ind_close_all_{datecode}.csv"
MA_LENGTH = 50

# Raw NSE "Index Name" -> canonical symbol already used elsewhere in the
# codebase (regime/sectors.py SECTORS, regime/vol_har.py NIFTY_SYMBOL/
# VIX_SYMBOL). "India VIX" needs no alias — NSE's raw name already matches.
ALIASES: dict[str, str] = {
    "Nifty 50": "NIFTY 50",
    "Nifty Auto": "NIFTY AUTO",
    "Nifty Bank": "NIFTY BANK",
    "Nifty Financial Services": "NIFTY FINANCIAL SERVICES",
    "Nifty FMCG": "NIFTY FMCG",
    "Nifty IT": "NIFTY IT",
    "Nifty Media": "NIFTY MEDIA",
    "Nifty Metal": "NIFTY METAL",
    "Nifty Pharma": "NIFTY PHARMA",
    "Nifty Realty": "NIFTY REALTY",
    "Nifty Energy": "NIFTY ENERGY",
    "Nifty Infrastructure": "NIFTY INFRASTRUCTURE",
    "Nifty PSU Bank": "NIFTY PSU BANK",
    "Nifty Private Bank": "NIFTY PRIVATE BANK",
    "Nifty Consumer Durables": "NIFTY CONSUMER DURABLES",
    "Nifty Oil & Gas": "NIFTY OIL AND GAS",
    "Nifty MidSmallcap 400": "NIFTYMIDSML400",
    # Added 2026-07-30. These five were already in sector_index_prices under
    # uppercase names (written by an earlier one-off import) but were missing
    # from ALIASES, so the nightly stage wrote a SECOND, title-cased row for
    # each. The uppercase series then looked frozen at 2026-07-06 while fresh
    # data accumulated beside it under a name nothing reads -- exactly the
    # duplicate-symbol failure this docstring warns about. They are the five
    # indices the Market Quadrant's MOMENTUM table reports.
    "Nifty Midcap 150": "NIFTY MIDCAP 150",
    "Nifty Smallcap 250": "NIFTY SMALLCAP 250",
    "Nifty Microcap 250": "NIFTY MICROCAP 250",
    "Nifty Next 50": "NIFTY NEXT 50",
    "Nifty 500": "NIFTY 500",
}


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_index_csv(text: str, trade_date: str) -> list[dict]:
    """Pure parser: NSE ind_close_all_*.csv text -> upsert-ready row dicts.

    ``trade_date`` (YYYY-MM-DD) is stamped explicitly rather than trusted from
    the CSV's own "Index Date" column, mirroring
    scripts/import_nse_index_history.py's fetch_day (the CSV's date column is
    display-formatted DD-MM-YYYY and occasionally inconsistent; the caller
    already knows which trading day it asked for).
    """
    text = text.lstrip("﻿")
    if not text.startswith("Index Name"):
        return []
    rows: list[dict] = []
    for row in csv.DictReader(io.StringIO(text)):
        raw_name = (row.get("Index Name") or "").strip()
        close = parse_float(row.get("Closing Index Value"))
        if not raw_name or close is None:
            continue
        symbol = ALIASES.get(raw_name, raw_name)
        rows.append({"symbol": symbol, "trade_date": trade_date, "close": close})
    return rows


def session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/csv,*/*",
            "Referer": "https://www.nseindia.com/",
        }
    )
    sess.get("https://www.nseindia.com", timeout=15)
    return sess

def fetch_index_csv(sess: requests.Session, day: date, retries: int = 2) -> str | None:
    """Fetch the raw CSV text for one calendar day, or None (holiday/no data/error)."""
    url = ARCHIVE_URL.format(datecode=day.strftime("%d%m%Y"))
    for attempt in range(retries + 1):
        try:
            resp = sess.get(url, timeout=20)
            if resp.status_code in {404, 403}:
                return None
            resp.raise_for_status()
            return resp.text
        except requests.RequestException:
            if attempt >= retries:
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def upsert_rows(conn, rows: list[dict]) -> int:
    """Idempotent upsert keyed on (symbol, trade_date) — the schema PK."""
    if not rows:
        return 0
    conn.executemany(
        """
        INSERT INTO sector_index_prices (symbol, trade_date, close)
        VALUES (:symbol, :trade_date, :close)
        ON CONFLICT(symbol, trade_date) DO UPDATE SET
            close=excluded.close, ingested_at=datetime('now')
        """,
        rows,
    )
    _update_sma50(conn, rows)
    return len(rows)


def _update_sma50(conn, rows: list[dict]) -> None:
    """Recompute sma50 for just the rows touched (last MA_LENGTH closes
    at-or-before each row's trade_date), not the whole history — cheap
    enough to run every night for ~160 indices."""
    for r in rows:
        closes = [
            c for (c,) in conn.execute(
                "SELECT close FROM sector_index_prices WHERE symbol=? AND trade_date<=? "
                "ORDER BY trade_date DESC LIMIT ?",
                (r["symbol"], r["trade_date"], MA_LENGTH),
            )
        ]
        if len(closes) < MA_LENGTH:
            continue
        sma = sum(closes) / MA_LENGTH
        conn.execute(
            "UPDATE sector_index_prices SET sma50=? WHERE symbol=? AND trade_date=?",
            (sma, r["symbol"], r["trade_date"]),
        )


def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE, status, rows, duration, detail),
    )


def run(conn, run_date: str, sess: requests.Session | None = None) -> dict:
    """Nightly stage: fetch the NSE all-index-close CSV for run_date and
    upsert every index's (symbol, trade_date, close) row. Failure-safe: any
    network/parse error is a `skip`, never a `fail` — mirrors the other
    ingest stages' per-stage isolation so run-eod never breaks on this."""
    started = time.monotonic()
    try:
        day = date.fromisoformat(run_date)
        s = sess or session()
        text = fetch_index_csv(s, day)
        if not text:
            dur = time.monotonic() - started
            _log_run(conn, run_date, "skip", 0, dur, "no NSE index CSV for date (holiday/unavailable)")
            conn.commit()
            return {"status": "skip", "rows": 0, "detail": "no CSV for date"}

        rows = parse_index_csv(text, run_date)
        if not rows:
            dur = time.monotonic() - started
            _log_run(conn, run_date, "skip", 0, dur, "CSV fetched but 0 parsable rows")
            conn.commit()
            return {"status": "skip", "rows": 0, "detail": "0 parsable rows"}

        written = upsert_rows(conn, rows)
        dur = time.monotonic() - started
        _log_run(conn, run_date, "ok", written, dur, f"indices={written}")
        conn.commit()
        return {"status": "ok", "rows": written, "detail": f"indices={written}"}
    except Exception as exc:  # noqa: BLE001
        dur = time.monotonic() - started
        _log_run(conn, run_date, "skip", 0, dur, f"error: {type(exc).__name__}: {exc}")
        conn.commit()
        return {"status": "skip", "rows": 0, "detail": f"error: {exc}"}
