"""MARS ingest stage — fetch sector + benchmark index history, compute MARS,
persist into sector_index_prices + sector_metrics.

This is the I/O half of the MARS feature; the pure math lives in
``regime.sectors.compute_mars``. Registered as the ``ingest_mars`` stage in
``run-eod`` (after ``ingest_chartsmaze``).

Degrades gracefully: if the Fyers provider isn't available (no token cached,
as on a fresh machine), the stage logs ``status: skip`` and writes nothing —
the Sectors tab then falls back to the ChartsMaze RS% bar + MA% chip.
"""
from __future__ import annotations

import logging
import time

from manas_os import config
from manas_os.providers.base import DailyBar
from manas_os.providers.fyers import FyersProvider
from manas_os.regime.sectors import (
    BENCHMARK,
    MA_LENGTH,
    SECTOR_INDICES,
    canonical_sector_key,
    compute_mars,
    sma,
)

logger = logging.getLogger("manas_os.regime.mars_ingest")

STAGE = "ingest_mars"
SOURCE = "fyers_index"
# Lookback window for history fetch — needs ≥ MA_LENGTH (50) with margin.
LOOKBACK_DAYS = 80


def _benchmark() -> str:
    return config.get("regime.mars_benchmark", BENCHMARK)


def _log_run(conn, run_date, status, rows, duration, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, "
        "rows_affected, duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE, status, rows, duration, detail),
    )


def _upsert_prices(conn, symbol: str, bars: list[DailyBar]) -> int:
    """Cache closes + rolling SMA50 for one index. Returns rows written."""
    if not bars:
        return 0
    closes = [b.close for b in bars]
    written = 0
    for i, bar in enumerate(bars):
        # SMA50 of closes up to and including this bar (None until enough history).
        seg = closes[: i + 1]
        ma = sma(seg, MA_LENGTH) if len(seg) >= MA_LENGTH else None
        conn.execute(
            "INSERT INTO sector_index_prices (symbol, trade_date, close, sma50) "
            "VALUES (?, ?, ?, ?) "
            "ON CONFLICT(symbol, trade_date) DO UPDATE SET "
            "close=excluded.close, sma50=excluded.sma50, ingested_at=datetime('now')",
            (symbol, bar.date, bar.close, ma),
        )
        written += 1
    return written


def _write_mars(conn, run_date: str, sector: str, mars_value, state) -> None:
    """Upsert MARS into sector_metrics, keyed by (snapshot_date, sector_key).

    `sector` is the raw NSE index label (e.g. 'NIFTY AUTO'); we canonicalize it
    through the same registry `ingest_chartsmaze` uses (regime.sectors.SECTORS)
    so both write paths land on the SAME row (canonical key 'AUTO') instead of
    appearing as two separate sectors in the UI.
    """
    sector_key = canonical_sector_key(sector, "index")
    conn.execute(
        "INSERT INTO sector_metrics (snapshot_date, sector_key, mars_score, mars_state) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(snapshot_date, sector_key) DO UPDATE SET "
        "mars_score=excluded.mars_score, mars_state=excluded.mars_state, "
        "ingested_at=datetime('now')",
        (run_date, sector_key, mars_value, state),
    )


def run(conn, run_date: str, provider: FyersProvider | None = None) -> dict:
    """Fetch index histories, compute + persist MARS for each sector.

    Returns {status, sectors, rows_affected, detail}. ``status`` is 'skip'
    when the provider is unavailable (no Fyers token) — never raises, so the
    daily pipeline's per-stage isolation stays honest.
    """
    started = time.monotonic()
    provider = provider or FyersProvider.from_config(config.load_config())

    if not provider.is_available():
        dur = time.monotonic() - started
        _log_run(conn, run_date, "skip", 0, dur, "fyers token not available")
        conn.commit()
        return {"status": "skip", "sectors": 0, "detail": "fyers unavailable"}

    benchmark = _benchmark()
    try:
        index_bars = provider.get_index_history(benchmark, LOOKBACK_DAYS)
    except Exception as exc:
        dur = time.monotonic() - started
        _log_run(conn, run_date, "fail", 0, dur, f"benchmark fetch: {exc}")
        conn.commit()
        return {"status": "fail", "sectors": 0, "detail": str(exc)}

    if not index_bars or len(index_bars) < MA_LENGTH:
        dur = time.monotonic() - started
        _log_run(conn, run_date, "skip", 0, dur,
                 f"benchmark history too short ({len(index_bars)})")
        conn.commit()
        return {"status": "skip", "sectors": 0, "detail": "benchmark too short"}

    price_rows = _upsert_prices(conn, benchmark, index_bars)
    sectors_done = 0
    sectors_short = 0
    sectors_failed = 0

    for sector in SECTOR_INDICES:
        try:
            bars = provider.get_index_history(sector, LOOKBACK_DAYS)
        except Exception as exc:
            logger.warning("MARS history failed for %s: %s", sector, exc)
            sectors_failed += 1
            continue
        if not bars:
            sectors_failed += 1
            continue
        price_rows += _upsert_prices(conn, sector, bars)
        mars_value, state = compute_mars(bars, index_bars)
        if mars_value is None:
            sectors_short += 1
            continue
        _write_mars(conn, run_date, sector, mars_value, state)
        sectors_done += 1

    dur = time.monotonic() - started
    detail = (f"benchmark={benchmark} sectors_done={sectors_done} "
              f"short={sectors_short} failed={sectors_failed} prices={price_rows}")
    status = "ok" if sectors_done else "skip"
    _log_run(conn, run_date, status, sectors_done, dur, detail)
    conn.commit()
    return {
        "status": status,
        "sectors": sectors_done,
        "rows_affected": price_rows,
        "detail": detail,
    }
