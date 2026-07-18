from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.alpha import schema as alpha_schema
from manas_os.alpha.activity import FORMULA_VERSION
from manas_os.api import app as api_app
from manas_os.cli import _load_stages
from manas_os.scanner import candidates, footprint


AS_OF = "2026-07-17"


def _weekdays(count: int, end: str = AS_OF) -> list[str]:
    cursor = date.fromisoformat(end)
    out: list[str] = []
    while len(out) < count:
        if cursor.weekday() < 5:
            out.append(cursor.isoformat())
        cursor -= timedelta(days=1)
    return list(reversed(out))


def _seed_prices(conn, symbol: str, dates: list[str]) -> None:
    conn.executemany(
        "INSERT INTO daily_prices "
        "(symbol,trade_date,series,open,high,low,close,prev_close,volume,delivery_pct,source) "
        "VALUES (?,?,'EQ',100,101,99,100,100,100,50,'bhavcopy')",
        [(symbol, trade_date) for trade_date in dates],
    )


def _signal(conn, symbol: str, trade_date: str, score: float, delivery_pct: float = 50.0) -> None:
    conn.execute(
        "INSERT INTO alpha_activity_signals "
        "(as_of_date,symbol,formula_version,score,percentile,state,persistence_sessions,"
        "delivery_pct,source,quality_status) VALUES (?,?,?,?,50,'baseline',0,?,'bhavcopy','ready')",
        (trade_date, symbol, FORMULA_VERSION, score, delivery_pct),
    )


def _fixture_db(tmp_path):
    path = tmp_path / "footprint.db"
    conn = db.init_db(path)
    alpha_schema.ensure_schema(conn)
    footprint.ensure_schema(conn)
    return path, conn


def test_classifier_covers_each_lane_and_separate_context(tmp_path):
    _, conn = _fixture_db(tmp_path)
    dates = _weekdays(25)
    cases = {
        "SA": (5.0, "silent_accumulation", "stealth_accumulation_in_base"),
        "AB": (8.0, "absorption", "churn_against_holding"),
        "PM": (6.0, "public_markup", "breakout_confirmation"),
        "SO": (5.5, "silent_offloading", "churn_against_holding"),
        "RC": (2.0, "retail_churn", None),
        "EXT": (5.0, "silent_offloading", "churn_against_holding"),
    }
    for symbol in cases:
        _seed_prices(conn, symbol, dates)

    conn.execute(
        "UPDATE daily_prices SET close=100.2,prev_close=100,high=101,low=99,volume=80 "
        "WHERE symbol='SA' AND trade_date=?", (AS_OF,),
    )
    conn.execute(
        "UPDATE daily_prices SET close=99,prev_close=100,high=99.4,low=98.7,volume=200 "
        "WHERE symbol='AB' AND trade_date=?", (AS_OF,),
    )
    conn.execute(
        "UPDATE daily_prices SET close=103,prev_close=100,high=104,low=99,volume=200 "
        "WHERE symbol='PM' AND trade_date=?", (AS_OF,),
    )
    conn.execute(
        "UPDATE daily_prices SET close=101,high=101.5,low=100.5 "
        "WHERE symbol='SO' AND trade_date=?", (dates[-2],),
    )
    conn.execute(
        "UPDATE daily_prices SET close=99,prev_close=101,high=99.4,low=98.6,volume=100 "
        "WHERE symbol='SO' AND trade_date=?", (AS_OF,),
    )
    conn.execute(
        "UPDATE daily_prices SET close=103,prev_close=100,high=104,low=99,volume=200 "
        "WHERE symbol='RC' AND trade_date=?", (AS_OF,),
    )
    conn.execute(
        "UPDATE daily_prices SET open=50,high=51,low=49,close=50,prev_close=50,volume=100 "
        "WHERE symbol='EXT'",
    )
    conn.execute(
        "UPDATE daily_prices SET high=100 WHERE symbol='EXT' AND trade_date=?", (dates[0],),
    )
    conn.execute(
        "UPDATE daily_prices SET open=60,close=60,prev_close=61,high=61,low=59,volume=100 "
        "WHERE symbol='EXT' AND trade_date=?", (AS_OF,),
    )
    delivery = {"SA": 50.0, "AB": 25.0, "RC": 24.0}
    for symbol, (score, _, _) in cases.items():
        _signal(conn, symbol, AS_OF, score, delivery.get(symbol, 50.0))

    rows = {row["symbol"]: row for row in footprint.compute(conn, AS_OF)}

    for symbol, (_, expected_lane, expected_context) in cases.items():
        assert rows[symbol]["lane"] == expected_lane
        assert rows[symbol]["context"] == expected_context
    assert rows["AB"]["tier"] == "EXTREME"
    assert rows["SA"]["tier"] == "STRICT"
    assert rows["RC"]["tier"] is None
    assert rows["SA"]["volume_ratio"] == 0.8
    assert rows["SA"]["delivery_band"] == "strong"
    assert rows["AB"]["delivery_band"] == "moderate"
    assert rows["RC"]["delivery_band"] == "weak"


def test_streak_avg4_boundaries_and_split_exclusion(tmp_path):
    _, conn = _fixture_db(tmp_path)
    dates = _weekdays(25)
    for symbol in ("DOCTRINE", "BOUNDARY", "AVGBOUND", "SPLIT"):
        _seed_prices(conn, symbol, dates)

    for trade_date, score in zip(dates[-4:], (4.0, 5.0, 6.0, 7.0)):
        _signal(conn, "DOCTRINE", trade_date, score)
    _signal(conn, "BOUNDARY", AS_OF, 4.0)
    for trade_date in dates[-4:]:
        _signal(conn, "AVGBOUND", trade_date, 5.0)
    _signal(conn, "SPLIT", AS_OF, 9.0)
    conn.execute(
        "UPDATE daily_prices SET close=200,prev_close=100,high=201,low=199,volume=200 "
        "WHERE symbol='SPLIT' AND trade_date=?", (AS_OF,),
    )

    rows = {row["symbol"]: row for row in footprint.compute(conn, AS_OF)}
    doctrine = rows["DOCTRINE"]
    assert doctrine["streak_days"] == 4
    assert doctrine["avg4"] == 5.5
    assert footprint.doctrine_flags(doctrine) == {
        "abnormal": True,
        "strict": True,
        "streak3": True,
        "avg4_over5": True,
    }
    assert footprint.doctrine_flags(rows["BOUNDARY"])["strict"] is False
    assert rows["BOUNDARY"]["tier"] == "ABNORMAL"
    assert rows["AVGBOUND"]["avg4"] == 5.0
    assert footprint.doctrine_flags(rows["AVGBOUND"])["avg4_over5"] is False
    assert rows["SPLIT"]["split_suspect"] == 1
    assert rows["SPLIT"]["tier"] is None
    assert rows["SPLIT"]["streak_days"] == 0
    assert rows["SPLIT"]["context"] is None
    assert rows["SPLIT"]["lane"] is None


def test_campaign_counts_and_delivery_weighted_signed_balance(tmp_path):
    _, conn = _fixture_db(tmp_path)
    dates = _weekdays(25)
    _seed_prices(conn, "FLOW", dates)
    d_acc, d_dist, d_abs = dates[-3:]
    conn.execute(
        "UPDATE daily_prices SET close=100.2,prev_close=100,high=101,low=99,volume=80 "
        "WHERE symbol='FLOW' AND trade_date=?", (d_acc,),
    )
    conn.execute(
        "UPDATE daily_prices SET close=99,prev_close=101,high=99.4,low=98.6,volume=100 "
        "WHERE symbol='FLOW' AND trade_date=?", (d_dist,),
    )
    conn.execute(
        "UPDATE daily_prices SET close=98,prev_close=99,high=98.3,low=97.7,volume=200 "
        "WHERE symbol='FLOW' AND trade_date=?", (d_abs,),
    )
    _signal(conn, "FLOW", d_acc, 4.0, 50.0)
    _signal(conn, "FLOW", d_dist, 6.0, 50.0)
    _signal(conn, "FLOW", d_abs, 8.0, 25.0)

    row = footprint.compute(conn, AS_OF)[0]

    assert row["silent_accum_days_20"] == 1
    assert row["silent_dist_days_20"] == 1
    assert row["net_silent_flow"] == -3.0


def test_footprint_api_symbol_board_scope_sort_and_empty_state(tmp_path, monkeypatch):
    path, conn = _fixture_db(tmp_path)
    rows = [
        (AS_OF, "AAA", 6.0, "abnormal", 3, 5.5, "strong", 1.0, 0.1,
         "stealth_accumulation_in_base", "silent_accumulation", 0, 4, 1, 8.0),
        (AS_OF, "BBB", 8.0, "extreme", 1, 4.0, "moderate", 2.0, -1.0,
         "churn_against_holding", "silent_offloading", 0, 1, 3, -12.0),
        (AS_OF, "CCC", 5.0, "abnormal", 2, 4.5, "weak", 0.8, 0.1,
         "stealth_accumulation_in_base", "silent_accumulation", 0, 2, 0, 3.0),
        (AS_OF, "OUT", 9.0, "extreme", 4, 7.0, "strong", 2.0, 2.0,
         "breakout_confirmation", "public_markup", 0, 0, 0, 99.0),
    ]
    conn.executemany(
        "INSERT INTO footprint_daily "
        "(trade_date,symbol,score,tier,streak_days,avg4,delivery_band,volume_ratio,day_change_pct,"
        "context,lane,split_suspect,silent_accum_days_20,silent_dist_days_20,net_silent_flow) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows,
    )
    conn.execute(
        "INSERT INTO scan_candidates (scan_date,symbol,setup) VALUES (?,?,?)",
        (AS_OF, "AAA", "fixture"),
    )
    conn.execute(
        "INSERT INTO discovery_bucket (scan_date,symbol,archetypes_json,metrics_json) "
        "VALUES (?,?,?,?)", (AS_OF, "BBB", "[]", "{}"),
    )
    conn.execute("INSERT INTO watchlist (symbol) VALUES ('CCC')")
    conn.commit()
    conn.close()

    original_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: original_connect(path))
    client = TestClient(api_app.app)

    symbol = client.get("/api/footprint/AAA", params={"date": AS_OF})
    assert symbol.status_code == 200
    body = symbol.json()
    assert body["available"] is True
    assert body["doctrine_flags"] == {
        "abnormal": True, "strict": True, "streak3": True, "avg4_over5": True,
    }
    assert body["campaign"] == {
        "silent_accum_days_20": 4,
        "silent_dist_days_20": 1,
        "net_silent_flow": 8.0,
    }
    assert body["series"] == [{"date": AS_OF, "score": 6.0, "lane": "silent_accumulation"}]

    board = client.get("/api/footprint/board", params={"date": AS_OF}).json()
    assert board["available"] is True
    assert [item["symbol"] for item in board["lanes"]["silent_accumulation"]] == ["AAA", "CCC"]
    assert board["lanes"]["silent_offloading"][0]["balance"] == "1acc/3dist"
    assert all(item["symbol"] != "OUT" for lane in board["lanes"].values() for item in lane)

    assert client.get("/api/footprint/MISSING", params={"date": AS_OF}).json()["available"] is False
    assert client.get("/api/footprint/board", params={"date": "2020-01-01"}).json()["available"] is False


def test_candidate_footprint_chip_does_not_change_rank_order(tmp_path):
    _, conn = _fixture_db(tmp_path)
    conn.execute(
        "INSERT INTO footprint_daily "
        "(trade_date,symbol,score,tier,streak_days,avg4,delivery_band,split_suspect) "
        "VALUES (?,?,?,?,?,?,?,0)",
        (AS_OF, "LOW", 8.0, "extreme", 4, 7.0, "strong"),
    )
    base = [
        {"symbol": "HIGH", "rank_inputs": (2.0, 1.0, 1), "score_breakdown": {},
         "setup_family": "momentum", "grade_cap": None, "evidence": []},
        {"symbol": "LOW", "rank_inputs": (1.0, 1.0, 1), "score_breakdown": {},
         "setup_family": "momentum", "grade_cap": None, "evidence": []},
    ]
    without = deepcopy(base)
    with_rows = deepcopy(base)
    for item in with_rows:
        candidates.append_footprint_evidence(conn, item["symbol"], AS_OF, item["evidence"])

    candidates._assign_ranks(without)
    candidates._assign_ranks(with_rows)

    assert [item["symbol"] for item in with_rows] == [item["symbol"] for item in without]
    assert [item["rank"] for item in with_rows] == [item["rank"] for item in without]
    assert with_rows[1]["evidence"] == [
        {"filter": "footprint", "value": "8.0 extreme | 4d streak | delivery strong"}
    ]


def test_pipeline_places_footprint_after_activity_and_logs_empty_stage(tmp_path):
    names = [name for name, _stage in _load_stages()]
    assert names.index("alpha_features") < names.index("footprint_driver")
    assert names.index("footprint_driver") < names.index("scan_candidates")

    _, conn = _fixture_db(tmp_path)
    result = footprint.run(conn, AS_OF)
    logged = conn.execute(
        "SELECT status,rows_affected,detail FROM pipeline_runs "
        "WHERE run_date=? AND stage='footprint_driver' ORDER BY run_id DESC LIMIT 1",
        (AS_OF,),
    ).fetchone()
    assert result["status"] == "skip"
    assert logged["status"] == "skip"
    assert logged["rows_affected"] == 0
    assert AS_OF in logged["detail"]
