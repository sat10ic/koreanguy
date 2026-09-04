"""N-41 — run FIFO round-trip matching over the real broker tradebook.

    .venv-orderflow/Scripts/python.exe unidesk/run_round_trips.py

Writes the durable artifact to unidesk/design/round_trips.json: per-trip
records, aggregates, unmatched fills (reported, never dropped), and the
audit-constant reconciliation (sameDayRoundTrips from the owner's audit vs
the computed count).
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from unidesk.research.round_trips import to_fills, match_round_trips  # noqa: E402

TRADES_JSON = REPO / "unidesk_terminal" / "src" / "data" / "broker" / "trades.json"
OUT = REPO / "unidesk" / "design" / "round_trips.json"


def main() -> int:
    raw = json.loads(TRADES_JSON.read_text(encoding="utf-8"))
    trades = raw["trades"] if isinstance(raw, dict) else raw
    fills = to_fills(trades)
    result = match_round_trips(fills)

    trips = result.round_trips
    same_day = [t for t in trips if t.same_day]
    wins = [t for t in trips if t.pnl > 0]
    pnl_total = sum(t.pnl for t in trips)
    unmatched_buy_qty = sum(f.quantity for f in result.unmatched_buys)
    unmatched_sell_qty = sum(f.quantity for f in result.unmatched_sells)

    payload = {
        "convention": "FIFO per symbol, long-only (DELIVERY tradebook); fees netted in fill values",
        "r_multiple_note": "fills carry no stop records — R-multiples are not computable without inventing a risk anchor; realised rupee P&L and percent return are the honest outputs",
        "fills_total": len(fills),
        "round_trips": len(trips),
        "same_day_round_trips": len(same_day),
        "audit_same_day_round_trips": 64,
        "audit_note": "audit constant from BROKER_AUDIT_2026-07-18.md — computed value reconciles the FY25-26 DELIVERY tradebook; differences in convention (product filter, date bounds) are recorded, not reconciled away",
        "winners": len(wins),
        "pnl_total_round_trips": round(pnl_total, 2),
        "open_positions": len(result.unmatched_buys),
        "open_position_qty": round(unmatched_buy_qty, 0),
        "orphan_sells": len(result.unmatched_sells),
        "orphan_sell_qty": round(unmatched_sell_qty, 0),
        "skipped_zero_quantity": result.skipped_zero_quantity,
        "reconciliation": {
            "fills_total": len(fills),
            "matched_buy_fills": result.matched_buy_fills,
            "matched_sell_fills": result.matched_sell_fills,
            "unmatched_buys": len(result.unmatched_buys),
            "unmatched_sells": len(result.unmatched_sells),
            "skipped_zero_quantity": result.skipped_zero_quantity,
        },
        "trips": [{
            "symbol": t.symbol, "close_date": t.close_date.isoformat(),
            "quantity": round(t.quantity, 1), "pnl": round(t.pnl, 2),
            "return_pct": round(t.return_pct, 2), "same_day": t.same_day,
            "holding_days": t.holding_days,
        } for t in trips],
        "unmatched_buys": [{"symbol": f.symbol, "trade_date": f.trade_date.isoformat(),
                            "quantity": f.quantity, "net_value": f.net_value}
                           for f in result.unmatched_buys],
        "unmatched_sells": [{"symbol": f.symbol, "trade_date": f.trade_date.isoformat(),
                             "quantity": f.quantity, "net_value": f.net_value}
                            for f in result.unmatched_sells],
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"[round-trips] fills={len(fills)} trips={len(trips)} "
          f"same-day={len(same_day)} (audit: 64) winners={len(wins)} "
          f"pnl={pnl_total:,.0f} open={len(result.unmatched_buys)} "
          f"orphan-sells={len(result.unmatched_sells)}")
    print(f"[round-trips] reconcile: {len(fills)} fills = "
          f"{result.matched_buy_fills} buys matched + {len(result.unmatched_buys)} open + "
          f"{result.matched_sell_fills} sells matched ({result.split_sell_fills} partially, remainder orphaned) + "
          f"{len(result.unmatched_sells)} pure orphans + {result.skipped_zero_quantity} skipped")
    print(f"[round-trips] artifact -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
