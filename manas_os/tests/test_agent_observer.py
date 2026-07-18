import json

from manas_os import db
from manas_os.agents import debate, observer


AS_OF = "2026-06-30"


class ObserverClient:
    model = "mock/observer"

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return json.dumps(response), self.model


def _patch_config(monkeypatch, *, model="mock/observer"):
    def fake_get(key, default=None):
        values = {
            "agents.observer_model": model,
            "agents.api_key": "test-key",
            "agents.max_tokens": 1200,
            "advisor.api_key": None,
        }
        return values.get(key, default)

    monkeypatch.setattr(observer.config, "get", fake_get)


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

    monkeypatch.setattr(observer.charts, "render_charts", fake_render)


BASE_PAYLOAD = {
    "phase_and_sequence": "Stage 2 uptrend, currently basing.",
    "supply_demand_behavior": "Demand absorbing supply on down days.",
    "base_age_and_quality": "8-week tight base.",
    "volume_behavior": "Volume contracting into the base.",
    "stock_vs_group": "Outperforming its group.",
    "plausible_hypotheses": ["Continuation breakout", "Failed base"],
    "confirming_evidence": "Higher lows on the daily.",
    "strongest_contradiction": "Weekly close below the 10-week line.",
    "what_must_happen_next": "Close above base high on expanding volume.",
    "invalidation_criteria": "Close below base low.",
}


def test_observer_run_persists_payload_and_sends_scan_date_recency_prompt(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        debate.ensure_schema(conn)
        _patch_config(monkeypatch)
        _patch_charts(monkeypatch, tmp_path)
        conn.commit()
        client = ObserverClient([dict(BASE_PAYLOAD)])
        shortlist = [{"symbol": "AAA", "setup": "Pullback", "setup_family": "strong_start"}]

        result = observer.run(conn, AS_OF, shortlist, client=client)

        assert result["status"] == "ok"
        assert result["rows"] == 1
        row = conn.execute(
            "SELECT verdict, lens_scores_json FROM agent_verdicts WHERE agent = 'observer' AND symbol = 'AAA'"
        ).fetchone()
        assert row["verdict"] == "OBSERVED"
        lens = json.loads(row["lens_scores_json"])
        assert lens["phase_and_sequence"] == BASE_PAYLOAD["phase_and_sequence"]
        assert "stale_evidence_warning" not in lens

        first_user = client.calls[0]["user"]
        assert [part["type"] for part in first_user] == ["text", "image_url", "image_url"]
        system_prompt = client.calls[0]["system"]
        assert AS_OF in system_prompt
        assert "RECENCY RULE" in system_prompt
    finally:
        conn.close()


def test_observer_flags_stale_evidence_from_any_narrative_field(tmp_path, monkeypatch):
    """I10: the ADANIENT incident had the stale month-year buried in narrative
    prose (not a dedicated date field), so the post-check must scan every
    free-text field the observer returns, including the hypotheses list."""
    conn = db.init_db(tmp_path / "m.db")
    try:
        debate.ensure_schema(conn)
        _patch_config(monkeypatch)
        _patch_charts(monkeypatch, tmp_path)
        conn.commit()
        payload = dict(BASE_PAYLOAD)
        payload["confirming_evidence"] = "Same behavior as the Sep 2024 breakout attempt."
        client = ObserverClient([payload])
        shortlist = [{"symbol": "ADANIENT", "setup": "Pullback", "setup_family": "strong_start"}]

        result = observer.run(conn, AS_OF, shortlist, client=client)

        assert result["status"] == "ok"
        lens = json.loads(conn.execute(
            "SELECT lens_scores_json FROM agent_verdicts WHERE agent = 'observer' AND symbol = 'ADANIENT'"
        ).fetchone()["lens_scores_json"])
        assert "Sep 2024" in lens["stale_evidence_warning"]
        assert "treat dated claims with suspicion" in lens["stale_evidence_warning"]
        # payloads dict returned from run() is what debate.py merges into the
        # shortlist item (item["observer"] = ...) feeding the council prompt.
        assert "stale_evidence_warning" in result["payloads"]["ADANIENT"]
    finally:
        conn.close()


def test_observer_per_symbol_failure_is_logged_and_no_row_persisted(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        debate.ensure_schema(conn)
        _patch_config(monkeypatch)
        _patch_charts(monkeypatch, tmp_path)
        conn.commit()
        client = ObserverClient([RuntimeError("observer unavailable")])
        shortlist = [{"symbol": "AAA", "setup": "Pullback", "setup_family": "strong_start"}]

        result = observer.run(conn, AS_OF, shortlist, client=client)

        assert result["status"] == "partial"
        assert conn.execute("SELECT COUNT(*) FROM agent_verdicts WHERE agent = 'observer'").fetchone()[0] == 0
        log = conn.execute("SELECT parsed_ok, error FROM scan_agent_logs WHERE agent = 'observer'").fetchone()
        assert log["parsed_ok"] == 0
        assert "observer unavailable" in log["error"]
    finally:
        conn.close()


def test_observer_unset_model_noops_without_rendering(tmp_path, monkeypatch):
    conn = db.init_db(tmp_path / "m.db")
    try:
        debate.ensure_schema(conn)
        _patch_config(monkeypatch, model=None)
        monkeypatch.setattr(
            observer.charts,
            "render_charts",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not render")),
        )
        conn.commit()
        shortlist = [{"symbol": "AAA"}]

        result = observer.run(conn, AS_OF, shortlist, client=ObserverClient([]))

        assert result == {"status": "skip", "rows": 0, "detail": "vision model unset"}
    finally:
        conn.close()
