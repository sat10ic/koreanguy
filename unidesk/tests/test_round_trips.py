"""N-41 — FIFO round-trip matching over the broker tradebook.

Hand-checked core case embedded as a test: buy 100@10 + 100@12, sell 150@15
then 50@14 — FIFO cost = 1000 + 600 = 1600 for the first exit, 600 for the
second; total pnl reconciles to sells − buys exactly.
"""
from __future__ import annotations

from datetime import date

import pytest

from unidesk.research.round_trips import to_fills, match_round_trips


def _rows(*rows):
    return [dict(trade_date=d, symbol=s, side=side, quantity=q, price=p, net_value=n)
            for d, s, side, q, p, n in rows]


def test_fifo_partial_then_flat_hand_checked():
    fills = to_fills(_rows(
        ("2026-01-05", "X", "BUY", 100, 10.0, 1000.0),
        ("2026-01-06", "X", "BUY", 100, 12.0, 1200.0),
        ("2026-01-07", "X", "SELL", 150, 15.0, 2250.0),
        ("2026-01-08", "X", "SELL", 50, 14.0, 700.0),
    ))
    r = match_round_trips(fills)
    assert len(r.realized_exits) == 2
    assert r.realized_exits[0].cost_basis == pytest.approx(1600.0)   # 100@10 + 50@12
    assert r.realized_exits[1].cost_basis == pytest.approx(600.0)    # 50@12
    assert r.realized_exits[-1].fully_closes is True
    total_pnl = sum(e.pnl for e in r.realized_exits)
    assert total_pnl == pytest.approx((2250.0 + 700.0) - (1000.0 + 1200.0))


def test_same_day_round_trip_flagged():
    fills = to_fills(_rows(
        ("2026-01-05", "X", "BUY", 100, 10.0, 1000.0),
        ("2026-01-05", "X", "SELL", 100, 11.0, 1100.0),
    ))
    r = match_round_trips(fills)
    assert len(r.round_trips) == 1
    assert r.round_trips[0].same_day is True


def test_unmatched_sells_reported_not_dropped():
    fills = to_fills(_rows(("2026-01-05", "X", "SELL", 100, 10.0, 1000.0)))
    r = match_round_trips(fills)
    assert len(r.unmatched_sells) == 1 and r.unmatched_sells[0].quantity == 100
    assert r.realized_exits == []


def test_open_position_reported_as_unmatched_buy():
    fills = to_fills(_rows(("2026-01-05", "X", "BUY", 100, 10.0, 1000.0)))
    r = match_round_trips(fills)
    assert len(r.unmatched_buys) == 1 and r.unmatched_buys[0].quantity == 100
    assert r.realized_exits == []


def test_zero_quantity_fill_skipped_and_counted():
    fills = to_fills(_rows(("2026-01-05", "X", "BUY", 0, 10.0, 0.0)))
    r = match_round_trips(fills)
    assert r.skipped_zero_quantity == 1


def test_oversell_split_into_matched_and_orphan():
    fills = to_fills(_rows(
        ("2026-01-05", "X", "BUY", 50, 10.0, 500.0),
        ("2026-01-06", "X", "SELL", 80, 12.0, 960.0),
    ))
    r = match_round_trips(fills)
    # 50 matched FIFO, 30 orphaned — both reported
    assert r.realized_exits[0].quantity == 50
    assert r.unmatched_sells and r.unmatched_sells[0].quantity == 30
    assert r.realized_exits[0].fully_closes is True
