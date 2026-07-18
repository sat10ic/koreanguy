import math
from datetime import date, timedelta

from manas_os import db
from manas_os.alpha import backfill, schema
from manas_os.cli import build_parser


def _seed_factor_panel(conn) -> tuple[list[str], list[str]]:
    days = [(date(2026, 1, 1) + timedelta(days=i)).isoformat() for i in range(6)]
    symbols = [f"S{i}" for i in range(8)]
    feature_version = "test-features-v1"
    activity_version = "test-activity-v1"
    for index, symbol in enumerate(symbols):
        for session_index, day in enumerate(days):
            close = 100.0 + index if session_index == 5 else 100.0
            delivery_pct = float(index + 1) if session_index == 0 else float(100 - index)
            conn.execute(
                "INSERT INTO daily_prices "
                "(symbol,trade_date,series,close,delivery_pct,source) "
                "VALUES (?,?,'EQ',?,?,'bhavcopy')",
                (symbol, day, close, delivery_pct),
            )
        conn.execute(
            "INSERT INTO alpha_feature_snapshots ("
            "as_of_date,symbol,feature_version,universe,source_max_date,"
            "source_denominator,momentum_zscore,market_residual_20,features_json) "
            "VALUES (?,?,?,'test',?,8,?,?,'{}')",
            (
                days[0],
                symbol,
                feature_version,
                days[0],
                float(7 - index),
                float(index),
            ),
        )
        # A future-only snapshot with reversed values must never pollute day 0.
        conn.execute(
            "INSERT INTO alpha_feature_snapshots ("
            "as_of_date,symbol,feature_version,universe,source_max_date,"
            "source_denominator,momentum_zscore,market_residual_20,features_json) "
            "VALUES (?,?,?,'test',?,8,?,?,'{}')",
            (
                days[5],
                symbol,
                "future-only-v1",
                days[5],
                float(index),
                float(7 - index),
            ),
        )
        conn.execute(
            "INSERT INTO alpha_activity_signals ("
            "as_of_date,symbol,formula_version,score,state,source,quality_status) "
            "VALUES (?,?,?,?,'baseline','bhavcopy','ready')",
            (days[0], symbol, activity_version, float(index)),
        )
    conn.execute(
        "INSERT INTO regime_snapshots (snapshot_date,market_mode) VALUES (?,?)",
        (days[0], "RISK_ON"),
    )
    conn.commit()
    return days, symbols


def test_backfill_computes_three_hand_checkable_factor_ics_without_lookahead(tmp_path):
    conn = db.init_db(tmp_path / "alpha-backfill.db")
    try:
        schema.ensure_schema(conn)
        days, _symbols = _seed_factor_panel(conn)

        result = backfill.backfill_factor_evaluations(
            conn, days[0], days[0], horizons=(5,)
        )

        rows = conn.execute(
            "SELECT factor_id,pearson_ic,spearman_rank_ic,universe_denominator,"
            "regime,future_available_at FROM alpha_factor_evaluations "
            "ORDER BY factor_id"
        ).fetchall()
        assert result["evaluations_written"] == 3
        assert [row["factor_id"] for row in rows] == [
            "activity_footprint_score",
            "market_residual_20",
            "momentum_zscore",
        ]
        by_factor = {row["factor_id"]: row for row in rows}
        for factor_id in ("activity_footprint_score", "market_residual_20"):
            assert math.isclose(by_factor[factor_id]["pearson_ic"], 1.0, abs_tol=1e-12)
            assert math.isclose(by_factor[factor_id]["spearman_rank_ic"], 1.0, abs_tol=1e-12)
        assert math.isclose(by_factor["momentum_zscore"]["pearson_ic"], -1.0, abs_tol=1e-12)
        assert math.isclose(by_factor["momentum_zscore"]["spearman_rank_ic"], -1.0, abs_tol=1e-12)
        assert all(row["universe_denominator"] == 8 for row in rows)
        assert all(row["regime"] == "RISK_ON" for row in rows)
        assert all(row["future_available_at"] == days[5] for row in rows)
        assert all(row["future_available_at"] > days[0] for row in rows)
    finally:
        conn.close()


def test_backfill_is_idempotent_and_refreshes_health_aggregates(tmp_path):
    conn = db.init_db(tmp_path / "alpha-backfill.db")
    try:
        schema.ensure_schema(conn)
        days, _symbols = _seed_factor_panel(conn)

        first = backfill.backfill_factor_evaluations(conn, days[0], days[0], horizons=(5,))
        second = backfill.backfill_factor_evaluations(conn, days[0], days[0], horizons=(5,))

        assert first["evaluations_written"] == second["evaluations_written"] == 3
        assert conn.execute("SELECT COUNT(*) FROM alpha_factor_evaluations").fetchone()[0] == 3
        health = conn.execute(
            "SELECT factor_id,mean_ic,ic_std,icir_sat10ic,mean_rank_ic,"
            "sign_consistency,evaluation_count,sample_size,last_evaluation_date "
            "FROM alpha_factor_health ORDER BY factor_id"
        ).fetchall()
        assert len(health) == 3
        assert all(row["evaluation_count"] == 1 for row in health)
        assert all(row["sample_size"] == 8 for row in health)
        assert all(row["ic_std"] == 0.0 for row in health)
        assert all(row["icir_sat10ic"] is None for row in health)
        assert all(row["last_evaluation_date"] == days[0] for row in health)
        health_by_factor = {row["factor_id"]: row for row in health}
        assert math.isclose(health_by_factor["activity_footprint_score"]["mean_ic"], 1.0)
        assert math.isclose(health_by_factor["market_residual_20"]["mean_rank_ic"], 1.0)
        assert math.isclose(health_by_factor["momentum_zscore"]["mean_ic"], -1.0)
        assert {row["factor_id"]: row["sign_consistency"] for row in health} == {
            "activity_footprint_score": 1.0,
            "market_residual_20": 1.0,
            "momentum_zscore": 0.0,
        }
    finally:
        conn.close()


def test_backfill_registers_residual_momentum_only_when_values_exist(tmp_path):
    conn = db.init_db(tmp_path / "alpha-backfill.db")
    try:
        schema.ensure_schema(conn)
        days, symbols = _seed_factor_panel(conn)
        for index, symbol in enumerate(symbols):
            conn.execute(
                "UPDATE alpha_feature_snapshots SET sector_residual_20=?,momentum_percentile=? "
                "WHERE as_of_date=? AND symbol=?",
                (float(index), float(index), days[0], symbol),
            )
        conn.commit()

        backfill.backfill_factor_evaluations(conn, days[0], days[0], horizons=(5,))

        row = conn.execute(
            "SELECT pearson_ic,spearman_rank_ic FROM alpha_factor_evaluations "
            "WHERE factor_id='sector_residual_20'"
        ).fetchone()
        assert row is not None
        assert math.isclose(row["pearson_ic"], 1.0, abs_tol=1e-12)
        assert math.isclose(row["spearman_rank_ic"], 1.0, abs_tol=1e-12)
        registered = conn.execute(
            "SELECT factor_version FROM alpha_factor_evaluations "
            "WHERE factor_id='residual_momentum_20'"
        ).fetchone()
        assert registered["factor_version"] == "alpha_features_v1"
        assert conn.execute(
            "SELECT COUNT(*) FROM alpha_factor_evaluations "
            "WHERE factor_id='sector_residual_20'"
        ).fetchone()[0] == 1
    finally:
        conn.close()


def test_backfill_skips_dates_without_a_complete_strictly_future_horizon(tmp_path, capsys):
    conn = db.init_db(tmp_path / "alpha-backfill.db")
    try:
        schema.ensure_schema(conn)
        days, _symbols = _seed_factor_panel(conn)

        result = backfill.backfill_factor_evaluations(
            conn, days[1], days[5], horizons=(5,)
        )

        assert result["dates_skipped_insufficient_future"] == 5
        assert result["evaluations_written"] == 0
        assert "insufficient future data" in capsys.readouterr().out
    finally:
        conn.close()


def test_backfill_reuses_historical_delivery_z_without_future_delivery_rows(tmp_path):
    conn = db.init_db(tmp_path / "alpha-backfill.db")
    try:
        schema.ensure_schema(conn)
        days = [(date(2025, 10, 1) + timedelta(days=i)).isoformat() for i in range(26)]
        for index in range(8):
            symbol = f"D{index}"
            for session_index, day in enumerate(days):
                close = 100.0 + index if session_index == 25 else 100.0
                if session_index < 20:
                    delivery_pct = 50.0
                elif session_index == 20:
                    delivery_pct = 50.0 + index
                else:
                    # Reversed future observations must not enter day-20 z-scores.
                    delivery_pct = 500.0 - index
                conn.execute(
                    "INSERT INTO daily_prices "
                    "(symbol,trade_date,series,close,delivery_pct,source) "
                    "VALUES (?,?,'EQ',?,?,'bhavcopy')",
                    (symbol, day, close, delivery_pct),
                )
        conn.commit()

        backfill.backfill_factor_evaluations(conn, days[20], days[20], horizons=(5,))

        row = conn.execute(
            "SELECT factor_version,pearson_ic,spearman_rank_ic,universe_denominator "
            "FROM alpha_factor_evaluations WHERE factor_id='delivery_z'"
        ).fetchone()
        assert row["factor_version"] == "scanner_delivery_z_50_v1"
        assert math.isclose(row["pearson_ic"], 1.0, abs_tol=1e-12)
        assert math.isclose(row["spearman_rank_ic"], 1.0, abs_tol=1e-12)
        assert row["universe_denominator"] == 8
    finally:
        conn.close()


def test_alpha_backfill_cli_requires_dates_and_selects_handler():
    parser = build_parser()
    args = parser.parse_args(
        ["alpha-backfill", "--start", "2025-01-01", "--end", "2025-12-31"]
    )

    assert args.command == "alpha-backfill"
    assert args.start == "2025-01-01"
    assert args.end == "2025-12-31"
    assert args.func.__name__ == "_cmd_alpha_backfill"
