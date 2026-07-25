"""Tests for manas_os/integrity/ -- pipeline & data-integrity watchdog.

Fixtures build a real on-disk SQLite file via db.init_db(tmp_path / "m.db")
(full schema.sql, same as test_run_manifest_and_exit_codes.py) so checks.py
functions can be exercised through the SAME read-only-URI path report.py
uses against the live DB -- never :memory:, never the real manas.db.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from manas_os import cli, db
from manas_os.integrity import checks, report

# 2026-01-09 is a Friday, not an NSE holiday (market_calendar.HOLIDAYS has
# nothing that week) -- last_trading_day(FRIDAY) == FRIDAY itself, so it
# doubles as both "today" and "the expected session" in the simple cases.
FRIDAY = date(2026, 1, 9)
FRIDAY_S = "2026-01-09"
THURSDAY_S = "2026-01-08"


def _mk_conn(tmp_path: Path) -> tuple[sqlite3.Connection, Path]:
    path = tmp_path / "m.db"
    conn = db.init_db(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS refusals ("
        "scan_date TEXT NOT NULL, symbol TEXT NOT NULL, setup_family TEXT, "
        "failed_gate TEXT NOT NULL, reason TEXT, evidence_json TEXT, "
        "ingested_at TEXT DEFAULT (datetime('now')), "
        "PRIMARY KEY (scan_date, symbol))"
    )
    conn.commit()
    return conn, path


def _ro_conn(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _insert_price(conn, symbol: str, trade_date: str, close: float = 100.0, series: str = "EQ") -> None:
    conn.execute(
        "INSERT INTO daily_prices (symbol, series, trade_date, open, high, low, close) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (symbol, series, trade_date, close, close, close, close),
    )


def _insert_run(conn, run_date: str, stage: str, status: str, rows_affected: int = 0) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (run_date, stage, status, rows_affected) VALUES (?, ?, ?, ?)",
        (run_date, stage, status, rows_affected),
    )


# ---------------------------------------------------------------------------
# a. check_freshness
# ---------------------------------------------------------------------------


def test_check_freshness_pass(tmp_path):
    conn, path = _mk_conn(tmp_path)
    _insert_run(conn, FRIDAY_S, "ingest_bhavcopy", "ok", 10)
    _insert_price(conn, "TCS", FRIDAY_S)
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_freshness(ro, FRIDAY)
    ro.close()

    assert result["status"] == "PASS"
    assert result["evidence"]["has_pipeline_run_for_expected_session"] is True
    assert result["evidence"]["sessions_behind"] == 0


def test_check_freshness_fail_no_pipeline_run(tmp_path):
    conn, path = _mk_conn(tmp_path)
    # prices are current, but NO pipeline_runs row for the expected session
    _insert_price(conn, "TCS", FRIDAY_S)
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_freshness(ro, FRIDAY)
    ro.close()

    assert result["status"] == "FAIL"
    assert result["evidence"]["has_pipeline_run_for_expected_session"] is False


def test_check_freshness_fail_stale_prices(tmp_path):
    conn, path = _mk_conn(tmp_path)
    _insert_run(conn, FRIDAY_S, "ingest_bhavcopy", "ok", 10)
    # prices only current through Thursday -- one session behind
    _insert_price(conn, "TCS", THURSDAY_S)
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_freshness(ro, FRIDAY)
    ro.close()

    assert result["status"] == "FAIL"
    assert result["evidence"]["last_price_date"] == THURSDAY_S
    assert result["evidence"]["sessions_behind"] == 1


def test_check_freshness_ignores_polluted_run_date_values(tmp_path):
    """pipeline_runs.run_date has been observed holding non-date strings
    (e.g. a stray 'order-wins-master.csv' row) in the real DB -- MAX(run_date)
    must not choke on or be skewed by that pollution."""
    conn, path = _mk_conn(tmp_path)
    _insert_run(conn, FRIDAY_S, "ingest_bhavcopy", "ok", 10)
    _insert_run(conn, "order-wins-master.csv", "some_stage", "ok", 1)
    _insert_price(conn, "TCS", FRIDAY_S)
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_freshness(ro, FRIDAY)
    ro.close()

    assert result["status"] == "PASS"
    assert result["evidence"]["last_pipeline_run_date"] == FRIDAY_S


# ---------------------------------------------------------------------------
# b. check_silent_skips
# ---------------------------------------------------------------------------


def test_check_silent_skips_pass_when_column_populated(tmp_path):
    conn, path = _mk_conn(tmp_path)
    _insert_run(conn, FRIDAY_S, "ingest_mars", "skip", 0)
    conn.execute(
        "INSERT INTO sector_metrics (snapshot_date, sector_key, mars_score) VALUES (?, ?, ?)",
        (FRIDAY_S, "NIFTY AUTO", 1.23),
    )
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_silent_skips(ro, FRIDAY_S)
    ro.close()

    assert result["status"] == "PASS"
    assert result["evidence"]["offenders"] == []


def test_check_silent_skips_fail_when_skip_and_column_null(tmp_path):
    """The real defect this check exists for: ingest_mars reports skip AND
    sector_metrics.mars_score stays NULL for every row on that date (a plain
    row-count check would miss this -- sector_metrics rows for the date
    already exist, written by an unrelated stage; only the mars_score COLUMN
    is empty)."""
    conn, path = _mk_conn(tmp_path)
    _insert_run(conn, FRIDAY_S, "ingest_mars", "skip", 0)
    conn.execute(
        "INSERT INTO sector_metrics (snapshot_date, sector_key, mars_score) VALUES (?, ?, ?)",
        (FRIDAY_S, "NIFTY AUTO", None),
    )
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_silent_skips(ro, FRIDAY_S)
    ro.close()

    assert result["status"] == "FAIL"
    assert any("ingest_mars" in o for o in result["evidence"]["offenders"])


def test_check_silent_skips_fail_when_skip_and_zero_rows(tmp_path):
    conn, path = _mk_conn(tmp_path)
    _insert_run(conn, FRIDAY_S, "scan_candidates", "skip", 0)
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_silent_skips(ro, FRIDAY_S)
    ro.close()

    assert result["status"] == "FAIL"
    assert any("scan_candidates" in o for o in result["evidence"]["offenders"])


def test_check_silent_skips_reports_unmapped_stages_explicitly(tmp_path):
    conn, path = _mk_conn(tmp_path)
    _insert_run(conn, FRIDAY_S, "agents_debate", "skip", 0)
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_silent_skips(ro, FRIDAY_S)
    ro.close()

    assert result["status"] == "PASS"  # unmapped stage can't be verified -> not an offender
    assert "agents_debate" in result["evidence"]["unmapped_skip_stages"]


# ---------------------------------------------------------------------------
# c. check_verdict_grading
# ---------------------------------------------------------------------------


def _insert_verdict(conn, scan_date, symbol, outcome_r):
    conn.execute(
        "INSERT INTO agent_verdicts (scan_date, symbol, agent, verdict, outcome_r) "
        "VALUES (?, ?, 'chair', 'TAKE', ?)",
        (scan_date, symbol, outcome_r),
    )


def test_check_verdict_grading_pass_when_old_verdicts_graded(tmp_path):
    conn, path = _mk_conn(tmp_path)
    _insert_verdict(conn, "2025-12-01", "TCS", 1.5)  # old, but graded
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_verdict_grading(ro, FRIDAY)
    ro.close()

    assert result["status"] == "PASS"
    assert result["evidence"]["stale_ungraded"] == 0


def test_check_verdict_grading_fail_when_old_verdict_ungraded(tmp_path):
    conn, path = _mk_conn(tmp_path)
    _insert_verdict(conn, "2025-12-01", "TCS", None)  # far more than 5 sessions before FRIDAY
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_verdict_grading(ro, FRIDAY)
    ro.close()

    assert result["status"] == "FAIL"
    assert result["evidence"]["stale_ungraded"] == 1
    assert result["evidence"]["oldest_stale_ungraded_scan_date"] == "2025-12-01"


def test_check_verdict_grading_pass_when_ungraded_is_recent(tmp_path):
    """A verdict from yesterday with no outcome yet is expected -- it hasn't
    had 5 trading sessions to resolve. Only STALE ungraded verdicts fail."""
    conn, path = _mk_conn(tmp_path)
    _insert_verdict(conn, THURSDAY_S, "TCS", None)  # 1 session before FRIDAY
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_verdict_grading(ro, FRIDAY)
    ro.close()

    assert result["status"] == "PASS"
    assert result["evidence"]["stale_ungraded"] == 0
    assert result["evidence"]["ungraded"] == 1  # still counted, just not stale


# ---------------------------------------------------------------------------
# d. check_card_consistency
# ---------------------------------------------------------------------------


def _insert_candidate(conn, scan_date, symbol, setup, timing_json):
    conn.execute(
        "INSERT INTO scan_candidates (scan_date, symbol, setup, timing_json) VALUES (?, ?, ?, ?)",
        (scan_date, symbol, setup, json.dumps(timing_json) if timing_json is not None else None),
    )


def test_check_card_consistency_fail_on_low_rvol_strong_start(tmp_path):
    """Mirrors the real defect: a 'Strong Start Ready' card whose own
    timing_json.rvol shows volume was NOT elevated."""
    conn, path = _mk_conn(tmp_path)
    _insert_candidate(
        conn, FRIDAY_S, "SANDHAR", "Strong Start Ready",
        {"available": True, "rvol": 0.31, "read": "volume is not yet expanded"},
    )
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_card_consistency(ro, FRIDAY_S)
    ro.close()

    assert result["status"] == "FAIL"
    offenders = result["evidence"]["offenders"]
    assert any(o["symbol"] == "SANDHAR" and o["rule"] == "strong_start_rvol_not_confirmed" for o in offenders)


def test_check_card_consistency_pass_when_rvol_confirms_label(tmp_path):
    conn, path = _mk_conn(tmp_path)
    _insert_candidate(
        conn, FRIDAY_S, "SANDHAR", "Strong Start Ready",
        {"available": True, "rvol": 2.4, "read": "volume confirmed"},
    )
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_card_consistency(ro, FRIDAY_S)
    ro.close()

    assert result["status"] == "PASS"
    assert result["evidence"]["offenders"] == []


def test_check_card_consistency_ignores_unrelated_labels(tmp_path):
    conn, path = _mk_conn(tmp_path)
    _insert_candidate(conn, FRIDAY_S, "TCS", "Pullback-to-EMA", {"rvol": 0.1})
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_card_consistency(ro, FRIDAY_S)
    ro.close()

    assert result["status"] == "PASS"


# ---------------------------------------------------------------------------
# e. check_overfit_capacity
# ---------------------------------------------------------------------------


def _write_const_file(path: Path, n_constants: int) -> None:
    lines = [f"CONST_{i} = {float(i)}\n" for i in range(n_constants)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def test_check_overfit_capacity_fail_when_ratio_over_one(tmp_path, monkeypatch):
    fixture_root = tmp_path / "fixture_root"
    const_file = tmp_path / "consts.py"
    _write_const_file(const_file, 5)  # 5 constants
    monkeypatch.setattr(checks, "OVERFIT_FILES", (str(const_file),))

    conn, path = _mk_conn(tmp_path)
    # 1 scan_date with >=20 distinct symbols -> 5 params / 1 date = 5.0 > 1.0
    for i in range(20):
        _insert_candidate(conn, FRIDAY_S, f"SYM{i}", "Pullback-to-EMA", None)
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_overfit_capacity(ro, root=fixture_root)
    ro.close()

    assert result["status"] == "FAIL"
    assert result["evidence"]["total_params"] == 5
    assert result["evidence"]["independent_dates"] == 1
    assert result["evidence"]["ratio"] == 5.0


def test_check_overfit_capacity_pass_when_ratio_at_or_under_one(tmp_path, monkeypatch):
    fixture_root = tmp_path / "fixture_root"
    const_file = tmp_path / "consts_small.py"
    _write_const_file(const_file, 2)  # 2 constants
    monkeypatch.setattr(checks, "OVERFIT_FILES", (str(const_file),))

    conn, path = _mk_conn(tmp_path)
    for d in ("2026-01-05", "2026-01-06", "2026-01-07"):
        for i in range(20):
            _insert_candidate(conn, d, f"SYM{i}", "Pullback-to-EMA", None)
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_overfit_capacity(ro, root=fixture_root)
    ro.close()

    # 2 params / 3 dates = 0.67 <= 1.0
    assert result["status"] == "PASS"
    assert result["evidence"]["ratio"] < 1.0


# ---------------------------------------------------------------------------
# f. check_survivorship
# ---------------------------------------------------------------------------


def test_check_survivorship_warn_on_ratio_over_3x(tmp_path):
    conn, path = _mk_conn(tmp_path)
    max_date = "2026-06-01"

    # scan_candidates cohort: 3 alive + 1 dead (no EQ bar within 60d of
    # max_date) = 25% dead rate.
    for sym in ("ALIVE_A", "ALIVE_B", "ALIVE_C"):
        _insert_price(conn, sym, max_date)
        _insert_candidate(conn, "2026-01-01", sym, "Pullback-to-EMA", None)
    _insert_price(conn, "DEAD_A", "2025-01-01")
    _insert_candidate(conn, "2026-01-01", "DEAD_A", "Pullback-to-EMA", None)

    # refusals cohort: all-dead (100%) -- ratio vs scan_candidates' 25% is 4x > 3x
    for sym in ("DEAD_B", "DEAD_C", "DEAD_D"):
        _insert_price(conn, sym, "2025-01-01")
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, failed_gate) VALUES (?, ?, ?)",
            ("2026-01-01", sym, "some_gate"),
        )
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_survivorship(ro)
    ro.close()

    assert result["status"] == "WARN"
    assert result["evidence"]["refusals"]["dead_rate"] == 1.0
    assert result["evidence"]["scan_candidates"]["dead_rate"] == 0.25


def test_check_survivorship_pass_when_rates_similar(tmp_path):
    conn, path = _mk_conn(tmp_path)
    max_date = "2026-06-01"
    for sym in ("A1", "A2", "A3", "A4"):
        _insert_price(conn, sym, max_date)
        _insert_candidate(conn, "2026-01-01", sym, "Pullback-to-EMA", None)
    for sym in ("B1", "B2", "B3", "B4"):
        _insert_price(conn, sym, max_date)
        conn.execute(
            "INSERT INTO refusals (scan_date, symbol, failed_gate) VALUES (?, ?, ?)",
            ("2026-01-01", sym, "some_gate"),
        )
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_survivorship(ro)
    ro.close()

    assert result["status"] == "PASS"
    assert result["evidence"]["scan_candidates"]["dead_rate"] == 0.0
    assert result["evidence"]["refusals"]["dead_rate"] == 0.0


def test_check_survivorship_reports_t10_dropout(tmp_path):
    """A symbol with an entry price but no bar 10 sessions later must show up
    as 'missing T+10' -- a delisting shouldn't just silently vanish from an
    average."""
    conn, path = _mk_conn(tmp_path)
    max_date = "2026-06-01"
    _insert_price(conn, "NOFUTURE", "2026-01-01")  # entry only, nothing after
    _insert_candidate(conn, "2026-01-01", "NOFUTURE", "Pullback-to-EMA", None)
    _insert_price(conn, "ALIVE", max_date)
    conn.execute(
        "INSERT INTO refusals (scan_date, symbol, failed_gate) VALUES (?, ?, ?)",
        ("2026-01-01", "ALIVE", "some_gate"),
    )
    conn.commit()
    conn.close()

    ro = _ro_conn(path)
    result = checks.check_survivorship(ro)
    ro.close()

    assert result["evidence"]["scan_candidates"]["n_rows_missing_t10"] == 1


# ---------------------------------------------------------------------------
# g. check_lookahead
# ---------------------------------------------------------------------------


def test_check_lookahead_fails_on_decision_path_hit(tmp_path):
    root = tmp_path / "manas_os"
    (root / "scanner").mkdir(parents=True)
    (root / "scanner" / "candidates.py").write_text(
        'row = conn.execute("SELECT MAX(scan_date) FROM scan_candidates").fetchone()\n',
        encoding="utf-8",
    )

    result = checks.check_lookahead(root=root)

    assert result["status"] == "FAIL"
    assert any("scanner/candidates.py" in h for h in result["evidence"]["decision_path_hits"])


def test_check_lookahead_does_not_fail_on_freshness_code_false_positive(tmp_path):
    """The spec's explicit false-positive case: a freshness/display helper
    doing `SELECT MAX(trade_date) ... WHERE trade_date <= ?` a couple of
    lines below the MAX( call is legitimate 'latest as-of' logic, not
    look-ahead bias, and must not fail even when it lives in a decision-path
    file."""
    root = tmp_path / "manas_os"
    (root / "scanner").mkdir(parents=True)
    (root / "scanner" / "discovery.py").write_text(
        "def latest_price_date(conn, on_or_before):\n"
        "    row = conn.execute(\n"
        '        "SELECT MAX(trade_date) AS d FROM daily_prices "\n'
        '        "WHERE series=\'EQ\' AND trade_date <= ?",\n'
        "        (on_or_before,),\n"
        "    ).fetchone()\n",
        encoding="utf-8",
    )

    result = checks.check_lookahead(root=root)

    assert result["status"] == "PASS"
    assert result["evidence"]["decision_path_hits"] == []


def test_check_lookahead_reports_non_decision_path_as_info_not_fail(tmp_path):
    root = tmp_path / "manas_os"
    (root / "alpha").mkdir(parents=True)
    (root / "alpha" / "symbol_identity.py").write_text(
        'global_max = conn.execute("SELECT MAX(trade_date) FROM daily_prices").fetchone()[0]\n',
        encoding="utf-8",
    )

    result = checks.check_lookahead(root=root)

    assert result["status"] == "PASS"
    assert any("alpha/symbol_identity.py" in h for h in result["evidence"]["info_hits_elsewhere"])


def test_check_lookahead_skips_tests_dir(tmp_path):
    root = tmp_path / "manas_os"
    (root / "tests").mkdir(parents=True)
    (root / "tests" / "test_whatever.py").write_text(
        'row = conn.execute("SELECT MAX(scan_date) FROM scan_candidates").fetchone()\n',
        encoding="utf-8",
    )

    result = checks.check_lookahead(root=root)

    assert result["status"] == "PASS"
    assert result["evidence"]["decision_path_hits"] == []
    assert result["evidence"]["info_hits_elsewhere"] == []


# ---------------------------------------------------------------------------
# read-only connection guarantee
# ---------------------------------------------------------------------------


def test_report_run_all_opens_strictly_read_only(tmp_path):
    """report.run_all must never be able to write to the DB it audits --
    that write-on-open failure mode is exactly what made `manas scorecard`
    hit 'database is locked' against a live pipeline (db/__init__.py's
    connect() docstring)."""
    conn, path = _mk_conn(tmp_path)
    _insert_run(conn, FRIDAY_S, "ingest_bhavcopy", "ok", 10)
    _insert_price(conn, "TCS", FRIDAY_S)
    conn.commit()
    conn.close()

    before = path.read_bytes()
    result = report.run_all(path, FRIDAY)
    after = path.read_bytes()

    assert result["overall_status"] in ("PASS", "WARN", "FAIL")
    assert before == after  # byte-identical -- nothing was written

    # And directly: a mode=ro connection must refuse writes outright.
    ro = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    with pytest.raises(sqlite3.OperationalError):
        ro.execute("INSERT INTO pipeline_runs (run_date, stage, status) VALUES ('x', 'y', 'z')")
    ro.close()


def test_report_run_all_survives_a_concurrent_writer(tmp_path):
    """WAL-mode readers must not raise 'database is locked' while another
    connection holds an open write transaction -- the exact failure mode
    this module was built to never repeat."""
    conn, path = _mk_conn(tmp_path)
    _insert_run(conn, FRIDAY_S, "ingest_bhavcopy", "ok", 10)
    _insert_price(conn, "TCS", FRIDAY_S)
    conn.commit()

    writer = db.connect(path)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute(
        "INSERT INTO pipeline_runs (run_date, stage, status) VALUES ('2026-01-10', 'x', 'ok')"
    )
    try:
        result = report.run_all(path, FRIDAY)
        assert result["overall_status"] in ("PASS", "WARN", "FAIL")
    finally:
        writer.rollback()
        writer.close()
        conn.close()


# ---------------------------------------------------------------------------
# to_markdown + CLI exit code
# ---------------------------------------------------------------------------


def test_to_markdown_headline_reflects_overall_status(tmp_path):
    conn, path = _mk_conn(tmp_path)
    # no pipeline_runs row at all, no prices -> freshness FAILs -> overall FAIL
    conn.commit()
    conn.close()

    result = report.run_all(path, FRIDAY)
    md = report.to_markdown(result)

    assert md.startswith("INTEGRITY: FAIL")
    # Derive the count from the result rather than hardcoding it -- this
    # assertion used to pin "of 7 checks failing" and broke the moment an
    # eighth check (check_calendar) was added, which is a brittle test, not a
    # real regression.
    assert f"of {result['n_checks']} checks failing" in md
    assert "freshness" in md


def test_cli_integrity_exit_code_nonzero_on_fail(tmp_path, monkeypatch, capsys):
    conn, path = _mk_conn(tmp_path)
    # deliberately empty DB -> freshness FAILs -> overall FAIL
    conn.commit()
    conn.close()
    monkeypatch.setattr(cli.db, "DB_PATH", path)

    parser = cli.build_parser()
    args = parser.parse_args(["integrity", "--date", FRIDAY_S, "--out", str(tmp_path / "out")])
    rc = args.func(args)

    assert rc != 0
    out = capsys.readouterr().out
    assert "INTEGRITY: FAIL" in out
    assert (tmp_path / "out" / f"INTEGRITY_{FRIDAY_S}.md").exists()
    assert (tmp_path / "out" / f"INTEGRITY_{FRIDAY_S}.json").exists()


def test_cli_integrity_exit_code_zero_on_pass(tmp_path, monkeypatch, capsys):
    """CLI wiring/exit-code test only -- decoupled from the real repo's
    check_lookahead state (which scans the live manas_os/ tree and, being a
    genuinely useful check, may legitimately be FAIL against real code at
    any given time; that is covered separately by the check-level tests and
    the real-DB verification run, not by this CLI-plumbing test)."""
    conn, path = _mk_conn(tmp_path)
    conn.commit()
    conn.close()
    monkeypatch.setattr(cli.db, "DB_PATH", path)

    forced_pass = {
        "today": FRIDAY_S,
        "expected_session": FRIDAY_S,
        "overall_status": "PASS",
        "n_checks": 7,
        "n_fail": 0,
        "n_warn": 0,
        "checks": [
            {"name": "stub", "status": "PASS", "detail": "stub check", "evidence": {}},
        ],
    }
    monkeypatch.setattr(
        "manas_os.integrity.report.run_all", lambda db_path, today: forced_pass
    )

    parser = cli.build_parser()
    args = parser.parse_args(["integrity", "--date", FRIDAY_S, "--out", str(tmp_path / "out")])
    rc = args.func(args)

    assert rc == 0
    out = capsys.readouterr().out
    assert "INTEGRITY: PASS" in out
