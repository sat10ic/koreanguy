"""SETUP-REGIME factor: hand-checked hot/cold/neutral classification, the
n<20 shrinkage floor, the relative-not-absolute state rule (a uniformly
negative market must not read all-cold), the look-ahead guard (a scan_date
whose horizon has not yet closed must never influence the result), tilt
bounds, and persistence idempotency.
"""
from __future__ import annotations

from manas_os import db
from manas_os.scanner import setup_regime as sr

# 20 sequential dates -- plain calendar days are fine, the module only cares
# about lexical/session ORDER, not real trading-calendar gaps.
DATES = [f"2026-01-{d:02d}" for d in range(1, 21)]


def _seed_close(conn, symbol: str, trade_date: str, close: float) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO daily_prices (symbol, trade_date, series, close, source) "
        "VALUES (?, ?, 'EQ', ?, 'test')",
        (symbol, trade_date, close),
    )


def _seed_candidate(conn, scan_date: str, symbol: str, setup_type: str, setup_family: str | None = None) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO scan_candidates (scan_date, symbol, setup, setup_type, setup_family) "
        "VALUES (?, ?, ?, ?, ?)",
        (scan_date, symbol, setup_type, setup_type, setup_family),
    )


def _seed_family_cohort(
    conn, scan_date: str, setup_type: str, n: int, target_pct_h5: float, prefix: str,
) -> None:
    """n symbols on scan_date, setup_family left NULL (exercises the
    candidates.setup_family(setup_type) fallback path -- the read-only reuse
    of SETUP_FAMILY this module is required to exercise). Each symbol's
    close is 100.0 on scan_date, filler (unchanged, 100.0) on the next 3
    sessions, and exactly target_pct_h5 on the 5th session after scan_date
    -- so the H=5 forward return is hand-computable to the exact target,
    while H=2 (which reads the 2nd-after-scan_date close, still filler=100)
    reads a flat 0% for every symbol/family alike (not asserted on)."""
    idx = DATES.index(scan_date)
    d3, d4, d5, d6, d7 = DATES[idx + 1: idx + 6]
    target_close = round(100.0 * (1 + target_pct_h5 / 100.0), 6)
    for i in range(n):
        sym = f"{prefix}{i}"
        _seed_close(conn, sym, scan_date, 100.0)
        for d in (d3, d4, d5, d6):
            _seed_close(conn, sym, d, 100.0)
        _seed_close(conn, sym, d7, target_close)
        _seed_candidate(conn, scan_date, sym, setup_type, setup_family=None)


def test_hot_neutral_cold_relative_to_all_families_not_absolute(tmp_path):
    """3 families, ALL with a NEGATIVE absolute H=5 median return (-0.1%,
    -0.6%, -1.4%) -- yet the least-bad family (momentum, -0.1%) must still
    read HOT because state is relative to the pooled all-families median
    (-0.6%), never to zero. This directly proves a uniformly bad market
    cannot mark every family cold."""
    conn = db.init_db(tmp_path / "m.db")
    sr.ensure_schema(conn)  # ALTER-adds scan_candidates.setup_type/setup_family (candidates.ensure_schema)
    try:
        scan_date = DATES[2]
        # n=25 each, comfortably above FLOOR_N=20.
        _seed_family_cohort(conn, scan_date, "pocket_pivot", 25, -0.1, "MOM")   # -> momentum
        _seed_family_cohort(conn, scan_date, "pullback", 25, -0.6, "PBK")       # -> base/pattern
        _seed_family_cohort(conn, scan_date, "ep", 25, -1.4, "CAT")             # -> catalyst

        as_of = DATES[16]  # well past scan_date's H=5 close (DATES[7])
        rows = sr.compute(conn, as_of, windows=(5, 20, 60))

        def cell(family, window, horizon):
            return next(r for r in rows if r["family"] == family and r["window"] == window and r["horizon"] == horizon)

        mom = cell("momentum", 5, 5)
        pbk = cell("base/pattern", 5, 5)
        cat = cell("catalyst", 5, 5)

        assert mom["n"] == 25 and pbk["n"] == 25 and cat["n"] == 25
        assert abs(mom["median_fwd"] - (-0.1)) < 1e-6
        assert abs(pbk["median_fwd"] - (-0.6)) < 1e-6
        assert abs(cat["median_fwd"] - (-1.4)) < 1e-6
        # pooled all-families median over the 75 obs (25 x -1.4, 25 x -0.6,
        # 25 x -0.1) is the middle cluster: -0.6.
        assert abs(mom["all_median"] - (-0.6)) < 1e-6

        # All three medians are negative...
        assert mom["median_fwd"] < 0 and pbk["median_fwd"] < 0 and cat["median_fwd"] < 0
        # ...yet momentum (least negative, delta=+0.5pp >= MARGIN_PP) reads HOT.
        assert mom["state"] == "hot"
        assert mom["tilt"] > 1.0
        # base/pattern sits exactly on the pooled median (delta=0) -> neutral.
        assert pbk["state"] == "neutral"
        assert pbk["tilt"] == 1.0
        # catalyst (delta=-0.8pp <= -MARGIN_PP) reads COLD.
        assert cat["state"] == "cold"
        assert cat["tilt"] < 1.0

        # windows=20/60 fall back gracefully to the same single eligible
        # scan_date (there's only one in this fixture) -- identical result.
        assert cell("momentum", 20, 5)["n"] == 25
        assert cell("momentum", 60, 5)["median_fwd"] == mom["median_fwd"]

        # describe_family renders a real line, not a fabricated one.
        assert "HOT" in mom["line"] and "n=25" in mom["line"]
        assert "COLD" in cat["line"]
    finally:
        conn.close()


def test_n_floor_forces_neutral_no_tilt(tmp_path):
    """A family with n=10 (< FLOOR_N=20) whose RAW median (+5%) would read
    wildly hot vs baseline (0%) must be forced to 'neutral' with tilt
    exactly 1.0 -- thin samples carry NO tilt regardless of the numbers."""
    conn = db.init_db(tmp_path / "m.db")
    sr.ensure_schema(conn)  # ALTER-adds scan_candidates.setup_type/setup_family (candidates.ensure_schema)
    try:
        scan_date = DATES[2]
        _seed_family_cohort(conn, scan_date, "pocket_pivot", 10, 5.0, "THIN")   # momentum, n=10 < floor
        _seed_family_cohort(conn, scan_date, "pullback", 25, 0.0, "BASE")       # base/pattern, n=25, flat

        as_of = DATES[16]
        rows = sr.compute(conn, as_of, windows=(5,))
        mom = next(r for r in rows if r["family"] == "momentum" and r["horizon"] == 5)

        assert mom["n"] == 10
        assert mom["median_fwd"] == 5.0  # the raw number really is +5%...
        assert mom["state"] == "neutral"  # ...but the floor forces neutral
        assert mom["tilt"] == 1.0
    finally:
        conn.close()


def test_lookahead_guard_excludes_unresolved_scan_date(tmp_path):
    """A scan_date whose H=5 forward window has NOT yet closed strictly
    before as_of must be excluded from the cohort -- even when the future
    price data technically already exists in daily_prices (simulating a
    replay/backfill DB that has since-realized prices). This asserts BOTH
    the low-level eligibility list AND that compute()'s aggregate numbers
    are untouched by the excluded date's (extreme) return."""
    conn = db.init_db(tmp_path / "m.db")
    sr.ensure_schema(conn)  # ALTER-adds scan_candidates.setup_type/setup_family (candidates.ensure_schema)
    try:
        # Eligible scan_date: resolves well before as_of.
        eligible_date = DATES[2]
        _seed_family_cohort(conn, eligible_date, "pocket_pivot", 3, -0.1, "OK")

        # Unresolved scan_date: its H=5 close (index 14+5-1=18) lands AFTER
        # as_of (index 16) -- must be excluded even though we seed the
        # (extreme, +400%) future close so a bug that skips the date-cutoff
        # check would be caught by a wildly wrong median/n.
        unresolved_date = DATES[14]
        _seed_close(conn, "FUTURESHOCK", unresolved_date, 100.0)
        for d in DATES[15:18]:
            _seed_close(conn, "FUTURESHOCK", d, 100.0)
        _seed_close(conn, "FUTURESHOCK", DATES[18], 500.0)  # +400% if wrongly included
        _seed_candidate(conn, unresolved_date, "FUTURESHOCK", "pocket_pivot", setup_family=None)

        as_of = DATES[16]
        calendar = sr._trading_calendar(conn)
        eligible = sr._eligible_scan_dates(conn, as_of, horizon=5, calendar=calendar)
        assert eligible_date in eligible
        assert unresolved_date not in eligible

        rows = sr.compute(conn, as_of, windows=(5,))
        mom = next(r for r in rows if r["family"] == "momentum" and r["horizon"] == 5)
        assert mom["n"] == 3  # FUTURESHOCK must NOT be counted
        assert abs(mom["median_fwd"] - (-0.1)) < 1e-6  # not skewed toward +400%
    finally:
        conn.close()


def test_unavailable_family_renders_honest_line_no_fabrication(tmp_path):
    """A known family with zero candidates in the cohort still gets a row
    (comprehensive shape) but with an honest UNAVAILABLE line, never a
    fabricated number."""
    conn = db.init_db(tmp_path / "m.db")
    sr.ensure_schema(conn)  # ALTER-adds scan_candidates.setup_type/setup_family (candidates.ensure_schema)
    try:
        scan_date = DATES[2]
        _seed_family_cohort(conn, scan_date, "pocket_pivot", 25, 1.0, "MOM")
        as_of = DATES[16]
        rows = sr.compute(conn, as_of, windows=(5,))
        weekly = next(r for r in rows if r["family"] == "weekly_base_breakout" and r["horizon"] == 5)
        assert weekly["n"] == 0
        assert weekly["median_fwd"] is None
        assert "UNAVAILABLE" in weekly["line"]
        assert weekly["state"] == "neutral"
        assert weekly["tilt"] == 1.0
    finally:
        conn.close()


def test_tilt_bounds_single_and_blended(tmp_path):
    assert sr.tilt("hot") == sr.TILT_MAX
    assert sr.tilt("cold") == sr.TILT_MIN
    assert sr.tilt("neutral") == 1.0

    # All windows agreeing must not exceed the single-state extremes.
    all_hot = sr.tilt({5: "hot", 20: "hot", 60: "hot"}, sr.DEFAULT_WINDOW_WEIGHTS)
    all_cold = sr.tilt({5: "cold", 20: "cold", 60: "cold"}, sr.DEFAULT_WINDOW_WEIGHTS)
    assert all_hot == sr.TILT_MAX
    assert all_cold == sr.TILT_MIN

    mixed = sr.tilt({5: "hot", 20: "neutral", 60: "cold"}, sr.DEFAULT_WINDOW_WEIGHTS)
    assert abs(mixed - 0.97) < 1e-6

    # Exhaustive sweep: every combination of states across the 3 default
    # windows must stay within [TILT_MIN, TILT_MAX].
    states_options = ("hot", "neutral", "cold")
    for s5 in states_options:
        for s20 in states_options:
            for s60 in states_options:
                v = sr.tilt({5: s5, 20: s20, 60: s60}, sr.DEFAULT_WINDOW_WEIGHTS)
                assert sr.TILT_MIN - 1e-9 <= v <= sr.TILT_MAX + 1e-9


def test_persistence_idempotent_rerun(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    sr.ensure_schema(conn)  # ALTER-adds scan_candidates.setup_type/setup_family (candidates.ensure_schema)
    try:
        scan_date = DATES[2]
        _seed_family_cohort(conn, scan_date, "pocket_pivot", 25, 0.8, "MOM")
        _seed_family_cohort(conn, scan_date, "pullback", 25, -0.2, "PBK")

        run_date = DATES[16]
        res1 = sr.run(conn, run_date)
        assert res1["status"] in {"ok", "partial"}
        count1 = conn.execute(
            "SELECT COUNT(*) FROM setup_regime_daily WHERE as_of = ?", (run_date,)
        ).fetchone()[0]

        res2 = sr.run(conn, run_date)
        assert res2["status"] in {"ok", "partial"}
        count2 = conn.execute(
            "SELECT COUNT(*) FROM setup_regime_daily WHERE as_of = ?", (run_date,)
        ).fetchone()[0]

        assert count1 == count2 == res2["rows"]
        # exactly one row per (family, window, horizon) cell -- no dupes.
        distinct = conn.execute(
            "SELECT COUNT(DISTINCT family || '|' || window || '|' || horizon) "
            "FROM setup_regime_daily WHERE as_of = ?", (run_date,)
        ).fetchone()[0]
        assert distinct == count2
    finally:
        conn.close()


def test_run_skips_when_no_scan_candidates(tmp_path):
    conn = db.init_db(tmp_path / "m.db")
    sr.ensure_schema(conn)  # ALTER-adds scan_candidates.setup_type/setup_family (candidates.ensure_schema)
    try:
        res = sr.run(conn, DATES[16])
        assert res["status"] == "skip"
        assert res["rows"] == 0
    finally:
        conn.close()
