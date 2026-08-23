"""W4 — traderlog/adopted/regime_daily.py.

The orchestration layer: backfill() must process breadth_daily dates in
strict ascending order, populate every regime_daily column the schema has,
and report exactly which dates were chain-break reseed points -- this is the
end-to-end proof of the gap-handling decision recorded in
DECISIONS.md 2026-08-23 and design/handoffs/HANDOFF_W4_breadth_COMPLETED.md.
"""
from __future__ import annotations

from traderlog.adopted import regime_daily as rd
from traderlog.db import init_db, now_iso


def _insert_breadth(conn, trade_date, *, up4=5.0, down4=2.0, p10=60.0, p20=55.0, p50=50.0):
    conn.execute(
        "INSERT INTO breadth_daily (trade_date, up_4pct, down_4pct, pct_above_10dma, "
        "pct_above_20dma, pct_above_50dma, ingested_at) VALUES (?,?,?,?,?,?,?)",
        (trade_date, up4, down4, p10, p20, p50, now_iso()),
    )


def test_backfill_processes_ascending_and_populates_every_column(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(1, 6):
        _insert_breadth(conn, f"2025-01-{i:02d}", up4=4.0 + i, down4=2.0)
    conn.commit()

    result = rd.backfill(conn)
    assert result == {"dates": 5, "ok": 5, "skipped": 0, "failed": [], "reseed_points": ["2025-01-01"]}

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

    result = rd.backfill(conn)
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

    r1 = rd.backfill(conn)
    r2 = rd.backfill(conn)
    assert r1["ok"] == r2["ok"] == 3
    assert conn.execute("SELECT COUNT(*) FROM regime_daily").fetchone()[0] == 3
    # And the values are byte-identical on the second pass.
    rows1 = [dict(r) for r in conn.execute("SELECT * FROM regime_daily ORDER BY trade_date")]
    rd.backfill(conn)
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
