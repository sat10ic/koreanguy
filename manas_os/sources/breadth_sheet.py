"""Breadth Google Sheet ingestion adapter (P0).

The breadth sheet is published as CSV. We fetch it, parse each row into a
`breadth_daily`-shaped dict, and upsert idempotently on the trade_date PK. A
`pipeline_runs` row (stage='ingest_breadth') records the outcome.

Network access is isolated in `_fetch_csv`/`run`; `parse_breadth_csv` is pure
and covered by a fixture test.
"""
from __future__ import annotations

import csv
import io
import time
from datetime import datetime

import requests

from manas_os import config

STAGE = "ingest_breadth"
SOURCE = "breadth_sheet"

# Sheet header -> breadth_daily column. Header lookup is case-insensitive and
# whitespace-normalized (see `_norm`), so minor spacing changes don't break us.
_COLUMN_MAP: dict[str, str] = {
    "advances": "advances",
    "declines": "declines",
    "up 4% (daily)": "up_4pct",
    "down 4% (daily)": "down_4pct",
    "up 25% (monthly)": "up_25pct_month",
    "down 25% (monthly)": "down_25pct_month",
    "up 50% (monthly)": "up_50pct_month",
    "down 50% (monthly)": "down_50pct_month",
    "% above 10 dma": "pct_above_10dma",
    "% above 20 dma": "pct_above_20dma",
    "% above 40 dma": "pct_above_40dma",
    "% 10 dma > 20 dma": "pct_10dma_gt_20dma",
    "% 20 dma > 40 dma": "pct_20dma_gt_40dma",
    "nifty": "nifty",
    "nifty chg %": "nifty_chg_pct",
}

# Which target columns are integers vs floats.
_INT_COLS = {
    "advances", "declines", "up_4pct", "down_4pct",
    "up_25pct_month", "down_25pct_month", "up_50pct_month", "down_50pct_month",
}


def _norm(header: str) -> str:
    return " ".join(header.strip().lower().split())


def _clean_number(raw: str) -> str | None:
    """Strip %, commas, whitespace; return None for blanks/dashes."""
    if raw is None:
        return None
    s = raw.strip().replace(",", "").replace("%", "").strip()
    if s == "" or s in {"-", "--", "NA", "N/A", "#N/A"}:
        return None
    return s


def _to_int(raw: str) -> int | None:
    s = _clean_number(raw)
    if s is None:
        return None
    # tolerate values that arrive as floats ("120.0")
    return int(round(float(s)))


def _to_float(raw: str) -> float | None:
    s = _clean_number(raw)
    return None if s is None else float(s)


_DATE_FORMATS = (
    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
    "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%b %d, %Y", "%d-%B-%Y",
)


def _to_iso_date(raw: str) -> str | None:
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_breadth_csv(text: str) -> list[dict]:
    """Pure parser: CSV text -> list of breadth_daily-shaped dicts.

    Rows without a parseable Date are skipped. Numeric fields are typed and
    defensively cleaned (%, commas, blanks). `trade_date` is normalized to ISO.
    """
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return []

    # Map normalized header -> actual fieldname in this CSV.
    header_by_norm = {_norm(h): h for h in reader.fieldnames if h is not None}
    date_field = next(
        (header_by_norm[n] for n in ("date",) if n in header_by_norm), None
    )

    rows: list[dict] = []
    for raw_row in reader:
        iso = _to_iso_date(raw_row.get(date_field)) if date_field else None
        if iso is None:
            continue  # skip header echoes, blank/total rows, unparseable dates
        rec: dict = {"trade_date": iso, "source": SOURCE}
        for norm_header, col in _COLUMN_MAP.items():
            src = header_by_norm.get(norm_header)
            raw_val = raw_row.get(src) if src else None
            rec[col] = _to_int(raw_val) if col in _INT_COLS else _to_float(raw_val)
        rows.append(rec)
    return rows


_UPSERT_COLS = [
    "trade_date", "advances", "declines", "up_4pct", "down_4pct",
    "up_25pct_month", "down_25pct_month", "up_50pct_month", "down_50pct_month",
    "pct_above_10dma", "pct_above_20dma", "pct_above_40dma",
    "pct_10dma_gt_20dma", "pct_20dma_gt_40dma", "nifty", "nifty_chg_pct", "source",
]


def upsert_rows(conn, rows: list[dict]) -> int:
    """Idempotent upsert on trade_date PK. Returns row count written."""
    if not rows:
        return 0
    placeholders = ", ".join("?" for _ in _UPSERT_COLS)
    updates = ", ".join(f"{c}=excluded.{c}" for c in _UPSERT_COLS if c != "trade_date")
    sql = (
        f"INSERT INTO breadth_daily ({', '.join(_UPSERT_COLS)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT(trade_date) DO UPDATE SET {updates}, "
        f"ingested_at=datetime('now')"
    )
    conn.executemany(sql, [[r.get(c) for c in _UPSERT_COLS] for r in rows])
    return len(rows)


def _fetch_csv(url: str) -> str:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def _log_run(conn, run_date: str, status: str, rows: int, dur: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, dur, detail),
    )


def run(conn, run_date: str) -> dict:
    """Fetch + parse + upsert the breadth sheet; write a pipeline_runs row.

    Returns {status, rows_affected, detail}. Failures are recorded (status='fail')
    and re-raised so the orchestrator's per-stage isolation reports them.
    """
    started = time.monotonic()
    url = config.get("sources.breadth_sheet_csv_url", "")
    if not url:
        dur = time.monotonic() - started
        _log_run(conn, run_date, "skip", 0, dur, "no breadth_sheet_csv_url configured")
        conn.commit()
        return {"status": "skip", "rows_affected": 0, "detail": "no url configured"}
    try:
        text = _fetch_csv(url)
        rows = parse_breadth_csv(text)
        written = upsert_rows(conn, rows)
        dur = time.monotonic() - started
        detail = f"parsed {len(rows)} rows, upserted {written}"
        _log_run(conn, run_date, "ok", written, dur, detail)
        conn.commit()
        return {"status": "ok", "rows_affected": written, "detail": detail}
    except Exception as exc:
        dur = time.monotonic() - started
        _log_run(conn, run_date, "fail", 0, dur, f"{type(exc).__name__}: {exc}")
        conn.commit()
        raise
