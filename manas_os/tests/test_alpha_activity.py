from datetime import date, timedelta

from manas_os import db
from manas_os.alpha import activity


def _seed(conn, symbol: str, *, spike: float = 1.0, future: bool = False) -> str:
    start = date(2026, 1, 1)
    for index in range(21 if future else 20):
        day = (start + timedelta(days=index)).isoformat()
        qty = 100_000 * (spike if index == 19 else 1.0)
        conn.execute(
            "INSERT INTO daily_prices "
            "(symbol,trade_date,series,open,high,low,close,volume,turnover,"
            "num_trades,delivery_pct,source) "
            "VALUES (?,?, 'EQ',100,102,99,101,?,?,?,?, 'bhavcopy')",
            (symbol, day, int(qty), 200.0, 1_000, 60.0),
        )
    conn.commit()
    return (start + timedelta(days=19)).isoformat()


def test_activity_formula_is_causal_direction_neutral_and_persisted(tmp_path):
    conn = db.init_db(tmp_path / "activity.db")
    try:
        as_of = _seed(conn, "SPIKE", spike=10.0, future=True)
        _seed(conn, "CALM", spike=1.0)
        rows = activity.compute(conn, as_of)
        by_symbol = {row["symbol"]: row for row in rows}

        q_ratio = (1_000.0) / ((19 * 100.0 + 1_000.0) / 20.0)
        expected = 1.165335 * q_ratio + 1.04631 + 1.152161 * (q_ratio**0.84) - 0.213928
        assert by_symbol["SPIKE"]["score"] == round(expected, 2)
        assert by_symbol["SPIKE"]["percentile"] == 100.0
        assert by_symbol["SPIKE"]["state"] == "isolated_extreme"

        # The 21st bar exists for SPIKE but is after as_of and must not affect the result.
        again = {row["symbol"]: row for row in activity.compute(conn, as_of)}
        assert again["SPIKE"]["score"] == by_symbol["SPIKE"]["score"]

        payload = activity.symbol(conn, "SPIKE", as_of=as_of)
        assert payload["latest"]["formula_version"] == activity.FORMULA_VERSION
        assert "direction unresolved" in payload["note"].lower()
        assert payload["shadow_only"] is True
    finally:
        conn.close()


def test_activity_needs_twenty_valid_sessions(tmp_path):
    conn = db.init_db(tmp_path / "activity.db")
    try:
        for index in range(19):
            day = (date(2026, 1, 1) + timedelta(days=index)).isoformat()
            conn.execute(
                "INSERT INTO daily_prices "
                "(symbol,trade_date,series,volume,num_trades,delivery_pct,source) "
                "VALUES ('SHORT',?,'EQ',100000,1000,50,'bhavcopy')",
                (day,),
            )
        conn.commit()
        assert activity.compute(conn, "2026-02-01") == []
        assert activity.leaders(conn)["state"] == "warming"
    finally:
        conn.close()


def test_activity_persistence_resets_across_a_missing_signal_session(tmp_path):
    conn = db.init_db(tmp_path / "activity.db")
    try:
        first = _seed(conn, "SPIKE", spike=10.0, future=True)
        activity.compute(conn, first)
        # Skip the immediately following valid price session, then compute a later
        # abnormal observation. A stale prior signal must not look continuous.
        later = (date.fromisoformat(first) + timedelta(days=2)).isoformat()
        conn.execute(
            "INSERT INTO daily_prices "
            "(symbol,trade_date,series,volume,turnover,num_trades,delivery_pct,source) "
            "VALUES ('SPIKE',?,'EQ',1000000,200,1000,60,'bhavcopy')",
            (later,),
        )
        conn.commit()
        rows = {row["symbol"]: row for row in activity.compute(conn, later)}
        assert rows["SPIKE"]["score"] >= activity.ABNORMAL_LEVEL
        assert rows["SPIKE"]["persistence_sessions"] == 1
    finally:
        conn.close()


def test_activity_leaders_include_comparable_trend_fields(tmp_path):
    conn = db.init_db(tmp_path / "activity.db")
    try:
        activity.ensure_schema(conn)
        scores = [2.0, 3.0, 4.0, 5.0, 8.0]
        for index, score in enumerate(scores, start=1):
            conn.execute(
                "INSERT INTO alpha_activity_signals "
                "(as_of_date,symbol,formula_version,score,state,persistence_sessions,"
                "source,quality_status) "
                "VALUES (?,?,?,?,?,?, 'bhavcopy','ready')",
                (
                    f"2026-01-{index:02d}",
                    "TREND",
                    activity.FORMULA_VERSION,
                    score,
                    "abnormal" if score >= activity.ABNORMAL_LEVEL else "baseline",
                    2 if score >= activity.ABNORMAL_LEVEL else 0,
                ),
            )
        conn.commit()

        payload = activity.leaders(conn, as_of="2026-01-05")
        row = payload["rows"][0]

        assert row["previous_score"] == 5.0
        assert row["score_change"] == 3.0
        assert row["score_avg_4"] == 5.0
        assert row["score_avg_10"] == 4.4
        assert row["trail"] == [2.0, 3.0, 4.0, 5.0, 8.0]
        assert payload["summary"] == {
            "universe": 1,
            "abnormal": 1,
            "extreme": 1,
            "persistent": 1,
        }
        conn.execute(
            "INSERT INTO alpha_activity_signals "
            "(as_of_date,symbol,formula_version,score,state,persistence_sessions,"
            "source,quality_status) "
            "VALUES ('2026-01-05','TREND','sat10ic_eod_activity_v1',99,"
            "'isolated_extreme',1,'bhavcopy','ready')"
        )
        conn.execute(
            "INSERT INTO alpha_activity_signals "
            "(as_of_date,symbol,formula_version,score,state,persistence_sessions,"
            "source,quality_status) "
            "VALUES ('2026-01-06','TREND','sat10ic_eod_activity_v1',100,"
            "'isolated_extreme',1,'bhavcopy','ready')"
        )
        conn.commit()
        symbol_payload = activity.symbol(conn, "TREND", as_of="2026-01-05", trail=10)
        assert len(symbol_payload["trail"]) == 5
        assert {row["formula_version"] for row in symbol_payload["trail"]} == {
            activity.FORMULA_VERSION
        }
        latest_payload = activity.leaders(conn)
        assert latest_payload["as_of"] == "2026-01-05"
        assert latest_payload["rows"][0]["formula_version"] == activity.FORMULA_VERSION
    finally:
        conn.close()


def test_activity_compute_excludes_probable_etf_units(tmp_path):
    conn = db.init_db(tmp_path / "activity.db")
    try:
        as_of = _seed(conn, "REALCO")
        _seed(conn, "NIFTYBEES")
        _seed(conn, "UNRESOLVED")
        activity.ensure_schema(conn)
        conn.execute(
            "INSERT INTO universe (symbol,as_of_date,series,sector,industry,is_tradeable) "
            "VALUES ('REALCO',?,'EQ','IT','Software',1),"
            "('NIFTYBEES',?,'EQ',NULL,NULL,0),"
            "('UNRESOLVED',?,'EQ',NULL,NULL,0)",
            (as_of, as_of, as_of),
        )
        conn.execute(
            "INSERT INTO alpha_activity_signals "
            "(as_of_date,symbol,formula_version,score,state,persistence_sessions,"
            "source,quality_status) "
            "VALUES (?, 'NIFTYBEES', ?, 99, 'isolated_extreme', 1, 'bhavcopy', 'ready')",
            (as_of, activity.FORMULA_VERSION),
        )

        rows = activity.compute(conn, as_of)

        assert {row["symbol"] for row in rows} == {"REALCO"}
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM alpha_activity_signals WHERE symbol='NIFTYBEES'"
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM alpha_activity_signals WHERE symbol='UNRESOLVED'"
            ).fetchone()[0]
            == 0
        )
    finally:
        conn.close()
