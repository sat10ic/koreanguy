import csv
import sqlite3

import pytest

from manas_os import db as manas_db
from manas_os.tools import import_broker
from manas_os.tools.import_broker import (
    aggregate_fills,
    fifo_match,
    import_tradebooks,
    read_tradebooks,
)


HEADERS = [
    "symbol", "isin", "trade_date", "exchange", "segment", "series",
    "trade_type", "auction", "quantity", "price", "trade_id", "order_id",
    "order_execution_time",
]


def _row(side, qty, price, trade_id, order_id, timestamp):
    return {
        "symbol": "ALPHA", "isin": "INE000000001", "trade_date": "2026-04-01",
        "exchange": "NSE", "segment": "EQ", "series": "EQ", "trade_type": side,
        "auction": "", "quantity": qty, "price": price, "trade_id": trade_id,
        "order_id": order_id, "order_execution_time": timestamp,
    }


def _write_tradebook(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def tradebooks(tmp_path):
    first = tmp_path / "tradebook one.csv"
    second = tmp_path / "tradebook (duplicate).csv"
    rows = [
        _row("BUY", 10, 100, "T1", "B1", "2026-04-01 09:20:00"),
        _row("BUY", 5, 110, "T2", "B1", "2026-04-01 09:20:01"),
        _row("SELL", 8, 120, "T3", "S1", "2026-04-01 11:00:00"),
        _row("BUY", 5, 90, "T4", "B2", "2026-04-01 12:00:00"),
        _row("SELL", 10, 130, "T5", "S2", "2026-04-01 14:00:00"),
    ]
    _write_tradebook(first, rows)
    _write_tradebook(second, [rows[0]])
    return first, second


def _create_journal(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE journal_trades ("
        "trade_id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT NOT NULL, "
        "symbol TEXT NOT NULL, setup TEXT, entry REAL, exit REAL, stop REAL, qty REAL, "
        "r_result REAL, mistake_tags_json TEXT, first_exit_flag_date TEXT, notes TEXT, "
        "created_at TEXT DEFAULT (datetime('now')))"
    )
    conn.commit()
    conn.close()


def test_fifo_aggregates_same_order_and_matches_partial_exits(tradebooks):
    rows, duplicate_count = read_tradebooks(tradebooks)
    fills = aggregate_fills(rows)
    matches, open_lots = fifo_match(fills)

    assert duplicate_count == 1
    assert len(fills) == 4
    buy_b1 = next(fill for fill in fills if fill.order_id == "B1")
    assert buy_b1.qty == pytest.approx(15)
    assert buy_b1.price == pytest.approx(103.3333333333)

    assert [match.qty for match in matches] == pytest.approx([8, 7, 3])
    assert sum(match.pnl for match in matches) == pytest.approx(440)
    assert len(open_lots) == 1
    assert open_lots[0].qty == pytest.approx(2)
    assert open_lots[0].price == pytest.approx(90)


def test_trade_id_dedupe_rejects_conflicting_economics(tmp_path):
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"
    _write_tradebook(first, [_row("BUY", 1, 100, "DUP", "B1", "2026-04-01 09:20:00")])
    _write_tradebook(second, [_row("BUY", 2, 100, "DUP", "B1", "2026-04-01 09:20:00")])

    with pytest.raises(ValueError, match="conflicting rows share trade_id"):
        read_tradebooks([first, second])


def test_import_tradebooks_routes_through_shared_db_connect(tmp_path, tradebooks, monkeypatch):
    # RELIABILITY_AUDIT_2026-07-19 defect #6: import_tradebooks() used to
    # open a raw sqlite3 connection with none of the canonical WAL/busy-
    # timeout settings, so it could collide with a concurrent writer (API
    # mutation thread, scheduler) instead of just waiting behind the shared
    # 30s busy_timeout. It must now go through manas_os.db.connect().
    db_path = tmp_path / "manas.db"
    _create_journal(db_path)

    captured = {}
    real_connect = manas_db.connect

    def spy_connect(path=None):
        conn = real_connect(path)
        captured["busy_timeout"] = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        captured["journal_mode"] = conn.execute("PRAGMA journal_mode").fetchone()[0]
        captured["path"] = str(path)
        return conn

    monkeypatch.setattr(manas_db, "connect", spy_connect)
    assert import_broker.db is manas_db  # same module object; patch above reaches it

    import_broker.import_tradebooks(tradebooks, db_path)

    assert captured["path"] == str(db_path)
    assert captured["busy_timeout"] == 30000
    assert captured["journal_mode"].lower() == "wal"

    # Independently confirm WAL is actually persisted in the file itself
    # (journal_mode, unlike busy_timeout, is stored in the DB header, so
    # this holds even from a brand-new connection).
    check = sqlite3.connect(db_path)
    try:
        assert check.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    finally:
        check.close()


def test_import_is_idempotent_and_persists_remaining_fifo_lot(tmp_path, tradebooks):
    db_path = tmp_path / "manas.db"
    _create_journal(db_path)

    first = import_tradebooks(tradebooks, db_path)
    second = import_tradebooks(tradebooks, db_path)

    assert (first.inserted, first.skipped) == (3, 0)
    assert (second.inserted, second.skipped) == (0, 3)

    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT source, import_key, broker_realized_pnl, r_result, exit_date "
            "FROM journal_trades ORDER BY trade_id"
        ).fetchall()
        assert len(rows) == 3
        assert all(row[0] == "zerodha_import" for row in rows)
        assert len({row[1] for row in rows}) == 3
        assert sum(row[2] for row in rows) == pytest.approx(440)
        assert all(row[3] is None for row in rows)
        assert all(row[4] == "2026-04-01" for row in rows)

        open_rows = conn.execute(
            "SELECT symbol, qty, avg_cost, first_buy_date FROM broker_open_lots"
        ).fetchall()
        assert open_rows == [("ALPHA", 2.0, 90.0, "2026-04-01")]
    finally:
        conn.close()
