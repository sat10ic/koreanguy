"""Breadth COUNTS compute stage (Step 0 of the breadth-enrichment wave).

Given ``run_date``, compute ~38 daily breadth COUNT metrics from OUR OWN
``daily_prices`` universe (not any external sheet) and upsert one row into
``breadth_counts``, keyed by ``trade_date``. This module is the raw-count
layer; a separate analytics module (built by a second model) will derive the
ratio/percentage columns on top of these counts.

Ground truth for every threshold is the verified source workbook
"Market Breadth V2.0.xlsm" (documented in
``manas_os/design/study/REVERSE_ENGINEERING.md``). The binding quirk decisions
(handoff §12) are applied here; comments cite the decision number.

No network fetch. Reads only from ``daily_prices``. stdlib + sqlite3 only
(no pandas/numpy) so it stays light enough for every EOD pipeline pass.
"""
from __future__ import annotations

import sqlite3
import time

STAGE = "breadth_counts"
SOURCE = "breadth_counts"

# ─────────────────────────────────────────────────────────────────────────────
# Target table DDL. The maintainer applies this; this module does NOT run a
# migration against a live orchestrator. Kept here so the storage contract is
# co-located with the one writer. Column names are exact (handoff §target).
# ─────────────────────────────────────────────────────────────────────────────
DDL = """\
CREATE TABLE IF NOT EXISTS breadth_counts (
    trade_date            TEXT PRIMARY KEY,
    total_universe        INTEGER,
    up_4pct               INTEGER,
    down_4pct             INTEGER,
    high_vol              INTEGER,
    low_vol               INTEGER,
    range_contraction     INTEGER,
    range_expansion       INTEGER,
    close_upper_half      INTEGER,
    close_lower_half      INTEGER,
    breakouts             INTEGER,
    breakout_sustained    INTEGER,
    breakout_failed       INTEGER,
    breakdowns            INTEGER,
    breakdown_sustained   INTEGER,
    breakdown_failed      INTEGER,
    up_15pct_5d           INTEGER,
    down_15pct_5d         INTEGER,
    up_25pct_20d          INTEGER,
    down_25pct_20d        INTEGER,
    above_10pct_10dema    INTEGER,
    below_10pct_10dema    INTEGER,
    above_10dema          INTEGER,
    above_20dema          INTEGER,
    above_50dema          INTEGER,
    above_200dema         INTEGER,
    new_52wk_high         INTEGER,
    new_52wk_low          INTEGER,
    from_52wh_15pct       INTEGER,
    from_52wh_30pct       INTEGER,
    from_52wh_50pct       INTEGER,
    from_52wh_70pct       INTEGER,
    from_52wh_70pct_plus  INTEGER,
    from_52wl_15pct       INTEGER,
    from_52wl_30pct       INTEGER,
    from_52wl_50pct       INTEGER,
    from_52wl_90pct       INTEGER,
    from_52wl_150pct      INTEGER,
    from_52wl_150pct_plus INTEGER,
    source                TEXT DEFAULT 'breadth_counts',
    ingested_at           TEXT DEFAULT (datetime('now'))
);
"""

# Output column order (matches DDL exactly, excluding the two managed columns
# source/ingested_at which get defaults). Kept as a list so the upsert and the
# counts dict stay in lockstep — never drift on column order.
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
        # EMA1 == the last value; but the recursion below would divide by 1,
        # which is fine — guard anyway for clarity.
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

# We need up to 252 prior sessions for 52wk extremes + 1 for today = 253,
# plus headroom so EMA200 has a stable seed after the same query. 252 + 200
# is a safe upper bound; ordering by date and slicing in Python keeps it one
# query per symbol.
_HISTORY_LOOKBACK = max(WEEKS_52_SESSIONS, 200) + VOL_AVG_WINDOW + 5


def _fetch_symbol_history(conn, symbol: str, run_date: str) -> list[sqlite3.Row]:
    """The MOST RECENT `_HISTORY_LOOKBACK` EQ rows for `symbol` with
    trade_date <= run_date, returned oldest-first.

    QC fix (2026-07-11): the original `ORDER BY trade_date ASC LIMIT ?`
    returned the OLDEST rows, so any symbol with more history than the
    window (most of the universe; data since 2004) never had run_date in
    its slice and was silently skipped — undercounting every metric on the
    real DB while small test fixtures passed. Take the newest N descending,
    then reverse to keep the oldest-first contract the callers rely on."""
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
    """Decision (universe filter): every symbol with an EQ row on run_date
    where close >= 1."""
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
    """Compute the full breadth-counts dict for run_date from daily_prices.

    Returns a dict keyed by the _COUNT_COLS names. Each value is an int count.
    Pure with respect to the DB: no writes, no side effects. Callers wrap this
    in the upsert/log/commit orchestration.
    """
    counts = {c: 0 for c in _COUNT_COLS}

    symbols = _eligible_universe(conn, run_date)
    counts["total_universe"] = len(symbols)
    if not symbols:
        return counts  # caller decides skip vs zero-row

    for symbol in symbols:
        hist = _fetch_symbol_history(conn, symbol, run_date)
        # The last row whose trade_date == run_date is "today". If the symbol
        # is in the eligible universe it has a row for run_date, but the
        # lookback query is inclusive of run_date so today is hist[-1] when
        # dates are unique per (symbol, series). Guard regardless.
        today = None
        prior: list[sqlite3.Row] = []
        for r in hist:
            if r["trade_date"] == run_date:
                today = r
            elif r["trade_date"] < run_date:
                prior.append(r)
        if today is None:
            # No exact row for run_date (shouldn't happen for an eligible
            # symbol, but stay defensive) — skip silently.
            continue

        _accumulate_symbol(counts, today, prior)

    return counts


def _accumulate_symbol(counts: dict[str, int], today: sqlite3.Row, prior: list[sqlite3.Row]) -> None:
    """Fold one symbol's today-row + prior history into the counts dict.

    Each metric guards its own data-availability: a symbol missing the history
    a metric needs (e.g. <20 sessions for vol avg) is excluded from THAT count
    only, never from the universe or from other counts it can support.
    """
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
            # sustained: closed within top 40% of range measured down from high
            if close is not None and close >= high - BO_BD_BAND_FRAC * span:
                counts["breakout_sustained"] += 1
            else:
                counts["breakout_failed"] += 1
        if is_breakdown:
            # sustained: closed within bottom 40% measured up from low
            if close is not None and close <= low + BO_BD_BAND_FRAC * span:
                counts["breakdown_sustained"] += 1
            else:
                counts["breakdown_failed"] += 1
    # else: zero-range day — decision 7 says exclude from sustained/failed.

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
    # Include today's high/low in the trailing window (decision 10: "including
    # today"). A new 52wh means today's high == the window max.
    highs = [r["high"] for r in prior if r["high"] is not None] + ([high] if high is not None else [])
    lows = [r["low"] for r in prior if r["low"] is not None] + ([low] if low is not None else [])
    if highs and lows and close is not None:
        high_52 = max(highs)
        low_52 = min(lows)
        # new high/low — decision 10: partial history still computed (assumption)
        if high is not None and high >= high_52:
            counts["new_52wk_high"] += 1
        if low is not None and low <= low_52:
            counts["new_52wk_low"] += 1

        # from-high bands (decision 11): inclusive nested — each band counted
        # independently against its own threshold, NOT mutually exclusive.
        if high_52 > 0:
            if close >= high_52 * (1 - 0.15):
                counts["from_52wh_15pct"] += 1
            if close >= high_52 * (1 - 0.30):
                counts["from_52wh_30pct"] += 1
            if close >= high_52 * (1 - 0.50):
                counts["from_52wh_50pct"] += 1
            if close >= high_52 * (1 - 0.70):
                counts["from_52wh_70pct"] += 1
            # 70% Plus = strict complement (deep laggards): > 70% below the high
            if close < high_52 * (1 - 0.70):
                counts["from_52wh_70pct_plus"] += 1

        # from-low bands (decision 11 + decision 2: measured from the LOW)
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
            # 150% Plus = strict complement (extended leaders): > 150% above low
            if close > low_52 * (1 + 1.50):
                counts["from_52wl_150pct_plus"] += 1


# ─────────────────────────────────────────────────────────────────────────────
# Upsert + orchestration (mirrors breadth_sheet.run exactly)
# ─────────────────────────────────────────────────────────────────────────────

def _upsert_row(conn, run_date: str, counts: dict[str, int]) -> None:
    """Idempotent upsert of one row on the trade_date PK."""
    cols = ["trade_date"] + _COUNT_COLS
    placeholders = ", ".join("?" for _ in cols)
    updates = ", ".join(f"{c}=excluded.{c}" for c in _COUNT_COLS)
    sql = (
        f"INSERT INTO breadth_counts ({', '.join(cols)}) "
        f"VALUES ({placeholders}) "
        f"ON CONFLICT(trade_date) DO UPDATE SET {updates}, "
        f"ingested_at=datetime('now')"
    )
    conn.execute(sql, [run_date] + [counts[c] for c in _COUNT_COLS])


def _log_run(conn, run_date: str, status: str, rows: int, dur: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (run_date, STAGE, SOURCE, status, rows, dur, detail),
    )


def run(conn, run_date: str) -> dict:
    """Compute breadth_counts for run_date from daily_prices and upsert the row.

    Idempotent: safe to re-run for the same run_date (upsert on trade_date PK).
    Returns {"status": "ok"|"skip"|"fail", "rows_affected": int, "detail": str}.
    Failures are recorded (status='fail') and re-raised so the orchestrator's
    per-stage isolation reports them — mirrors breadth_sheet.run exactly.
    """
    started = time.monotonic()
    try:
        # Eligible-universe check first: a date with no rows is a skip, not a
        # zero-row insert (handoff function contract).
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
