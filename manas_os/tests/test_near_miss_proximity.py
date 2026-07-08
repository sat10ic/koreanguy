"""W2.2: near-miss lane exposes the gate-proximity map (distance value + the
'what would it take' chip text) server-side via _distance_to_pass. Locks the
contract the Setups/Focus near-miss lanes render against."""
from fastapi.testclient import TestClient

from manas_os import db
from manas_os.api import app as api_app
from manas_os.scanner.candidates import ensure_refusals_schema


def _seed_refusal(conn, scan_date, symbol, failed_gate, reason, evidence):
    ensure_refusals_schema(conn)
    conn.execute(
        "INSERT INTO refusals (scan_date, symbol, setup_family, failed_gate, reason, evidence_json) "
        "VALUES (?, ?, 'catalyst', ?, ?, ?)",
        (scan_date, symbol, failed_gate, reason, evidence),
    )
    conn.commit()


def test_near_miss_endpoint_returns_distance_proximity_fields(tmp_path, monkeypatch):
    # The fresh-leg gate: reason text carries two numbers (extension vs cap),
    # so _distance_to_pass must produce a numeric value + pp unit + the
    # what-would-it-take sentence the lane renders.
    db_path = tmp_path / "manas.db"
    conn = db.init_db(db_path)
    try:
        _seed_refusal(conn, "2026-01-15", "ACME", "fresh-leg",
                      "extension 8.9% exceeds 8.0% cap", "{}")
    finally:
        conn.close()

    orig_connect = db.connect
    monkeypatch.setattr(db, "connect", lambda db_path_arg=None: orig_connect(db_path))
    client = TestClient(api_app.app)

    res = client.get("/api/setups/near-misses", params={"date": "2026-01-15"})
    assert res.status_code == 200
    payload = res.json()
    assert payload["available"] is True
    item = payload["near_misses"][0]
    assert item["symbol"] == "ACME"
    # W2.2 contract: distance carries the proximity map fields.
    d = item["distance"]
    assert set(["label", "value", "unit", "what_would_it_take", "read", "severity"]).issubset(d.keys())
    # fresh-leg with two numbers in the reason -> value = |8.9 - 8.0| = 0.9 pp.
    assert d["value"] == 0.9
    assert d["unit"] == "pp"
    assert "fresh-leg cap" in d["what_would_it_take"]
    assert d["label"] == "watch"  # not a hard-no gate


def test_distance_to_pass_risk_gate_uses_evidence_rr_when_below_floor(tmp_path):
    # The risk gate: when evidence carries rr below the floor, the proximity
    # value = 1.5 - rr (the gap to acceptable R:R), unit R.
    from manas_os.api.app import _distance_to_pass

    d = _distance_to_pass("risk", {"rr": 1.1, "stop_pct": 9.0}, "rr below floor")
    assert d["value"] == 0.4  # 1.5 - 1.1
    assert d["unit"] == "R"
    assert "tighter stop" in d["what_would_it_take"]


def test_distance_to_pass_tradability_is_hard_no(tmp_path):
    # Tradability refusals are structural (liquidity/quality) — labeled
    # "hard no", not a near-miss watch. The lane renders this distinctly.
    from manas_os.api.app import _distance_to_pass

    d = _distance_to_pass("tradability", {}, "illiquid")
    assert d["label"] == "hard no"
    assert d["severity"] == "hard"
    assert d["value"] is None  # no numeric distance for a structural refusal


def test_distance_to_pass_participation_uses_delivery_z(tmp_path):
    # Participation gate: delivery_z below the 1.0 floor -> value = 1.0 - z.
    from manas_os.api.app import _distance_to_pass

    d = _distance_to_pass("participation", {"delivery_z": 0.3}, "delivery_z 0.3 < 1.0")
    assert d["value"] == 0.7  # 1.0 - 0.3
    assert d["unit"] == "z"
