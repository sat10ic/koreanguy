from datetime import date, timedelta

from manas_os import db
from manas_os.agents import coach, lessons


def _dates(n, start="2026-06-01"):
    d = date.fromisoformat(start)
    out = []
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


class LessonClient:
    def __init__(self, responses=None, exc=None):
        self.responses = list(responses or [])
        self.exc = exc
        self.calls = []

    def chat(self, *, system, user, include_usage=False):
        self.calls.append({"system": system, "user": user, "include_usage": include_usage})
        if self.exc:
            raise self.exc
        raw = self.responses.pop(0)
        return raw, "mock/lessons"


def _patch_lesson_dir(monkeypatch, tmp_path):
    lesson_dir = tmp_path / "lessons"
    monkeypatch.setattr(lessons, "LESSON_DIR", lesson_dir)
    monkeypatch.setattr(lessons, "LESSON_DIGEST_PATH", lesson_dir / "_digest.md")
    return lesson_dir


def _seed_candidate_thesis(conn, scan_date, symbol="AAA", *, entry=100.0, stop=95.0, verdict="TAKE"):
    conn.execute(
        "INSERT OR REPLACE INTO scan_candidates "
        "(scan_date, symbol, setup, entry, stop, source) VALUES (?, ?, 'EP', ?, ?, 'test')",
        (scan_date, symbol, entry, stop),
    )
    for agent in ["chair", "mock/model", "vision", "sizer"]:
        conn.execute(
            "INSERT OR REPLACE INTO agent_verdicts "
            "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, bull_case, bear_case, reasoning) "
            "VALUES (?, ?, ?, ?, 4, 1, '{}', 'bull demand', 'bear failure', ?)",
            (scan_date, symbol, agent, verdict if agent == "chair" else "TAKE", f"{agent} thesis"),
        )
    conn.commit()


def _seed_prices(conn, symbol, dates, *, entry=100.0, final_close=110.0, touch=True):
    rows = []
    for i, d in enumerate(dates):
        close = final_close if i == 10 else 100.0
        high = entry + 0.5 if touch else entry - 1.0
        rows.append((symbol, d, "EQ", close, high, close - 1.0, close, close - 0.1, 500000, "test"))
    conn.executemany(
        "INSERT OR REPLACE INTO daily_prices "
        "(symbol, trade_date, series, open, high, low, close, prev_close, volume, source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


def test_backfill_writes_lesson_digest_and_propagates_outcome_to_all_agent_rows(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        lesson_dir = _patch_lesson_dir(monkeypatch, tmp_path)
        days = _dates(12)
        _seed_candidate_thesis(conn, days[0])
        _seed_prices(conn, "AAA", days)
        client = LessonClient([
            "AAA proved the thesis with conviction 4 and a computed +2R close. [clean-hit]",
            "- AAA clean-hit: demand followed through.",
        ])

        result = lessons.run(conn, days[10], client=client)

        assert result == {"status": "ok", "backfilled": 1, "never_triggered": 0, "lessons": 1, "digest": True}
        rows = conn.execute(
            "SELECT agent, outcome_r FROM agent_verdicts WHERE scan_date = ? AND symbol = 'AAA' ORDER BY agent",
            (days[0],),
        ).fetchall()
        assert {row["agent"]: round(row["outcome_r"], 4) for row in rows} == {
            "chair": 2.0,
            "mock/model": 2.0,
            "sizer": 2.0,
            "vision": 2.0,
        }
        lesson_text = (lesson_dir / f"{days[0]}_AAA.md").read_text(encoding="utf-8")
        assert "clean-hit" in lesson_text
        assert "computed +2R" in lesson_text
        assert (lesson_dir / "_digest.md").read_text(encoding="utf-8") == "- AAA clean-hit: demand followed through.\n"
        assert len(client.calls) == 2
        assert '"r_path"' in client.calls[0]["user"]
        assert '"outcome_r": 2.0' in client.calls[0]["user"]
    finally:
        conn.close()


def test_never_triggered_leaves_outcome_null_and_marks_reasoning(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        _patch_lesson_dir(monkeypatch, tmp_path)
        days = _dates(12)
        _seed_candidate_thesis(conn, days[0], symbol="NTG")
        _seed_prices(conn, "NTG", days, touch=False)

        result = lessons.run(conn, days[10], client=LessonClient(["unused"]))

        assert result["backfilled"] == 0
        assert result["never_triggered"] == 1
        rows = conn.execute(
            "SELECT outcome_r, reasoning FROM agent_verdicts WHERE scan_date = ? AND symbol = 'NTG'",
            (days[0],),
        ).fetchall()
        assert all(row["outcome_r"] is None for row in rows)
        assert all("[never triggered]" in row["reasoning"] for row in rows)
    finally:
        conn.close()


def test_llm_failure_writes_stub_lesson_and_keeps_previous_digest(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    try:
        lesson_dir = _patch_lesson_dir(monkeypatch, tmp_path)
        lesson_dir.mkdir(parents=True)
        (lesson_dir / "_digest.md").write_text("previous digest\n", encoding="utf-8")
        days = _dates(12)
        _seed_candidate_thesis(conn, days[0], symbol="FAIL")
        _seed_prices(conn, "FAIL", days, final_close=90.0)

        result = lessons.run(conn, days[10], client=LessonClient(exc=RuntimeError("llm down")))

        assert result["backfilled"] == 1
        assert result["lessons"] == 1
        assert result["digest"] is False
        text = (lesson_dir / f"{days[0]}_FAIL.md").read_text(encoding="utf-8")
        assert "lesson stub" in text
        assert "outcome_r=-2.0000R" in text
        assert "tag=clean-miss" in text
        assert (lesson_dir / "_digest.md").read_text(encoding="utf-8") == "previous digest\n"
    finally:
        conn.close()


def test_coach_runs_lessons_final_step_on_skip(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "manas.db")
    calls = []
    try:
        monkeypatch.setattr(coach.lessons, "run", lambda c, run_date: calls.append((c, run_date)) or {"status": "ok"})

        result = coach.run(conn, "2026-06-30")

        assert result["status"] == "skip"
        assert calls == [(conn, "2026-06-30")]
    finally:
        conn.close()
