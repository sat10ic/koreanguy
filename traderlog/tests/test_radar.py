from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from traderlog.api import app as api_app
from traderlog.db import connect, init_db, now_iso
from traderlog.derive.radar import build_radar


def _row(
    post_id: str,
    ts_utc: str,
    *,
    handle: str = "@Trader",
    kind: str = "watch_idea",
    symbols: object = None,
    confidence: float | None = 0.8,
) -> dict:
    return {
        "post_id": post_id,
        "handle": handle,
        "ts_utc": ts_utc,
        "url": f"https://x.com/{handle.lstrip('@')}/status/{post_id}",
        "text": f"exact text {post_id}",
        "kind": kind,
        "confidence": confidence,
        "symbols": json.dumps(symbols if symbols is not None else ["ABC"]),
    }


def test_radar_filters_kinds_and_normalizes_symbols_and_handles_without_duplicate_mentions():
    result = build_radar(
        [
            _row("one", "2026-08-20T09:00:00+00:00", symbols=[" #abc ", "ABC", "", 7]),
            _row("two", "2026-08-21T09:00:00+00:00", handle="trader", symbols=["ABC"]),
            _row("noise", "2026-08-21T10:00:00+00:00", kind="noise", symbols=["ABC"]),
        ],
        validated_symbols={"ABC"},
        days=30,
        min_traders=1,
        window_end="2026-08-21T23:59:59+00:00",
    )

    symbol = result["co_attention"][0]
    assert symbol["symbol"] == "ABC"
    assert symbol["mention_count"] == 2
    assert symbol["distinct_trader_count"] == 1
    assert [item["post_id"] for item in symbol["evidence"]] == ["one", "two"]
    assert result["classified_eligible_post_count"] == 2
    assert result["included_mention_count"] == 2
    assert result["coverage_debt"]["invalid_symbol_value_count"] == 2


def test_radar_uses_seven_calendar_day_boundaries_and_latest_cluster_end_for_ties():
    result = build_radar(
        [
            _row("a1", "2026-08-01T09:00:00+00:00", handle="a", symbols=["ABC"]),
            _row("b1", "2026-08-07T09:00:00+00:00", handle="b", symbols=["ABC"]),
            _row("a2", "2026-08-08T09:00:00+00:00", handle="a", symbols=["ABC"]),
            _row("b2", "2026-08-14T09:00:00+00:00", handle="b", symbols=["ABC"]),
        ],
        validated_symbols={"ABC"},
        days=30,
        min_traders=1,
        window_end="2026-08-14T23:59:59+00:00",
    )

    cluster = result["co_attention"][0]["strongest_cluster"]
    assert cluster == {
        "start_date": "2026-08-08",
        "end_date": "2026-08-14",
        "distinct_trader_count": 2,
        "mention_count": 2,
    }


def test_radar_uses_asia_kolkata_dates_across_the_utc_midnight_rollover():
    result = build_radar(
        [_row("late-utc", "2026-08-24T20:00:00+00:00", symbols=["ABC"])],
        validated_symbols={"ABC"},
        days=1,
        min_traders=1,
        window_end="2026-08-24T20:30:00+00:00",
    )

    assert result["window"] == {"start_date": "2026-08-25", "end_date": "2026-08-25"}
    assert result["co_attention"][0]["strongest_cluster"] == {
        "start_date": "2026-08-19",
        "end_date": "2026-08-25",
        "distinct_trader_count": 1,
        "mention_count": 1,
    }


def test_radar_reports_the_actual_seven_day_window_boundary_when_mentions_are_sparse():
    result = build_radar(
        [
            _row("first", "2026-08-15T09:00:00+00:00", handle="a", symbols=["ABC"]),
            _row("last", "2026-08-21T09:00:00+00:00", handle="b", symbols=["ABC"]),
        ],
        validated_symbols={"ABC"},
        days=30,
        min_traders=1,
        window_end="2026-08-21T23:59:59+00:00",
    )

    assert result["co_attention"][0]["strongest_cluster"] == {
        "start_date": "2026-08-15",
        "end_date": "2026-08-21",
        "distinct_trader_count": 2,
        "mention_count": 2,
    }


def test_radar_applies_days_and_minimum_traders_then_separates_unvalidated_symbols():
    result = build_radar(
        [
            _row("old", "2026-07-01T09:00:00+00:00", handle="old", symbols=["OLD"]),
            _row("abc-a", "2026-08-20T09:00:00+00:00", handle="a", symbols=["ABC"]),
            _row("abc-b", "2026-08-21T09:00:00+00:00", handle="b", symbols=["ABC"]),
            _row("xyz-a", "2026-08-22T09:00:00+00:00", handle="a", symbols=["XYZ"]),
            _row("solo", "2026-08-22T10:00:00+00:00", handle="solo", symbols=["SOLO"]),
        ],
        validated_symbols={"ABC", "SOLO"},
        days=7,
        min_traders=2,
        window_end="2026-08-25T12:00:00+00:00",
    )

    assert [item["symbol"] for item in result["co_attention"]] == ["ABC"]
    assert result["classified_eligible_post_count"] == 4
    assert result["included_mention_count"] == 4
    assert result["coverage_debt"]["unvalidated_mention_count"] == 1
    assert result["coverage_debt"]["unvalidated_symbols"] == [
        {"symbol": "XYZ", "mention_count": 1, "distinct_trader_count": 1}
    ]


def test_radar_counts_invalid_symbol_json_without_crashing_and_preserves_exact_evidence():
    broken = _row("broken", "2026-08-20T09:00:00+00:00", symbols=[])
    broken["symbols"] = "{not json"
    result = build_radar(
        [broken, _row("evidence", "2026-08-21T09:01:02+00:00", handle="@Exact", symbols=["ABC"], confidence=0.73)],
        validated_symbols={"ABC"},
        days=30,
        min_traders=1,
        window_end="2026-08-21T23:59:59+00:00",
    )

    assert result["coverage_debt"]["invalid_symbol_json_count"] == 1
    evidence = result["co_attention"][0]["evidence"][0]
    assert evidence == {
        "post_id": "evidence",
        "handle": "@Exact",
        "ts_utc": "2026-08-21T09:01:02+00:00",
        "url": "https://x.com/Exact/status/evidence",
        "text": "exact text evidence",
        "kind": "watch_idea",
        "confidence": 0.73,
    }


@pytest.fixture
def radar_db(tmp_path, monkeypatch):
    path = tmp_path / "traderlog.db"
    conn = init_db(path)
    conn.execute(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES ('trader', 1, 0, ?)",
        (now_iso(),),
    )
    conn.commit()
    conn.close()
    monkeypatch.setattr(api_app, "connect", lambda: connect(path))
    monkeypatch.setattr(api_app, "_radar_now", lambda: "2026-08-25T12:00:00+00:00")
    return path


def test_radar_endpoint_uses_only_a_disposable_database(radar_db):
    conn = connect(radar_db)
    try:
        conn.execute(
            "INSERT INTO posts (post_id, handle, ts_utc, ts_ist, text, url, fetched_at, is_mock, ingested_at) "
            "VALUES ('post', 'trader', '2026-08-24T09:00:00+00:00', '2026-08-24T09:00:00+00:00', "
            "'source text', 'https://x.com/trader/status/post', ?, 0, ?)",
            (now_iso(), now_iso()),
        )
        conn.execute(
            "INSERT INTO post_class (post_id, kind, confidence, symbols, is_mock, ingested_at) "
            "VALUES ('post', 'trade_event', 0.91, '[\"ABC\"]', 0, ?)",
            (now_iso(),),
        )
        conn.execute(
            "INSERT INTO daily_prices (symbol, trade_date, close, source, ingested_at) "
            "VALUES ('ABC', '2026-08-24', 100, 'bhavcopy', ?)",
            (now_iso(),),
        )
        conn.commit()
    finally:
        conn.close()

    response = TestClient(api_app.app).get("/api/radar?days=30&min_traders=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_mock"] is False
    assert payload["requested"] == {"days": 30, "min_traders": 1}
    assert payload["co_attention"][0]["symbol"] == "ABC"
    assert payload["co_attention"][0]["evidence"][0]["text"] == "source text"
