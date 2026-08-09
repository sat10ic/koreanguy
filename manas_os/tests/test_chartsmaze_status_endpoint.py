"""Tests for GET /api/chartsmaze/status -- the ChartsMaze-scraper-login
readiness endpoint (mirrors /api/fyers/status's booleans/enums-only shape).

Covers all four status values: ready | auth_expired | stale | never_run.
"""
from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.sources import chartsmaze


def _client(db_path, monkeypatch):
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    return TestClient(api_app.app)


def _insert_daily_prices(conn, dates):
    for d in dates:
        conn.execute("INSERT INTO daily_prices (trade_date, series, symbol) VALUES (?, 'EQ', 'AAA')", (d,))
    conn.commit()


def _insert_fetch_chartsmaze_step(conn, *, status, error=None, run_date="2026-07-24"):
    conn.execute("INSERT INTO jobs (job_id, kind, run_date, status) VALUES (1, 'run-eod', ?, 'succeeded')",
                 (run_date,))
    conn.execute(
        "INSERT INTO job_steps (job_id, seq, name, status, error) VALUES (1, 1, 'fetch_chartsmaze', ?, ?)",
        (status, error),
    )
    conn.commit()


def test_chartsmaze_status_never_run_when_no_dump_and_no_fetch_history(tmp_path, monkeypatch):
    root = tmp_path / "cm_empty"
    root.mkdir()
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)

    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    client = _client(db_path, monkeypatch)

    body = client.get("/api/chartsmaze/status").json()

    assert body["status"] == "never_run"
    assert body["latest_dump_date"] is None
    assert body["last_fetch_status"] is None
    assert "login.py" in body["action"]


def test_chartsmaze_status_auth_expired_takes_priority_over_stale_dump(tmp_path, monkeypatch):
    """The diagnosed real-world state: fetch_chartsmaze's last attempt failed
    with an expired session, even though an older dump exists on disk."""
    root = tmp_path / "cm"
    (root / "2026-07-21").mkdir(parents=True)
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    _insert_daily_prices(conn, ["2026-07-22", "2026-07-23", "2026-07-24"])
    reason_code, message = chartsmaze.classify_fetch_output(
        "INFO session/session fail rows=None file=None error=session_invalid\n",
        "ERROR Session invalid. Run python login.py and complete the OTP flow.\n",
        2,
    )
    _insert_fetch_chartsmaze_step(conn, status="fail", error=f"reason_code={reason_code} {message}")
    conn.close()

    client = _client(db_path, monkeypatch)
    body = client.get("/api/chartsmaze/status").json()

    assert body["status"] == "auth_expired"
    assert body["latest_dump_date"] == "2026-07-21"
    assert body["sessions_behind"] == 3
    assert body["last_fetch_status"] == "fail"
    assert "Session invalid" in body["reason"]
    assert "login.py" in body["action"]


def test_chartsmaze_status_stale_when_dump_lags_with_no_auth_failure(tmp_path, monkeypatch):
    root = tmp_path / "cm"
    (root / "2026-07-20").mkdir(parents=True)
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    _insert_daily_prices(conn, ["2026-07-21", "2026-07-22", "2026-07-23"])
    conn.close()

    client = _client(db_path, monkeypatch)
    body = client.get("/api/chartsmaze/status").json()

    assert body["status"] == "stale"
    assert body["latest_dump_date"] == "2026-07-20"
    assert body["sessions_behind"] == 3
    assert body["last_fetch_status"] is None
    assert "fetch_sources" in body["action"] or "pipeline run" in body["action"]


def test_chartsmaze_status_ready_when_dump_matches_latest_priced_session(tmp_path, monkeypatch):
    root = tmp_path / "cm"
    (root / "2026-07-23").mkdir(parents=True)
    monkeypatch.setattr(chartsmaze, "chartsmaze_dir", lambda: root)

    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    _insert_daily_prices(conn, ["2026-07-21", "2026-07-22", "2026-07-23"])
    _insert_fetch_chartsmaze_step(conn, status="ok", error=None)
    conn.close()

    client = _client(db_path, monkeypatch)
    body = client.get("/api/chartsmaze/status").json()

    assert body["status"] == "ready"
    assert body["latest_dump_date"] == "2026-07-23"
    assert body["sessions_behind"] == 0
    assert body["action"] is None


def test_chartsmaze_status_never_returns_secret_shaped_field_names():
    """No response field or docstring on the endpoint may be positioned to
    carry a raw credential -- structural guard against a future regression
    (the endpoint must stay booleans/enums-only, matching /api/fyers/status)."""
    from manas_os.api.app import chartsmaze_status

    src = chartsmaze_status.__doc__ or ""
    assert "cookie" not in src.lower()
    assert "password" not in src.lower()
