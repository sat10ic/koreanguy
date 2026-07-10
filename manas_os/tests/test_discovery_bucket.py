"""WAVE K K4 — smoke tests for scanner/discovery.py (counterfactual-only bucket)."""
import sqlite3

from manas_os import db
from manas_os.scanner import discovery


def _mk_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(db._SCHEMA.read_text(encoding="utf-8"))
    return conn


def _seed_symbol(conn, symbol, n=90, price=100.0):
    import datetime
    d = datetime.date(2026, 1, 1)
    prev_close = None
    for i in range(n):
        d2 = d + datetime.timedelta(days=i)
        p = price + i * 0.3
        conn.execute(
            "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close, "
            "prev_close, volume, delivery_qty, delivery_pct) VALUES (?, 'EQ', ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, d2.isoformat(), p, p + 1, p - 1, p, prev_close, 500_000, 200_000, 40.0),
        )
        prev_close = p
    conn.commit()
    return d2.isoformat()


def test_build_bucket_empty_when_no_prices():
    conn = _mk_conn()
    assert discovery.build_bucket(conn, "2026-01-01") == []


def test_build_bucket_and_persist_roundtrip():
    conn = _mk_conn()
    scan_date = _seed_symbol(conn, "TESTCO", n=90)
    bucket = discovery.build_bucket(conn, scan_date)
    rows = discovery.persist_bucket(conn, scan_date, bucket)
    assert rows == len(bucket)
    persisted = conn.execute(
        "SELECT symbol, archetypes_json, metrics_json FROM discovery_bucket WHERE scan_date = ?",
        (scan_date,),
    ).fetchall()
    assert len(persisted) == rows


def test_run_never_raises_and_logs_pipeline_run():
    conn = _mk_conn()
    scan_date = _seed_symbol(conn, "RUNCO", n=90)
    result = discovery.run(conn, scan_date)
    assert result["status"] in ("ok", "skip")
    log = conn.execute(
        "SELECT status FROM pipeline_runs WHERE stage = ?", (discovery.STAGE,)
    ).fetchall()
    assert len(log) == 1


def test_run_skip_when_no_prices_on_or_before_date():
    conn = _mk_conn()
    result = discovery.run(conn, "2020-01-01")
    assert result["status"] == "skip"
    assert result["rows"] == 0
