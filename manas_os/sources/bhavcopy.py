"""NSE sec_bhavdata_full ingestion → daily_prices.

The NSE "full bhavcopy" CSV (``cmDDMMMYYYYbhav.csv``) carries OHLC plus delivery
data. Real headers and values have leading spaces, and DELIV_QTY/DELIV_PER are
``-`` for non-EQ series (bonds, BE/BZ, etc.) — those become NULL.

Public surface:
    parse_bhavcopy(text) -> list[dict]   # pure; one dict per data row
    run(conn, run_date)  -> int          # finds file, upserts, logs pipeline_runs

Real header (verbatim, incl. leading spaces after commas):
    SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE,
    LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS,
    NO_OF_TRADES, DELIV_QTY, DELIV_PER
"""
from __future__ import annotations

import csv
import io
import time
from datetime import date, datetime
from pathlib import Path

from manas_os import config

_DEFAULT_DIR = "../bhavcopy_extractor/data/bhavcopy"
_SOURCE = "bhavcopy"
_STAGE = "ingest_bhavcopy"

# Column keys after stripping whitespace from headers.
_COLS = {
    "SYMBOL", "SERIES", "DATE1", "PREV_CLOSE", "OPEN_PRICE", "HIGH_PRICE",
    "LOW_PRICE", "LAST_PRICE", "CLOSE_PRICE", "AVG_PRICE", "TTL_TRD_QNTY",
    "TURNOVER_LACS", "NO_OF_TRADES", "DELIV_QTY", "DELIV_PER",
}


def _num(value: str | None) -> float | None:
    """Parse a float; '-', '' and None → None."""
    if value is None:
        return None
    v = value.strip()
    if v in ("", "-"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _intnum(value: str | None) -> int | None:
    f = _num(value)
    return int(f) if f is not None else None


def _iso_date(date1: str) -> str:
    """'01-Jul-2025' → '2025-07-01'."""
    return datetime.strptime(date1.strip(), "%d-%b-%Y").date().isoformat()


def parse_bhavcopy(text: str) -> list[dict]:
    """Parse a full-bhavcopy CSV string into a list of daily_prices-shaped dicts.

    Pure: no I/O, no DB. Headers/values are stripped of surrounding whitespace;
    delivery '-' becomes None; TURNOVER_LACS is mapped straight to ``turnover``.
    """
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return []

    header = [h.strip() for h in rows[0]]
    idx = {name: i for i, name in enumerate(header)}
    # Sanity: require the core columns to be present.
    missing = _COLS - set(idx)
    if missing:
        raise ValueError(f"bhavcopy missing columns: {sorted(missing)}")

    def cell(row: list[str], name: str) -> str | None:
        i = idx[name]
        return row[i].strip() if i < len(row) else None

    out: list[dict] = []
    for row in rows[1:]:
        if not row or not (cell(row, "SYMBOL") or ""):
            continue
        out.append({
            "symbol": (cell(row, "SYMBOL") or "").upper(),
            "trade_date": _iso_date(cell(row, "DATE1") or ""),
            "series": (cell(row, "SERIES") or "").upper(),
            "prev_close": _num(cell(row, "PREV_CLOSE")),
            "open": _num(cell(row, "OPEN_PRICE")),
            "high": _num(cell(row, "HIGH_PRICE")),
            "low": _num(cell(row, "LOW_PRICE")),
            "last_price": _num(cell(row, "LAST_PRICE")),
            "close": _num(cell(row, "CLOSE_PRICE")),
            "avg_price": _num(cell(row, "AVG_PRICE")),
            "volume": _intnum(cell(row, "TTL_TRD_QNTY")),
            "turnover": _num(cell(row, "TURNOVER_LACS")),
            "num_trades": _intnum(cell(row, "NO_OF_TRADES")),
            "delivery_qty": _intnum(cell(row, "DELIV_QTY")),
            "delivery_pct": _num(cell(row, "DELIV_PER")),
            "source": _SOURCE,
        })
    return out


def filename_for(run_date: str) -> str:
    """ISO date '2025-07-01' → 'cm01JUL2025bhav.csv' (uppercase month).

    The primary/legacy name. Kept for back-compat; ingest uses
    ``filename_candidates`` so it also finds the ``sec_bhavdata_full_*`` name.
    """
    d = date.fromisoformat(run_date)
    return f"cm{d.strftime('%d%b%Y').upper()}bhav.csv"


def filename_candidates(run_date: str) -> list[str]:
    """Both on-disk names a full-bhavcopy can carry for a date — same columns.

    NSE ships the identical sec_bhavdata_full payload under two names depending
    on the download source: the legacy ``cmDDMMMYYYYbhav.csv`` (girish mirror)
    and ``sec_bhavdata_full_DDMMYYYY.csv`` (NSE-Data-bank mirror). Ingest tries
    both so data downloaded from either source is picked up.
    """
    d = date.fromisoformat(run_date)
    return [
        f"cm{d.strftime('%d%b%Y').upper()}bhav.csv",
        f"sec_bhavdata_full_{d.strftime('%d%m%Y')}.csv",
    ]


def bhavcopy_dir() -> Path:
    raw = config.get("sources.bhavcopy_dir", _DEFAULT_DIR)
    p = Path(raw)
    if not p.is_absolute():
        p = (Path(__file__).resolve().parents[1] / p).resolve()
    return p


def _upsert(conn, records: list[dict]) -> int:
    sql = (
        "INSERT OR REPLACE INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, prev_close, "
        " last_price, avg_price, volume, turnover, num_trades, delivery_qty, "
        " delivery_pct, source) "
        "VALUES (:symbol, :trade_date, :series, :open, :high, :low, :close, "
        " :prev_close, :last_price, :avg_price, :volume, :turnover, "
        " :num_trades, :delivery_qty, :delivery_pct, :source)"
    )
    conn.executemany(sql, records)
    return len(records)


def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, _STAGE, _SOURCE, status, rows, duration, detail),
    )


def run(conn, run_date: str) -> int:
    """Ingest the bhavcopy for ``run_date`` into daily_prices (idempotent).

    Returns the number of rows upserted. Writes a pipeline_runs row either way.
    """
    started = time.monotonic()
    directory = bhavcopy_dir()
    path = next((directory / n for n in filename_candidates(run_date)
                 if (directory / n).exists()), None)
    if path is None:
        tried = " / ".join(filename_candidates(run_date))
        _log_run(conn, run_date, "skip", 0, time.monotonic() - started,
                 f"file not found (tried: {tried})")
        conn.commit()
        return 0
    try:
        records = parse_bhavcopy(path.read_text(encoding="utf-8"))
        rows = _upsert(conn, records)
        _log_run(conn, run_date, "ok", rows, time.monotonic() - started,
                 f"{path.name}: {rows} rows")
        conn.commit()
        return rows
    except Exception as exc:  # noqa: BLE001
        _log_run(conn, run_date, "fail", 0, time.monotonic() - started, str(exc))
        conn.commit()
        raise
