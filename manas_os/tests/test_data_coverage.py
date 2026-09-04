import sqlite3

from manas_os.api import freshness_map


def test_coverage_marks_skipped_stale_source_red_with_exact_reason():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    for source in freshness_map.SOURCES:
        if source.table == "daily_prices":
            conn.execute("CREATE TABLE IF NOT EXISTS daily_prices (trade_date TEXT, series TEXT)")
        else:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {source.table} ({source.date_column} TEXT)")
    conn.executescript("""
      CREATE TABLE pipeline_runs (
        run_id INTEGER PRIMARY KEY, run_date TEXT, stage TEXT, status TEXT,
        detail TEXT, ran_at TEXT
      );
      CREATE TABLE jobs (job_id INTEGER, run_date TEXT);
      CREATE TABLE job_steps (
        step_id INTEGER, job_id INTEGER, name TEXT, status TEXT,
        error TEXT, detail TEXT, finished_at TEXT
      );
    """)
    for date in ("2026-07-14", "2026-07-15", "2026-07-16"):
        conn.execute("INSERT INTO daily_prices (trade_date,series) VALUES (?,'EQ')", (date,))
    conn.execute("INSERT INTO sector_metrics (snapshot_date) VALUES ('2026-07-14')")
    # Message text updated 2026-07-25: the old "chartsmaze folder missing: <path>"
    # wording was a misleading symptom -- the root actually existed with dated
    # subfolders present, only that one date's dump was absent. The corrected
    # message (chartsmaze.missing_folder_message) names the newest dump that
    # IS present instead of just the missing path. _action() now matches on
    # "no chartsmaze dump for" (see manas_os/api/freshness_map.py).
    reason = "no chartsmaze dump for 2026-07-16 (latest available: 2026-07-14)"
    conn.execute(
        "INSERT INTO pipeline_runs VALUES (1,'2026-07-16','ingest_chartsmaze','skip',?, '2026-07-16 18:00')",
        (reason,),
    )

    payload = freshness_map.coverage(conn)
    sector = next(row for row in payload["sources"] if row["key"] == "sectors")

    assert len(payload["sources"]) == len(freshness_map.SOURCES)
    assert sector["health"] == "red"
    assert sector["lag_sessions"] == 2
    assert sector["reason"] == reason
    assert sector["last_status"] == "skip"
    assert "Run the ChartsMaze extractor" in sector["what_to_do"]
    assert sector["auth_expired"] is False


def test_coverage_reports_auth_expired_for_chartsmaze_sources_when_login_expired():
    """A fetch_chartsmaze job_steps failure classified auth_expired must mark
    every ChartsMaze-tagged source (screeners/sectors/industries) as an
    actionable auth problem, not generic lag -- the bug this feature fixes:
    an expired scraper login used to render identically to any other stale
    source ("N sessions behind"), with no way to tell the two apart."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    for source in freshness_map.SOURCES:
        if source.table == "daily_prices":
            conn.execute("CREATE TABLE IF NOT EXISTS daily_prices (trade_date TEXT, series TEXT)")
        else:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {source.table} ({source.date_column} TEXT)")
    conn.executescript("""
      CREATE TABLE pipeline_runs (
        run_id INTEGER PRIMARY KEY, run_date TEXT, stage TEXT, status TEXT,
        detail TEXT, ran_at TEXT
      );
      CREATE TABLE jobs (job_id INTEGER PRIMARY KEY, run_date TEXT);
      CREATE TABLE job_steps (
        step_id INTEGER PRIMARY KEY, job_id INTEGER, name TEXT, status TEXT,
        error TEXT, detail TEXT, finished_at TEXT
      );
    """)
    for date in ("2026-07-19", "2026-07-20", "2026-07-21"):
        conn.execute("INSERT INTO daily_prices (trade_date,series) VALUES (?,'EQ')", (date,))
    conn.execute("INSERT INTO sector_metrics (snapshot_date) VALUES ('2026-07-16')")
    conn.execute("INSERT INTO jobs VALUES (1, '2026-07-21')")
    conn.execute(
        "INSERT INTO job_steps VALUES (1, 1, 'fetch_chartsmaze', 'fail', "
        "'reason_code=auth_expired Session invalid. Run python login.py and complete the OTP flow.', "
        "NULL, '2026-07-21 18:00')"
    )

    payload = freshness_map.coverage(conn)
    by_key = {row["key"]: row for row in payload["sources"]}

    for key in ("screeners", "sectors", "industries"):
        assert by_key[key]["auth_expired"] is True, key
        assert by_key[key]["health"] == "red", key
        assert "login.py" in by_key[key]["what_to_do"], key
        assert "expired" in by_key[key]["what_to_do"].lower(), key

    # Non-ChartsMaze sources are untouched by the ChartsMaze login state.
    assert by_key["prices"]["auth_expired"] is False
    assert by_key["deals"]["auth_expired"] is False
