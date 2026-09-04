from datetime import date, timedelta

from manas_os import db
from manas_os.alpha import factor_health, schema


def test_factor_ic_uses_only_available_forward_sessions_and_persists_health(tmp_path):
    conn = db.init_db(tmp_path / "factors.db")
    try:
        schema.ensure_schema(conn)
        days = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(25)]
        for symbol, drift, percentile in (("LOW", -0.2, 10.0), ("MID", 0.0, 50.0), ("HIGH", 0.3, 90.0)):
            for index, day in enumerate(days):
                close = 100.0 + drift * index
                conn.execute(
                    "INSERT INTO daily_prices (symbol,trade_date,series,close,source) VALUES (?,?,'EQ',?,'bhavcopy')",
                    (symbol, day, close),
                )
            conn.execute(
                "INSERT INTO alpha_feature_snapshots (as_of_date,symbol,feature_version,universe,"
                "source_max_date,source_denominator,momentum_percentile,features_json) "
                "VALUES (?,?,?,'test',?,3,?,'{}')",
                (days[0], symbol, factor_health.FACTOR_VERSION, days[0], percentile),
            )
        conn.commit()

        assert factor_health.evaluate(conn, days[24]) == 3
        evaluations = conn.execute(
            "SELECT horizon_sessions,pearson_ic,spearman_rank_ic,future_available_at "
            "FROM alpha_factor_evaluations ORDER BY horizon_sessions"
        ).fetchall()
        assert [row["horizon_sessions"] for row in evaluations] == [5, 10, 20]
        assert all(row["pearson_ic"] > 0.99 for row in evaluations)
        assert all(row["spearman_rank_ic"] == 1.0 for row in evaluations)
        assert evaluations[-1]["future_available_at"] == days[20]
        payload = factor_health.health(conn)
        assert payload["state"] == "ready"
        assert len(payload["rows"]) == 3
        assert payload["shadow_only"] is True
    finally:
        conn.close()


def test_factor_ic_stays_warming_before_forward_data_exists(tmp_path):
    conn = db.init_db(tmp_path / "factors.db")
    try:
        schema.ensure_schema(conn)
        conn.execute(
            "INSERT INTO alpha_feature_snapshots (as_of_date,symbol,feature_version,universe,"
            "source_max_date,source_denominator,momentum_percentile,features_json) "
            "VALUES ('2026-01-01','ONLY',?,'test','2026-01-01',1,50,'{}')",
            (factor_health.FACTOR_VERSION,),
        )
        conn.execute(
            "INSERT INTO daily_prices (symbol,trade_date,series,close) VALUES ('ONLY','2026-01-01','EQ',100)"
        )
        conn.commit()
        assert factor_health.evaluate(conn, "2026-01-01") == 0
        assert factor_health.health(conn)["state"] == "warming"
    finally:
        conn.close()
