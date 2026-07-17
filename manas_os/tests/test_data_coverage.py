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
    reason = "chartsmaze folder missing: legacy/SwingEdge/data/chartsmaze/2026-07-16"
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
