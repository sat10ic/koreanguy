import json
from pathlib import Path

from manas_os import db
from manas_os.agents import debate, vision
from manas_os.scanner import candidates as scanner_candidates


AS_OF = "2026-06-30"


class VisionClient:
    model = "mock/vision"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return json.dumps(response), self.model


def _patch_config(monkeypatch, *, model="mock/vision", top_n=8):
    def fake_get(key, default=None):
        values = {
            "agents.vision_model": model,
            "agents.vision_top_n": top_n,
            "agents.api_key": "test-key",
            "agents.max_tokens": 1200,
            "advisor.api_key": None,
        }
        return values.get(key, default)

    monkeypatch.setattr(vision.config, "get", fake_get)


def _seed_candidate(conn, symbol, rank, setup_family="strong_start"):
    scanner_candidates.ensure_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO scan_candidates "
        "(scan_date, symbol, setup, readiness, grade, entry, stop, target, rr, suggested_qty, "
        "trade_plan_json, evidence_json, timing_json, score_breakdown_json, gates_json, setup_family, rank, rank_of) "
        "VALUES (?, ?, 'Pullback', 90, 'A', 100, 95, 112, 2.4, 10, '{}', '[]', '{}', '{}', '[]', ?, ?, 3)",
        (AS_OF, symbol, setup_family, rank),
    )


def _seed_chair(conn, symbol, rank, verdict="TAKE", setup_family="strong_start"):
    _seed_candidate(conn, symbol, rank, setup_family)
    debate.ensure_schema(conn)
    conn.execute(
        "INSERT OR REPLACE INTO agent_verdicts "
        "(scan_date, symbol, agent, verdict, conviction, rank, lens_scores_json, reasoning) "
        "VALUES (?, ?, 'chair', ?, 4, ?, '{}', ?)",
        (AS_OF, symbol, verdict, rank, f"chair reason {symbol}"),
    )


def _patch_charts(monkeypatch, tmp_path):
    def fake_render(_conn, scan_date, symbols):
        chart_dir = tmp_path / "charts" / scan_date
        chart_dir.mkdir(parents=True, exist_ok=True)
        out = {}
        for symbol in symbols:
            daily = chart_dir / f"{symbol}_daily.png"
            weekly = chart_dir / f"{symbol}_weekly.png"
            daily.write_bytes(b"\x89PNG\r\n\x1a\nDaily")
            weekly.write_bytes(b"\x89PNG\r\n\x1a\nWeekly")
            out[symbol] = {"daily": str(daily), "weekly": str(weekly)}
        return out

    monkeypatch.setattr(vision.charts, "render_charts", fake_render)


def test_vision_promote_reorders_and_clamps_at_two(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _patch_charts(monkeypatch, tmp_path)
        _seed_chair(conn, "AAA", 1)
        _seed_chair(conn, "BBB", 2)
        _seed_chair(conn, "CCC", 3)
        conn.commit()
        client = VisionClient([
            {"action": "hold", "what_i_see": "AAA is fine.", "reason": "No change."},
            {"action": "hold", "what_i_see": "BBB is fine.", "reason": "No change."},
            {"action": "promote", "magnitude": 99, "what_i_see": "CCC is clean.", "reason": "Tighter than peers."},
        ])

        result = vision.run(conn, AS_OF, client=client)

        assert result["status"] == "ok"
        rows = conn.execute(
            "SELECT symbol, rank FROM agent_verdicts WHERE agent = 'chair' ORDER BY rank"
        ).fetchall()
        assert [(r["symbol"], r["rank"]) for r in rows] == [("CCC", 1), ("AAA", 2), ("BBB", 3)]
        lens = json.loads(conn.execute(
            "SELECT lens_scores_json FROM agent_verdicts WHERE agent = 'vision' AND symbol = 'CCC'"
        ).fetchone()["lens_scores_json"])
        assert lens == {"action": "promote", "magnitude": 2}
        first_user = client.calls[0]["user"]
        assert [part["type"] for part in first_user] == ["text", "image_url", "image_url"]
    finally:
        conn.close()


def test_vision_veto_flips_chair_verdict_to_skip_with_reason(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _patch_charts(monkeypatch, tmp_path)
        _seed_chair(conn, "AAA", 1)
        conn.commit()
        client = VisionClient([
            {"action": "veto", "what_i_see": "Breakout failed.", "reason": "Weekly chart rejects the move."},
        ])

        result = vision.run(conn, AS_OF, client=client)

        assert result["status"] == "ok"
        chair = conn.execute(
            "SELECT verdict, reasoning FROM agent_verdicts WHERE agent = 'chair' AND symbol = 'AAA'"
        ).fetchone()
        assert chair["verdict"] == "SKIP"
        assert "vision veto: Weekly chart rejects the move." in chair["reasoning"]
        assert conn.execute(
            "SELECT verdict FROM agent_verdicts WHERE agent = 'vision' AND symbol = 'AAA'"
        ).fetchone()["verdict"] == "SKIP"
    finally:
        conn.close()


def test_vision_per_finalist_failure_leaves_rank_untouched(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch)
        _patch_charts(monkeypatch, tmp_path)
        _seed_chair(conn, "AAA", 1)
        conn.commit()
        client = VisionClient([RuntimeError("vision unavailable")])

        result = vision.run(conn, AS_OF, client=client)

        assert result["status"] == "partial"
        chair = conn.execute(
            "SELECT verdict, rank FROM agent_verdicts WHERE agent = 'chair' AND symbol = 'AAA'"
        ).fetchone()
        assert (chair["verdict"], chair["rank"]) == ("TAKE", 1)
        assert conn.execute("SELECT COUNT(*) FROM agent_verdicts WHERE agent = 'vision'").fetchone()[0] == 0
        log = conn.execute("SELECT parsed_ok, error FROM scan_agent_logs WHERE agent = 'vision'").fetchone()
        assert log["parsed_ok"] == 0
        assert "vision unavailable" in log["error"]
    finally:
        conn.close()


def test_vision_unset_model_noops_without_rendering(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        _patch_config(monkeypatch, model=None)
        monkeypatch.setattr(
            vision.charts,
            "render_charts",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not render")),
        )
        _seed_chair(conn, "AAA", 1)
        conn.commit()

        result = vision.run(conn, AS_OF, client=VisionClient([]))

        assert result == {"status": "skip", "rows": 0, "detail": "vision model unset"}
        assert conn.execute("SELECT COUNT(*) FROM agent_verdicts WHERE agent = 'vision'").fetchone()[0] == 0
    finally:
        conn.close()
