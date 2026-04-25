"""SwingEdge Lite Dashboard API — comprehensive backend tests."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://51d172be-2a06-4e1e-9483-29a235028169.preview.emergentagent.com").rstrip("/")
TIMEOUT = 30


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------------- Health ----------------
def test_health(api):
    r = api.get(f"{BASE_URL}/api/health", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "ok"
    assert "ts" in d


# ---------------- Regime ----------------
def test_regime(api):
    r = api.get(f"{BASE_URL}/api/regime", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d.get("available") is True, f"regime not available: {d}"
    # Field is named `regime` in API response (not `state`)
    state = d.get("state") or d.get("regime")
    assert state in ("RISK_ON", "CAUTION", "RISK_OFF"), f"unexpected regime: {d}"
    assert "pillars_passed" in d
    pillars = d.get("pillars") or {}
    for p in ("trend", "momentum", "breadth", "volatility"):
        assert p in pillars, f"missing pillar {p}"
        assert "pass" in pillars[p]
        assert "value" in pillars[p]


# ---------------- Universe summary ----------------
def test_universe_summary(api):
    r = api.get(f"{BASE_URL}/api/universe/summary", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d.get("available") is True
    for k in ("total", "bullish", "bearish", "purple_dots_today",
              "extended_yellow", "extended_red", "setup_pass_count", "sectors"):
        assert k in d
    assert isinstance(d["sectors"], list)
    assert d["total"] > 0
    if d["sectors"]:
        assert "sector" in d["sectors"][0]
        assert "count" in d["sectors"][0]


# ---------------- Screen ----------------
def test_screen_basic(api):
    r = api.get(f"{BASE_URL}/api/screen", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d.get("available") is True
    assert isinstance(d["rows"], list)


def test_screen_filters(api):
    r = api.get(f"{BASE_URL}/api/screen?bucket=Bullish&sort_by=rs_score&limit=10", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d.get("available") is True
    for row in d["rows"]:
        assert row.get("bucket") == "Bullish"


# ---------------- RS grid ----------------
def test_rs_grid(api):
    r = api.get(f"{BASE_URL}/api/rs_grid", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d["available"] is True
    expected = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-",
                "D+", "D", "D-", "E+", "E", "F", "G"]
    assert d["order"] == expected
    for g in expected:
        assert g in d["grades"]
        assert g in d["counts"]
    total = sum(d["counts"].values())
    assert total > 0


# ---------------- Candidates ----------------
def test_candidates(api):
    r = api.get(f"{BASE_URL}/api/candidates", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert "primary" in d
    assert "secondary" in d
    assert isinstance(d["primary"], list)
    assert isinstance(d["secondary"], list)


def test_candidates_history(api):
    r = api.get(f"{BASE_URL}/api/candidates/history", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d.get("available") is True
    assert isinstance(d["rows"], list)
    assert len(d["rows"]) >= 1


# ---------------- Positions ----------------
def test_positions(api):
    r = api.get(f"{BASE_URL}/api/positions", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d.get("available") is True
    assert "rows" in d and "summary" in d and "stats" in d
    assert len(d["rows"]) >= 1, "expected demo seed positions"
    states = {row["state"] for row in d["rows"]}
    # At least one state machine state should be present
    assert states.intersection({"PENDING_CONFIRM", "ACTIVE", "EXITED_TRAIL", "EXITED_STOP", "EXITED_TARGET", "EXITED_TIME"})


# ---------------- Watchlist ----------------
def test_watchlist_get(api):
    r = api.get(f"{BASE_URL}/api/watchlist", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d.get("available") is True
    assert isinstance(d["rows"], list)
    if d["rows"]:
        row = d["rows"][0]
        assert "symbol" in row
        assert "grade_history_5d" in row


def test_watchlist_add_remove(api):
    # Bug-fix #2: must use a real symbol from universe.csv (RELIANCE) — fake
    # symbols are now rejected with 400 by /api/watchlist/add.
    sym = "RELIANCE"
    # Pre-clean in case a previous run left it in the file
    api.post(f"{BASE_URL}/api/watchlist/remove", json={"symbol": sym}, timeout=TIMEOUT)

    # Add
    r = api.post(f"{BASE_URL}/api/watchlist/add", json={"symbol": sym}, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json().get("ok") is True

    # Verify presence
    r2 = api.get(f"{BASE_URL}/api/watchlist", timeout=TIMEOUT)
    assert r2.status_code == 200
    syms = [row["symbol"] for row in r2.json().get("rows", [])]
    assert sym in syms

    # Remove
    r3 = api.post(f"{BASE_URL}/api/watchlist/remove", json={"symbol": sym}, timeout=TIMEOUT)
    assert r3.status_code == 200
    assert r3.json().get("ok") is True

    # Verify removed
    r4 = api.get(f"{BASE_URL}/api/watchlist", timeout=TIMEOUT)
    assert r4.status_code == 200
    syms2 = [row["symbol"] for row in r4.json().get("rows", [])]
    assert sym not in syms2


def test_watchlist_add_missing_symbol(api):
    r = api.post(f"{BASE_URL}/api/watchlist/add", json={}, timeout=TIMEOUT)
    assert r.status_code == 400


def test_watchlist_add_unknown_symbol_returns_400(api):
    # Bug-fix #2: unknown symbols (not in universe.csv) must be rejected with 400.
    r = api.post(f"{BASE_URL}/api/watchlist/add", json={"symbol": "FAKEFAKE"}, timeout=TIMEOUT)
    assert r.status_code == 400, f"expected 400 for unknown symbol, got {r.status_code}: {r.text}"


def test_watchlist_get_remains_200_after_add_attempts(api):
    # Bug-fix #1 smoke: even after an unknown-symbol add attempt, GET /api/watchlist
    # must continue to return 200 (NaN handling).
    api.post(f"{BASE_URL}/api/watchlist/add", json={"symbol": "FAKEFAKE"}, timeout=TIMEOUT)
    r = api.get(f"{BASE_URL}/api/watchlist", timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json().get("available") is True


# ---------------- Symbol detail ----------------
def test_symbol_detail(api):
    r = api.get(f"{BASE_URL}/api/symbol/RELIANCE", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d.get("available") is True
    assert "meta" in d and "bars" in d
    assert len(d["bars"]) > 0
    bar0 = d["bars"][0]
    for k in ("date", "open", "high", "low", "close", "volume"):
        assert k in bar0
    # Indicators expected on at least one bar
    has_inds = any(("sma50" in b) or ("rsi14" in b) or ("atr14" in b) for b in d["bars"])
    assert has_inds


# ---------------- SVRO arms ----------------
def test_svro_arms(api):
    r = api.get(f"{BASE_URL}/api/svro/arms", timeout=TIMEOUT)
    assert r.status_code == 200
    # availability optional; just shape
    assert isinstance(r.json(), dict)


# ---------------- Pipeline status / run ----------------
def test_pipeline_status(api):
    r = api.get(f"{BASE_URL}/api/pipeline/status", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    for k in ("running", "current_stage", "progress", "stages"):
        assert k in d


def test_pipeline_run_idempotent_running_check(api):
    # First call may start it
    r1 = api.post(f"{BASE_URL}/api/pipeline/run", json={"max_symbols": 1}, timeout=TIMEOUT)
    assert r1.status_code == 200
    body1 = r1.json()
    assert "ok" in body1
    # Immediately call again — should report already-running OR ok again if first finished super fast
    time.sleep(0.5)
    r2 = api.post(f"{BASE_URL}/api/pipeline/run", json={"max_symbols": 1}, timeout=TIMEOUT)
    assert r2.status_code == 200
    body2 = r2.json()
    if body1.get("ok") is True:
        # Either still running (ok:false) or it finished and started again (ok:true)
        assert "ok" in body2


# ---------------- Universe ----------------
def test_universe(api):
    r = api.get(f"{BASE_URL}/api/universe", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d.get("available") is True
    assert isinstance(d["rows"], list)
    assert d["total"] > 100
    assert isinstance(d["sectors"], list)


# ---------------- Config ----------------
def test_config_no_secrets(api):
    r = api.get(f"{BASE_URL}/api/config", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert isinstance(d, dict)
    fyers = d.get("fyers") or {}
    for k, v in fyers.items():
        if "token" in k.lower():
            assert v == "***", f"token not masked: {k}={v}"
