"""Tests for the Alpha outcome resolver backend."""
from __future__ import annotations

import json
import sqlite3
import pytest

from manas_os.alpha.schema import ensure_schema
from manas_os.alpha.resolver import resolve_all_outcomes, resolve_one_decision

DAILY_PRICES_DDL = """
CREATE TABLE IF NOT EXISTS daily_prices (
    symbol        TEXT NOT NULL,
    trade_date    TEXT NOT NULL,
    series        TEXT DEFAULT 'EQ',
    open          REAL, high REAL, low REAL, close REAL, prev_close REAL,
    last_price    REAL, avg_price REAL,
    volume        INTEGER,
    turnover      REAL,
    num_trades    INTEGER,
    delivery_qty  INTEGER,
    delivery_pct  REAL,
    source        TEXT,
    ingested_at   TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (symbol, trade_date, series)
);
"""

@pytest.fixture
def conn():
    """Create an in-memory database with the complete alpha schemas."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute(DAILY_PRICES_DDL)
    ensure_schema(c)
    yield c
    c.close()


def seed_prices(conn, symbol: str, bars: list[dict]):
    """Helper to insert daily prices for tests."""
    for bar in bars:
        conn.execute("""
            INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, high, low, close, prev_close)
            VALUES (?, ?, 'EQ', ?, ?, ?, ?, ?)
        """, (
            symbol.upper(),
            bar["trade_date"],
            bar.get("open"),
            bar.get("high"),
            bar.get("low"),
            bar.get("close"),
            bar.get("prev_close"),
        ))
    conn.commit()


def seed_decision(conn, memory_id: str, decision_time: str, symbol: str, decision: str, confirmation: float, invalidation: float, time_window: int):
    """Helper to insert a decision memory."""
    proposed_path = {
        "confirmation": confirmation,
        "invalidation": invalidation,
        "time_window": time_window
    }
    conn.execute("""
        INSERT INTO decision_memories (memory_id, decision_time, symbol, decision, proposed_path_json, evidence_json, data_quality)
        VALUES (?, ?, ?, ?, ?, '{}', 1.0)
    """, (
        memory_id,
        decision_time,
        symbol.upper(),
        decision,
        json.dumps(proposed_path),
    ))
    conn.commit()


def test_resolver_no_trigger(conn):
    # Setup decision: confirmation=100, invalidation=90, window=3
    seed_decision(conn, "dec_no_trig", "2026-07-10T15:31:00+05:30", "TEST1", "TAKE", 100.0, 90.0, 3)

    # Seed 3 price bars where price never triggers (>100) or invalidates (<90)
    seed_prices(conn, "TEST1", [
        {"trade_date": "2026-07-13", "open": 95.0, "high": 98.0, "low": 93.0, "close": 96.0, "prev_close": 94.0},
        {"trade_date": "2026-07-14", "open": 96.0, "high": 99.0, "low": 94.0, "close": 95.0, "prev_close": 96.0},
        {"trade_date": "2026-07-15", "open": 95.0, "high": 97.0, "low": 92.0, "close": 94.0, "prev_close": 95.0},
    ])

    resolved = resolve_all_outcomes(conn)
    assert resolved == 1

    # Check written row
    row = conn.execute("SELECT * FROM decision_memory_outcomes WHERE memory_id = 'dec_no_trig'").fetchone()
    assert row is not None
    assert row["outcome_available_at"] == "2026-07-15T15:31:00+05:30"
    
    outcome = json.loads(row["outcome_json"])
    assert outcome["status"] == "NO_TRIGGER"
    assert outcome["sessions_elapsed"] == 3


def test_resolver_invalidated(conn):
    # Setup decision: confirmation=100, invalidation=90, window=3
    seed_decision(conn, "dec_invalidated", "2026-07-10T15:31:00+05:30", "TEST2", "TAKE", 100.0, 90.0, 3)

    # Bar 1: does not invalidate or trigger
    # Bar 2: invalidates (low=89 <= 90) before triggering
    # Bar 3: would have triggered, but it is already invalidated!
    seed_prices(conn, "TEST2", [
        {"trade_date": "2026-07-13", "open": 95.0, "high": 98.0, "low": 93.0, "close": 96.0, "prev_close": 94.0},
        {"trade_date": "2026-07-14", "open": 92.0, "high": 94.0, "low": 89.0, "close": 91.0, "prev_close": 96.0},
        {"trade_date": "2026-07-15", "open": 91.0, "high": 105.0, "low": 90.5, "close": 102.0, "prev_close": 91.0},
    ])

    resolved = resolve_all_outcomes(conn)
    assert resolved == 1

    row = conn.execute("SELECT * FROM decision_memory_outcomes WHERE memory_id = 'dec_invalidated'").fetchone()
    outcome = json.loads(row["outcome_json"])
    assert outcome["status"] == "INVALIDATED"
    assert outcome["trigger_date"] == "2026-07-14"


def test_resolver_gap_over_invalidation(conn):
    seed_decision(conn, "dec_gap_over", "2026-07-10T15:31:00+05:30", "TEST3", "TAKE", 100.0, 90.0, 3)

    # Bar 1: gaps over invalidation (open = 85 <= 90) but high goes to 102 (above 100 trigger)
    # This should be classified as GAP_OVER_INVALIDATION (untradeable)
    seed_prices(conn, "TEST3", [
        {"trade_date": "2026-07-13", "open": 85.0, "high": 102.0, "low": 84.0, "close": 86.0, "prev_close": 95.0},
    ])

    resolved = resolve_all_outcomes(conn)
    assert resolved == 1

    row = conn.execute("SELECT * FROM decision_memory_outcomes WHERE memory_id = 'dec_gap_over'").fetchone()
    outcome = json.loads(row["outcome_json"])
    assert outcome["status"] == "GAP_OVER_INVALIDATION"
    assert outcome["trigger_date"] == "2026-07-13"


def test_resolver_triggered_then_stopped(conn):
    seed_decision(conn, "dec_stop", "2026-07-10T15:31:00+05:30", "TEST4", "TAKE", 100.0, 90.0, 3)

    # Bar 1: open = 95, high = 102 (triggers!), low = 88 (also hits stop!)
    # Should trigger and then get stopped out on day 1
    seed_prices(conn, "TEST4", [
        {"trade_date": "2026-07-13", "open": 95.0, "high": 102.0, "low": 88.0, "close": 90.0, "prev_close": 94.0},
    ])

    resolved = resolve_all_outcomes(conn)
    assert resolved == 1

    row = conn.execute("SELECT * FROM decision_memory_outcomes WHERE memory_id = 'dec_stop'").fetchone()
    outcome = json.loads(row["outcome_json"])
    assert outcome["status"] == "RESOLVED"
    assert outcome["entry_date"] == "2026-07-13"
    assert outcome["entry_fill"] == 100.0  # entry at confirmation
    assert outcome["exit_reason"] == "stop"
    assert outcome["exit_price"] == 90.0
    assert outcome["exit_date"] == "2026-07-13"
    assert outcome["mae_r"] == -1.2  # (88 - 100) / 10 = -1.2 R because the day's low was 88
    assert outcome["time_to_stop"] == 0


def test_resolver_runner(conn):
    seed_decision(conn, "dec_runner", "2026-07-10T15:31:00+05:30", "TEST5", "TAKE", 100.0, 90.0, 3)

    # Seed 21 bars: triggers on day 1, runs up, never stopped
    bars = []
    # Day 1: triggers (open=95, high=102, low=92, close=98) -> entry_fill = 100.0
    bars.append({"trade_date": "2026-07-13", "open": 95.0, "high": 102.0, "low": 92.0, "close": 98.0, "prev_close": 94.0})
    # Day 2: gaps up (open=105, high=112, low=103, close=110) -> hits +1R (110)
    bars.append({"trade_date": "2026-07-14", "open": 105.0, "high": 112.0, "low": 103.0, "close": 110.0, "prev_close": 98.0})
    # Day 3: gaps down (open=108, high=124, low=105, close=120) -> hits +2R (120), overnight gap = 108 - 110 = -2.0 (-0.2R)
    bars.append({"trade_date": "2026-07-15", "open": 108.0, "high": 124.0, "low": 105.0, "close": 120.0, "prev_close": 110.0})

    # Day 4 to 21
    for day in range(16, 36):
        date_str = f"2026-07-{day}"
        bars.append({"trade_date": date_str, "open": 120.0, "high": 125.0, "low": 118.0, "close": 120.0, "prev_close": 120.0})

    seed_prices(conn, "TEST5", bars)

    resolved = resolve_all_outcomes(conn)
    assert resolved == 1

    row = conn.execute("SELECT * FROM decision_memory_outcomes WHERE memory_id = 'dec_runner'").fetchone()
    outcome = json.loads(row["outcome_json"])
    assert outcome["status"] == "RESOLVED"
    assert outcome["time_to_1r"] == 1  # hit on index 1
    assert outcome["time_to_2r"] == 2  # hit on index 2
    assert outcome["time_to_stop"] is None
    assert outcome["exit_reason"] == "horizon_close"
    assert outcome["fwd_r_5"] == 2.0  # close of bar 5 is 120.0 -> (120 - 100) / 10 = 2.0
    assert outcome["fwd_r_20"] == 2.0
    assert outcome["sum_adverse_gaps_r"] == -0.2  # overnight gap on Day 3 only


def test_resolver_pending(conn):
    # Setup decision
    seed_decision(conn, "dec_pending", "2026-07-10T15:31:00+05:30", "TEST6", "TAKE", 100.0, 90.0, 3)

    # 1. No price data at all -> UNRESOLVABLE because the symbol is completely unknown in daily_prices
    assert resolve_one_decision(conn, "dec_pending", "2026-07-10T15:31:00+05:30", "TEST6", None)["status"] == "UNRESOLVABLE"
    
    # Seed historical price to make TEST6 a known symbol, but no future prices yet
    seed_prices(conn, "TEST6", [
        {"trade_date": "2026-07-10", "open": 90.0, "high": 92.0, "low": 89.0, "close": 91.0, "prev_close": 90.0},
    ])

    # Now it should be PENDING since the symbol is known, but there are no future bars
    resolved = resolve_all_outcomes(conn)
    assert resolved == 0

    # 2. Add some price data, but less than validity window (1 bar, doesn't trigger)
    seed_prices(conn, "TEST6", [
        {"trade_date": "2026-07-13", "open": 95.0, "high": 98.0, "low": 93.0, "close": 96.0, "prev_close": 91.0},
    ])
    
    # Still pending because window=3 and only 1 bar is available without triggering or invalidating
    resolved = resolve_all_outcomes(conn)
    assert resolved == 0


def test_resolver_idempotent(conn):
    seed_decision(conn, "dec_idem", "2026-07-10T15:31:00+05:30", "TEST7", "TAKE", 100.0, 90.0, 3)
    seed_prices(conn, "TEST7", [
        {"trade_date": "2026-07-13", "open": 85.0, "high": 102.0, "low": 84.0, "close": 86.0, "prev_close": 95.0},
    ])

    resolved_first = resolve_all_outcomes(conn)
    assert resolved_first == 1

    resolved_second = resolve_all_outcomes(conn)
    assert resolved_second == 0  # no new outcomes resolved
