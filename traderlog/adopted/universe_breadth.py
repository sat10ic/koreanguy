"""Compute NIFTYMIDSML400 breadth from bhavcopy — the regime's true universe.

Adopted (copied, not imported) from ``manas_os/sources/universe_breadth.py``
on 2026-08-23 for TraderLog W4. See CANONICAL.md §5 and
DECISIONS.md 2026-08-23 "Adopt the XP and MBI scores, but not the regime
governor". Once copied this file is TraderLog's own; drift from the manas_os
original is expected and fine.

XP's weights were calibrated on the NIFTYMIDSML400 universe (finallynitin's
Market Quadrant). Feeding it advancer counts from a different universe
produces plausible, wrong numbers silently — this module and its constituents
CSV are therefore a HARD DEPENDENCY of XP, not an optional breadth extra.

Per day, for each constituent present in daily_prices:
  - daily % change (close vs prev_close) -> up-4.5% / down-4.5% counts, adv/dec
  - close vs SMA10/20/50/200 -> % above each
These populate the breadth_daily columns XP + MBI read.

Canonical-row coverage rule: at least 85% of the configured constituent list
must have an actual EQ row on the date. The current static 400-symbol list
therefore requires 340 observations. This preserves observed historical
membership drift while rejecting materially incomplete source dates; the stored
``universe_size`` remains the actual observed count.

Constituent list: traderlog/data/niftymidsml400_constituents.csv (copied from
manas_os/data/niftymidsml400_constituents.csv, 2026-08-23, 400 NSE index
constituents).
Point-in-time caveat: uses the CURRENT constituent set for all history (minor
survivorship bias); acceptable for a single-user tool, revisit if it matters.

Changes made during adoption (drift, documented per CANONICAL.md §5):
  * ``_MA_WINDOWS`` drops 40 (kept: 10, 20, 50, 200) because TraderLog's
    ``breadth_daily`` (db/schema.sql, W0) has columns for pct_above_10/20/50/200
    dma only — no pct_above_40dma column exists, and neither XP nor MBI needs
    it (XP needs 10/20; MBI needs 10/20/50). Computing it would have nowhere
    to be written.
  * ``_upsert`` writes to TraderLog's ``breadth_daily`` shape: ``universe_size``
    instead of manas_os's separate universe/nhnl_universe columns (the single
    ``constituents`` count is stored; ``nhnl_universe`` is dropped, no matching
    column). ``nifty``/``nifty_chg_pct`` are left NULL — no NIFTY index feed is
    wired into TraderLog; nothing in W4 reads them.
  * ``pipeline_runs`` logging uses TraderLog's column names.
"""
from __future__ import annotations

import csv
import math
import time
from pathlib import Path

from traderlog.db import now_iso

_ROOT = Path(__file__).resolve().parents[1]  # traderlog/
_CONSTITUENTS = _ROOT / "data" / "niftymidsml400_constituents.csv"
STAGE = "adopted.universe_breadth"
SOURCE = "niftymidsml400_bhavcopy"

_MOVE_THRESHOLD = 4.5  # % move for the 4.5+/4.5- burst counts

# The current NIFTYMIDSML400 constituent file is applied backward through
# history, so requiring every one of its 400 symbols would discard legitimate
# historical sessions after membership changes.  Accept at least 85% of that
# configured list; below it, the apparent breadth is too incomplete to label as
# the XP calibration universe.  The persisted universe_size remains the actual
# observed count, never this threshold.
MIN_COVERAGE_FRACTION = 0.85

# 10/20/50/200 only — see module docstring "Changes made during adoption".
_MA_WINDOWS = (10, 20, 50, 200)

# 52-week new highs / new lows.
_NHNL_WINDOW = 252  # trading sessions ~= 52 weeks

# Lookback must cover the longest window plus weekends/holidays: 252 sessions is
# ~365 calendar days, and the 200SMA needs ~280. 420 gives headroom on both.
_LOOKBACK_DAYS = 420


def load_constituents(path: Path | str = _CONSTITUENTS) -> list[str]:
    """The NIFTYMIDSML400 symbols (uppercased). Empty list if the file is absent."""
    p = Path(path)
    if not p.exists():
        return []
    out: list[str] = []
    with p.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = (row.get("Symbol") or "").strip().upper()
            if sym:
                out.append(sym)
    return out


def _sma(values: list[float], n: int) -> float | None:
    return sum(values[:n]) / n if len(values) >= n else None


def minimum_coverage(symbols: list[str]) -> int:
    """Minimum observed constituents required for canonical daily breadth."""
    return math.ceil(len(symbols) * MIN_COVERAGE_FRACTION)


def compute_breadth(conn, run_date: str, symbols: list[str] | None = None) -> dict | None:
    """Breadth counts for the constituents as of run_date. None if no data."""
    symbols = symbols if symbols is not None else load_constituents()
    if not symbols:
        return None
    placeholders = ",".join("?" * len(symbols))
    rows = conn.execute(
        f"SELECT symbol, trade_date, close, prev_close, high, low FROM daily_prices "
        f"WHERE series='EQ' AND symbol IN ({placeholders}) "
        f"AND trade_date <= ? AND trade_date >= date(?, ?) "
        f"ORDER BY symbol, trade_date DESC",
        (*symbols, run_date, run_date, f"-{_LOOKBACK_DAYS} days"),
    ).fetchall()
    if not rows:
        return None

    by_sym: dict[str, list] = {}
    for r in rows:
        by_sym.setdefault(r["symbol"], []).append(r)

    n = up = down = adv = dec = 0
    nh = nl = nhnl_n = 0
    above = {w: 0 for w in _MA_WINDOWS}
    for sym, srows in by_sym.items():
        latest = srows[0]
        if latest["trade_date"] != run_date or latest["close"] is None:
            continue
        n += 1
        close = latest["close"]
        prev = latest["prev_close"]
        if prev:
            ch = (close - prev) / prev * 100.0
            if ch >= _MOVE_THRESHOLD:
                up += 1
            elif ch <= -_MOVE_THRESHOLD:
                down += 1
            if ch > 0:
                adv += 1
            elif ch < 0:
                dec += 1
        closes = [r["close"] for r in srows if r["close"] is not None]
        for w in _MA_WINDOWS:
            ma = _sma(closes, w)
            if ma is not None and close > ma:
                above[w] += 1

        win = srows[:_NHNL_WINDOW]
        if len(win) >= _NHNL_WINDOW:
            highs = [r["high"] for r in win if r["high"] is not None]
            lows = [r["low"] for r in win if r["low"] is not None]
            if highs and lows:
                nhnl_n += 1
                if latest["high"] is not None and latest["high"] >= max(highs):
                    nh += 1
                if latest["low"] is not None and latest["low"] <= min(lows):
                    nl += 1

    if n == 0:
        return None
    pct = lambda k: round(above[k] / n * 100.0, 2)  # noqa: E731
    return {
        "trade_date": run_date,
        "constituents": n,
        "advances": adv,
        "declines": dec,
        # Floored at 0.25% of ~400 so a zero-count day doesn't hit log(0) in
        # xp.compute_xp — see adopted/xp.py's term-5 penalty note.
        "up_4pct": round(max(up / n * 100.0, 0.25), 3),
        "down_4pct": round(max(down / n * 100.0, 0.25), 3),
        "pct_above_10dma": pct(10),
        "pct_above_20dma": pct(20),
        "pct_above_50dma": pct(50),
        "pct_above_200dma": pct(200),
        "new_highs_52w": nh,
        "new_lows_52w": nl,
        "net_new_highs_pct": (round((nh - nl) / nhnl_n * 100.0, 2) if nhnl_n else None),
    }


def _upsert(conn, b: dict) -> None:
    conn.execute(
        "INSERT INTO breadth_daily (trade_date, advances, declines, up_4pct, down_4pct, "
        "pct_above_10dma, pct_above_20dma, pct_above_50dma, pct_above_200dma, "
        "new_highs_52w, new_lows_52w, net_new_highs_pct, universe_size, source, ingested_at) "
        "VALUES (:trade_date, :advances, :declines, :up_4pct, :down_4pct, "
        ":pct_above_10dma, :pct_above_20dma, :pct_above_50dma, :pct_above_200dma, "
        ":new_highs_52w, :new_lows_52w, :net_new_highs_pct, :universe_size, :source, :ingested_at) "
        "ON CONFLICT(trade_date) DO UPDATE SET "
        "advances=excluded.advances, declines=excluded.declines, up_4pct=excluded.up_4pct, "
        "down_4pct=excluded.down_4pct, pct_above_10dma=excluded.pct_above_10dma, "
        "pct_above_20dma=excluded.pct_above_20dma, pct_above_50dma=excluded.pct_above_50dma, "
        "pct_above_200dma=excluded.pct_above_200dma, "
        "new_highs_52w=excluded.new_highs_52w, new_lows_52w=excluded.new_lows_52w, "
        "net_new_highs_pct=excluded.net_new_highs_pct, "
        "universe_size=excluded.universe_size, "
        "source=excluded.source, ingested_at=excluded.ingested_at",
        {
            "trade_date": b["trade_date"],
            "advances": b["advances"],
            "declines": b["declines"],
            "up_4pct": b["up_4pct"],
            "down_4pct": b["down_4pct"],
            "pct_above_10dma": b["pct_above_10dma"],
            "pct_above_20dma": b["pct_above_20dma"],
            "pct_above_50dma": b["pct_above_50dma"],
            "pct_above_200dma": b["pct_above_200dma"],
            "new_highs_52w": b["new_highs_52w"],
            "new_lows_52w": b["new_lows_52w"],
            "net_new_highs_pct": b["net_new_highs_pct"],
            "universe_size": b["constituents"],
            "source": SOURCE,
            "ingested_at": now_iso(),
        },
    )


def _log(conn, run_date, status, rows, started, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (stage, run_date, status, rows, duration_ms, detail, ts) "
        "VALUES (?,?,?,?,?,?,?)",
        (STAGE, run_date, status, rows, int((time.monotonic() - started) * 1000), detail, now_iso()),
    )


def run(conn, run_date: str) -> dict:
    """Compute + persist NIFTYMIDSML400 breadth for run_date. Never raises."""
    started = time.monotonic()
    try:
        symbols = load_constituents()
        if not symbols:
            _log(conn, run_date, "skip", 0, started, "no configured constituents")
            conn.commit()
            return {"status": "skip", "rows": 0, "detail": "no configured constituents"}
        b = compute_breadth(conn, run_date, symbols=symbols)
        if b is None:
            required = minimum_coverage(symbols)
            detail = (
                f"coverage 0/{len(symbols)} below required "
                f"{MIN_COVERAGE_FRACTION:.0%} ({required}): no constituent prices for date"
            )
            _log(conn, run_date, "fail", 0, started, detail)
            conn.commit()
            return {"status": "fail", "rows": 0, "detail": detail}
        required = minimum_coverage(symbols)
        if b["constituents"] < required:
            detail = (
                f"coverage {b['constituents']}/{len(symbols)} "
                f"below required {MIN_COVERAGE_FRACTION:.0%} ({required})"
            )
            _log(conn, run_date, "fail", 0, started, detail)
            conn.commit()
            return {"status": "fail", "rows": 0, "detail": detail}
        _upsert(conn, b)
        detail = f"n={b['constituents']} up4.5={b['up_4pct']} down4.5={b['down_4pct']}"
        _log(conn, run_date, "ok", 1, started, detail)
        conn.commit()
        return {"status": "ok", "rows": 1, "breadth": b}
    except Exception as exc:  # noqa: BLE001
        _log(conn, run_date, "fail", 0, started, str(exc))
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}
