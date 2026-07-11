from __future__ import annotations

from datetime import datetime, timedelta
import json
import sqlite3

import pytest

from manas_os.sources import intraday
from manas_os import db


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def _epoch(iso: str) -> int:
    return int(datetime.fromisoformat(iso).timestamp())


def _candle(iso: str, close: float = 101.0) -> list[float]:
    return [_epoch(iso), 100.0, max(102.0, close), 99.0, close, 1000.0]


def test_schema_is_idempotent_and_primary_key_includes_provider() -> None:
    conn = _conn()
    intraday.ensure_schema(conn)
    intraday.ensure_schema(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(intraday_bars)")}
    assert {"provider", "symbol", "interval", "bar_ts", "provenance_json"} <= columns

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO intraday_bars "
            "(provider,symbol,interval,bar_ts,trade_date,open,high,low,close,volume,provenance_json,ingested_at) "
            "VALUES ('fake','ACME','15m','2026-07-10T09:15:00+05:30','2026-07-10',1,1,1,1,1,'{}','x')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO intraday_bars "
            "(provider,symbol,interval,bar_ts,trade_date,open,high,low,close,volume,provenance_json,ingested_at) "
            "VALUES ('fake','ACME','5m','2026-07-10T03:45:00+00:00','2026-07-10',1,1,1,1,1,'{}','x')"
        )


def test_base_schema_initialises_intraday_store_in_memory() -> None:
    conn = db.connect(":memory:")
    try:
        conn.executescript(db._SCHEMA.read_text(encoding="utf-8"))
        table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'intraday_bars'"
        ).fetchone()
        assert table[0] == "intraday_bars"
    finally:
        conn.close()


@pytest.mark.parametrize(
    ("wall_time", "segment"),
    [
        ("09:14:59", None),
        ("09:15:00", "09:15-09:30"),
        ("09:29:59", "09:15-09:30"),
        ("09:30:00", "09:30-10:00"),
        ("10:00:00", "10:00-12:00"),
        ("12:00:00", "12:00-13:30"),
        ("13:30:00", "13:30-15:00"),
        ("15:00:00", "15:00-15:30"),
        ("15:29:59", "15:00-15:30"),
        ("15:30:00", None),
    ],
)
def test_tradetm_segment_boundaries(wall_time: str, segment: str | None) -> None:
    assert intraday.tradetm_segment(f"2026-07-10T{wall_time}+05:30") == segment


def test_upsert_is_idempotent_canonicalises_ist_and_records_provenance() -> None:
    conn = _conn()
    ts = _epoch("2026-07-10T09:15:00+05:30")
    kwargs = dict(
        provider="fyers",
        symbol="acme",
        interval="5m",
        provider_symbol="NSE:ACME-EQ",
        request_from="2026-07-10T09:15:00+05:30",
        request_to="2026-07-10T09:20:00+05:30",
        fetched_at="2026-07-10T16:00:00+05:30",
    )
    assert intraday.upsert_bars(conn, candles=[[ts, 100, 102, 99, 101, 1000]], **kwargs) == 1
    assert intraday.upsert_bars(conn, candles=[[ts, 100, 103, 99, 102, 1200]], **kwargs) == 1
    rows = conn.execute("SELECT * FROM intraday_bars").fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row["bar_ts"] == "2026-07-10T09:15:00+05:30"
    assert row["segment"] == "09:15-09:30"
    assert row["close"] == 102
    assert row["volume"] == 1200
    provenance = json.loads(row["provenance_json"])
    assert provenance["provider_symbol"] == "NSE:ACME-EQ"
    assert provenance["request_from"] == "2026-07-10T09:15:00+05:30"


class _FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def history(self, payload):
        self.calls.append(payload)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_fyers_adapter_uses_injected_client_and_expected_history_contract() -> None:
    client = _FakeClient([{"s": "ok", "candles": [_candle("2026-07-10T09:15:00+05:30")]}])
    adapter = intraday.FyersHistoryAdapter(client=client, symbol_mapper=lambda symbol: f"NSE:{symbol}-EQ")
    bars = adapter.history(
        "ACME",
        "5m",
        intraday.as_ist("2026-07-10T09:15:00+05:30"),
        intraday.as_ist("2026-07-10T09:20:00+05:30"),
    )
    assert len(bars) == 1
    assert client.calls == [
        {
            "symbol": "NSE:ACME-EQ",
            "resolution": "5",
            "date_format": "0",
            "range_from": str(_epoch("2026-07-10T09:15:00+05:30")),
            "range_to": str(_epoch("2026-07-10T09:20:00+05:30")),
            "cont_flag": "1",
        }
    ]


def test_window_fetch_rate_limit_is_failure_safe_and_resume_skips_stored_bars() -> None:
    conn = _conn()
    first = _FakeClient(
        [
            {
                "s": "ok",
                "candles": [
                    _candle("2026-07-10T09:15:00+05:30"),
                    _candle("2026-07-10T09:20:00+05:30"),
                    _candle("2026-07-10T09:25:00+05:30"),
                ],
            },
            {"s": "error", "code": 429, "message": "rate limit reached"},
        ]
    )
    result = intraday.fetch_and_store(
        conn,
        symbol="ACME",
        interval="5m",
        start="2026-07-10T09:15:00+05:30",
        end="2026-07-10T09:35:00+05:30",
        adapter=intraday.FyersHistoryAdapter(client=first, symbol_mapper=lambda symbol: f"NSE:{symbol}-EQ"),
        window_size=timedelta(minutes=10),
    )
    assert result["status"] == "rate_limited"
    assert result["next_from"] == "2026-07-10T09:30:00+05:30"
    assert conn.execute("SELECT COUNT(*) FROM intraday_bars").fetchone()[0] == 3

    second = _FakeClient(
        [{"s": "ok", "candles": [_candle("2026-07-10T09:30:00+05:30"), _candle("2026-07-10T09:35:00+05:30")]}]
    )
    resumed = intraday.fetch_and_store(
        conn,
        symbol="ACME",
        interval="5m",
        start="2026-07-10T09:15:00+05:30",
        end="2026-07-10T09:35:00+05:30",
        adapter=intraday.FyersHistoryAdapter(client=second, symbol_mapper=lambda symbol: f"NSE:{symbol}-EQ"),
        window_size=timedelta(minutes=10),
    )
    assert resumed["status"] == "ok"
    assert datetime.fromtimestamp(int(second.calls[0]["range_from"]), intraday.UTC).astimezone(intraday.INDIA_TZ).isoformat() == "2026-07-10T09:30:00+05:30"
    assert resumed["completeness"]["complete"] is True
    assert resumed["completeness"]["coverage_ratio"] == 1.0


def test_tiered_coverage_uses_existing_tables_and_explains_union() -> None:
    conn = _conn()
    conn.executescript(
        "CREATE TABLE universe(symbol TEXT, as_of_date TEXT, is_tradeable INTEGER);"
        "CREATE TABLE screener_hits(trade_date TEXT, symbol TEXT);"
        "CREATE TABLE focus_list(symbol TEXT, active INTEGER);"
        "CREATE TABLE agent_verdicts(scan_date TEXT, symbol TEXT);"
        "CREATE TABLE journal_trades(symbol TEXT, exit REAL);"
    )
    conn.executemany("INSERT INTO universe VALUES (?,?,?)", [("AAA", "2026-07-10", 1), ("ZZZ", "2026-07-10", 0)])
    conn.executemany("INSERT INTO screener_hits VALUES (?,?)", [("2026-07-10", "BBB"), ("2026-07-09", "OLD")])
    conn.executemany("INSERT INTO focus_list VALUES (?,?)", [("CCC", 1), ("OFF", 0)])
    conn.executemany("INSERT INTO agent_verdicts VALUES (?,?)", [("2026-07-10", "BBB"), ("2026-07-10", "DDD")])
    conn.executemany("INSERT INTO journal_trades VALUES (?,?)", [("EEE", None), ("CLOSED", 123.0)])

    result = intraday.tiered_coverage_symbols(conn, "2026-07-10")
    assert result["5m"] == ["AAA"]
    assert result["1m"] == ["BBB", "CCC", "DDD", "EEE"]
    assert result["1m_reasons"]["BBB"] == ["debated", "scanner_hit"]
    assert result["warnings"] == []


def test_tiered_coverage_degrades_when_tables_are_absent() -> None:
    conn = _conn()
    result = intraday.tiered_coverage_symbols(conn, "2026-07-10")
    assert result["5m"] == []
    assert result["1m"] == []
    assert len(result["warnings"]) == 5
