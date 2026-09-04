"""W4 — traderlog.checks.runner.check_derive.

check_derive is the W4-owned check (OWNER_WAVE["derive"] == "W4"). It must
stay honest about two independent things: XP recursion-chain integrity (a
hard fail, never fine to hide) and freshness relative to "now" (a distinct
stale_<n>d status, never silently widened to pass). See DECISIONS.md
2026-08-23 and the note in checks/runner.py's check_derive docstring.
"""
from __future__ import annotations

from datetime import datetime, timezone

from traderlog.checks.runner import NOT_BUILT, PASS, check_derive
from traderlog.db import init_db, now_iso


def _insert_breadth(conn, trade_date):
    conn.execute(
        "INSERT INTO breadth_daily (trade_date, up_4pct, down_4pct, pct_above_10dma, "
        "pct_above_20dma, pct_above_50dma, ingested_at) VALUES (?,5.0,2.0,60.0,55.0,50.0,?)",
        (trade_date, now_iso()),
    )


def _insert_regime(
    conn,
    trade_date,
    *,
    xp_value=10.0,
    xp_z_state=20.0,
    mbi_day_color="WHITE",
    mbi_score=0,
    warning_day=0,
):
    conn.execute(
        "INSERT INTO regime_daily "
        "(trade_date, xp_value, xp_z_state, mbi_day_color, mbi_score, warning_day, ingested_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (trade_date, xp_value, xp_z_state, mbi_day_color, mbi_score, warning_day, now_iso()),
    )


def test_not_built_when_no_breadth_at_all(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    result = check_derive(conn)
    assert result.status == NOT_BUILT
    conn.close()


def test_not_built_when_fewer_than_five_regime_rows(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(1, 4):
        _insert_breadth(conn, f"2026-08-{i:02d}")
        _insert_regime(conn, f"2026-08-{i:02d}")
    conn.commit()
    result = check_derive(conn)
    assert result.status == NOT_BUILT
    conn.close()


def test_fails_when_xp_chain_broken(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(1, 6):
        d = f"2026-08-{i:02d}"
        _insert_breadth(conn, d)
        _insert_regime(conn, d, xp_value=None if i == 3 else 10.0)
    conn.commit()
    result = check_derive(conn, now=datetime(2026, 8, 5, tzinfo=timezone.utc))
    assert result.status.startswith("fail")
    assert "2026-08-03" in result.status
    conn.close()


def test_pass_when_five_recent_and_fresh(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(1, 6):
        d = f"2026-08-{i:02d}"
        _insert_breadth(conn, d)
        _insert_regime(conn, d)
    conn.commit()
    # "now" is the same day as the latest session -> fresh.
    result = check_derive(conn, now=datetime(2026, 8, 5, 12, 0, tzinfo=timezone.utc))
    assert result.status == PASS
    conn.close()


def test_stale_when_latest_session_is_old_relative_to_now(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(1, 6):
        d = f"2026-03-{18 + i:02d}"
        _insert_breadth(conn, d)
        _insert_regime(conn, d)
    conn.commit()
    # "now" is 2026-08-23, latest session 2026-03-23 -> ~5 months stale.
    result = check_derive(conn, now=datetime(2026, 8, 23, tzinfo=timezone.utc))
    assert result.status.startswith("stale_")
    assert not result.status.startswith("fail")
    assert result.ok  # stale is honest, not a hard failure
    conn.close()


def test_stale_report_is_never_widened_to_pass_by_a_close_but_old_date(tmp_path):
    """A 6-day-old session must NOT read as pass just because it's close."""
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(1, 6):
        d = f"2026-08-{10 + i:02d}"
        _insert_breadth(conn, d)
        _insert_regime(conn, d)
    conn.commit()
    result = check_derive(conn, now=datetime(2026, 8, 21, tzinfo=timezone.utc))  # 6 days after 08-15
    assert result.status == "stale_6d"
    conn.close()


def test_fails_when_breadth_is_ahead_of_regime(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(1, 7):
        _insert_breadth(conn, f"2026-08-{i:02d}")
    for i in range(1, 6):
        _insert_regime(conn, f"2026-08-{i:02d}")
    conn.commit()

    result = check_derive(conn, now=datetime(2026, 8, 6, tzinfo=timezone.utc))

    assert result.status.startswith("fail")
    assert "breadth/regime coverage mismatch" in result.status
    conn.close()


def test_fails_when_recent_regime_row_lacks_a_required_mbi_field(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    for i in range(1, 6):
        d = f"2026-08-{i:02d}"
        _insert_breadth(conn, d)
        _insert_regime(conn, d, mbi_score=None if i == 4 else 0)
    conn.commit()

    result = check_derive(conn, now=datetime(2026, 8, 5, tzinfo=timezone.utc))

    assert result.status.startswith("fail")
    assert "mbi_score null on 2026-08-04" in result.status
    conn.close()
