from __future__ import annotations

import json

import pytest

from traderlog.api import app as api_app
from traderlog.db import connect, init_db, now_iso


@pytest.fixture
def api_db(tmp_path, monkeypatch):
    path = tmp_path / "traderlog.db"
    conn = init_db(path)
    conn.execute(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES ('trader', 1, 0, ?)",
        (now_iso(),),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(api_app, "connect", lambda: connect(path))
    test_conn = connect(path)
    yield test_conn
    test_conn.close()


def _post(conn, post_id: str, ts: str, *, conversation_id: str | None = None,
          in_reply_to: str | None = None, kind: str | None = None,
          confidence: float | None = None) -> None:
    conn.execute(
        "INSERT INTO posts "
        "(post_id, handle, conversation_id, in_reply_to, ts_utc, ts_ist, text, url, fetched_at, is_mock, ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (post_id, "trader", conversation_id or post_id, in_reply_to, ts, ts, post_id,
         f"https://x.com/trader/status/{post_id}", now_iso(), 0, now_iso()),
    )
    if kind is not None:
        conn.execute(
            "INSERT INTO post_class (post_id, kind, confidence, is_mock, ingested_at) VALUES (?,?,?,?,?)",
            (post_id, kind, confidence, 0, now_iso()),
        )


def _position(conn, position_id: str, *, confidence: float | None, opened_at: str,
              unresolved: list[str] | None = None) -> None:
    conn.execute(
        "INSERT INTO positions "
        "(position_id, handle, symbol, root_post_id, status, opened_at, confidence, state_json, evidence_json, unresolved_json, is_mock, ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (position_id, "trader", position_id, position_id, "open", opened_at, confidence,
         "{}", "{}", json.dumps(unresolved or []), 0, now_iso()),
    )


def test_feed_filters_before_limit_excludes_null_confidence_and_readds_root(api_db):
    _post(api_db, "root", "2026-08-20T09:00:00+00:00", kind="trade_event", confidence=0.8)
    _post(
        api_db, "reply", "2026-08-20T11:00:00+00:00", conversation_id="root",
        in_reply_to="root", kind="trade_event", confidence=0.9,
    )
    _post(api_db, "null-conf", "2026-08-20T12:00:00+00:00", kind="trade_event")
    _post(api_db, "other-kind", "2026-08-20T13:00:00+00:00", kind="breadth", confidence=1.0)
    api_db.commit()

    result = api_app.feed(kind="trade_event", min_confidence=0.0, limit=1)

    assert [post["post_id"] for post in result["posts"]] == ["root", "reply"]
    assert all(post["confidence"] is not None for post in result["posts"])


def test_feed_supports_unclassified_before_limit(api_db):
    _post(api_db, "unclassified", "2026-08-20T09:00:00+00:00")
    _post(api_db, "classified", "2026-08-20T12:00:00+00:00", kind="noise", confidence=1.0)
    api_db.commit()

    result = api_app.feed(kind="unclassified", limit=1)

    assert [post["post_id"] for post in result["posts"]] == ["unclassified"]


def test_feed_supports_unresolved_before_limit(api_db):
    _post(api_db, "unresolved", "2026-08-20T09:00:00+00:00", kind="trade_event", confidence=0.8)
    _post(api_db, "resolved", "2026-08-20T12:00:00+00:00", kind="trade_event", confidence=0.8)
    _position(api_db, "unresolved-position", confidence=0.8, opened_at="2026-08-20", unresolved=["stop missing"])
    _position(api_db, "resolved-position", confidence=0.8, opened_at="2026-08-20")
    api_db.executemany(
        "INSERT INTO position_events (position_id, post_id, kind, stated_at, is_mock, ingested_at) VALUES (?,?,?,?,?,?)",
        [
            ("unresolved-position", "unresolved", "entry", "2026-08-20T09:00:00+00:00", 0, now_iso()),
            ("resolved-position", "resolved", "entry", "2026-08-20T12:00:00+00:00", 0, now_iso()),
        ],
    )
    api_db.commit()

    result = api_app.feed(unresolved=True, limit=1)

    assert [post["post_id"] for post in result["posts"]] == ["unresolved"]


def test_positions_min_confidence_filters_before_limit_and_excludes_null(api_db):
    _position(api_db, "low", confidence=0.8, opened_at="2026-08-20")
    _position(api_db, "null", confidence=None, opened_at="2026-08-21")
    api_db.commit()

    result = api_app.positions(min_confidence=0.0, limit=1)

    assert [position["position_id"] for position in result["positions"]] == ["low"]


# ---------------------------------------------------------------------------
# /api/symbol — the Symbol landing page payload (scouting-wire wave, S9)
# ---------------------------------------------------------------------------

def _daily_price(conn, symbol: str, trade_date: str, close: float,
                 source: str = "bhavcopy") -> None:
    conn.execute(
        "INSERT INTO daily_prices "
        "(symbol, trade_date, open, high, low, close, volume, source, ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (symbol, trade_date, close - 1, close + 1, close - 2, close, 1000.0, source, now_iso()),
    )


def _position_on(conn, position_id: str, symbol: str, *, status: str = "open") -> None:
    conn.execute(
        "INSERT INTO positions "
        "(position_id, handle, symbol, root_post_id, status, opened_at, confidence, state_json, evidence_json, unresolved_json, is_mock, ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (position_id, "trader", symbol, position_id, status, "2026-08-01", 0.9,
         "{}", "{}", "[]", 0, now_iso()),
    )


def _idea(conn, post_id: str, symbol: str, kind: str = "watch", trigger: str = "") -> int:
    conn.execute(
        "INSERT INTO watch_ideas "
        "(post_id, handle, symbol, kind, trigger_text, level, stated_at, status, is_mock, ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (post_id, "trader", symbol, kind, trigger, None, "2026-08-14T09:00:00+00:00", "open", 0, now_iso()),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def test_symbol_validated_returns_documented_shape(api_db):
    _daily_price(api_db, "DIXON", "2026-08-01", 103.5)
    _daily_price(api_db, "DIXON", "2026-08-02", 107.0)
    api_db.commit()

    result = api_app.symbol("DIXON")

    assert result["symbol"] == "DIXON"
    assert result["validated"] is True
    assert result["source"] == "bhavcopy"
    assert result["positions"] == []
    assert result["mentions"] == []
    assert result["is_mock"] is False
    assert [p["trade_date"] for p in result["prices"]] == ["2026-08-01", "2026-08-02"]
    # Price rows are exactly the documented five fields, ascending by date.
    assert set(result["prices"][0].keys()) == {"trade_date", "open", "high", "low", "close", "volume"}
    assert result["prices"][0]["close"] == 103.5


def test_symbol_validated_is_case_normalised(api_db):
    _daily_price(api_db, "DIXON", "2026-08-01", 103.5)
    api_db.commit()

    result = api_app.symbol("dixon")

    assert result["symbol"] == "DIXON"
    assert result["validated"] is True


def test_symbol_not_validated_returns_empty_prices(api_db):
    result = api_app.symbol("ZZZZNOTREAL")

    assert result["validated"] is False
    assert result["prices"] == []
    assert result["source"] is None
    assert result["positions"] == []
    assert result["mentions"] == []


def test_symbol_corpus_present_but_no_prices(api_db):
    _post(api_db, "fcl-entry", "2026-08-10T09:00:00+00:00")
    _position_on(api_db, "fcl-pos", "FCL")
    _idea(api_db, "fcl-entry", "FCL", kind="watch", trigger="above 1,240 on volume")
    api_db.commit()

    result = api_app.symbol("FCL")

    # Not validated — the bhavcopy NSE EQ source has no rows for it — but the
    # corpus context still comes back so the UI can say WHICH part is missing.
    assert result["validated"] is False
    assert result["prices"] == []
    assert [p["position_id"] for p in result["positions"]] == ["fcl-pos"]
    assert len(result["mentions"]) == 1
    mention = result["mentions"][0]
    assert mention["symbol"] == "FCL"
    assert mention["handle"] == "trader"
    assert mention["kind"] == "watch"
    assert mention["trigger_text"] == "above 1,240 on volume"
    assert mention["post_id"] == "fcl-entry"


# ---------------------------------------------------------------------------
# /api/breadth — additive advances/declines on history rows (scouting-wire, S9)
# ---------------------------------------------------------------------------

def test_breadth_history_rows_carry_advances_declines(api_db):
    api_db.executemany(
        "INSERT INTO regime_daily (trade_date, xp_value, xp_band, is_mock, ingested_at) "
        "VALUES (?,?,?,?,?)",
        [
            ("2026-08-14", 8.0, "LOW", 0, now_iso()),
            ("2026-08-15", 6.0, "LOW", 0, now_iso()),
        ],
    )
    api_db.execute(
        "INSERT INTO breadth_daily (trade_date, advances, declines, ingested_at) "
        "VALUES (?,?,?,?)",
        ("2026-08-15", 232.0, 164.0, now_iso()),
    )
    api_db.commit()

    result = api_app.breadth(days=10)
    by_date = {h["trade_date"]: h for h in result["history"]}

    # The row with a breadth_daily entry carries the joined numbers...
    assert by_date["2026-08-15"]["advances"] == 232.0
    assert by_date["2026-08-15"]["declines"] == 164.0
    # ...and the row without one carries nulls, never a fabricated zero.
    assert by_date["2026-08-14"]["advances"] is None
    assert by_date["2026-08-14"]["declines"] is None
    # Existing regime fields are untouched.
    assert by_date["2026-08-14"]["xp_band"] == "LOW"


# ---------------------------------------------------------------------------
# /api/traders — additive stop-discipline fields (scouting-wire, S9)
# ---------------------------------------------------------------------------

def test_traders_summary_carries_stop_discipline_fields_null_when_absent(api_db):
    result = api_app.traders()

    trader = next(r for r in result["traders"] if r["handle"] == "trader")
    assert trader["stop_stated_pct"] is None
    assert trader["stop_honored_pct"] is None


def test_traders_summary_carries_stop_discipline_fields_when_present(api_db):
    api_db.execute(
        "INSERT INTO trader_style "
        "(handle, as_of, stop_stated_pct, stop_honored_pct, is_mock, ingested_at) "
        "VALUES (?,?,?,?,?,?)",
        ("trader", "2026-08-01", 75.0, 60.0, 0, now_iso()),
    )
    api_db.commit()

    result = api_app.traders()

    trader = next(r for r in result["traders"] if r["handle"] == "trader")
    assert trader["stop_stated_pct"] == 75.0
    assert trader["stop_honored_pct"] == 60.0
