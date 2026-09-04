from __future__ import annotations

import json
import sqlite3

import pytest

from traderlog.db import init_db, now_iso
from traderlog.derive.style import (
    RATE_MIN_CLOSED,
    _aggregate,
    _prices_from_events,
    _prices_from_state,
    derive,
    run,
)


# ---------------------------------------------------------------------------
# Helpers -- disposable sqlite DB with known traders/positions/events
# ---------------------------------------------------------------------------

def _add_trader(conn, handle: str, *, active: int = 1, is_mock: int = 0) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO traders (handle, active, is_mock, ingested_at) "
        "VALUES (?,?,?,?)",
        (handle, active, is_mock, now_iso()),
    )


def _add_post(conn, post_id: str, handle: str) -> None:
    _add_trader(conn, handle)
    stamp = now_iso()
    conn.execute(
        "INSERT INTO posts (post_id,handle,ts_utc,ts_ist,text,url,fetched_at,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (post_id, handle, stamp, stamp, f"{post_id} source text",
         f"https://x.com/{handle}/status/{post_id}", stamp, stamp),
    )


def _state(
    entry: float | None = None,
    stop: float | None = None,
    exit_price: float | None = None,
) -> dict:
    """A reconciler-shaped state_json dict. ONLY the prices matter to the
    derivation -- ``net_result_pct`` / ``holding_days`` are read from the
    denormalised positions columns (which the tests pass separately)."""
    return {
        "symbol": "XYZ",
        "status": "closed",
        "entries": (
            [{"price": entry, "date": "2026-08-01", "post_id": "entry-post"}]
            if entry is not None
            else []
        ),
        "adds": [],
        "stop": (
            {"price": stop, "post_id": "stop-post"} if stop is not None else None
        ),
        "targets": [],
        "exits": (
            [{"price": exit_price, "qty_pct": 100.0, "post_id": "exit-post"}]
            if exit_price is not None
            else []
        ),
        "net_result_pct": None,
        "holding_days": None,
        "confidence": 0.8,
        "unresolved": [],
    }


def _add_position(
    conn,
    position_id: str,
    handle: str,
    *,
    status: str = "closed",
    net: float | None = None,
    hold: float | None = None,
    state: dict | None = None,
    is_mock: int = 0,
) -> None:
    _add_trader(conn, handle)
    if state is None:
        state = _state()
    conn.execute(
        "INSERT INTO positions "
        "(position_id,handle,symbol,root_post_id,status,net_result_pct,holding_days,"
        " state_json,evidence_json,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (position_id, handle, "XYZ", f"root-{position_id}", status, net, hold,
         json.dumps(state), "{}", is_mock, now_iso()),
    )


def _add_event(
    conn, position_id: str, post_id: str, kind: str, price: float | None,
    seq: int, *, is_mock: int = 0,
) -> None:
    conn.execute(
        "INSERT INTO position_events "
        "(position_id,post_id,kind,price,stated_at,seq,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (position_id, post_id, kind, price, now_iso(), seq, is_mock, now_iso()),
    )


@pytest.fixture
def db(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    yield conn
    conn.close()


def _row(conn, handle: str):
    return conn.execute(
        "SELECT * FROM trader_style WHERE handle = ? ORDER BY as_of DESC LIMIT 1",
        (handle,),
    ).fetchone()


def _count(conn, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ---------------------------------------------------------------------------
# Threshold gate -- exactly 10 vs 9
# ---------------------------------------------------------------------------

def test_threshold_gate_at_exactly_ten(db):
    # alpha: 10 closed, all with stated results / stated stops / stated exits.
    for i in range(10):
        _add_position(
            db, f"a{i}", "alpha",
            net=5.0 if i % 2 == 0 else -3.0, hold=10,
            state=_state(entry=100 + i, stop=90 + i, exit_price=120 + i),
        )
    # beta: 9 closed, otherwise identical quality of data.
    for i in range(9):
        _add_position(
            db, f"b{i}", "beta",
            net=1.0, hold=5,
            state=_state(entry=10 + i, stop=9 + i, exit_price=11 + i),
        )
    db.commit()

    stats = run(db, "2026-08-26")
    a = _row(db, "alpha")
    b = _row(db, "beta")

    # At 10 closed the own-denominator rates populate and are correct.
    assert a["n_positions"] == 10
    assert a["stated_win_rate"] == pytest.approx(0.5)
    assert a["avg_result_pct"] == pytest.approx(1.0)   # 5*(+5) + 5*(-3) = 10 / 10
    assert a["avg_r"] == pytest.approx(2.0)            # (exit-entry)/(entry-stop) = 20/10
    assert a["stop_stated_pct"] == pytest.approx(1.0)
    assert a["stop_honored_pct"] == pytest.approx(1.0)
    assert a["median_hold_days"] == pytest.approx(10.0)

    # At 9 closed every rate/mean column is NULL -- never a percentage --
    # while n_positions and median still populate.
    assert b["n_positions"] == 9
    assert b["stated_win_rate"] is None
    assert b["avg_result_pct"] is None
    assert b["avg_r"] is None
    assert b["stop_stated_pct"] is None
    assert b["stop_honored_pct"] is None
    assert b["median_hold_days"] == pytest.approx(5.0)

    # threshold summary names exactly the handles whose denominators crossed.
    assert stats["threshold"]["win_rate"] == ["alpha"]
    assert stats["threshold"]["stop_stated"] == ["alpha"]
    assert stats["threshold"]["avg_r"] == ["alpha"]
    assert stats["threshold"]["stop_honored"] == ["alpha"]
    # the web spec's minimum is auditable: 10 closed positions
    assert RATE_MIN_CLOSED == 10


# ---------------------------------------------------------------------------
# Win-rate math -- unstated results are excluded, never counted as losses
# ---------------------------------------------------------------------------

def test_win_rate_math_excludes_unstated_results(db):
    # 12 closed: 8 positive, 2 negative, 2 WITH NO stated result.
    for i in range(8):
        _add_position(db, f"w{i}", "gamma", net=4.0,
                      state=_state(entry=10, stop=9, exit_price=12))
    for i in range(2):
        _add_position(db, f"l{i}", "gamma", net=-2.0,
                      state=_state(entry=10, stop=9, exit_price=8))
    for i in range(2):
        # unstated result -- must be excluded from the denominator entirely
        _add_position(db, f"u{i}", "gamma", net=None,
                      state=_state(entry=10, stop=9, exit_price=11))
    db.commit()

    stats = run(db, "2026-08-26")
    row = _row(db, "gamma")
    assert stats["per_handle"]["gamma"]["stated_results"] == 10
    assert stats["per_handle"]["gamma"]["wins"] == 8
    assert row["stated_win_rate"] == pytest.approx(0.8)
    assert row["avg_result_pct"] == pytest.approx(2.8)  # (8*4 + 2*(-2)) / 10
    # the 2 unstated contributed neither a win nor a loss to the rate


def test_open_positions_never_in_win_denominator(db):
    # 10 closed winning + 3 OPEN positions that state a (bad) result: open
    # positions are not part of C(h), so the win rate stays 1.0.
    for i in range(10):
        _add_position(db, f"w{i}", "eta", net=4.0,
                      state=_state(entry=10, stop=9, exit_price=12))
    for i in range(3):
        _add_position(db, f"o{i}", "eta", status="open", net=-50.0,
                      state=_state(entry=10, stop=9, exit_price=2))
    db.commit()

    run(db, "2026-08-26")
    row = _row(db, "eta")
    assert row["n_positions"] == 13
    assert row["stated_win_rate"] == pytest.approx(1.0)


def test_genuine_zero_win_rate_is_stored_not_null(db):
    # 10 closed, all with a stated NEGATIVE result: the measured win rate is
    # genuinely 0.0 and must not be confused with a NULL "no data".
    for i in range(10):
        _add_position(db, f"z{i}", "theta", net=-1.0,
                      state=_state(entry=10, stop=9, exit_price=8))
    db.commit()

    run(db, "2026-08-26")
    row = _row(db, "theta")
    assert row["stated_win_rate"] == pytest.approx(0.0)
    assert row["stated_win_rate"] is not None
    assert row["avg_result_pct"] == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# Stop discipline math
# ---------------------------------------------------------------------------

def test_stop_honored_math_with_exclusions(db):
    # 12 closed: 10 stop+exit (8 above the final stop, 1 exactly AT it, 1
    # BELOW it), 1 with a stated stop but NO exit, 1 with no stop and no exit.
    for i in range(8):
        _add_position(db, f"h{i}", "delta", state=_state(entry=100, stop=90, exit_price=95 + i))
    _add_position(db, "at", "delta", state=_state(entry=100, stop=90, exit_price=90))  # == stop: honoured
    _add_position(db, "below", "delta", state=_state(entry=100, stop=90, exit_price=85))  # violated
    _add_position(db, "noexit", "delta", state=_state(entry=100, stop=90))  # stop, no exit
    _add_position(db, "nostop", "delta", state=_state(entry=100))  # no stop, no exit
    db.commit()

    stats = run(db, "2026-08-26")
    row = _row(db, "delta")
    d = stats["per_handle"]["delta"]
    assert d["closed"] == 12
    assert d["stop_stated"] == 11
    # honoured denominator = stop stated AND exit stated -> 10, not 12
    assert d["honored_denom"] == 10
    assert d["honored"] == 9  # 8 above + 1 at-stop; the below-stop one is not
    assert row["stop_stated_pct"] == pytest.approx(11 / 12)
    assert row["stop_honored_pct"] == pytest.approx(9 / 10)
    # positions without an exit are excluded from the honoured denominator --
    # they are not counted as violations.


# ---------------------------------------------------------------------------
# Median hold
# ---------------------------------------------------------------------------

def test_median_hold_days_math(db):
    # 5 closed with holding_days [3, 7, 11, 20, NULL] -> median of [3,7,11,20]
    # = (7+11)/2 = 9.0; NULL holding excluded; open positions count in
    # n_positions but never in the median.
    holds = [3, 7, 11, 20, None]
    for i, h in enumerate(holds):
        _add_position(db, f"m{i}", "kappa", net=None, hold=h,
                      state=_state(entry=10, stop=9))
    _add_position(db, "open1", "kappa", status="open", net=None, hold=2, state=_state())
    db.commit()

    run(db, "2026-08-26")
    row = _row(db, "kappa")
    assert row["n_positions"] == 6
    assert row["median_hold_days"] == pytest.approx(9.0)
    assert row["stated_win_rate"] is None  # no stated results at all
    # median needs no 10-sample threshold (distribution stat, not a rate)
    assert stats_hold_samples(db, "kappa") == 4


def stats_hold_samples(conn, handle: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM positions "
        "WHERE handle = ? AND status = 'closed' AND holding_days IS NOT NULL AND is_mock = 0",
        (handle,),
    ).fetchone()[0]


# ---------------------------------------------------------------------------
# avg_r math -- NULL contributions for unstated prices
# ---------------------------------------------------------------------------

def test_avg_r_math_and_uncomputable_exclusions(db):
    # 10 computable R: entry 100, stop 90, exit 110..119 -> R = (exit-100)/10
    # = 1.0..1.9, mean 1.45. Plus 2 closed positions that cannot contribute:
    # one with no exit price, one with entry == stop (division by zero).
    for i in range(10):
        _add_position(db, f"r{i}", "lambda",
                      state=_state(entry=100, stop=90, exit_price=110 + i))
    _add_position(db, "noexit", "lambda", state=_state(entry=100, stop=90))
    _add_position(db, "zerospread", "lambda",
                  state=_state(entry=100, stop=100, exit_price=120))
    db.commit()

    stats = run(db, "2026-08-26")
    row = _row(db, "lambda")
    assert stats["per_handle"]["lambda"]["computable_r"] == 10
    assert row["avg_r"] == pytest.approx(1.45)
    assert row["avg_r"] is not None
    # the two uncomputable positions are NULL contributions, not zeros or guesses


# ---------------------------------------------------------------------------
# preach_score + v1 json -- always NULL in W6, with documented reasons
# ---------------------------------------------------------------------------

def test_preach_and_v1_json_always_null(db):
    # A rich trader whose positions and education links would, if read, be
    # plenty to score preach. derive/style.py does NOT read edu_links (its
    # writer derive/preach.py is a separate W6 item and the table is empty in
    # production), so preach_score must stay NULL even when links exist here.
    _add_trader(db, "mu")
    _add_post(db, "edu-post", "mu")
    edu_id = db.execute(
        "INSERT INTO edu_items (post_id,handle,principle_text,stated_at,ingested_at) "
        "VALUES (?,?,?,?,?)",
        ("edu-post", "mu", "the stop goes where the idea is wrong", now_iso(), now_iso()),
    ).lastrowid
    for i in range(10):
        _add_position(db, f"p{i}", "mu", net=2.0,
                      state=_state(entry=100, stop=90, exit_price=110))
        db.execute(
            "INSERT INTO edu_links (edu_id,position_id,verdict,ingested_at) "
            "VALUES (?,?,?,?)",
            (edu_id, f"p{i}", "followed", now_iso()),
        )
    db.commit()

    run(db, "2026-08-26")
    row = _row(db, "mu")
    assert row["preach_score"] is None
    assert row["sector_tilt_json"] is None
    assert row["entry_type_json"] is None


# ---------------------------------------------------------------------------
# Idempotency + history
# ---------------------------------------------------------------------------

def test_rerun_same_as_of_is_idempotent(db):
    for i in range(10):
        _add_position(db, f"i{i}", "nu", net=1.0, hold=4,
                      state=_state(entry=10, stop=9, exit_price=11))
    db.commit()

    first = run(db, "2026-08-26")
    counts1 = _count(db, "trader_style")
    second = run(db, "2026-08-26")
    counts2 = _count(db, "trader_style")

    assert counts1 == counts2 == 1
    assert second["rows"] == first["rows"] == 1
    row = _row(db, "nu")
    assert row["n_positions"] == 10 and row["stated_win_rate"] == pytest.approx(1.0)
    # exactly two pipeline_runs rows for the stage (one per run)
    runs = db.execute(
        "SELECT COUNT(*) FROM pipeline_runs WHERE stage = 'derive.style'"
    ).fetchone()[0]
    assert runs == 2
    ok_rows = db.execute(
        "SELECT status, rows, run_date FROM pipeline_runs "
        "WHERE stage = 'derive.style' ORDER BY id"
    ).fetchall()
    assert [r["status"] for r in ok_rows] == ["ok", "ok"]
    assert [r["rows"] for r in ok_rows] == [1, 1]
    assert [r["run_date"] for r in ok_rows] == ["2026-08-26", "2026-08-26"]


def test_rerun_later_date_appends_history(db):
    for i in range(10):
        _add_position(db, f"i{i}", "xi", net=1.0,
                      state=_state(entry=10, stop=9, exit_price=11))
    db.commit()

    run(db, "2026-08-26")
    # the corpus changes before the second run (one more winning position)
    _add_position(db, "new", "xi", net=2.0, state=_state(entry=10, stop=9, exit_price=12))
    db.commit()
    run(db, "2026-08-27")

    rows = db.execute(
        "SELECT as_of, n_positions, stated_win_rate FROM trader_style "
        "WHERE handle = 'xi' ORDER BY as_of"
    ).fetchall()
    assert [r["as_of"] for r in rows] == ["2026-08-26", "2026-08-27"]
    assert rows[0]["n_positions"] == 10 and rows[0]["stated_win_rate"] == pytest.approx(1.0)
    # the later row reflects the newer corpus; the earlier row is untouched
    assert rows[1]["n_positions"] == 11 and rows[1]["stated_win_rate"] == pytest.approx(1.0)
    # the API pattern (MAX(as_of) per handle) resolves to the newest row
    latest = _row(db, "xi")
    assert latest["as_of"] == "2026-08-27"


# ---------------------------------------------------------------------------
# Isolation, mock exclusion, inactive handles, zero-position traders
# ---------------------------------------------------------------------------

def test_per_handle_isolation(db):
    # alpha: 10 winners; beta: 10 with NO stated results. Nothing may leak
    # across handles in either direction.
    for i in range(10):
        _add_position(db, f"a{i}", "alpha", net=4.0,
                      state=_state(entry=10, stop=9, exit_price=12))
    for i in range(10):
        _add_position(db, f"b{i}", "beta", net=None,
                      state=_state(entry=10, stop=9, exit_price=12))
    db.commit()

    run(db, "2026-08-26")
    a = _row(db, "alpha")
    b = _row(db, "beta")
    assert a["stated_win_rate"] == pytest.approx(1.0)
    assert b["stated_win_rate"] is None
    assert b["n_positions"] == 10
    assert b["median_hold_days"] is None  # no holding_days stated for beta
    assert _count(db, "trader_style") == 2


def test_mock_positions_excluded_and_mock_traders_get_no_row(db):
    # zeta: 10 REAL closed winners + 5 MOCK closed losers. The mock rows must
    # not touch a single count or denominator.
    _add_trader(db, "zeta")
    for i in range(10):
        _add_position(db, f"rz{i}", "zeta", net=4.0,
                      state=_state(entry=10, stop=9, exit_price=12))
    for i in range(5):
        _add_position(db, f"mz{i}", "zeta", net=-99.0, is_mock=1,
                      state=_state(entry=10, stop=9, exit_price=1))
    # a MOCK trader (traders.is_mock=1) must never get a trader_style row
    _add_trader(db, "mockperson", is_mock=1)
    db.commit()

    stats = run(db, "2026-08-26")
    z = _row(db, "zeta")
    assert z["n_positions"] == 10
    assert z["stated_win_rate"] == pytest.approx(1.0)
    assert stats["per_handle"]["zeta"]["closed"] == 10
    assert "mockperson" not in stats["per_handle"]
    assert db.execute(
        "SELECT COUNT(*) FROM trader_style WHERE handle = 'mockperson'"
    ).fetchone()[0] == 0


def test_inactive_trader_keeps_last_row(db):
    _add_trader(db, "omicron", active=1)
    for i in range(10):
        _add_position(db, f"o{i}", "omicron", net=1.0,
                      state=_state(entry=10, stop=9, exit_price=11))
    _add_trader(db, "stillactive", active=1)
    for i in range(10):
        _add_position(db, f"s{i}", "stillactive", net=2.0,
                      state=_state(entry=10, stop=9, exit_price=12))
    db.commit()

    run(db, "2026-08-26")
    db.execute("UPDATE traders SET active = 0 WHERE handle = 'omicron'")
    db.commit()
    run(db, "2026-08-27")

    # omicron: no new row (not computed), the 2026-08-26 row remains
    omicron_days = [r[0] for r in db.execute(
        "SELECT as_of FROM trader_style WHERE handle = 'omicron' ORDER BY as_of")]
    assert omicron_days == ["2026-08-26"]
    # stillactive gets the new-as_of row
    assert _row(db, "stillactive")["as_of"] == "2026-08-27"
    assert _count(db, "trader_style") == 3  # omicron D1 + stillactive D1 + D2


def test_zero_position_trader_gets_honest_row(db):
    _add_trader(db, "emptyhanded")
    _add_trader(db, "busy")
    for i in range(10):
        _add_position(db, f"b{i}", "busy", net=0.5,
                      state=_state(entry=10, stop=9, exit_price=11))
    db.commit()

    run(db, "2026-08-26")
    e = _row(db, "emptyhanded")
    assert e["n_positions"] == 0
    assert e["median_hold_days"] is None
    assert e["stated_win_rate"] is None
    assert e["stop_stated_pct"] is None
    assert e["preach_score"] is None
    assert _row(db, "busy")["n_positions"] == 10


# ---------------------------------------------------------------------------
# Price sources -- state_json is the position; events are the rescue path
# ---------------------------------------------------------------------------

def test_state_json_unparseable_falls_back_to_position_events(db):
    # state_json is malformed legacy junk; the event rows carry the stated
    # prices, so R is computable from events (documented fallback path).
    _add_trader(db, "rho")
    _add_post(db, "r1-entry", "rho")
    _add_post(db, "r1-stop", "rho")
    _add_post(db, "r1-exit", "rho")
    _add_position(db, "r1", "rho", net=2.0)
    # state_json is malformed legacy junk; the event rows carry the stated
    # prices, so R is computable from events (documented fallback path).
    db.execute(
        "UPDATE positions SET state_json = 'not-json{{' WHERE position_id = 'r1'"
    )
    _add_event(db, "r1", "r1-entry", "entry", 100.0, 1)
    _add_event(db, "r1", "r1-stop", "sl_set", 90.0, 2)
    _add_event(db, "r1", "r1-exit", "exit", 120.0, 3)
    db.commit()

    stats = run(db, "2026-08-26")
    d = stats["per_handle"]["rho"]
    assert d["computable_r"] == 1
    assert d["stop_stated"] == 1
    assert d["honored_denom"] == 1
    # the aggregate math itself (R = (120-100)/(100-90) = 2.0) is validated
    # through _aggregate's unit test; here the DB plumbing is proven.


def test_parsed_state_json_ignores_events(db):
    # state_json parses but carries no exit price; an event row DOES carry an
    # exit price. state_json is the position, so the exit is "not stated":
    # R must not be computable, and the stop+exit honoured denominator must
    # not count it either.
    _add_trader(db, "sigma")
    _add_post(db, "s1-exit", "sigma")
    _add_position(db, "s1", "sigma", state=_state(entry=100, stop=90))
    _add_event(db, "s1", "s1-exit", "exit", 130.0, 1)
    db.commit()

    stats = run(db, "2026-08-26")
    d = stats["per_handle"]["sigma"]
    assert d["computable_r"] == 0
    assert d["honored_denom"] == 0
    assert d["stop_stated"] == 1  # the stop IS stated via state_json


def test_prices_from_state_first_entry_last_priced_exit():
    state = {
        "entries": [{"price": 100.0, "post_id": "e0"}, {"price": None, "post_id": "e1"}],
        "stop": {"price": 90.0, "post_id": "s0"},
        "exits": [
            {"price": None, "qty_pct": 50.0, "post_id": "x0"},   # partial, no price
            {"date": "2026-08-09", "qty_pct": 50.0, "post_id": "x1"},  # no price key
            {"price": 120.0, "qty_pct": 100.0, "post_id": "x2"},  # final exit
        ],
    }
    prices = _prices_from_state(state)
    assert prices["entry"] == 100.0
    assert prices["stop"] == 90.0
    assert prices["exit"] == 120.0
    assert _prices_from_state({"entries": [], "stop": None, "exits": []}) == {
        "entry": None, "stop": None, "exit": None,
    }


def test_prices_from_events_last_stop_and_exit_win():
    rows = [
        {"kind": "sl_set", "price": 90.0},
        {"kind": "sl_move", "price": 95.0},   # trailed stop: final
        {"kind": "partial_exit", "price": 110.0},
        {"kind": "exit", "price": 120.0},     # final exit
        {"kind": "commentary", "price": None},
    ]
    class _FakeCursor:
        def fetchall(self):
            return rows
    class _FakeConn:
        def execute(self, sql, params):
            return _FakeCursor()
    prices = _prices_from_events(_FakeConn(), "x")  # type: ignore[arg-type]
    assert prices == {"entry": None, "stop": 95.0, "exit": 120.0}


# ---------------------------------------------------------------------------
# Aggregate math without a DB (prices supplied directly)
# ---------------------------------------------------------------------------

def test_aggregate_math_independent_of_db():
    closed = [
        {"position_id": "1", "net_result_pct": 4.0, "holding_days": 5},
        {"position_id": "2", "net_result_pct": None, "holding_days": None},
        {"position_id": "3", "net_result_pct": -1.0, "holding_days": 3},
        {"position_id": "4", "net_result_pct": 2.0, "holding_days": None},
    ]
    prices = {
        "1": {"entry": 100.0, "stop": 90.0, "exit": 120.0},   # R (120-100)/10 = 2.0
        "2": {"entry": 100.0, "stop": 90.0, "exit": 120.0},   # R 2.0; no stated result
        "3": {"entry": 100.0, "stop": 50.0, "exit": 75.0},    # R (75-100)/50 = -0.5
        "4": {"entry": 50.0, "stop": 40.0, "exit": 90.0},     # R (90-50)/10 = 4.0
    }
    agg = _aggregate(closed, lambda p: prices[p["position_id"]])

    assert agg["stated_results"] == 3
    assert agg["wins"] == 2
    assert agg["hold_days"] == pytest.approx([5.0, 3.0])
    assert agg["r_values"] == pytest.approx([2.0, 2.0, -0.5, 4.0])
    assert agg["stop_stated"] == 4
    assert agg["honored_denom"] == 4
    assert agg["honored"] == 4
    # exit price at-or-above the final stop = honoured by the long convention
    # (positions 3 and 4 close above their stops even when the R is negative)


def test_aggregate_entry_equals_stop_is_not_computable():
    closed = [{"position_id": "1", "net_result_pct": None, "holding_days": None}]
    prices = {"1": {"entry": 100.0, "stop": 100.0, "exit": 120.0}}
    agg = _aggregate(closed, lambda p: prices[p["position_id"]])
    assert agg["r_values"] == []


# ---------------------------------------------------------------------------
# Failure path -- never partially commits, fail is logged
# ---------------------------------------------------------------------------

def test_run_failure_rolls_back_and_logs_fail(db):
    for i in range(10):
        _add_position(db, f"f{i}", "phi", net=1.0,
                      state=_state(entry=10, stop=9, exit_price=11))
    db.commit()
    run(db, "2026-08-26")

    # Force the next run's INSERT to abort mid-transaction.
    db.execute(
        "CREATE TRIGGER reject_style_insert BEFORE INSERT ON trader_style "
        "WHEN NEW.as_of = '2026-08-27' BEGIN "
        "SELECT RAISE(ABORT, 'forced insert failure'); END"
    )
    db.commit()

    with pytest.raises(sqlite3.IntegrityError, match="forced insert failure"):
        run(db, "2026-08-27")

    # The prior day's row survived the rollback; no partial write appeared.
    assert _count(db, "trader_style") == 1
    assert _row(db, "phi")["as_of"] == "2026-08-26"
    fail_row = db.execute(
        "SELECT status, rows, run_date FROM pipeline_runs "
        "WHERE stage = 'derive.style' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert fail_row["status"] == "fail"
    assert fail_row["rows"] == 0
    assert fail_row["run_date"] == "2026-08-27"