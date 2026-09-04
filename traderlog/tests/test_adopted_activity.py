"""W5 — traderlog/adopted/activity.py + activity_pipeline.py (Reactor Scale).

End-to-end proof of the volume reverse-engineering adoption recorded in
DECISIONS.md 2026-08-22 and TASKS.md W5: the adopted formula's q_ratio/d_ratio/
activity_score against hand math, the warm-up rule (a symbol/date with fewer
than 20 PRIOR sessions is skipped — never half-baked ratios), idempotent
re-runs, the formula_version stamp, the empty-symbol guard, the ported
universe gates (ETF-name heuristic, price floor, turnover floor,
circuit-lock), and the pipeline_runs logging.
"""
from __future__ import annotations

from traderlog.adopted import activity
from traderlog.adopted import activity_pipeline as ap
from traderlog.db import init_db, now_iso

# Formula constants (frozen, from manas_os/alpha/activity.py V2 calibration).
Q = 1.165335
D = 1.04631
I = 1.152161
E = 0.84
INTERCEPT = -0.213928

FORMULA_VERSION = "reactor-v1-adapted-20260825"


def _insert_eq(
    conn, symbol, trade_date, *, volume, num_trades, delivery_pct,
    close=500.0, high=501.0, low=499.0, series="EQ", open_=500.5,
):
    """One daily_prices row (bhavcopy-shaped). Default close=500/vol=200000
    gives avg turnover = 500*200000/1e7 = 10cr — comfortably above the 2cr
    floor, price >= 30, high>low — gates pass."""
    conn.execute(
        "INSERT INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, prev_close, volume, "
        "turnover, num_trades, delivery_pct, source, ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (symbol, trade_date, series, open_, high, low, close, close, volume,
         1, num_trades, delivery_pct, "test", now_iso()),
    )


def _insert_run(conn, symbol, n_sessions, *, volume=200000, num_trades=100,
                delivery_pct=50.0, close=500.0, start="2025-01-01"):
    """n_sessions identical sessions starting at ``start`` (one per calendar day)."""
    from datetime import date, timedelta
    base = date.fromisoformat(start)
    for i in range(n_sessions):
        _insert_eq(
            conn, symbol, (base + timedelta(days=i)).isoformat(),
            volume=volume, num_trades=num_trades, delivery_pct=delivery_pct,
            close=close,
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Pure scoring core — hand math
# ---------------------------------------------------------------------------

def test_session_signal_hand_math(tmp_path):
    """Pure core: q_ratio/d_ratio/activity_score match hand-computed values.

    Prior 20 sessions: volume=200000, num_trades=100 -> avg trade qty 2000,
    delivery 50. Today: volume=400000 -> avg qty 4000, delivery 75.
    q_ratio = 4000/2000 = 2.0; d_ratio = 75/50 = 1.5.
    score = Q*2 + D*1.5 + I*(2*1.5)^E + intercept, rounded to 2 dp.
    """
    signal = activity.session_signal(
        "ABC", "2025-01-21",
        volume=400000, num_trades=100, delivery_pct=75.0,
        prior_avg_qtys=[2000.0] * 20,
        prior_delivery_pcts=[50.0] * 19,
    )
    assert signal is not None
    assert signal["avg_trade_qty"] == 4000.0
    assert signal["q_ratio"] == 2.0
    assert signal["d_ratio"] == 1.5

    expected_raw = Q * 2.0 + D * 1.5 + I * ((2.0 * 1.5) ** E) + INTERCEPT
    assert signal["raw_score"] == expected_raw
    assert signal["activity_score"] == round(expected_raw, 2)


def test_session_signal_baseline_constant_series_scores_3_15(tmp_path):
    """q=d=1 (constant series): score = Q + D + I + intercept = 3.149878."""
    signal = activity.session_signal(
        "ABC", "2025-01-21",
        volume=2000, num_trades=100, delivery_pct=50.0,
        prior_avg_qtys=[20.0] * 20,
        prior_delivery_pcts=[50.0] * 19,
    )
    assert signal is not None
    assert signal["q_ratio"] == 1.0
    assert signal["d_ratio"] == 1.0
    assert signal["activity_score"] == 3.15  # round(Q + D + I + intercept, 2)


def test_session_signal_warmup_and_guard_refusals(tmp_path):
    """<20 prior sessions -> None; non-positive denominator -> None (never a
    fabricated ratio)."""
    assert activity.session_signal(
        "ABC", "2025-01-21", volume=2000, num_trades=100, delivery_pct=50.0,
        prior_avg_qtys=[20.0] * 19,   # only 19 prior
        prior_delivery_pcts=[50.0] * 19,
    ) is None
    assert activity.session_signal(
        "ABC", "2025-01-21", volume=2000, num_trades=100, delivery_pct=50.0,
        prior_avg_qtys=[0.0] * 20,    # prior-20 mean is 0 -> refused
        prior_delivery_pcts=[50.0] * 19,
    ) is None
    assert activity.session_signal(
        "ABC", "2025-01-21", volume=0, num_trades=100, delivery_pct=50.0,
        prior_avg_qtys=[20.0] * 20, prior_delivery_pcts=[50.0] * 19,
    ) is None


def test_universe_verdict_ported_gates(tmp_path):
    """Ported universe_filter logic: price floor, turnover floor, ETF heuristic,
    circuit-lock; market cap skipped-not-passed."""
    def bars(n, close=500.0, volume=200000, flat=False):
        out = []
        for i in range(n):
            out.append({
                "trade_date": f"2025-01-{i+1:02d}",
                "open": close, "high": close if flat else close + 1.0,
                "low": close if flat else close - 1.0, "close": close,
                "volume": volume,
            })
        return out

    ok = activity.universe_verdict(bars(20), "GOOD")
    assert ok["tradeable"] is True
    assert ok["metrics"]["mcap_check"] == "skipped: mcap unavailable"

    cheap = activity.universe_verdict(bars(20, close=25.0), "CHEAP")
    assert cheap["tradeable"] is False
    assert any("price" in r for r in cheap["reasons_failed"])

    thin = activity.universe_verdict(bars(20, volume=1000), "THIN")
    assert thin["tradeable"] is False
    assert any("turnover" in r for r in thin["reasons_failed"])

    etf = activity.universe_verdict(bars(20), "NIFTYBEES")
    assert etf["tradeable"] is False
    assert any("ETF" in r for r in etf["reasons_failed"])
    assert activity.is_probable_etf("GOLDBEES") is True
    assert activity.is_probable_etf("RELIANCE") is False

    locked = activity.universe_verdict(bars(5, flat=True), "LOCK")
    assert locked["tradeable"] is False
    assert any("circuit" in r for r in locked["reasons_failed"])


# ---------------------------------------------------------------------------
# Pipeline — end to end on disposable DBs
# ---------------------------------------------------------------------------

def test_backfill_happy_path_hand_math(tmp_path):
    """21 sessions: 20 identical prior (avg qty 2000, delivery 50) then a
    doubled-volume / 1.5x-delivery day. Exactly one signal, values as hand
    math above; 20 warm-up skips."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_run(conn, "ABC", 20)
    _insert_eq(conn, "ABC", "2025-01-21", volume=400000, num_trades=100,
               delivery_pct=75.0)
    conn.commit()

    result = ap.backfill(conn)
    assert result["status"] == "ok"
    assert result["rows"] == 1
    assert result["dates"] == 1
    assert result["symbols"] == 1
    assert result["symbols_with_signals"] == 1
    assert result["warmup_skipped"] == 20
    assert result["excluded_universe"] == 0
    assert result["guards_skipped"] == 0
    assert result["date_first"] == result["date_last"] == "2025-01-21"

    row = conn.execute(
        "SELECT * FROM alpha_activity_signals WHERE symbol='ABC'"
    ).fetchone()
    assert row["q_ratio"] == 2.0
    assert row["d_ratio"] == 1.5
    expected_raw = Q * 2.0 + D * 1.5 + I * ((2.0 * 1.5) ** E) + INTERCEPT
    assert row["activity_score"] == round(expected_raw, 2)
    assert row["formula_version"] == FORMULA_VERSION

    logged = conn.execute(
        "SELECT stage, status, rows FROM pipeline_runs WHERE stage=?",
        (ap.STAGE,),
    ).fetchall()
    assert len(logged) == 1
    assert logged[0]["status"] == "ok"
    assert logged[0]["rows"] == 1
    conn.close()


def test_backfill_warmup_skips_under_20_prior_sessions(tmp_path):
    """XP/C8 warm-up lesson: a symbol with exactly 20 sessions writes NOTHING
    (its latest session has only 19 prior); a 25-session symbol writes exactly
    sessions 21..25 (5 signals)."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_run(conn, "FEW", 20)
    _insert_run(conn, "WARM", 25, start="2025-02-01")
    conn.commit()

    result = ap.backfill(conn)
    assert result["rows"] == 5
    assert result["warmup_skipped"] == 40  # 20 for FEW + 20 for WARM

    few = conn.execute(
        "SELECT COUNT(*) n FROM alpha_activity_signals WHERE symbol='FEW'"
    ).fetchone()["n"]
    assert few == 0

    dates = [r["trade_date"] for r in conn.execute(
        "SELECT trade_date FROM alpha_activity_signals WHERE symbol='WARM' ORDER BY trade_date"
    ).fetchall()]
    assert dates == ["2025-02-21", "2025-02-22", "2025-02-23", "2025-02-24", "2025-02-25"]
    conn.close()


def test_backfill_idempotent_rerun(tmp_path):
    """Re-running writes the same content (ingested_at aside) and never
    duplicates; one pipeline_runs row per run."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_run(conn, "WARM", 25)
    conn.commit()

    r1 = ap.backfill(conn)
    r2 = ap.backfill(conn)
    assert r1["rows"] == r2["rows"] == 5
    assert conn.execute("SELECT COUNT(*) FROM alpha_activity_signals").fetchone()[0] == 5

    rows1 = [dict(r) for r in conn.execute(
        "SELECT symbol, trade_date, q_ratio, d_ratio, activity_score, formula_version "
        "FROM alpha_activity_signals ORDER BY trade_date"
    ).fetchall()]
    ap.backfill(conn)
    rows2 = [dict(r) for r in conn.execute(
        "SELECT symbol, trade_date, q_ratio, d_ratio, activity_score, formula_version "
        "FROM alpha_activity_signals ORDER BY trade_date"
    ).fetchall()]
    assert rows1 == rows2

    runs = conn.execute(
        "SELECT status FROM pipeline_runs WHERE stage=?", (ap.STAGE,)
    ).fetchall()
    assert [r["status"] for r in runs] == ["ok", "ok", "ok"]
    conn.close()


def test_backfill_formula_version_stamped(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_run(conn, "WARM", 25)
    conn.commit()
    ap.backfill(conn)
    versions = [r[0] for r in conn.execute(
        "SELECT DISTINCT formula_version FROM alpha_activity_signals"
    ).fetchall()]
    assert versions == [FORMULA_VERSION]
    conn.close()


def test_backfill_empty_universe_guard(tmp_path):
    """No EQ symbols -> graceful skip, nothing written, pipeline_runs logged."""
    conn = init_db(tmp_path / "traderlog.db")
    result = ap.backfill(conn)
    assert result["status"] == "skip"
    assert result["symbols"] == 0
    assert result["rows"] == 0
    assert conn.execute("SELECT COUNT(*) FROM alpha_activity_signals").fetchone()[0] == 0
    logged = conn.execute(
        "SELECT status FROM pipeline_runs WHERE stage=?", (ap.STAGE,)
    ).fetchone()
    assert logged["status"] == "skip"
    conn.close()


def test_backfill_invalid_sessions_not_scored_not_counted(tmp_path):
    """A num_trades=0 session is not a usable session: not scored, and not
    counted toward the 20-prior warm-up. 25 sessions with #10 invalid leaves
    24 valid; signals start at the 21st valid session -> 4 rows."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_run(conn, "MIX", 25)
    conn.execute(
        "UPDATE daily_prices SET num_trades=0 WHERE symbol='MIX' AND trade_date='2025-01-10'"
    )
    conn.commit()

    result = ap.backfill(conn)
    assert result["invalid_sessions"] == 1
    assert result["rows"] == 4
    dates = [r["trade_date"] for r in conn.execute(
        "SELECT trade_date FROM alpha_activity_signals WHERE symbol='MIX' ORDER BY trade_date"
    ).fetchall()]
    assert dates == ["2025-01-22", "2025-01-23", "2025-01-24", "2025-01-25"]
    conn.close()


def test_backfill_universe_gates_exclude_etf_price_turnover_circuit(tmp_path):
    """Ported universe gates restrict signals: ETF-name heuristic, sub-30 price,
    sub-2cr turnover, and circuit-locked stretches write nothing."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_run(conn, "GOOD", 25)                 # passes gates -> 5 signals
    _insert_run(conn, "NIFTYBEES", 25, start="2025-03-01")   # ETF name
    _insert_run(conn, "CHEAP", 25, start="2025-04-01", close=25.0)   # price < 30
    _insert_run(conn, "THIN", 25, start="2025-05-01", volume=1000)   # 0.05cr < 2cr
    # Circuit lock: flat (high==low) on the last 5 sessions only.
    _insert_run(conn, "LOCK", 20, start="2025-06-01")
    for i in range(21, 26):
        _insert_eq(conn, "LOCK", f"2025-06-{i:02d}", volume=200000,
                   num_trades=100, delivery_pct=50.0, high=500.0, low=500.0)
    conn.commit()

    result = ap.backfill(conn)
    assert result["rows"] == 5  # GOOD only
    assert result["symbols_with_signals"] == 1
    # Exclusions: NIFTYBEES 25 + CHEAP 25 + THIN 25 + LOCK 5 (flat date and its
    # 4 predecessors are judged on windows containing flat bars)
    assert result["excluded_universe"] == 80
    by_symbol = {
        r[0]: r[1] for r in conn.execute(
            "SELECT symbol, COUNT(*) FROM alpha_activity_signals GROUP BY symbol"
        ).fetchall()
    }
    assert by_symbol == {"GOOD": 5}
    conn.close()


def test_backfill_guard_refuses_zero_delivery_denominator(tmp_path):
    """A constant delivery_pct=0 series: the prior-19 mean is 0, so the ratio
    is refused (guards_skipped), never persisted as division-by-zero."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_run(conn, "NODEL", 21, delivery_pct=0.0)
    conn.commit()

    result = ap.backfill(conn)
    assert result["warmup_skipped"] == 20
    assert result["guards_skipped"] == 1
    assert result["rows"] == 0
    assert conn.execute("SELECT COUNT(*) FROM alpha_activity_signals").fetchone()[0] == 0
    conn.close()


def test_distribution_reports(tmp_path):
    """distribution() returns the reported shape with min/median/max and
    abnormal/extreme counts at the adopted thresholds."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_run(conn, "ABC", 20)
    _insert_eq(conn, "ABC", "2025-01-21", volume=400000, num_trades=100,
               delivery_pct=75.0)
    conn.commit()
    ap.backfill(conn)

    dist = ap.distribution(conn)
    assert dist["rows"] == 1
    assert dist["symbols"] == 1
    assert dist["dates"] == 1
    assert dist["date_first"] == dist["date_last"] == "2025-01-21"
    expected_raw = Q * 2.0 + D * 1.5 + I * ((2.0 * 1.5) ** E) + INTERCEPT
    assert dist["score_min"] == dist["score_max"] == dist["score_median"] == round(expected_raw, 2)
    assert dist["abnormal"] == 1      # ~6.59 >= 3.5
    assert dist["extreme"] == 0       # ~6.59 < 8.0
    assert dist["formula_version"] == FORMULA_VERSION
    conn.close()