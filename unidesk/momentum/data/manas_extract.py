"""Read-only extract from manas_os/data/manas.db (D17).

unidesk does not import ``manas_os`` (D4). This module opens the sqlite
file ``mode=ro`` and copies the rows UniDesk needs into our own parquet.
manas remains the sole writer of that database.

What we take:

* ``sector_index_prices`` — Nifty 50 / 500 / Midcap 150 / Smallcap 250 /
  India VIX (price closes, not TRI)
* ``universe`` — dated snapshots (``as_of_date``), not today's list
  projected backward (D14.5)

daily_prices (2021-07-12 → 2026-08-21, 1.60M bars) is inventoried, not
copied this slice — D15 bhavcopy stays the EOD bar home.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from unidesk.momentum.data.indices import persist_index_rows

DEFAULT_DB = Path(__file__).resolve().parents[3] / "manas_os" / "data" / "manas.db"

SYMBOL_TO_ID = {
    "NIFTY 50": "NIFTY_50",
    "NIFTY 500": "NIFTY_500",
    "NIFTY MIDCAP 150": "NIFTY_MIDCAP_150",
    "NIFTY SMALLCAP 250": "NIFTY_SMALLCAP_250",
    "India VIX": "INDIA_VIX",
}
SOURCE_TIER_MANAS = "MANAS_SECTOR_INDEX_PRICES"


def _connect(db: Path) -> sqlite3.Connection:
    uri = f"file:{Path(db).resolve().as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def extract_index_rows(db: Path = DEFAULT_DB) -> list[dict]:
    """Copy the R0 index set out of sector_index_prices."""
    con = _connect(db)
    try:
        qmarks = ",".join("?" * len(SYMBOL_TO_ID))
        rows = con.execute(
            f"SELECT symbol, trade_date, open, high, low, close "
            f"FROM sector_index_prices WHERE symbol IN ({qmarks}) "
            f"ORDER BY trade_date, symbol",
            tuple(SYMBOL_TO_ID),
        ).fetchall()
    finally:
        con.close()
    out = []
    for symbol, trade_date, open_, high, low, close in rows:
        index_id = SYMBOL_TO_ID.get(symbol)
        if index_id is None or close is None:
            continue
        out.append({
            "session": str(trade_date)[:10],
            "index_id": index_id,
            "index_name": symbol,
            "open": open_,
            "high": high,
            "low": low,
            "close": float(close),
            "source_tier": SOURCE_TIER_MANAS,
            "source_file": Path(db).name,
        })
    return out


def extract_universe_rows(db: Path = DEFAULT_DB) -> list[dict]:
    """Dated universe snapshots. Each row is (symbol, as_of_date) — PIT."""
    con = _connect(db)
    try:
        rows = con.execute(
            "SELECT symbol, as_of_date, series, sector, industry, is_tradeable "
            "FROM universe ORDER BY as_of_date, symbol"
        ).fetchall()
    finally:
        con.close()
    return [
        {
            "symbol": symbol,
            "as_of_date": str(as_of)[:10],
            "series": series,
            "sector": sector,
            "industry": industry,
            "is_tradeable": int(is_tradeable or 0),
            "source_tier": "MANAS_UNIVERSE",
            "source_file": Path(db).name,
        }
        for symbol, as_of, series, sector, industry, is_tradeable in rows
    ]


def merge_index_rows(primary: list[dict], overlay: list[dict]) -> list[dict]:
    """``overlay`` wins on (session, index_id) — used to keep nse-archives
    days that manas has not ingested yet."""
    by = {(r["session"], r["index_id"]): r for r in primary}
    by.update({(r["session"], r["index_id"]): r for r in overlay})
    return [by[k] for k in sorted(by)]


def persist_universe_rows(rows: list[dict], path: Path) -> Path:
    import pyarrow as pa
    import pyarrow.parquet as pq
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), path)
    return path


def write_index_extract(
    dest: Path,
    *,
    db: Path = DEFAULT_DB,
    overlay: Optional[list[dict]] = None,
) -> dict:
    primary = extract_index_rows(db)
    merged = merge_index_rows(primary, overlay or [])
    persist_index_rows(merged, dest)
    sessions = {r["session"] for r in merged}
    ids = {r["index_id"] for r in merged}
    return {
        "rows": len(merged),
        "sessions": len(sessions),
        "index_ids": sorted(ids),
        "min_session": min(sessions) if sessions else None,
        "max_session": max(sessions) if sessions else None,
        "path": str(dest),
    }
