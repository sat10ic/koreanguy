"""Tests for the ChartsMaze reader + freshness run + history migration."""
from pathlib import Path

import pytest

from manas_os import db
from manas_os.sources import chartsmaze, chartsmaze_migrate

_REAL_DATE = "2026-07-04"
# The real ChartsMaze history still lives in the legacy tree (migration is a
# separate manual step). Point the readers there so we exercise real files.
_LEGACY_CM = (Path(__file__).resolve().parents[2] / "legacy" / "SwingEdge"
              / "data" / "chartsmaze").resolve()
_REAL_FOLDER = _LEGACY_CM / _REAL_DATE


@pytest.fixture
def legacy_cm(monkeypatch):
    """Repoint chartsmaze_dir() at the real legacy history for this test."""
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: _LEGACY_CM)


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_read_market_breadth(legacy_cm):
    df = chartsmaze.read_market_breadth(_REAL_DATE)
    assert not df.empty
    # First column is the metric label (transposed layout); BOM stripped.
    assert df.columns[0] == "Type of Info"


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_read_sector_analytics(legacy_cm):
    df = chartsmaze.read_sector_analytics(_REAL_DATE, "Relative Strength", "sectors")
    assert list(df.columns) == ["name", "pct"]
    assert not df.empty


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_run_records_freshness(legacy_cm, tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        count = chartsmaze.run(conn, _REAL_DATE)
        assert count > 0
        row = conn.execute(
            "SELECT status, rows_affected FROM pipeline_runs "
            "WHERE stage='ingest_chartsmaze'"
        ).fetchone()
        assert row[0] == "ok"
        assert row[1] == count
    finally:
        conn.close()


# ── parse_industry_analytics — pure parser ──────────────────────────────────
# Synthetic CSV echoing the real industry-analytics shape (BOM, % suffixes,
# messy spacing). Verifies BOM strip, substring header match, typing.
_INDUSTRY_CSV = (
    "\ufeffBasic Industry,Industry 1D Performance(%),Industry 1W Performance(%),"
    "Industry 1M Performance(%),Industry 3M Performance(%),"
    "Industry 1M Performance Rank,Industry 3M Performance Rank,"
    "Number of Stocks,Group Market Cap,Industry % from 52W High\n"
    "Investment Banking & Broking,0.40,2.37,6.31,15.84,44,51,42,454000,9.8\n"
    "Electrical - Power Equipment,-3.92,-4.66,-3.96,19.55,101,39,70,1227695,9.7\n"
    ",x,y,z\n"  # blank name → skipped
)


def test_parse_industry_analytics_pure():
    rows = chartsmaze.parse_industry_analytics(_INDUSTRY_CSV)
    assert len(rows) == 2  # blank-name row skipped
    first = rows[0]
    assert first["name"] == "Investment Banking & Broking"
    assert first["perf_1d"] == 0.4
    assert first["perf_1m"] == 6.31
    assert first["rank_3m"] == 51
    assert first["num_stocks"] == 42
    assert first["market_cap_cr"] == 454000.0
    assert first["pct_from_52w_high"] == 9.8
    # negative perf parses with sign intact
    assert rows[1]["perf_1d"] == -3.92


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_read_industry_analytics_real(legacy_cm):
    df = chartsmaze.read_industry_analytics(_REAL_DATE)
    assert not df.empty
    assert {"name", "perf_1m", "perf_3m", "num_stocks"} <= set(df.columns)
    # Sorted by ChartsMaze rank in the file; just sanity-check values exist.
    assert df["perf_1m"].notna().any()


@pytest.mark.skipif(not _REAL_FOLDER.is_dir(), reason="real chartsmaze folder absent")
def test_run_populates_sector_and_industry_metrics(legacy_cm, tmp_path):
    """run() writes sector, industry, and per-stock RS rows plus freshness."""
    conn = db.init_db(tmp_path / "manas.db")
    try:
        chartsmaze.run(conn, _REAL_DATE)

        sec = conn.execute("SELECT COUNT(*) AS n FROM sector_metrics").fetchone()["n"]
        ind = conn.execute("SELECT COUNT(*) AS n FROM industry_metrics").fetchone()["n"]
        stocks = conn.execute("SELECT COUNT(*) AS n FROM stock_industry_rs").fetchone()["n"]
        assert sec > 0, "sector_metrics not populated"
        assert ind > 0, "industry_metrics not populated"
        assert stocks > 0, "stock_industry_rs not populated"

        top_stock = conn.execute(
            "SELECT ticker, industry, rs FROM stock_industry_rs "
            "WHERE snapshot_date = ? ORDER BY rs DESC, ticker LIMIT 1",
            (_REAL_DATE,),
        ).fetchone()
        assert top_stock is not None
        assert top_stock["ticker"]
        assert top_stock["industry"]
        assert top_stock["rs"] is not None

        # sector_metrics carry the RS% from sector-analytics-Relative Strength.
        cap = conn.execute(
            "SELECT sector_key, rs_score FROM sector_metrics "
            "WHERE rs_score IS NOT NULL ORDER BY rs_score DESC LIMIT 1"
        ).fetchone()
        assert cap is not None
        assert cap["sector_key"]
        assert cap["rs_score"] >= 0

        # industries sorted by perf_1m desc on read; just confirm a value present.
        top = conn.execute(
            "SELECT name, perf_1m FROM industry_metrics "
            "WHERE perf_1m IS NOT NULL ORDER BY perf_1m DESC LIMIT 1"
        ).fetchone()
        assert top is not None and top["name"]

        # pipeline_runs still records the ingest honestly.
        run = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_chartsmaze'"
        ).fetchone()
        assert run["status"] == "ok"
    finally:
        conn.close()


def test_run_missing_folder_skips(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        n = chartsmaze.run(conn, "1999-01-01")
        assert n == 0
        row = conn.execute(
            "SELECT status FROM pipeline_runs WHERE stage='ingest_chartsmaze'"
        ).fetchone()
        assert row[0] == "skip"
    finally:
        conn.close()


def test_migrate_history_copies_fixture(tmp_path):
    # Build a tiny fixture tree mimicking the real layout.
    src = tmp_path / "src"
    (src / "2026-01-01" / "analytics").mkdir(parents=True)
    (src / "2026-01-01" / "analytics" / "market-breadth.csv").write_text("a,b\n1,2\n")
    (src / "2026-01-02" / "scanners").mkdir(parents=True)
    (src / "2026-01-02" / "scanners" / "gap-up.csv").write_text("x\n1\n")
    (src / "order-wins-master.csv").write_text("m\n1\n")

    dst = tmp_path / "dst"
    copied = chartsmaze_migrate.migrate_history(src, dst)

    assert set(copied) == {"2026-01-01", "2026-01-02", "order-wins-master.csv"}
    assert (dst / "2026-01-01" / "analytics" / "market-breadth.csv").read_text() == "a,b\n1,2\n"
    assert (dst / "2026-01-02" / "scanners" / "gap-up.csv").exists()
    assert (dst / "order-wins-master.csv").exists()
    # Source preserved.
    assert (src / "2026-01-01" / "analytics" / "market-breadth.csv").exists()

    # Idempotent: existing date folders are skipped on a second run.
    copied2 = chartsmaze_migrate.migrate_history(src, dst)
    assert "2026-01-01" not in copied2
    assert "2026-01-02" not in copied2


# ── Fetch-failure classification (auth-expired visibility fix, 2026-07-25) ──
# extractor.py's real cron output on an expired session (chartsmaze_extractor/
# run_cron.py): "INFO session/session fail rows=None file=None
# error=session_invalid" then "ERROR Session invalid. Run python login.py and
# complete the OTP flow." classify_fetch_output must turn that into a
# machine-readable reason_code instead of the caller collapsing it to a bare
# "exit 2".

_REAL_SESSION_INVALID_STDOUT = (
    "INFO session/session fail rows=None file=None error=session_invalid\n"
)
_REAL_SESSION_INVALID_STDERR = (
    "ERROR Session invalid. Run python login.py and complete the OTP flow.\n"
)


def test_classify_fetch_output_detects_session_invalid():
    reason_code, message = chartsmaze.classify_fetch_output(
        _REAL_SESSION_INVALID_STDOUT, _REAL_SESSION_INVALID_STDERR, 2
    )
    assert reason_code == "auth_expired"
    assert "Session invalid" in message
    assert "login.py" in message


def test_classify_fetch_output_unknown_failure_keeps_raw_tail():
    """A failure that ISN'T the known auth pattern must still be diagnosable
    -- the whole point of this feature is that unknown failures no longer
    collapse to a bare exit code."""
    reason_code, message = chartsmaze.classify_fetch_output(
        "", "Traceback (most recent call last):\nConnectionError: mystery failure\n", 1
    )
    assert reason_code == "unknown"
    assert "exit 1" in message
    assert "mystery failure" in message


def test_classify_fetch_output_redacts_secret_shaped_values():
    """No cookie/token/OTP-shaped string may survive into the persisted
    message -- this is what gets written to job_steps.error and can be
    returned by /api/chartsmaze/status."""
    stderr = "set-cookie: session_token=ABCDEFGHIJKL1234567890XYZ; otp=482913 login failed"
    reason_code, message = chartsmaze.classify_fetch_output("", stderr, 1)
    assert reason_code == "unknown"
    assert "ABCDEFGHIJKL1234567890XYZ" not in message
    assert "482913" not in message
    assert "<redacted>" in message


def test_classify_fetch_output_truncates_tail_to_500_chars():
    huge = "x" * 5000
    _reason_code, message = chartsmaze.classify_fetch_output("", huge, 1)
    # tail is capped at 500 chars; the message overall stays well short of
    # the 1000-char cap jobs._error() applies before persisting.
    assert len(message) < 600


def test_parse_reason_code_roundtrips_classify_output():
    _reason_code, message = chartsmaze.classify_fetch_output(
        _REAL_SESSION_INVALID_STDOUT, _REAL_SESSION_INVALID_STDERR, 2
    )
    persisted = f"reason_code=auth_expired {message}"
    code, human = chartsmaze.parse_reason_code(persisted)
    assert code == "auth_expired"
    assert human == message


def test_parse_reason_code_handles_legacy_unprefixed_text():
    code, human = chartsmaze.parse_reason_code("exit 1")
    assert code is None
    assert human == "exit 1"


def test_parse_reason_code_handles_none():
    assert chartsmaze.parse_reason_code(None) == (None, None)


# ── latest_available_dump / missing_folder_message ─────────────────────────

def test_latest_available_dump_picks_newest_dated_subfolder(tmp_path, monkeypatch):
    root = tmp_path / "cm"
    (root / "2026-07-18").mkdir(parents=True)
    (root / "2026-07-21").mkdir(parents=True)
    (root / "not-a-date").mkdir(parents=True)  # ignored -- not YYYY-MM-DD
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)

    assert chartsmaze.latest_available_dump() == "2026-07-21"


def test_latest_available_dump_none_when_root_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: tmp_path / "nope")
    assert chartsmaze.latest_available_dump() is None


def test_missing_folder_message_root_absent_names_the_root(tmp_path, monkeypatch):
    absent_root = tmp_path / "nope"
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: absent_root)

    msg = chartsmaze.missing_folder_message("2026-07-24")

    assert msg == f"chartsmaze root missing: {absent_root}"
    assert "no chartsmaze dump for" not in msg


def test_missing_folder_message_names_latest_available_dump_when_root_present(tmp_path, monkeypatch):
    """Regression for the bug this feature fixes: the root DID exist with
    dated subfolders up to 2026-07-21, only 2026-07-24's dump was absent --
    the old "chartsmaze folder missing: <path>" text sent the reader hunting
    for a folder that was actually there."""
    root = tmp_path / "cm"
    (root / "2026-07-18").mkdir(parents=True)
    (root / "2026-07-21").mkdir(parents=True)
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)

    msg = chartsmaze.missing_folder_message("2026-07-24")

    assert msg == "no chartsmaze dump for 2026-07-24 (latest available: 2026-07-21)"
    assert "root missing" not in msg


def test_missing_folder_message_root_present_but_empty(tmp_path, monkeypatch):
    root = tmp_path / "cm"
    root.mkdir()
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)

    msg = chartsmaze.missing_folder_message("2026-07-24")

    assert "present but empty" in msg


def test_run_missing_folder_uses_corrected_message(tmp_path, monkeypatch):
    """run()'s skip detail must use the new accurate message, not the old
    misleading "chartsmaze folder missing: <path>" text."""
    root = tmp_path / "cm"
    (root / "2026-07-21").mkdir(parents=True)
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)

    conn = db.init_db(tmp_path / "manas.db")
    try:
        chartsmaze.run(conn, "2026-07-24")
        row = conn.execute(
            "SELECT detail FROM pipeline_runs WHERE stage='ingest_chartsmaze'"
        ).fetchone()
        assert row[0] == "no chartsmaze dump for 2026-07-24 (latest available: 2026-07-21)"
    finally:
        conn.close()


# ── fetch_failure_reason ─────────────────────────────────────────────────

def test_fetch_failure_reason_none_when_never_run(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        assert chartsmaze.fetch_failure_reason(conn) is None
    finally:
        conn.close()


def test_fetch_failure_reason_extracts_auth_expired(tmp_path):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        conn.execute(
            "INSERT INTO jobs (job_id, kind, status) VALUES (1, 'run-eod', 'failed')"
        )
        conn.execute(
            "INSERT INTO job_steps (job_id, seq, name, status, error) VALUES "
            "(1, 1, 'fetch_chartsmaze', 'fail', "
            "'reason_code=auth_expired Session invalid. Run python login.py and complete the OTP flow.')"
        )
        conn.commit()

        result = chartsmaze.fetch_failure_reason(conn)

        assert result is not None
        assert result["status"] == "fail"
        assert result["reason_code"] == "auth_expired"
        assert "login.py" in result["reason"]
    finally:
        conn.close()
