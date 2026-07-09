import base64

from fastapi.testclient import TestClient

from manas_os import db
from manas_os.agents import lessons
from manas_os.api import app as api_app
from manas_os.scanner import candidates as scanner_candidates


AS_OF = "2026-06-30"
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def _client(db_path, monkeypatch):
    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    return TestClient(api_app.app)


def test_desk_chart_serves_png_and_404s_when_absent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    chart_dir = tmp_path / "data" / "agent_charts" / AS_OF
    chart_dir.mkdir(parents=True)
    (chart_dir / "AAA_daily.png").write_bytes(PNG_1X1)

    client = _client(db_path, monkeypatch)
    ok = client.get("/api/desk/chart", params={"date": AS_OF, "symbol": "AAA", "tf": "daily"})
    assert ok.status_code == 200
    assert ok.headers["content-type"] == "image/png"
    assert ok.content == PNG_1X1

    missing = client.get("/api/desk/chart", params={"date": AS_OF, "symbol": "AAA", "tf": "weekly"})
    assert missing.status_code == 404
    assert missing.json() == {"available": False, "date": AS_OF, "symbol": "AAA", "tf": "weekly"}


def test_desk_track_record_aggregates_agent_family_outcomes(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    conn = db.init_db(db_path)
    try:
        scanner_candidates.ensure_schema(conn)
        for idx, outcome in enumerate([1.2, -0.5, 2.0], start=1):
            symbol = f"A{idx}"
            conn.execute(
                "INSERT OR REPLACE INTO scan_candidates "
                "(scan_date, symbol, setup, setup_family, readiness, grade, entry, stop, rr, suggested_qty) "
                "VALUES (?, ?, 'Pullback', 'base/pattern', 80, 'A', 100, 95, 2.0, 10)",
                (AS_OF, symbol),
            )
            conn.execute(
                "INSERT OR REPLACE INTO agent_verdicts "
                "(scan_date, symbol, agent, verdict, outcome_r) VALUES (?, ?, 'mock/model-a', 'TAKE', ?)",
                (AS_OF, symbol, outcome),
            )
        conn.execute(
            "INSERT OR REPLACE INTO scan_candidates "
            "(scan_date, symbol, setup, setup_family, readiness, grade, entry, stop, rr, suggested_qty) "
            "VALUES (?, 'B1', 'Breakout', 'catalyst', 80, 'A', 100, 95, 2.0, 10)",
            (AS_OF,),
        )
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, outcome_r) VALUES (?, 'B1', 'chair', 'SKIP', -1.0)",
            (AS_OF,),
        )
        conn.commit()
    finally:
        conn.close()

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/track-record")
    assert resp.status_code == 200
    records = resp.json()["records"]
    model = next(r for r in records if r["agent"] == "mock/model-a" and r["family"] == "base/pattern")
    assert model["n"] == 3
    assert model["hit_rate"] == 2 / 3
    assert abs(model["avg_r"] - 0.9) < 1e-9
    assert model["thin"] is True
    chair = next(r for r in records if r["agent"] == "chair" and r["family"] == "catalyst")
    assert chair["n"] == 1
    assert chair["hit_rate"] == 0
    assert chair["avg_r"] == -1.0


def test_desk_lessons_lists_markdown_and_digest(tmp_path, monkeypatch):
    db_path = tmp_path / "m.db"
    db.init_db(db_path).close()
    lesson_dir = tmp_path / "lessons"
    lesson_dir.mkdir()
    (lesson_dir / "2026-06-30_AAA.md").write_text(
        "[clean-hit] AAA followed through.\nSecond line.", encoding="utf-8"
    )
    (lesson_dir / "2026-06-29_BBB.md").write_text(
        "BBB was a right-process-loss after tape rolled over.", encoding="utf-8"
    )
    (lesson_dir / "_digest.md").write_text("Carry forward the clean base lesson.", encoding="utf-8")
    monkeypatch.setattr(lessons, "LESSON_DIR", lesson_dir)

    client = _client(db_path, monkeypatch)
    resp = client.get("/api/desk/lessons", params={"limit": 1})
    assert resp.status_code == 200
    body = resp.json()
    assert body["digest"] == "Carry forward the clean base lesson."
    assert body["lessons"] == [
        {
            "filename": "2026-06-30_AAA.md",
            "tag": "clean-hit",
            "first_line": "[clean-hit] AAA followed through.",
        }
    ]
