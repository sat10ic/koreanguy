"""Compute NIFTYMIDSML400 breadth from bhavcopy — the regime's true universe.

Replaces the Google-sheet breadth (a different, ~1100-stock universe that made
XP read ~6x too high) with breadth computed from our own daily_prices over the
exact 400 NIFTYMIDSML400 constituents. Same universe the XP/MBI reference
(finallynitin's Market Quadrant) was calibrated on.

Per day, for each constituent present in daily_prices:
  - daily % change (close vs prev_close) → up-4.5% / down-4.5% counts, adv/dec
  - close vs SMA10/20/40/50 → % above each
These aggregate into the breadth_daily columns XP + MBI read.

Constituent list: manas_os/data/niftymidsml400_constituents.csv (NSE index dump).
Point-in-time caveat: uses the CURRENT constituent set for all history (minor
survivorship bias); acceptable for a single-user tool, revisit if it matters.
"""
from __future__ import annotations

import csv
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CONSTITUENTS = _ROOT / "data" / "niftymidsml400_constituents.csv"
STAGE = "ingest_universe_breadth"
SOURCE = "niftymidsml400_bhavcopy"

_MOVE_THRESHOLD = 4.5  # % move for the 4.5+/4.5- burst counts

# 200 added 2026-07-30 for the Market Quadrant's BIAS row, which had no input at
# all and was rendering a 40-day stand-in labelled as long-term bias.
_MA_WINDOWS = (10, 20, 40, 50, 200)

# 52-week new highs / new lows — the Quadrant's TREND row, and the only breadth
# family that cleared its range in the user's 838-trade study (10-day sum of
# NH-NL +1.72R; the whole "% above a moving average" family was uncallable).
# We have shipped the uncallable family and left this one empty until now.
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


def compute_breadth(conn, run_date: str, symbols: list[str] | None = None) -> dict | None:
    """Breadth counts for the constituents as of run_date. None if no data.

    Pulls each constituent's trailing closes (≤100 calendar days ≈ 70 trading
    days, enough for the 50-day SMA) in one query,
    then computes the daily-move and MA-participation tallies in Python.
    """
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

    # group trailing closes per symbol (already date-desc)
    by_sym: dict[str, list] = {}
    for r in rows:
        by_sym.setdefault(r["symbol"], []).append(r)

    n = up = down = adv = dec = 0
    nh = nl = nhnl_n = 0
    above = {w: 0 for w in _MA_WINDOWS}
    for sym, srows in by_sym.items():
        latest = srows[0]
        if latest["trade_date"] != run_date or latest["close"] is None:
            continue  # constituent didn't trade on run_date
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

        # 52-week new high / new low. Counted only for names with a full year of
        # history -- a 3-month-old listing making "a 52-week high" is an artefact
        # of its own short life, not a breadth signal. nhnl_n tracks the eligible
        # denominator separately so the ratio stays honest.
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
    # up_4pct/down_4pct stored as % OF UNIVERSE (not raw count) — user decision:
    # bounds the XP recursion (raw counts blew up to ~64k in rallies) and makes
    # XP universe-invariant. The 4.5R MBI ratio is unaffected (it's a ratio).
    return {
        "trade_date": run_date,
        "constituents": n,
        "advances": adv,
        "declines": dec,
        # Floor at one-stock-equivalent (0.25% of ~400) so a zero-count day
        # doesn't hit log(0): the XP term-5 penalty log(down%) would otherwise
        # explode positive on zero-decliner rally days (XP spiked to ~18k).
        "up_4pct": round(max(up / n * 100.0, 0.25), 3),    # % up ≥4.5% (XP z_state input)
        "down_4pct": round(max(down / n * 100.0, 0.25), 3),  # % down ≥4.5% (XP term 5)
        "pct_above_10dma": pct(10),
        "pct_above_20dma": pct(20),
        "pct_above_40dma": pct(40),
        "pct_above_50dma": pct(50),
        "pct_above_200dma": pct(200),
        "new_highs_52w": nh,
        "new_lows_52w": nl,
        # net NH-NL as a % of the eligible (>=1yr history) universe, so it is
        # comparable across days even as constituents age into eligibility.
        "net_new_highs_pct": (round((nh - nl) / nhnl_n * 100.0, 2) if nhnl_n else None),
        "nhnl_universe": nhnl_n,
    }


def _upsert(conn, b: dict) -> None:
    conn.execute(
        "INSERT INTO breadth_daily (trade_date, advances, declines, up_4pct, down_4pct, "
        "pct_above_10dma, pct_above_20dma, pct_above_40dma, pct_above_50dma, "
        "pct_above_200dma, new_highs_52w, new_lows_52w, net_new_highs_pct, "
        "nhnl_universe, source) "
        "VALUES (:trade_date, :advances, :declines, :up_4pct, :down_4pct, "
        ":pct_above_10dma, :pct_above_20dma, :pct_above_40dma, :pct_above_50dma, "
        ":pct_above_200dma, :new_highs_52w, :new_lows_52w, :net_new_highs_pct, "
        ":nhnl_universe, :source) "
        "ON CONFLICT(trade_date) DO UPDATE SET "
        "advances=excluded.advances, declines=excluded.declines, up_4pct=excluded.up_4pct, "
        "down_4pct=excluded.down_4pct, pct_above_10dma=excluded.pct_above_10dma, "
        "pct_above_20dma=excluded.pct_above_20dma, pct_above_40dma=excluded.pct_above_40dma, "
        "pct_above_50dma=excluded.pct_above_50dma, "
        "pct_above_200dma=excluded.pct_above_200dma, "
        "new_highs_52w=excluded.new_highs_52w, new_lows_52w=excluded.new_lows_52w, "
        "net_new_highs_pct=excluded.net_new_highs_pct, "
        "nhnl_universe=excluded.nhnl_universe, "
        "source=excluded.source, ingested_at=datetime('now')",
        {**b, "source": SOURCE},
    )


def run(conn, run_date: str) -> dict:
    """Compute + persist NIFTYMIDSML400 breadth for run_date. Never raises."""
    started = time.monotonic()
    try:
        b = compute_breadth(conn, run_date)
        if b is None:
            _log(conn, run_date, "skip", 0, started, "no constituent prices for date")
            conn.commit()
            return {"status": "skip", "rows": 0}
        _upsert(conn, b)
        detail = f"n={b['constituents']} up4.5={b['up_4pct']} down4.5={b['down_4pct']}"
        _log(conn, run_date, "ok", 1, started, detail)
        conn.commit()
        return {"status": "ok", "rows": 1, "breadth": b}
    except Exception as exc:  # noqa: BLE001
        _log(conn, run_date, "fail", 0, started, str(exc))
        conn.commit()
        return {"status": "fail", "rows": 0, "detail": str(exc)}


def _log(conn, run_date, status, rows, started, detail) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, source, status, rows_affected, "
        "duration_s, detail) VALUES (?,?,?,?,?,?,?)",
        (run_date, STAGE, SOURCE, status, rows, round(time.monotonic() - started, 3), detail),
    )
