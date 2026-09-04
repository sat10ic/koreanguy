"""T2.2 — the PEAD/gap-drift decile study (the roadmap's most important research bet).

Question: do gap events on UNDER-COVERED small/mid caps drift harder than on
large caps? If yes (small-decile T+10 drift materially above large-decile),
PEAD becomes the feed's anchor setup.

Honest scope: historical GROWTH data only exists for ChartsMaze dump dates, so
this studies the PRICE legs of an EP — gap-up >=4% on volume >=1.5x 20-bar avg
after a QUIET pre-gap base (25-bar band <=25%, drift <=10%) — across all
history in daily_prices. Market cap comes from the LATEST symbol_quality row
(point-in-time mcap unavailable) — an approximation, flagged in output.
"""
from __future__ import annotations

from statistics import median
from typing import Any


def find_gap_events(conn, start_date: str, end_date: str) -> list[dict[str, Any]]:
    """One pass over daily_prices; returns qualifying gap events."""
    rows = conn.execute(
        "SELECT symbol, trade_date, open, high, low, close, prev_close, volume "
        "FROM daily_prices WHERE series='EQ' AND trade_date >= date(?, '-60 days') "
        "AND trade_date <= ? ORDER BY symbol, trade_date",
        (start_date, end_date),
    ).fetchall()
    by_sym: dict[str, list] = {}
    for r in rows:
        by_sym.setdefault(r["symbol"], []).append(r)

    events = []
    for sym, bars in by_sym.items():
        for i in range(26, len(bars)):
            b = bars[i]
            if b["trade_date"] < start_date:
                continue
            o, pc, v = b["open"], b["prev_close"], b["volume"]
            if not o or not pc or not v:
                continue
            gap = (o - pc) / pc * 100.0
            if gap < 4.0:
                continue
            pre = bars[i - 25:i]
            closes = [x["close"] for x in pre if x["close"]]
            highs = [x["high"] for x in pre if x["high"]]
            lows = [x["low"] for x in pre if x["low"]]
            vols = [x["volume"] for x in pre[-20:] if x["volume"]]
            if len(closes) < 20 or not vols:
                continue
            if v < 1.5 * (sum(vols) / len(vols)):
                continue
            band = (max(highs) - min(lows)) / closes[-1] * 100.0
            drift = abs(closes[-1] - closes[0]) / closes[0] * 100.0
            if band > 25.0 or drift > 10.0:
                continue
            events.append({"symbol": sym, "date": b["trade_date"], "gap": round(gap, 1),
                           "entry": b["close"], "idx": i})
    # forward returns T+10 / T+20 from event close
    out = []
    for e in events:
        bars = by_sym[e["symbol"]]
        i = e["idx"]
        if i + 20 >= len(bars):
            continue
        c0 = bars[i]["close"]
        c10, c20 = bars[i + 10]["close"], bars[i + 20]["close"]
        if not c0 or not c10 or not c20:
            continue
        out.append({**e, "fwd10": (c10 - c0) / c0 * 100.0, "fwd20": (c20 - c0) / c0 * 100.0})
    return out


def mcap_map(conn) -> dict[str, float]:
    rows = conn.execute(
        "SELECT symbol, market_cap_cr FROM symbol_quality WHERE market_cap_cr IS NOT NULL "
        "AND trade_date = (SELECT MAX(trade_date) FROM symbol_quality)"
    ).fetchall()
    return {r["symbol"]: float(r["market_cap_cr"]) for r in rows}


def run_study(conn, start_date: str, end_date: str) -> str:
    events = find_gap_events(conn, start_date, end_date)
    caps = mcap_map(conn)
    buckets = {
        "small (500-3000cr)": lambda m: 500 <= m <= 3000,
        "mid (3000-8000cr)": lambda m: 3000 < m <= 8000,
        "large (>8000cr)": lambda m: m > 8000,
        "micro (<500cr) [pump zone]": lambda m: m < 500,
        "mcap unknown": None,
    }
    lines = [f"PEAD/gap-drift decile study {start_date}..{end_date}",
             f"events: {len(events)} (gap>=4% + vol>=1.5x + quiet 25-bar base)",
             "NOTE: mcap = latest snapshot (approximation, not point-in-time)",
             f"{'bucket':<28} {'n':>5} {'med fwd10%':>11} {'med fwd20%':>11} {'hit10(>+3%)':>12}"]
    lines.append("-" * len(lines[-1]))
    for name, pred in buckets.items():
        if pred is None:
            grp = [e for e in events if e["symbol"] not in caps]
        else:
            grp = [e for e in events if e["symbol"] in caps and pred(caps[e["symbol"]])]
        if len(grp) < 10:
            lines.append(f"{name:<28} {len(grp):>5} {'n<10':>11} {'n<10':>11} {'n<10':>12}")
            continue
        f10 = [e["fwd10"] for e in grp]
        f20 = [e["fwd20"] for e in grp]
        hit = sum(1 for x in f10 if x > 3.0) / len(f10)
        lines.append(f"{name:<28} {len(grp):>5} {median(f10):>10.2f}% {median(f20):>10.2f}% "
                     f"{hit*100:>11.1f}%")
    return "\n".join(lines)
