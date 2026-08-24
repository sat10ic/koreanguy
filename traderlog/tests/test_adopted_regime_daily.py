"""W4 — traderlog/adopted/regime_daily.py.

The orchestration layer: backfill() must process breadth_daily dates in
strict ascending order, populate every regime_daily column the schema has,
and report exactly which dates were chain-break reseed points -- this is the
end-to-end proof of the gap-handling decision recorded in
DECISIONS.md 2026-08-23 and design/handoffs/HANDOFF_W4_breadth_COMPLETED.md,
plus the percent-input convention (C6 retracted), observed-z reseed
seeding (C8), and the warm-up discard (C8 second half: the first
``warmup_sessions`` sessions run in memory and are not persisted) from the
2026-08-24 AUDIT_LEDGER.md addenda.
"""
from __future__ import annotations

from traderlog.adopted import regime_daily as rd
from traderlog.adopted.xp import compute_xp
from traderlog.db import init_db, now_iso


def _insert_breadth(
    conn, trade_date, *, up4=5.0, down4=2.0, p10=60.0, p20=55.0, p50=50.0, universe_size=None,
):
    conn.execute(
        "INSERT INTO breadth_daily (trade_date, up_4pct, down_4pct, pct_above_10dma, "
        "pct_above_20dma, pct_above_50dma, universe_size, ingested_at) VALUES (?,?,?,?,?,?,?,?)",
        (trade_date, up4, down4, p10, p20, p50, universe_size, now_iso()),
    )


def test_backfill_processes_ascending_and_populates_every_column(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(1, 6):
        _insert_breadth(conn, f"2025-01-{i:02d}", up4=4.0 + i, down4=2.0)
    conn.commit()

    # warmup_sessions=0 disables the warm-up discard: every row is persisted.
    result = rd.backfill(conn, warmup_sessions=0)
    assert result == {
        "dates": 5, "ok": 5, "skipped": 0, "warmup": 0,
        "failed": [], "reseed_points": ["2025-01-01"],
    }

    rows = conn.execute(
        "SELECT trade_date, xp_value, xp_z_state, xp_band, r10, r20, r50, r4p5, "
        "band_r10, band_r20, band_r50, band_r4p5, mbi_day_color, mbi_score, "
        "warning_day, source_date FROM regime_daily ORDER BY trade_date"
    ).fetchall()
    assert len(rows) == 5
    for row in rows:
        for col in row.keys():
            assert row[col] is not None, f"{col} is null on {row['trade_date']}"

    # XP values must differ day over day (real recursion happened, not a
    # constant placeholder).
    xps = [r["xp_value"] for r in rows]
    assert len(set(xps)) == 5


def test_backfill_detects_gap_break_and_marks_reseed_points(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-05-01")
    _insert_breadth(conn, "2025-05-02")
    _insert_breadth(conn, "2025-08-01")  # 91-day hole — the deliberate gap
    conn.commit()

    # warmup_sessions=0 so the gap mechanics are exercised directly.
    result = rd.backfill(conn, warmup_sessions=0)
    assert result["reseed_points"] == ["2025-05-01", "2025-08-01"]

    xp_by_date = {
        r["trade_date"]: r["xp_value"]
        for r in conn.execute("SELECT trade_date, xp_value FROM regime_daily").fetchall()
    }
    # 2025-08-01 must NOT equal what continuing the chain would have produced.
    day1_row = conn.execute(
        "SELECT xp_value, xp_z_state FROM regime_daily WHERE trade_date='2025-05-02'"
    ).fetchone()
    from traderlog.adopted.xp import compute_xp
    would_have_continued, _ = compute_xp(5.0, 2.0, 60.0, 55.0, day1_row["xp_value"], day1_row["xp_z_state"])
    assert xp_by_date["2025-08-01"] != would_have_continued


def test_backfill_is_idempotent(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(1, 4):
        _insert_breadth(conn, f"2025-01-{i:02d}")
    conn.commit()

    r1 = rd.backfill(conn, warmup_sessions=0)
    r2 = rd.backfill(conn, warmup_sessions=0)
    assert r1["ok"] == r2["ok"] == 3
    assert conn.execute("SELECT COUNT(*) FROM regime_daily").fetchone()[0] == 3
    # And the values are byte-identical on the second pass.
    rows1 = [dict(r) for r in conn.execute("SELECT * FROM regime_daily ORDER BY trade_date")]
    rd.backfill(conn, warmup_sessions=0)
    rows2 = [dict(r) for r in conn.execute("SELECT * FROM regime_daily ORDER BY trade_date")]
    for a, b in zip(rows1, rows2):
        a.pop("ingested_at", None)
        b.pop("ingested_at", None)
        assert a == b


def test_run_skips_date_with_no_breadth_daily_row(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    result = rd.run(conn, "2025-01-01")
    assert result["status"] == "skip"
    assert conn.execute("SELECT COUNT(*) FROM regime_daily").fetchone()[0] == 0


def test_compute_regime_row_recompute_is_deterministic(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-01-01")
    _insert_breadth(conn, "2025-01-02")
    conn.commit()
    rd.run(conn, "2025-01-01")

    a = rd.compute_regime_row(conn, "2025-01-02")
    b = rd.compute_regime_row(conn, "2025-01-02")
    assert a == b


def test_compute_regime_row_feeds_raw_percent_columns_to_xp(tmp_path):
    """C6 RETRACTED (design/AUDIT_LEDGER.md 2026-08-24): breadth_daily
    up_4pct/down_4pct are PERCENTAGES and must be fed to the XP recursion
    UNCONVERTED — the retracted C6 fix's percent->count conversion
    (percent * universe_size / 100) was a ~4x scale error. universe_size
    plays no role in the XP call. The reseed-day z-state seeds from the row's
    own observed up_4pct (C8), not the count-scale constant."""
    conn = init_db(tmp_path / "traderlog.db")
    # up4=1.0%, down4=0.5% of a 400-name universe: the old code would have
    # converted these to counts 4.0 / 2.0; the fixed code feeds 1.0 / 0.5 raw.
    _insert_breadth(conn, "2025-01-01", up4=1.0, down4=0.5, p10=60.0, p20=55.0, universe_size=400)
    conn.commit()

    row = rd.compute_regime_row(conn, "2025-01-01")
    assert row is not None

    # Day 1 always reseeds: xp_prev from xp_seed=15.0 (config default), z_prev
    # from the row's OWN observed up_4pct = 1.0 (percent scale).
    expected_xp, expected_z = compute_xp(1.0, 0.5, 60.0, 55.0, 15.0, 1.0)
    assert row["xp_value"] == expected_xp
    assert row["xp_z_state"] == expected_z

    # What the retracted C6 fix produced (count-fed recursion with the
    # count-scale z seed) must differ — this test is not a no-op.
    converted_xp, converted_z = compute_xp(4.0, 2.0, 60.0, 55.0, 15.0, 20.0)
    assert row["xp_value"] != converted_xp
    assert row["xp_z_state"] != converted_z


def test_compute_regime_row_universe_size_not_consulted_for_xp(tmp_path):
    """With the percent->count conversion removed (C6 retracted), universe_size
    no longer affects the XP recursion: a row without it computes identically
    to a row with it (raw percent columns + observed-z seeding)."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-01-01", up4=1.0, down4=0.5, p10=60.0, p20=55.0, universe_size=None)
    conn.commit()

    row = rd.compute_regime_row(conn, "2025-01-01")
    expected_xp, expected_z = compute_xp(1.0, 0.5, 60.0, 55.0, 15.0, 1.0)
    assert row["xp_value"] == expected_xp
    assert row["xp_z_state"] == expected_z


def test_run_fails_on_null_up4pct_row_without_fabricating(tmp_path):
    """Data honesty: a breadth_daily row with no observed up_4pct (NULL)
    cannot feed the recursion — the C8 observed-z seeding has no source value
    and feeding a missing advancer percent into compute_xp is refused. The
    date is recorded as failed (never raises, never persists, never
    fabricates a number)."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_breadth(conn, "2025-01-01", up4=None, down4=2.0)
    conn.commit()

    result = rd.run(conn, "2025-01-01")
    assert result["status"] == "fail"
    assert conn.execute("SELECT COUNT(*) FROM regime_daily").fetchone()[0] == 0


def test_backfill_warmup_discards_series_start_transient(tmp_path):
    """C8 regression (design/AUDIT_LEDGER.md 2026-08-24, second half): the
    series-start transient — the 2024-09 EXTREME/_XP_CAP cluster, driven by
    pct_above_20dma == 0.0 while the SMA20 lookback has no history at corpus
    start (logit(0) clamps to +~1.95 on the -0.077*logit(p20) term) — must be
    DISCARDED, not persisted. backfill's warm-up runs the first
    ``warmup_sessions`` sessions in memory (compute-and-skip): zero persisted
    rows before session 21, and the first persisted session derives its
    recursion base from the threaded in-memory chain, never a fresh reseed."""
    conn = init_db(tmp_path / "traderlog.db")
    # 30 sessions mirroring the REAL series start: up_4pct 0.86-10%,
    # pct_above_10dma == 0.0 for the first 9 sessions (no SMA10 history) then
    # 39-57, pct_above_20dma == 0.0 for the first 19 sessions (no SMA20
    # history) then 35-55 — the exact p20==0.0 startup artifact that snowballs
    # into the cap without warm-up.
    series = []
    for i in range(1, 31):
        up4 = round(0.86 + ((i - 1) % 10) * 1.0, 3)            # 0.86 .. 9.86 %
        down4 = round(0.25 + ((i - 1) % 4) * 0.5, 3)           # 0.25 .. 1.75 %
        p10 = 0.0 if i <= 9 else 39.0 + ((i - 10) % 19)        # 0.0 then 39..57
        p20 = 0.0 if i <= 19 else 35.0 + ((i - 20) % 21)       # 0.0 then 35..55
        series.append((up4, down4, p10, p20))
        _insert_breadth(conn, f"2024-09-{i:02d}", up4=up4, down4=down4, p10=p10, p20=p20)
    conn.commit()

    result = rd.backfill(conn, warmup_sessions=20)
    assert result["failed"] == []
    assert result["warmup"] == 20
    assert result["ok"] == 10
    assert result["reseed_points"] == []  # series start is discarded, not a persisted break

    # Zero persisted rows before session 21; persisted dates are 21..30 only.
    rows = conn.execute(
        "SELECT trade_date, xp_value, xp_z_state, xp_band FROM regime_daily ORDER BY trade_date"
    ).fetchall()
    assert [r["trade_date"] for r in rows] == [f"2024-09-{i:02d}" for i in range(21, 31)]

    # No cap hits, no EXTREME band anywhere in the PERSISTED series.
    for r in rows:
        assert r["xp_value"] < 250.0, (
            f"_XP_CAP hit on {r['trade_date']}: xp={r['xp_value']}"
        )
        assert r["xp_band"] != "EXTREME", (
            f"EXTREME band on {r['trade_date']}: xp={r['xp_value']}"
        )

    # Session 21 (= 2024-09-21) must derive from the THREADED chain, not a
    # fresh reseed: replicate the warm-up chain by hand — session 1 reseeds
    # from xp_seed=15.0 / z=observed up_4pct, sessions 2..21 thread.
    chain = compute_xp(series[0][0], series[0][1], series[0][2], series[0][3], 15.0, series[0][0])
    for i in range(1, 21):  # sessions 2..21
        up4, down4, p10, p20 = series[i]
        chain = compute_xp(up4, down4, p10, p20, chain[0], chain[1])
    s21 = rows[0]
    assert s21["trade_date"] == "2024-09-21"
    assert s21["xp_value"] == chain[0]
    assert s21["xp_z_state"] == chain[1]
    # And it is NOT a fresh reseed value (which would start from xp_seed=15.0
    # and that day's own observed z) — the chain through session 20 differs.
    fresh_reseed_xp, fresh_reseed_z = compute_xp(
        series[20][0], series[20][1], series[20][2], series[20][3], 15.0, series[20][0],
    )
    assert s21["xp_value"] != fresh_reseed_xp
    assert s21["xp_z_state"] != fresh_reseed_z
