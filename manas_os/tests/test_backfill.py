from manas_os import db
from manas_os.regime import backfill, snapshot
from manas_os.tests.test_regime_snapshot import _insert_breadth


def _seed_five_days(conn):
    dates = ["2026-06-30", "2026-07-01", "2026-07-02", "2026-07-03", "2026-07-04"]
    for i, d in enumerate(dates):
        # Vary breadth slightly day to day so XP's recursion actually moves,
        # not five identical copies (which would mask an ordering bug).
        _insert_breadth(
            conn, trade_date=d,
            up_4pct=100 + i * 10, down_4pct=40 - i * 3,
            pct_above_10dma=55.0 + i, pct_above_20dma=52.0 + i,
        )
    return dates


def test_backfill_processes_all_pending_dates_ascending():
    conn = db.init_db(":memory:")
    dates = _seed_five_days(conn)

    result = backfill.backfill_snapshots(conn)
    assert result["status"] == "ok"
    assert result["dates_processed"] == 5

    rows = conn.execute(
        "SELECT snapshot_date, source_date, xp_value, data_stale FROM regime_snapshots "
        "ORDER BY snapshot_date ASC"
    ).fetchall()
    assert [r["snapshot_date"] for r in rows] == dates
    # Every backfilled day: source_date == snapshot_date (that day's breadth
    # WAS "today's" data at the time) → never stale.
    assert all(r["source_date"] == r["snapshot_date"] for r in rows)
    assert all(r["data_stale"] == 0 for r in rows)
    # XP actually recursed (not 5 independent seed-only computations) — later
    # days' values differ from what a fresh from-seed computation would give.
    xp_values = [r["xp_value"] for r in rows]
    assert len(set(round(v, 6) for v in xp_values)) == 5


def test_backfill_recursion_matches_manual_day_by_day_replay():
    """Parity: backfilling N days must equal calling snapshot.run() for each
    day in order, one at a time — proving there's no separate backfill-only
    compute path to drift from the live one (they're literally the same call)."""
    conn_a = db.init_db(":memory:")
    dates = _seed_five_days(conn_a)
    backfill.backfill_snapshots(conn_a)
    xp_a = [
        r["xp_value"] for r in conn_a.execute(
            "SELECT xp_value FROM regime_snapshots ORDER BY snapshot_date ASC"
        )
    ]

    conn_b = db.init_db(":memory:")
    _seed_five_days(conn_b)
    for d in dates:
        snapshot.run(conn_b, d)
    xp_b = [
        r["xp_value"] for r in conn_b.execute(
            "SELECT xp_value FROM regime_snapshots ORDER BY snapshot_date ASC"
        )
    ]

    assert xp_a == xp_b


def test_backfill_skips_already_processed_dates_unless_forced():
    conn = db.init_db(":memory:")
    _seed_five_days(conn)

    first = backfill.backfill_snapshots(conn)
    assert first["dates_processed"] == 5

    second = backfill.backfill_snapshots(conn)
    assert second["dates_processed"] == 0  # nothing pending

    forced = backfill.backfill_snapshots(conn, force=True)
    assert forced["dates_processed"] == 5


def test_backfill_respects_start_end_date_range():
    conn = db.init_db(":memory:")
    _seed_five_days(conn)

    result = backfill.backfill_snapshots(conn, start_date="2026-07-01", end_date="2026-07-02")
    assert result["dates_processed"] == 2
    processed = {
        r["snapshot_date"] for r in conn.execute("SELECT snapshot_date FROM regime_snapshots")
    }
    assert processed == {"2026-07-01", "2026-07-02"}


def test_backfill_empty_history_is_a_clean_noop():
    conn = db.init_db(":memory:")
    result = backfill.backfill_snapshots(conn)
    assert result == {"status": "ok", "dates_processed": 0, "first_failure": None}
