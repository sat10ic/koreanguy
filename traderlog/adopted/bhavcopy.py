"""NSE sec_bhavdata_full ingestion -> daily_prices.

Adopted (copied, not imported) from ``manas_os/sources/bhavcopy.py`` on
2026-08-23 for TraderLog W4. See CANONICAL.md §5 and
DECISIONS.md 2026-08-23 "Adopt the XP and MBI scores, but not the regime
governor". Once copied this file is TraderLog's own; drift from the manas_os
original is expected and fine.

Changes made during adoption (drift, documented per CANONICAL.md §5):
  * ``manas_os.config`` -> ``traderlog.config`` (config key ``breadth.bhavcopy_dir``).
  * Default directory resolves to the REPO-ROOT ``data/bhavcopy`` (verified
    2026-08-23: 493 files there), not a path relative to this package.
  * ``daily_prices`` upsert trims to the columns TraderLog's schema actually
    has (no ``last_price``/``avg_price``/``delivery_qty`` columns exist on
    TraderLog's ``daily_prices`` -- those three are parsed but simply not
    written; nothing downstream in W4 needs them).
  * ``pipeline_runs`` logging uses TraderLog's column names
    (stage, run_date, status, rows, duration_ms, detail, ts) instead of
    manas_os's (source, rows_affected, duration_s).

The NSE "full bhavcopy" CSV carries OHLC plus delivery data under two on-disk
naming conventions that carry the identical payload (verified 2026-08-23 by
reading both): the legacy ``cmDDMMMYYYYbhav.csv`` and the newer
``sec_bhavdata_full_DDMMYYYY.csv``. Real headers and values have leading
spaces, and DELIV_QTY/DELIV_PER are ``-`` for non-EQ series (bonds, BE/BZ,
etc.) -- those become NULL.

Public surface:
    parse_bhavcopy(text) -> list[dict]   # pure; one dict per data row
    discover_dates(dir)  -> list[str]    # every ISO date with a file on disk
    run(conn, run_date)  -> int          # finds file, upserts, logs pipeline_runs

Real header (verbatim, incl. leading spaces after commas):
    SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE,
    LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS,
    NO_OF_TRADES, DELIV_QTY, DELIV_PER
"""
from __future__ import annotations

import csv
import io
import re
import time
from datetime import date, datetime
from pathlib import Path

from traderlog import config
from traderlog.db import now_iso

# Repo root, resolved from this file's location: traderlog/adopted/bhavcopy.py
# -> parents[0]=adopted, [1]=traderlog, [2]=repo root.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_DIR = "data/bhavcopy"
_STAGE = "adopted.bhavcopy"
_SOURCE = "bhavcopy"

# Column keys after stripping whitespace from headers.
_COLS = {
    "SYMBOL", "SERIES", "DATE1", "PREV_CLOSE", "OPEN_PRICE", "HIGH_PRICE",
    "LOW_PRICE", "LAST_PRICE", "CLOSE_PRICE", "AVG_PRICE", "TTL_TRD_QNTY",
    "TURNOVER_LACS", "NO_OF_TRADES", "DELIV_QTY", "DELIV_PER",
}

_CM_RE = re.compile(r"^cm(\d{2})([A-Za-z]{3})(\d{4})bhav\.csv$")
_SEC_RE = re.compile(r"^sec_bhavdata_full_(\d{2})(\d{2})(\d{4})\.csv$")
_MONTHS = {m.upper(): i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1
)}


def _num(value: str | None) -> float | None:
    """Parse a float; '-', '' and None -> None."""
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
    """'01-Jul-2025' -> '2025-07-01'."""
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
    """ISO date '2025-07-01' -> 'cm01JUL2025bhav.csv' (uppercase month)."""
    d = date.fromisoformat(run_date)
    return f"cm{d.strftime('%d%b%Y').upper()}bhav.csv"


def filename_candidates(run_date: str) -> list[str]:
    """Both on-disk names a full-bhavcopy can carry for a date -- same columns.

    Verified 2026-08-23 by reading both: NSE ships the identical
    sec_bhavdata_full payload under two names depending on the download
    source: the legacy ``cmDDMMMYYYYbhav.csv`` and the newer
    ``sec_bhavdata_full_DDMMYYYY.csv``. The two naming conventions on this
    machine's data/bhavcopy/ barely overlap (26 of 493 files) and together
    cover 2024-09-02 through 2026-08-14 -- far more than either alone.
    """
    d = date.fromisoformat(run_date)
    return [
        f"cm{d.strftime('%d%b%Y').upper()}bhav.csv",
        f"sec_bhavdata_full_{d.strftime('%d%m%Y')}.csv",
    ]


def bhavcopy_dir() -> Path:
    raw = config.get("breadth.bhavcopy_dir", _DEFAULT_DIR)
    p = Path(raw)
    if not p.is_absolute():
        p = (_REPO_ROOT / p).resolve()
    return p


def discover_dates(directory: Path | str | None = None) -> list[str]:
    """Every ISO date that has a bhavcopy file on disk, ascending, deduped.

    Recognises both naming conventions. This is what tells the run_w4 shim
    which dates to backfill -- it does NOT assume any date range.
    """
    d = Path(directory) if directory is not None else bhavcopy_dir()
    if not d.is_dir():
        return []
    found: set[str] = set()
    for f in d.iterdir():
        if not f.is_file():
            continue
        m = _CM_RE.match(f.name)
        if m:
            dd, mo, yy = m.groups()
            mo_num = _MONTHS.get(mo.upper())
            if mo_num:
                found.add(date(int(yy), mo_num, int(dd)).isoformat())
            continue
        m = _SEC_RE.match(f.name)
        if m:
            dd, mo, yy = m.groups()
            try:
                found.add(date(int(yy), int(mo), int(dd)).isoformat())
            except ValueError:
                continue
    return sorted(found)


def _upsert(conn, records: list[dict]) -> int:
    stamp = now_iso()
    sql = (
        "INSERT OR REPLACE INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, prev_close, "
        " volume, turnover, num_trades, delivery_pct, source, ingested_at) "
        "VALUES (:symbol, :trade_date, :series, :open, :high, :low, :close, "
        " :prev_close, :volume, :turnover, :num_trades, :delivery_pct, "
        " :source, :ingested_at)"
    )
    for r in records:
        r["ingested_at"] = stamp
    conn.executemany(sql, records)
    return len(records)


def _log_run(conn, run_date, status, rows, duration_s, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (stage, run_date, status, rows, duration_ms, detail, ts) "
        "VALUES (?,?,?,?,?,?,?)",
        (_STAGE, run_date, status, rows, int(duration_s * 1000), detail, now_iso()),
    )


def run(conn, run_date: str) -> int:
    """Ingest the bhavcopy for ``run_date`` into daily_prices (idempotent).

    Returns the number of rows upserted. Writes a pipeline_runs row either way.
    Tries both filename conventions (filename_candidates), preferring whichever
    exists on disk.
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
        actual_dates = sorted({record["trade_date"] for record in records})
        if actual_dates != [run_date]:
            raise ValueError(
                f"DATE1 mismatch for requested {run_date}: "
                f"CSV contains {', '.join(actual_dates) if actual_dates else 'no data rows'}"
            )
        rows = _upsert(conn, records)
        _log_run(conn, run_date, "ok", rows, time.monotonic() - started,
                 f"{path.name}: {rows} rows")
        conn.commit()
        return rows
    except Exception as exc:  # noqa: BLE001
        _log_run(conn, run_date, "fail", 0, time.monotonic() - started, str(exc))
        conn.commit()
        raise


def backfill(conn, dates: list[str] | None = None) -> dict:
    """Ingest every discovered date in ascending order. Idempotent.

    Returns {"dates": n, "rows": total_rows, "failed": [dates]}.
    """
    dates = dates if dates is not None else discover_dates()
    total_rows = 0
    failed: list[str] = []
    for d in dates:
        try:
            total_rows += run(conn, d)
        except Exception:  # noqa: BLE001 - already logged to pipeline_runs by run()
            failed.append(d)
    return {"dates": len(dates), "rows": total_rows, "failed": failed}
