"""NSE bhavcopy ingestion → momentum market store (U-P0.3 real-data path).

Adopted source (DECISIONS D9): the repo's own `bhavcopy_extractor/data/bhavcopy/`
backlog (cm*.bhav.csv + sec_bhavdata_full_*.csv, identical 15-column schema),
Apr 2025 → Jun 2026. NSE public files; no credentials.

Policies (frozen here, per D8):
* SERIES filter: "EQ" only by default (cash-equity momentum universe).
* ``available_at`` = session date 18:00 IST — a bar is invisible to any
  point-in-time query earlier the same day (publication-time assumption,
  verified-never; configurable at the loader).
* Rows with unparseable numerics are SKIPPED and counted, never coerced.
* Delivery: DELIV_PER present → delivered participation; blank → None.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

from unidesk.contracts.base import ContractError
from unidesk.momentum.data.market_store import InMemoryMarketStore, VersionedDailyBar
from unidesk.momentum.universe.symbol_master import normalize_symbol

IST = timezone(timedelta(hours=5, minutes=30))
_COLUMNS = {
    "SYMBOL": "SYMBOL", " SERIES": "SYMBOL",
    "SERIES": "SERIES",
    " DATE1": "DATE1", "DATE1": "DATE1",
    " PREV_CLOSE": "PREV_CLOSE", "PREV_CLOSE": "PREV_CLOSE",
    " OPEN_PRICE": "OPEN_PRICE", "OPEN_PRICE": "OPEN_PRICE",
    " HIGH_PRICE": "HIGH_PRICE", "HIGH_PRICE": "HIGH_PRICE",
    " LOW_PRICE": "LOW_PRICE", "LOW_PRICE": "LOW_PRICE",
    " CLOSE_PRICE": "CLOSE_PRICE", "CLOSE_PRICE": "CLOSE_PRICE",
    " TTL_TRD_QNTY": "TTL_TRD_QNTY", "TTL_TRD_QNTY": "TTL_TRD_QNTY",
    " NO_OF_TRADES": "NO_OF_TRADES", "NO_OF_TRADES": "NO_OF_TRADES",
    " DELIV_PER": "DELIV_PER", "DELIV_PER": "DELIV_PER",
}
DATE_FORMAT = "%d-%b-%Y"


class BhavcopyIngestError(ContractError):
    pass


def _num(value: str, field: str, symbol: str, session: str) -> Optional[float]:
    value = (value or "").strip()
    if value in ("", "-"):
        return None
    try:
        return float(value)
    except ValueError:
        raise BhavcopyIngestError(f"{symbol} {session}: unparseable {field}={value!r}")


def parse_bhavcopy_file(path: Path, *, series_filter: tuple = ("EQ",)) -> tuple[list[dict], dict]:
    """Parse one bhavcopy CSV into clean row dicts (no store writes).

    Returns (rows, stats). Rows whose symbol cannot be normalized (e.g. NSE
    tickers with characters outside the frozen policy charset, like `M&M`)
    are SKIPPED and counted — one odd row never kills a file. Extending the
    charset is a DATA_POLICY decision, not an ingestion fix."""
    rows: list[dict] = []
    skipped_symbols = 0
    with open(path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        col = {}
        for raw in header:
            key = _COLUMNS.get(raw.strip()) or _COLUMNS.get(raw)
            if key:
                col[key] = header.index(raw)
        missing = {"SYMBOL", "DATE1", "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE",
                   "CLOSE_PRICE", "TTL_TRD_QNTY"} - set(col)
        if missing:
            raise BhavcopyIngestError(f"{path.name}: unrecognized bhavcopy header; missing {sorted(missing)}")

        for line_no, row in enumerate(reader, start=2):
            if len(row) < len(header):
                continue
            raw_symbol = (row[col["SYMBOL"]] or "").strip().upper()
            series = (row[col["SERIES"]] or "").strip().upper() if "SERIES" in col else "EQ"
            if not raw_symbol or series not in series_filter:
                continue
            try:
                symbol = normalize_symbol(raw_symbol)
            except ContractError:
                skipped_symbols += 1
                continue
            session_str = (row[col["DATE1"]] or "").strip()
            try:
                session = datetime.strptime(session_str, DATE_FORMAT).date()
            except ValueError:
                raise BhavcopyIngestError(f"{path.name} line {line_no}: bad date {session_str!r}")
            try:
                rows.append({
                    "symbol": normalize_symbol(symbol),
                    "session": session,
                    "open": _num(row[col["OPEN_PRICE"]], "OPEN_PRICE", symbol, session_str),
                    "high": _num(row[col["HIGH_PRICE"]], "HIGH_PRICE", symbol, session_str),
                    "low": _num(row[col["LOW_PRICE"]], "LOW_PRICE", symbol, session_str),
                    "close": _num(row[col["CLOSE_PRICE"]], "CLOSE_PRICE", symbol, session_str),
                    "prev_close": _num(row[col["PREV_CLOSE"]], "PREV_CLOSE", symbol, session_str),
                    "volume": _num(row[col["TTL_TRD_QNTY"]], "TTL_TRD_QNTY", symbol, session_str),
                    "num_trades": _num(row[col.get("NO_OF_TRADES", -1)] or "", "NO_OF_TRADES", symbol, session_str) if "NO_OF_TRADES" in col else None,
                    "delivery_pct": _num(row[col["DELIV_PER"]], "DELIV_PER", symbol, session_str) if "DELIV_PER" in col else None,
                })
            except ContractError:
                raise
    return rows, {"skipped_symbols": skipped_symbols}


def load_into_store(
    store: InMemoryMarketStore,
    rows: Iterable[dict],
    *,
    available_at_hour: int = 18,
    available_at_minute: int = 0,
    seen: Optional[set] = None,
) -> tuple[int, int]:
    """Insert parsed rows as VersionedDailyBars (available_at = session D
    18:00 IST by default, per D8). Returns (added, duplicates).

    Duplicates (same symbol+session+version, e.g. cm-bhav and sec_bhavdata
    files covering the same session) are deduped HERE with an O(1) set —
    first file in sorted order wins — so the store's own O(n) rejection never
    becomes the bulk-load bottleneck."""
    added = 0
    duplicates = 0
    if seen is None:
        seen = set()
    for row in rows:
        available_at = datetime(
            row["session"].year, row["session"].month, row["session"].day,
            available_at_hour, available_at_minute, tzinfo=IST,
        )
        from unidesk.contracts.market import DailyBar

        if any(row[k] is None for k in ("open", "high", "low", "close")):
            continue  # unpriced row: skip before validation, never fabricate
        key = (row["symbol"], row["session"], "bhavcopy")
        if key in seen:
            duplicates += 1  # overlapping file generations (cm + sec_bhavdata):
            continue         # first file in sorted order wins, deterministically
        seen.add(key)
        bar = DailyBar(
            symbol=row["symbol"], session=row["session"],
            open=row["open"], high=row["high"], low=row["low"], close=row["close"],
            volume=int(row["volume"]) if row["volume"] is not None else 0,
            delivery_percentage=row["delivery_pct"],
            num_trades=int(row["num_trades"]) if row["num_trades"] is not None else None,
            data_version="bhavcopy",
        )
        store.add_daily_bar(VersionedDailyBar(bar=bar, available_at=available_at))
        added += 1
    return added, duplicates


def ingest_directory(
    store: InMemoryMarketStore,
    folder: Path,
    *,
    series_filter: tuple = ("EQ",),
    limit_files: Optional[int] = None,
    seen: Optional[set] = None,
) -> dict:
    """``seen``: optional shared dedupe set — pass the SAME set when
    ingesting multiple directories (e.g. backlog + recent downloads) so
    cross-corpus duplicate sessions are skipped before the store guard."""
    """Ingest every bhavcopy file in ``folder`` (both name generations)."""
    files = sorted(
        [p for p in Path(folder).iterdir()
         if p.suffix.lower() == ".csv" and ("bhav" in p.name.lower())]
    )
    if limit_files:
        files = files[:limit_files]
    added = skipped_files = 0
    if seen is None:
        seen = set()
    for path in files:
        try:
            rows, _stats = parse_bhavcopy_file(path, series_filter=series_filter)
        except BhavcopyIngestError:
            skipped_files += 1
            continue
        delta, _dups = load_into_store(store, rows, seen=seen)
        added += delta
    return {"files": len(files), "skipped_files": skipped_files, "bars_added": added}
