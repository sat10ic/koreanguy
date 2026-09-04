"""Breadth COUNTS compute stage -- raw daily breadth counts over our own universe.

Adopted (copied, not imported) from ``manas_os/sources/breadth_counts.py`` on
2026-08-23 for TraderLog W4. See CANONICAL.md §5 and
DECISIONS.md 2026-08-23 "Adopt the XP and MBI scores, but not the regime
governor". Once copied this file is TraderLog's own; drift from the manas_os
original is expected and fine.

Given ``run_date``, compute ~38 daily breadth COUNT metrics from OUR OWN
``daily_prices`` universe (not any external sheet) and upsert one row into
``breadth_counts``, keyed by ``trade_date``.

Ground truth for every threshold is the verified source workbook
"Market Breadth V2.0.xlsm" (documented in
``manas_os/design/study/REVERSE_ENGINEERING.md``, read-only reference).

Changes made during adoption (drift, documented per CANONICAL.md §5):
  * TraderLog's ``breadth_counts`` table stores the ~38 counts as one
    ``counts_json`` blob plus ``universe_size`` (db/schema.sql, W0), not one
    column per metric as in manas_os. The DDL and per-column upsert here are
    replaced with a JSON upsert; the math is untouched.
  * Dropped ``compute_wave2_metrics``/``_upsert_wave2_metrics``/
    ``backfill_wave2_metrics`` entirely -- they write DMA-cross/21-session-move
    columns (``pct_10dma_gt_20dma`` etc.) that do not exist on TraderLog's
    ``breadth_daily`` and are not required by the XP/MBI adoption this wave
    ships. Nothing in W4's deliverables needs them.
  * ``pipeline_runs`` logging uses TraderLog's column names.

No network fetch. Reads only from ``daily_prices``. stdlib + sqlite3 only
(no pandas/numpy) so it stays light enough for every EOD pipeline pass.
"""
from __future__ import annotations

import json
import sqlite3
import time

from traderlog.db import now_iso

STAGE = "adopted.breadth_counts"

# Output column order — kept as a list so the upsert and the counts dict stay
# in lockstep. "total_universe" is itself one of the ~38 counts, per the
# original module.
_COUNT_COLS = [
    "total_universe",
    "up_4pct", "down_4pct",
    "high_vol", "low_vol",
    "range_contraction", "range_expansion",
    "close_upper_half", "close_lower_half",
    "breakouts", "breakout_sustained", "breakout_failed",
    "breakdowns", "breakdown_sustained", "breakdown_failed",
    "up_15pct_5d", "down_15pct_5d",
    "up_25pct_20d", "down_25pct_20d",
    "above_10pct_10dema", "below_10pct_10dema",
    "above_10dema", "above_20dema", "above_50dema", "above_200dema",
    "new_52wk_high", "new_52wk_low",
    "from_52wh_15pct", "from_52wh_30pct", "from_52wh_50pct", "from_52wh_70pct",
    "from_52wh_70pct_plus",
    "from_52wl_15pct", "from_52wl_30pct", "from_52wl_50pct",
    "from_52wl_90pct", "from_52wl_150pct", "from_52wl_150pct_plus",
]

# Threshold constants — one place, named, so the criteria are auditable.
THRESH_UP_4PCT = 0.04            # net change >= +4% (decision 1: /prev_close)
THRESH_DOWN_4PCT = -0.04         # net change <= -4%
THRESH_RANGE_CONTRACT = 0.03     # daily range <= 3% of low (decision 5)
THRESH_RANGE_EXPAND = 0.0501     # daily range >= 5.01% of low
THRESH_VOL_HIGH = 1.5            # > 1.5x 20d avg vol (decision 4)
THRESH_VOL_LOW = 0.5             # < 0.5x 20d avg vol
VOL_AVG_WINDOW = 20              # trailing sessions EXCLUDING today (decision 4)
THRESH_BO = 1.04                 # high >= prev_close * 1.04 (decision 3)
THRESH_BD = 0.96                 # low <= prev_close * 0.96
BO_BD_BAND_FRAC = 0.40           # within 40% of range from the extreme (decision 7)
THRESH_5D_UP = 0.15              # +15% over 5 sessions (decision 8)
THRESH_5D_DN = -0.15
THRESH_20D_UP = 0.25             # +25% over 20 sessions
THRESH_20D_DN = -0.25
THRESH_DEMA_DEV = 0.10           # +/-10% vs 10-EMA (decision 9)
WEEKS_52_SESSIONS = 252          # ~52 weeks of trading sessions (decision 10)


# ─────────────────────────────────────────────────────────────────────────────
# Pure helpers (unit-testable without a DB)
# ─────────────────────────────────────────────────────────────────────────────

def ema(values: list[float], period: int) -> float | None:
    """Standard EMA seeded by the SMA of the first `period` values.

    The workbook's "DEMA" is the vendor's name for a plain EMA, not a
    double-EMA (decision 9). Returns None if fewer than `period` closes are
    available (the seed is undefined) — callers must then exclude the symbol
    from that DEMA-based count.
    """
    if len(values) < period or period <= 0:
        return None
    seed = sum(values[:period]) / period
    if period == 1:
        return values[-1]
    alpha = 2.0 / (period + 1)
    ema_prev = seed
    for v in values[period:]:
        ema_prev = alpha * v + (1 - alpha) * ema_prev
    return ema_prev


def net_change_pct(close: float, prev_close: float | None) -> float | None:
    """Decision 1: divide by PREV_CLOSE (correcting the source workbook's
    divide-by-current bug). Returns None if prev_close is missing/<=0."""
    if prev_close is None or prev_close <= 0:
        return None
    return (close - prev_close) / prev_close


def daily_range_pct(high: float, low: float) -> float | None:
    """Decision 5: range as a fraction of the day's LOW."""
    if low is None or low <= 0:
        return None
    return (high - low) / low


# ─────────────────────────────────────────────────────────────────────────────
# Per-symbol history fetch. One ordered query per symbol builds every rolling
# window this module needs (vol avg, DEMA, 52wk extremes, 5d/20d moves).
# ─────────────────────────────────────────────────────────────────────────────

_HISTORY_LOOKBACK = max(WEEKS_52_SESSIONS, 200) + VOL_AVG_WINDOW + 5


def _fetch_symbol_history(conn, symbol: str, run_date: str) -> list[sqlite3.Row]:
    """The MOST RECENT `_HISTORY_LOOKBACK` EQ rows for `symbol` with
    trade_date <= run_date, returned oldest-first."""
    rows = list(conn.execute(
        "SELECT trade_date, open, high, low, close, prev_close, volume "
        "FROM daily_prices "
        "WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "ORDER BY trade_date DESC "
        "LIMIT ?",
        (symbol, run_date, _HISTORY_LOOKBACK),
    ))
    rows.reverse()
    return rows


def _eligible_universe(conn, run_date: str) -> list[str]:
    """Every symbol with an EQ row on run_date where close >= 1."""
    rows = conn.execute(
        "SELECT DISTINCT symbol FROM daily_prices "
        "WHERE trade_date = ? AND series = 'EQ' AND close >= 1 "
        "ORDER BY symbol ASC",
        (run_date,),
    )
    return [r["symbol"] for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Core compute. Pure given (conn, run_date): reads daily_prices, returns the
# dict of counts. Separated from run() so tests exercise the math directly.
# ─────────────────────────────────────────────────────────────────────────────

def compute_counts(conn, run_date: str) -> dict[str, int]:
    """Compute the full breadth-counts dict for run_date from daily_prices."""
    counts = {c: 0 for c in _COUNT_COLS}

    symbols = _eligible_universe(conn, run_date)
    counts["total_universe"] = len(symbols)
    if not symbols:
        return counts

    for symbol in symbols:
        hist = _fetch_symbol_history(conn, symbol, run_date)
        today = None
        prior: list[sqlite3.Row] = []
        for r in hist:
            if r["trade_date"] == run_date:
                today = r
            elif r["trade_date"] < run_date:
                prior.append(r)
        if today is None:
            continue

        _accumulate_symbol(counts, today, prior)

    return counts


def _accumulate_symbol(counts: dict[str, int], today: sqlite3.Row, prior: list[sqlite3.Row]) -> None:
    """Fold one symbol's today-row + prior history into the counts dict."""
    close = today["close"]
    high = today["high"]
    low = today["low"]
    prev_close = today["prev_close"]

    # ── 4% Advance / Decline (decision 1: /prev_close) ──
    if prev_close is not None and prev_close > 0:
        chg = (close - prev_close) / prev_close
        if chg >= THRESH_UP_4PCT:
            counts["up_4pct"] += 1
        elif chg <= THRESH_DOWN_4PCT:
            counts["down_4pct"] += 1

    # ── Range bands (decision 5) ──
    rng = daily_range_pct(high, low) if (high is not None and low is not None) else None
    is_expansion = False
    if rng is not None:
        if rng <= THRESH_RANGE_CONTRACT:
            counts["range_contraction"] += 1
        elif rng >= THRESH_RANGE_EXPAND:
            counts["range_expansion"] += 1
            is_expansion = True

    # ── Close upper/lower half — expansion candles ONLY (decision 6) ──
    if is_expansion and close is not None and high is not None and low is not None and high > low:
        mid = (high + low) / 2.0
        if close >= mid:
            counts["close_upper_half"] += 1
        else:
            counts["close_lower_half"] += 1

    # ── Breakout / Breakdown (decision 3: 4% from prev_close) ──
    is_breakout = False
    is_breakdown = False
    if prev_close is not None and prev_close > 0:
        if high is not None and high >= prev_close * THRESH_BO:
            is_breakout = True
            counts["breakouts"] += 1
        if low is not None and low <= prev_close * THRESH_BD:
            is_breakdown = True
            counts["breakdowns"] += 1

    # ── BO/BD sustained vs failed (decision 7: 40% of range from the extreme) ──
    if high is not None and low is not None and high > low:
        span = high - low
        if is_breakout:
            if close is not None and close >= high - BO_BD_BAND_FRAC * span:
                counts["breakout_sustained"] += 1
            else:
                counts["breakout_failed"] += 1
        if is_breakdown:
            if close is not None and close <= low + BO_BD_BAND_FRAC * span:
                counts["breakdown_sustained"] += 1
            else:
                counts["breakdown_failed"] += 1

    # ── Volume high/low vs trailing 20d avg EXCLUDING today (decision 4) ──
    vol_today = today["volume"]
    if vol_today is not None and len(prior) >= VOL_AVG_WINDOW:
        prior_vols = [r["volume"] for r in prior[-VOL_AVG_WINDOW:]
                      if r["volume"] is not None]
        if len(prior_vols) == VOL_AVG_WINDOW and all(v is not None for v in prior_vols):
            avg_vol = sum(prior_vols) / VOL_AVG_WINDOW
            if avg_vol > 0:
                if vol_today > THRESH_VOL_HIGH * avg_vol:
                    counts["high_vol"] += 1
                elif vol_today < THRESH_VOL_LOW * avg_vol:
                    counts["low_vol"] += 1

    # ── 5-day / 20-day moves (decision 8: close N sessions ago -> today) ──
    closes = [r["close"] for r in prior if r["close"] is not None]
    if close is not None:
        if len(closes) >= 5:
            base5 = closes[-5]
            if base5 and base5 > 0:
                move5 = (close - base5) / base5
                if move5 >= THRESH_5D_UP:
                    counts["up_15pct_5d"] += 1
                elif move5 <= THRESH_5D_DN:
                    counts["down_15pct_5d"] += 1
        if len(closes) >= 20:
            base20 = closes[-20]
            if base20 and base20 > 0:
                move20 = (close - base20) / base20
                if move20 >= THRESH_20D_UP:
                    counts["up_25pct_20d"] += 1
                elif move20 <= THRESH_20D_DN:
                    counts["down_25pct_20d"] += 1

    # ── DEMA10/20/50/200 + 10% deviation (decision 9) ──
    closes_with_today = closes + ([close] if close is not None else [])
    d10 = ema(closes_with_today, 10)
    d20 = ema(closes_with_today, 20)
    d50 = ema(closes_with_today, 50)
    d200 = ema(closes_with_today, 200)
    if close is not None:
        if d10 is not None:
            if close >= d10 * (1 + THRESH_DEMA_DEV):
                counts["above_10pct_10dema"] += 1
            elif close <= d10 * (1 - THRESH_DEMA_DEV):
                counts["below_10pct_10dema"] += 1
            if close > d10:
                counts["above_10dema"] += 1
        if d20 is not None and close > d20:
            counts["above_20dema"] += 1
        if d50 is not None and close > d50:
            counts["above_50dema"] += 1
        if d200 is not None and close > d200:
            counts["above_200dema"] += 1

    # ── 52-week extremes + distance bands (decisions 10, 11) ──
    highs = [r["high"] for r in prior if r["high"] is not None] + ([high] if high is not None else [])
    lows = [r["low"] for r in prior if r["low"] is not None] + ([low] if low is not None else [])
    if highs and lows and close is not None:
        high_52 = max(highs)
        low_52 = min(lows)
        if high is not None and high >= high_52:
            counts["new_52wk_high"] += 1
        if low is not None and low <= low_52:
            counts["new_52wk_low"] += 1

        if high_52 > 0:
            if close >= high_52 * (1 - 0.15):
                counts["from_52wh_15pct"] += 1
            if close >= high_52 * (1 - 0.30):
                counts["from_52wh_30pct"] += 1
            if close >= high_52 * (1 - 0.50):
                counts["from_52wh_50pct"] += 1
            if close >= high_52 * (1 - 0.70):
                counts["from_52wh_70pct"] += 1
            if close < high_52 * (1 - 0.70):
                counts["from_52wh_70pct_plus"] += 1

        if low_52 > 0:
            if close <= low_52 * (1 + 0.15):
                counts["from_52wl_15pct"] += 1
            if close <= low_52 * (1 + 0.30):
                counts["from_52wl_30pct"] += 1
            if close <= low_52 * (1 + 0.50):
                counts["from_52wl_50pct"] += 1
            if close <= low_52 * (1 + 0.90):
                counts["from_52wl_90pct"] += 1
            if close <= low_52 * (1 + 1.50):
                counts["from_52wl_150pct"] += 1
            if close > low_52 * (1 + 1.50):
                counts["from_52wl_150pct_plus"] += 1


# ─────────────────────────────────────────────────────────────────────────────
# Upsert + orchestration
# ─────────────────────────────────────────────────────────────────────────────

def _upsert_row(conn, run_date: str, counts: dict[str, int]) -> None:
    """Idempotent upsert of one row on the trade_date PK.

    TraderLog's breadth_counts stores the ~38 counts as one JSON blob
    (db/schema.sql, W0) rather than one column per metric.
    """
    conn.execute(
        "INSERT INTO breadth_counts (trade_date, counts_json, universe_size, ingested_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(trade_date) DO UPDATE SET "
        "counts_json=excluded.counts_json, universe_size=excluded.universe_size, "
        "ingested_at=excluded.ingested_at",
        (run_date, json.dumps(counts), counts["total_universe"], now_iso()),
    )


def _log_run(conn, run_date: str, status: str, rows: int, dur: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (stage, run_date, status, rows, duration_ms, detail, ts) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (STAGE, run_date, status, rows, int(dur * 1000), detail, now_iso()),
    )


def run(conn, run_date: str) -> dict:
    """Compute breadth_counts for run_date from daily_prices and upsert the row.

    Idempotent: safe to re-run for the same run_date (upsert on trade_date PK).
    Returns {"status": "ok"|"skip"|"fail", "rows_affected": int, "detail": str}.
    """
    started = time.monotonic()
    try:
        symbols = _eligible_universe(conn, run_date)
        if not symbols:
            dur = time.monotonic() - started
            detail = f"no eligible daily_prices rows for {run_date}"
            _log_run(conn, run_date, "skip", 0, dur, detail)
            conn.commit()
            return {"status": "skip", "rows_affected": 0, "detail": detail}

        counts = compute_counts(conn, run_date)
        _upsert_row(conn, run_date, counts)
        dur = time.monotonic() - started
        detail = (
            f"universe={counts['total_universe']} "
            f"up4={counts['up_4pct']} dn4={counts['down_4pct']} "
            f"bo={counts['breakouts']} bd={counts['breakdowns']} "
            f"52wh={counts['new_52wk_high']} 52wl={counts['new_52wk_low']}"
        )
        _log_run(conn, run_date, "ok", 1, dur, detail)
        conn.commit()
        return {"status": "ok", "rows_affected": 1, "detail": detail}
    except Exception as exc:
        dur = time.monotonic() - started
        _log_run(conn, run_date, "fail", 0, dur, f"{type(exc).__name__}: {exc}")
        conn.commit()
        raise
