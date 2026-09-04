"""INS-2 tape-after-mention tests.

Locks the IST anchor policy and the trading-session return math per
design/INSIGHT_SURFACES_PLAN.md §INS-2: pre-open posts may anchor to that
session's open; intraday/after-close posts anchor to the next available
session; holidays and weekends come from the symbol's actual price series;
missing horizons are null; and the anchor is always an OPEN, so look-ahead
through a later or same-day close is impossible.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from traderlog.api import app as api_app
from traderlog.db import connect, init_db, now_iso
from traderlog.derive.tape import (
    MAX_TAPE_SYMBOLS,
    STATE_CAPPED,
    STATE_COMPUTED,
    STATE_MISSING_TIMESTAMP,
    STATE_NO_FORWARD_SESSION,
    STATE_NO_NSE_HISTORY,
    apply_tape,
    compute_tape,
)


def _sessions(spec):
    """spec: list of (trade_date, open, close) -> daily_prices-like rows."""
    return [
        {"trade_date": trade_date, "open": open_, "close": close}
        for (trade_date, open_, close) in spec
    ]


def _series() -> list[tuple[str, float, float]]:
    """24 trading sessions across Aug-Sep 2026 with a holiday + weekend gap.

    Real 2026 weekdays: 08-03..08-07 (Mon-Fri), then 08-10 is a market holiday
    (skipped), 08-11..08-14 (Tue-Fri), the weekend 08-15/16, then 08-17..08-21,
    08-24..08-28, 08-31..09-04 (Mon-Fri). open[i] = 100 + i, close[i] = 100.5 + i.
    """
    dates = [
        "2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06", "2026-08-07",
        "2026-08-11", "2026-08-12", "2026-08-13", "2026-08-14",
        "2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21",
        "2026-08-24", "2026-08-25", "2026-08-26", "2026-08-27", "2026-08-28",
        "2026-08-31", "2026-09-01", "2026-09-02", "2026-09-03", "2026-09-04",
    ]
    return [
        (trade_date, 100.0 + index, 100.5 + index)
        for index, trade_date in enumerate(dates)
    ]


# ---------------------------------------------------------------------------
# Anchor policy
# ---------------------------------------------------------------------------


def test_pre_open_post_anchors_to_same_day_open():
    tape = compute_tape(_sessions(_series()), "2026-08-03T08:30:00+05:30")

    assert tape.state == STATE_COMPUTED
    assert tape.anchor_date == "2026-08-03"
    assert tape.anchor_open == 100.0
    # +1 lands on 08-04, the second session of the series.
    assert tape.ret_1d == pytest.approx(101.5 / 100.0 - 1.0)
    # +5 counts five trading sessions (08-04,05,06,07, then 08-11): the 08-10
    # holiday AND the weekend are skipped, so the close is session index 5.
    assert tape.ret_5d == pytest.approx(105.5 / 100.0 - 1.0)
    assert tape.n_eligible == 4
    assert tape.n_missing == 0


def test_intraday_post_anchors_to_next_session_open():
    tape = compute_tape(_sessions(_series()), "2026-08-03T10:30:00+05:30")

    assert tape.state == STATE_COMPUTED
    # 10:30 IST is not before 09:00, so 08-03's own open is NOT usable: the
    # anchor moves to the next available session.
    assert tape.anchor_date == "2026-08-04"
    assert tape.anchor_open == 101.0
    assert tape.ret_1d == pytest.approx(102.5 / 101.0 - 1.0)


def test_after_close_post_anchors_to_next_session_open():
    tape = compute_tape(_sessions(_series()), "2026-08-03T16:00:00+05:30")

    assert tape.anchor_date == "2026-08-04"
    assert tape.anchor_open == 101.0


def test_weekend_post_anchors_to_next_available_session():
    # 2026-08-15 is a Saturday: no same-day session, so even a pre-open post
    # moves to the next session (08-17, Monday).
    tape = compute_tape(_sessions(_series()), "2026-08-15T08:00:00+05:30")

    assert tape.anchor_date == "2026-08-17"
    assert tape.anchor_open == 109.0


def test_holiday_pre_open_post_anchors_to_next_available_session():
    # 2026-08-10 is a market holiday in this series: its date has no session,
    # so "pre-open on that day" still cannot anchor a same-day open.
    tape = compute_tape(_sessions(_series()), "2026-08-10T07:00:00+05:30")

    assert tape.anchor_date == "2026-08-11"
    assert tape.anchor_open == 105.0


def test_session_boundary_at_exactly_0900_ist_is_not_pre_open():
    # The locked boundary is strict: 09:00:00 IST is NOT before 09:00, so it
    # anchors to the next session.
    tape = compute_tape(_sessions(_series()), "2026-08-03T09:00:00+05:30")

    assert tape.anchor_date == "2026-08-04"


def test_aware_utc_timestamp_is_converted_to_ist_before_anchoring():
    # 03:00 UTC == 08:30 IST on 08-03 -> pre-open, same-day anchor.
    pre_open = compute_tape(_sessions(_series()), "2026-08-03T03:00:00+00:00")
    assert pre_open.anchor_date == "2026-08-03"

    # 04:30 UTC == 10:00 IST on 08-03 -> intraday, next session.
    intraday = compute_tape(_sessions(_series()), "2026-08-03T04:30:00+00:00")
    assert intraday.anchor_date == "2026-08-04"


# ---------------------------------------------------------------------------
# Session math across gaps, missing tails, and nulls
# ---------------------------------------------------------------------------


def test_plus20_horizon_skips_holiday_and_weekend_gaps():
    tape = compute_tape(_sessions(_series()), "2026-08-03T08:00:00+05:30")

    # Anchor is session 0 (08-03). Index 0 + 20 = session 20 = 09-01.
    # Calendar span is 29 days (holiday + weekends inside), but the horizon is
    # exactly 20 trading sessions of the symbol's own series.
    assert tape.ret_20d == pytest.approx((100.5 + 20) / 100.0 - 1.0)
    assert _series()[20][0] == "2026-09-01"
    assert tape.n_eligible == 4


def test_missing_tail_horizons_are_null_not_zero():
    # Anchor on 09-01 (session 20): only +1 (09-02) has a session after it.
    tape = compute_tape(_sessions(_series()), "2026-09-01T08:30:00+05:30")

    assert tape.anchor_date == "2026-09-01"
    assert tape.ret_1d == pytest.approx(121.5 / 120.0 - 1.0)
    assert tape.ret_5d is None
    assert tape.ret_10d is None
    assert tape.ret_20d is None
    assert tape.n_eligible == 1
    assert tape.n_missing == 3


def test_lookahead_impossible_anchor_uses_open_not_close():
    # The anchor session's own close is deliberately loud (999) and must never
    # leak into the returns: the anchor is the OPEN, and +1 reads the NEXT
    # session's close only.
    loud = [
        ("2026-08-10", 100.0, 999.0),
        ("2026-08-11", 110.0, 115.0),
        ("2026-08-12", 120.0, 121.0),
        ("2026-08-13", 130.0, 132.0),
        ("2026-08-14", 140.0, 150.0),
    ]
    tape = compute_tape(_sessions(loud), "2026-08-10T08:00:00+05:30")

    assert tape.anchor_open == 100.0
    assert tape.ret_1d == pytest.approx(115.0 / 100.0 - 1.0)
    # The same-day close (999) never appears: no close-to-close computation.
    assert tape.ret_1d != pytest.approx(999.0 / 100.0 - 1.0)
    assert tape.ret_5d is None
    assert tape.n_eligible == 1
    assert tape.n_missing == 3


def test_null_anchor_open_omits_all_returns_but_keeps_anchor():
    rows = [
        ("2026-08-03", None, 100.0),
        ("2026-08-04", 110.0, 115.0),
        ("2026-08-05", 120.0, 125.0),
    ]
    tape = compute_tape(_sessions(rows), "2026-08-03T08:00:00+05:30")

    assert tape.state == STATE_COMPUTED
    assert tape.anchor_date == "2026-08-03"
    assert tape.anchor_open is None
    assert tape.ret_1d is None and tape.ret_5d is None
    assert tape.n_eligible == 0
    assert tape.n_missing == 4


def test_null_close_at_a_horizon_is_null_and_counts_as_missing():
    rows = [
        ("2026-08-03", 100.0, 101.0),
        ("2026-08-04", 102.0, None),  # +1 close missing
        ("2026-08-05", 103.0, 104.0),
        ("2026-08-06", 104.0, 105.0),
        ("2026-08-07", 105.0, 106.0),
        ("2026-08-11", 106.0, 107.0),  # +5 close (index 5)
        ("2026-08-12", 107.0, 108.0),
    ]
    tape = compute_tape(_sessions(rows), "2026-08-03T08:00:00+05:30")

    assert tape.ret_1d is None
    assert tape.ret_5d == pytest.approx(107.0 / 100.0 - 1.0)
    assert tape.ret_10d is None and tape.ret_20d is None
    assert tape.n_eligible == 1
    assert tape.n_missing == 3


def test_unsorted_sessions_give_the_same_result_as_sorted():
    series = _series()
    sorted_tape = compute_tape(_sessions(series), "2026-08-03T08:30:00+05:30")
    shuffled = compute_tape(_sessions(list(reversed(series))), "2026-08-03T08:30:00+05:30")

    assert shuffled == sorted_tape


# ---------------------------------------------------------------------------
# Kill-condition / malformed-input states
# ---------------------------------------------------------------------------


def test_missing_or_malformed_timestamp_omits_percentages():
    for bad in (None, "", "not-a-timestamp", 42):
        tape = compute_tape(_sessions(_series()), bad)
        assert tape.state == STATE_MISSING_TIMESTAMP
        assert tape.anchor_date is None and tape.anchor_open is None
        assert tape.ret_1d is None and tape.ret_20d is None
        assert tape.n_eligible == 0
        assert tape.n_missing == 4


def test_empty_price_history_is_the_no_nse_history_state():
    tape = compute_tape([], "2026-08-03T08:30:00+05:30")

    assert tape.state == STATE_NO_NSE_HISTORY
    assert tape.anchor_date is None
    assert tape.n_eligible == 0
    assert tape.n_missing == 4


def test_no_session_on_or_after_the_mention_is_no_forward_session():
    only = [("2026-08-03", 100.0, 101.0)]
    # Mention the day after the only session: nothing can anchor.
    tape = compute_tape(_sessions(only), "2026-08-04T08:00:00+05:30")
    assert tape.state == STATE_NO_FORWARD_SESSION
    assert tape.anchor_date is None
    assert tape.n_eligible == 0
    assert tape.n_missing == 4

    # A pre-open mention ON the last session anchors it but has no forward
    # sessions: every horizon is null, and the counts say so.
    last = compute_tape(_sessions(only), "2026-08-03T08:00:00+05:30")
    assert last.state == STATE_COMPUTED
    assert last.anchor_date == "2026-08-03"
    assert last.anchor_open == 100.0
    assert last.ret_1d is None and last.ret_20d is None
    assert last.n_eligible == 0
    assert last.n_missing == 4


# ---------------------------------------------------------------------------
# Row attachment (`apply_tape`) -- the /api/radar glue
# ---------------------------------------------------------------------------


def test_apply_tape_attaches_fields_and_honours_the_symbol_cap():
    series = _series()
    rows = [
        {"symbol": "AAA", "evidence": [{"post_id": "p1"}]},
        {"symbol": "BBB", "evidence": [{"post_id": "p2"}]},
        {"symbol": "CCC", "evidence": [{"post_id": "p3"}]},
    ]
    ts_by_post = {
        "p1": "2026-08-03T08:30:00+05:30",
        "p2": "2026-08-03T10:30:00+05:30",
    }
    sessions = {"AAA": _sessions(series), "BBB": _sessions(series)}

    apply_tape(rows, ts_ist_by_post_id=ts_by_post, sessions_by_symbol=sessions, max_symbols=2)

    assert rows[0]["anchor_date"] == "2026-08-03"
    assert rows[0]["anchor_open"] == 100.0
    assert rows[0]["tape_state"] == STATE_COMPUTED
    assert rows[0]["n_eligible"] == 4 and rows[0]["n_missing"] == 0

    assert rows[1]["anchor_date"] == "2026-08-04"
    assert rows[1]["tape_state"] == STATE_COMPUTED

    # Row 2 is past the cap: marked capped, no numbers invented.
    assert rows[2]["tape_state"] == STATE_CAPPED
    assert rows[2]["anchor_date"] is None
    assert rows[2]["n_eligible"] == 0 and rows[2]["n_missing"] == 4


def test_apply_tape_missing_post_or_evidence_is_missing_timestamp():
    rows = [
        {"symbol": "AAA", "evidence": [{"post_id": "ghost"}]},  # no ts lookup
        {"symbol": "BBB", "evidence": []},                      # no evidence at all
    ]
    apply_tape(rows, ts_ist_by_post_id={}, sessions_by_symbol={})

    assert rows[0]["tape_state"] == STATE_MISSING_TIMESTAMP
    assert rows[1]["tape_state"] == STATE_MISSING_TIMESTAMP
    assert rows[0]["anchor_date"] is None and rows[1]["anchor_date"] is None


def test_apply_tape_default_cap_constant_is_positive_and_large_enough_for_radar():
    assert MAX_TAPE_SYMBOLS >= 100


# ---------------------------------------------------------------------------
# Endpoint integration: /api/radar over a disposable database
# ---------------------------------------------------------------------------


@pytest.fixture
def tape_radar_db(tmp_path, monkeypatch):
    path = tmp_path / "traderlog.db"
    conn = init_db(path)
    conn.execute(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES ('@alpha', 1, 0, ?)",
        (now_iso(),),
    )
    conn.execute(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES ('@bravo', 1, 0, ?)",
        (now_iso(),),
    )
    for index, (trade_date, open_, close) in enumerate(_series()):
        conn.execute(
            "INSERT INTO daily_prices (symbol, trade_date, open, close, source, ingested_at) "
            "VALUES ('TAPE1', ?, ?, ?, 'bhavcopy', ?)",
            (trade_date, open_, close, now_iso()),
        )
    conn.commit()
    conn.close()
    monkeypatch.setattr(api_app, "connect", lambda: connect(path))
    monkeypatch.setattr(api_app, "_radar_now", lambda: "2026-08-25T12:00:00+00:00")
    return path


def _insert_mention(conn, post_id, handle, ts_utc, ts_ist, symbol="TAPE1"):
    now = now_iso()
    conn.execute(
        "INSERT INTO posts (post_id, handle, ts_utc, ts_ist, text, url, fetched_at, is_mock, ingested_at) "
        "VALUES (?, ?, ?, ?, 'exact text', ?, ?, 0, ?)",
        (post_id, handle, ts_utc, ts_ist, f"https://x.com/{handle.lstrip('@')}/status/{post_id}", now, now),
    )
    conn.execute(
        "INSERT INTO post_class (post_id, kind, confidence, symbols, is_mock, ingested_at) "
        "VALUES (?, 'watch_idea', 0.9, ?, 0, ?)",
        (post_id, json.dumps([symbol]), now),
    )


def test_radar_endpoint_returns_tape_after_mention_fields(tape_radar_db):
    conn = connect(tape_radar_db)
    try:
        # alpha is pre-open on 08-03 (08:30 IST); bravo is intraday (09:30 IST).
        _insert_mention(conn, "alpha", "@alpha", "2026-08-03T03:00:00+00:00", "2026-08-03T08:30:00+05:30")
        _insert_mention(conn, "bravo", "@bravo", "2026-08-03T04:00:00+00:00", "2026-08-03T09:30:00+05:30")
        conn.commit()
    finally:
        conn.close()

    payload = TestClient(api_app.app).get("/api/radar?days=30&min_traders=2").json()

    assert payload["is_mock"] is False
    row = payload["co_attention"][0]
    assert row["symbol"] == "TAPE1"
    # The anchor is the symbol's FIRST mention in the window: @alpha's 08:30 IST
    # pre-open post -> same-day open of the first session.
    assert row["anchor_date"] == "2026-08-03"
    assert row["anchor_open"] == 100.0
    assert row["ret_1d"] == pytest.approx(101.5 / 100.0 - 1.0)
    assert row["ret_5d"] == pytest.approx(105.5 / 100.0 - 1.0)
    assert row["ret_10d"] == pytest.approx(110.5 / 100.0 - 1.0)
    assert row["ret_20d"] == pytest.approx(120.5 / 100.0 - 1.0)
    assert row["n_eligible"] == 4
    assert row["n_missing"] == 0
    assert row["tape_state"] == STATE_COMPUTED


def test_radar_endpoint_symbol_beyond_cap_gets_no_numbers(tape_radar_db, monkeypatch):
    conn = connect(tape_radar_db)
    try:
        # A second validated symbol with a tiny series and two traders.
        conn.execute(
            "INSERT INTO daily_prices (symbol, trade_date, open, close, source, ingested_at) "
            "VALUES ('TAPE2', '2026-08-03', 10.0, 11.0, 'bhavcopy', ?)",
            (now_iso(),),
        )
        # TAPE1's cluster ends 08-03; TAPE2's ends 08-04, so TAPE2 ranks first.
        _insert_mention(conn, "t1a", "@alpha", "2026-08-03T03:00:00+00:00", "2026-08-03T08:30:00+05:30", symbol="TAPE1")
        _insert_mention(conn, "t1b", "@bravo", "2026-08-03T04:00:00+00:00", "2026-08-03T09:30:00+05:30", symbol="TAPE1")
        _insert_mention(conn, "t2a", "@alpha", "2026-08-03T03:00:00+00:00", "2026-08-03T08:30:00+05:30", symbol="TAPE2")
        _insert_mention(conn, "t2c", "@bravo", "2026-08-04T03:00:00+00:00", "2026-08-04T08:30:00+05:30", symbol="TAPE2")
        conn.commit()
    finally:
        conn.close()

    # Force a cap of 1. TAPE2's strongest cluster ends later than TAPE1's (its
    # second mention is 08-04), so TAPE2 ranks first and gets the tape; TAPE1
    # falls past the cap.
    monkeypatch.setattr("traderlog.derive.tape.MAX_TAPE_SYMBOLS", 1)
    payload = TestClient(api_app.app).get("/api/radar?days=30&min_traders=2").json()

    rows = {row["symbol"]: row for row in payload["co_attention"]}
    assert rows["TAPE2"]["tape_state"] == STATE_COMPUTED
    assert rows["TAPE2"]["anchor_date"] == "2026-08-03"
    assert rows["TAPE1"]["tape_state"] == STATE_CAPPED
    assert rows["TAPE1"]["anchor_date"] is None
    assert rows["TAPE1"]["n_eligible"] == 0