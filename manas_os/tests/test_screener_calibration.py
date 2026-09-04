"""SHIP-1 #8: screener-hit forward-return calibration -- hand-checked excess
return math + n-floor suppression."""
from __future__ import annotations

from manas_os import db
from manas_os.ml import screener_calibration as sc


def _seed_price(conn, symbol, trade_date, open_, close):
    conn.execute(
        "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, open, close, source) "
        "VALUES (?, ?, 'EQ', ?, ?, 'test')",
        (symbol, trade_date, open_, close),
    )


def _seed_hit(conn, trade_date, symbol, screener):
    conn.execute(
        "INSERT OR REPLACE INTO screener_hits (trade_date, symbol, screener) VALUES (?, ?, ?)",
        (trade_date, symbol, screener),
    )


DATES = ["2026-01-0" + str(d) for d in range(1, 9)]  # 8 trading sessions


def _seed_ramp(conn, symbol, start, pct_per_day):
    """Seed a daily open/close ramp so forward returns are hand-computable."""
    price = start
    for d in DATES:
        o = price
        c = round(price * (1 + pct_per_day), 4)
        _seed_price(conn, symbol, d, o, c)
        price = c


def test_hand_checked_excess_return(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        # Screener "WINNER" hits HITSYM on day 1 (index 0). It rallies +1%/day.
        # Baseline symbol BASE rallies +0.2%/day (flat-ish universe).
        _seed_ramp(conn, "HITSYM", 100.0, 0.01)
        _seed_ramp(conn, "BASE", 100.0, 0.002)
        _seed_hit(conn, DATES[0], "HITSYM", "WINNER")

        rows = sc.compute(conn, "2026-02-01")
        # horizon=5 cell for WINNER
        cell = next(r for r in rows if r["screener"] == "WINNER" and r["horizon"] == 5)
        assert cell["n"] == 1

        # Hand-check: entry = next session's open after DATES[0] = day2 open.
        entry = 100.0 * (1.01) ** 1  # day2 open == day1 close
        # T+5 close = close of the 5th session strictly after DATES[0] = day6 close
        exit_close = 100.0 * (1.01) ** 6
        expected_screener_pct = round((exit_close - entry) / entry * 100.0, 6)

        # Baseline: BOTH EQ symbols on DATES[0] (HITSYM + BASE) are within the
        # stride-sample cap, so the baseline pool includes the screener hit
        # itself -- a deliberate simplification (the baseline is a random
        # universe sample, not "universe minus today's hits").
        base_entry = 100.0 * (1.002) ** 1
        base_exit = 100.0 * (1.002) ** 6
        base_pct = round((base_exit - base_entry) / base_entry * 100.0, 6)
        expected_baseline_pct = (expected_screener_pct + base_pct) / 2.0

        expected_excess = round(expected_screener_pct - expected_baseline_pct, 3)
        assert abs(cell["avg_excess_pct"] - expected_excess) < 0.01
        assert cell["win_rate"] == 1.0
    finally:
        conn.close()


def test_n_floor_suppression_flagged(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed_ramp(conn, "BASE", 100.0, 0.001)
        # Only 5 hits -- well below TRUST_FLOOR_N (30).
        for i in range(5):
            sym = f"THIN{i}"
            _seed_ramp(conn, sym, 100.0, 0.005)
            _seed_hit(conn, DATES[0], sym, "THIN_SCREENER")

        res = sc.run(conn, "2026-02-01")
        assert res["status"] == "ok"
        ranked = sc.latest_ranked(conn, horizon=5)
        row = next(r for r in ranked if r["screener"] == "THIN_SCREENER")
        assert row["n"] == 5
        assert row["unproven"] is True
    finally:
        conn.close()


def test_idempotent_rerun_same_as_of(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed_ramp(conn, "BASE", 100.0, 0.001)
        _seed_ramp(conn, "HITSYM", 100.0, 0.01)
        _seed_hit(conn, DATES[0], "HITSYM", "WINNER")

        res1 = sc.run(conn, "2026-02-01")
        res2 = sc.run(conn, "2026-02-01")
        assert res1["status"] == "ok" and res2["status"] == "ok"
        count = conn.execute(
            "SELECT COUNT(*) FROM screener_calibration WHERE as_of = '2026-02-01'"
        ).fetchone()[0]
        assert count == res2["rows"]  # no duplicate rows from the rerun
    finally:
        conn.close()


def test_pending_hits_without_full_window_excluded(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _seed_ramp(conn, "BASE", 100.0, 0.001)
        # Hit on the LAST available date -- no horizon window exists yet.
        _seed_price(conn, "FRESH", DATES[-1], 100.0, 101.0)
        _seed_hit(conn, DATES[-1], "FRESH", "NEWSCREEN")
        rows = sc.compute(conn, "2026-02-01")
        assert not any(r["screener"] == "NEWSCREEN" for r in rows)
    finally:
        conn.close()
