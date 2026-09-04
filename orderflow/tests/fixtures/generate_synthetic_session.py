"""Fixture tooling: regenerate ``synthetic_session.json`` deterministically.

This script is fixture tooling, not production code. It necessarily writes
raw FYERS wire-format field names — that is the point of the fixture: it is
the stand-in for captured live messages, i.e. the ADAPTER's input, not
anything downstream. Production code under ``orderflow/market_data`` and
``orderflow/checks`` never mentions these names (enforced by
``orderflow/tests/test_boundaries.py``).

Deterministic: same output every run (no RNG, no wall clock). Run:

    python orderflow/tests/fixtures/generate_synthetic_session.py

Session design (40 s, 4 symbols across 4 liquidity buckets):

  NSE:ABCAP-EQ   liquid_midcap     depth ~300 ms, quotes ~1.0 s
  NSE:MODMID-EQ  moderate_midcap   depth ~700 ms, quotes ~1.5 s
  NSE:LIQSML-EQ  liquid_smallcap   depth ~1.2 s,  quotes ~2.0 s
  NSE:THINSML-EQ thin_smallcap     depth ~2.6 s,  quotes ~3.0 s
                                   + one engineered ~10.4 s depth stale
                                     period (t=5.5 s → 15.9 s), kept separate
                                     from the disconnect window on purpose

  t=20.0s  forced disconnect (fixture transport raises)
  t=28.0s  reconnect + resubscribe acks, data resumes

  A second subscribe batch (2 probe symbols) is rejected by the fixture's
  simulated limit so the audit's rejection path is exercised and reported.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

SESSION_START = datetime(2026, 8, 28, 4, 15, 0, tzinfo=timezone.utc)  # 09:45 IST
SESSION_MS = 40_000
DISCONNECT_MS = 20_000
RECONNECT_MS = 28_000

SYMBOLS = [
    # symbol, bucket, depth_ms, quote_ms
    ("NSE:ABCAP-EQ", "liquid_midcap", 300, 1_000),
    ("NSE:MODMID-EQ", "moderate_midcap", 700, 1_500),
    ("NSE:LIQSML-EQ", "liquid_smallcap", 1_200, 2_000),
    ("NSE:THINSML-EQ", "thin_smallcap", 2_600, 3_000),
]
EXTRA_PROBE = ["NSE:PROBE1-EQ", "NSE:PROBE2-EQ"]

BASE_EPOCH = int(SESSION_START.timestamp())

# optional-field policy per symbol: which optional fields the fixture carries
WITH_ORDER_COUNT = {sym for sym, *_ in SYMBOLS if "THIN" not in sym}
WITH_TOTALS = {"NSE:ABCAP-EQ", "NSE:LIQSML-EQ"}
WITH_LAST_TRADE_QTY = {"NSE:ABCAP-EQ", "NSE:MODMID-EQ"}

# engineered stale period for the thin smallcap: no depth between these times
THIN_SYMBOL = "NSE:THINSML-EQ"
THIN_STALE_FROM_MS = 8_000
THIN_STALE_UNTIL_MS = 14_500


def price(sym_index: int, t_ms: float, base: float) -> float:
    """Deterministic small walk around ``base``."""
    step = ((int(t_ms) // 300) + sym_index * 3) % 7
    return round(base + step * 0.05, 2)


def quote_msg(sym: str, sym_index: int, t_ms: float) -> dict:
    ltp = price(sym_index, t_ms, 100.0 + sym_index * 20)
    msg = {
        "type": "sf",
        "symbol": sym,
        "ltp": ltp,
        "open_price": round(ltp - 0.8, 2),
        "high_price": round(ltp + 1.2, 2),
        "low_price": round(ltp - 1.1, 2),
        "prev_close_price": round(ltp - 0.35, 2),
        "vol_traded_today": 120_000 + sym_index * 37_500 + int(t_ms),
        "exch_feed_time": BASE_EPOCH + int((t_ms - 140) // 1000),  # ~140 ms feed latency, 1 s resolution
    }
    if sym in WITH_LAST_TRADE_QTY:
        msg["last_traded_qty"] = 25 + (int(t_ms) // 500) % 4 * 25
    return msg


def depth_msg(sym: str, sym_index: int, t_ms: float) -> dict:
    mid = price(sym_index, t_ms, 100.0 + sym_index * 20)
    msg = {
        "type": "dp",
        "symbol": sym,
        "exch_feed_time": BASE_EPOCH + int((t_ms - 140) // 1000),
    }
    for i in range(1, 6):
        msg[f"bid_price{i}"] = round(mid - 0.05 * i, 2)
        msg[f"ask_price{i}"] = round(mid + 0.05 * i, 2)
        msg[f"bid_size{i}"] = 400 + sym_index * 90 + i * 50 + (int(t_ms) // 250) % 3 * 10
        msg[f"ask_size{i}"] = 350 + sym_index * 80 + i * 45 + (int(t_ms) // 250) % 2 * 15
        if sym in WITH_ORDER_COUNT:
            msg[f"bid_order{i}"] = 2 + i + sym_index
            msg[f"ask_order{i}"] = 3 + i + sym_index
    if sym in WITH_TOTALS:
        msg["tot_buy_qty"] = 45_000 + sym_index * 1_000 + int(t_ms)
        msg["tot_sell_qty"] = 52_000 - sym_index * 800 - int(t_ms)
    return msg


def main() -> None:
    events: list[tuple[float, str, str, int]] = []
    for idx, (sym, _bucket, depth_ms, quote_ms) in enumerate(SYMBOLS):
        t = 300.0
        while t <= SESSION_MS:
            if not (DISCONNECT_MS <= t < RECONNECT_MS):
                events.append((t, "depth", sym, idx))
            t += depth_ms
        t = 600.0
        while t <= SESSION_MS:
            if not (DISCONNECT_MS <= t < RECONNECT_MS):
                events.append((t, "quote", sym, idx))
            t += quote_ms
    # the engineered stale window: drop thin smallcap depth inside it
    events = [
        e
        for e in events
        if not (e[1] == "depth" and e[2] == THIN_SYMBOL and THIN_STALE_FROM_MS <= e[0] <= THIN_STALE_UNTIL_MS)
    ]

    records: list[dict] = [
        {"_t_ms": 5, "control": {"type": "cn", "code": 200, "message": "Authentication done", "s": "ok"}},
        {"_t_ms": 10, "control": {"type": "sub", "code": 200, "message": "Subscribed", "s": "ok"}},
        {"_t_ms": 12, "control": {"type": "sub", "code": 200, "message": "Subscribed", "s": "ok"}},
        {"_t_ms": 15, "control": {"type": "sub", "code": 11011, "message": "subscription failed", "s": "error"}},
        {"_t_ms": 17, "control": {"type": "sub", "code": 11011, "message": "subscription failed", "s": "error"}},
    ]
    for t, kind, sym, idx in sorted(events, key=lambda e: e[0]):
        msg = depth_msg(sym, idx, t) if kind == "depth" else quote_msg(sym, idx, t)
        records.append({"_t_ms": int(t), "msg": msg})
    # lifecycle records are PART of the timeline: merged in by _t_ms below
    records.append({"_t_ms": DISCONNECT_MS, "disconnect": True, "cause": "fixture_forced_disconnect"})
    records.append({"_t_ms": RECONNECT_MS, "connect": True})
    records.append({"_t_ms": RECONNECT_MS + 10, "control": {"type": "sub", "code": 200, "message": "Subscribed", "s": "ok"}})
    records.append({"_t_ms": RECONNECT_MS + 12, "control": {"type": "sub", "code": 200, "message": "Subscribed", "s": "ok"}})
    records.sort(key=lambda r: r.get("_t_ms", 0))

    fixture = {
        "_provenance": {
            "generator": "orderflow/tests/fixtures/generate_synthetic_session.py",
            "note": (
                "Synthetic stand-in for captured live messages: raw decoded "
                "message dicts as emitted by the official fyers-apiv3 client. "
                "NOT real market data; wire field names appear here by design."
            ),
            "generated_at": SESSION_START.isoformat(),
        },
        "session_start_utc": SESSION_START.isoformat(),
        "subscribe_symbols": [sym for sym, *_ in SYMBOLS],
        "extra_probe_symbols": EXTRA_PROBE,
        "liquidity_buckets": {sym: bucket for sym, bucket, *_ in SYMBOLS},
        "depth_stale_ms": 5_000,
        "quote_stale_ms": 10_000,
        "measurement_notes": [
            "Synthetic fixture; cadences and the 8 s forced disconnect are scripted, not measured.",
            "The mid-session subscribe rejection is fixture-simulated to exercise the audit's rejection path.",
        ],
        "records": records,
    }
    out = Path(__file__).with_name("synthetic_session.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(fixture, fh, indent=1)
        fh.write("\n")
    print(f"wrote {out} with {len(records)} records")


if __name__ == "__main__":
    main()
