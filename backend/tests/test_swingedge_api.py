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
              "extended_yellow", "extended_red", "setup_pass_count",
              "sectors", "industries", "basic_industries"):
        assert k in d, f"missing key {k}"
    assert isinstance(d["sectors"], list)
    assert isinstance(d["industries"], list)
    assert isinstance(d["basic_industries"], list)
    assert d["total"] > 0
    # Iteration 3: 3-level breakdown
    assert len(d["sectors"]) >= 5, f"expected ~11 sectors, got {len(d['sectors'])}"
    assert len(d["industries"]) >= 30, f"expected ~70 industries, got {len(d['industries'])}"
    assert len(d["basic_industries"]) >= 30, f"expected ~70 basic_industries, got {len(d['basic_industries'])}"
    if d["sectors"]:
        for k in ("sector", "count", "bullish", "purple_dots", "avg_rs_score"):
            assert k in d["sectors"][0], f"sectors[0] missing {k}"
    if d["industries"]:
        assert "industry" in d["industries"][0]
    if d["basic_industries"]:
        assert "basic_industry" in d["basic_industries"][0]


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
    # Iteration 3: history is real backfill output; empty list is a valid honest result.


# ---------------- Positions ----------------
def test_positions(api):
    # Iteration 3: positions table can be empty after wipe of DEMO_SEED rows.
    # The contract is: 200, available=True, rows is a list, NO row contains
    # 'DEMO_SEED' marker in its notes. summary key always present.
    r = api.get(f"{BASE_URL}/api/positions", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert d.get("available") is True
    assert "rows" in d and "summary" in d
    assert isinstance(d["rows"], list)
    for row in d["rows"]:
        notes = row.get("notes") or ""
        assert "DEMO_SEED" not in notes, f"position still has DEMO_SEED marker: {row}"


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


# ============== Iteration 3: new feature tests ==============

def test_positions_no_demo_seed_marker(api):
    """Iteration 3 (a): demo seed positions wiped — none should have DEMO_SEED marker."""
    r = api.get(f"{BASE_URL}/api/positions", timeout=TIMEOUT)
    assert r.status_code == 200
    rows = r.json().get("rows", [])
    seeds = [row for row in rows if "DEMO_SEED" in (row.get("notes") or "")]
    assert seeds == [], f"unexpected DEMO_SEED rows: {seeds}"


def test_universe_summary_three_level_breakdown(api):
    """Iteration 3 (c): /api/universe/summary returns sectors, industries, basic_industries."""
    r = api.get(f"{BASE_URL}/api/universe/summary", timeout=TIMEOUT)
    assert r.status_code == 200
    d = r.json()
    assert "sectors" in d and "industries" in d and "basic_industries" in d
    # Each entry has the breakdown shape
    if d["basic_industries"]:
        b0 = d["basic_industries"][0]
        for k in ("basic_industry", "count", "bullish", "purple_dots", "avg_rs_score"):
            assert k in b0, f"basic_industries[0] missing key {k}"


def test_watchlist_groww_has_real_data(api):
    """Iteration 3 (b): GROWW row must have non-null grade/rs_score/close/bucket and grade_history_5d list."""
    r = api.get(f"{BASE_URL}/api/watchlist", timeout=TIMEOUT)
    assert r.status_code == 200
    rows = r.json().get("rows", [])
    groww = [row for row in rows if row.get("symbol") == "GROWW"]
    assert groww, "GROWW not found in watchlist"
    g = groww[0]
    assert g.get("grade") is not None, f"GROWW grade is null: {g}"
    assert g.get("rs_score") is not None, f"GROWW rs_score is null: {g}"
    assert g.get("close") is not None, f"GROWW close is null: {g}"
    assert g.get("bucket") is not None, f"GROWW bucket is null: {g}"
    hist = g.get("grade_history_5d")
    assert isinstance(hist, list), f"grade_history_5d not a list: {hist}"
    assert len(hist) >= 1, f"grade_history_5d empty: {hist}"


def test_watchlist_add_unknown_yfinance_returns_400(api):
    """Iteration 3 (b): non-existent symbols rejected (yfinance returns no data)."""
    sym = "ZZZNOTREAL"
    # Pre-clean
    api.post(f"{BASE_URL}/api/watchlist/remove", json={"symbol": sym}, timeout=TIMEOUT)
    r = api.post(f"{BASE_URL}/api/watchlist/add", json={"symbol": sym}, timeout=TIMEOUT)
    assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
    body = r.json()
    detail = (body.get("detail") or "").lower()
    assert "unknown" in detail or "no data" in detail or "yfinance" in detail


def test_watchlist_add_auto_extends_universe(api):
    """Iteration 3 (b): real-but-not-in-universe symbol is auto-added to universe.csv,
    /api/universe lists it, and a background backfill produces ohlcv bars."""
    sym = "CONCORDBIO"  # Confirmed not in current universe.csv
    # Cleanup before
    api.post(f"{BASE_URL}/api/watchlist/remove", json={"symbol": sym}, timeout=TIMEOUT)
    try:
        r = api.post(f"{BASE_URL}/api/watchlist/add", json={"symbol": sym}, timeout=TIMEOUT)
        assert r.status_code == 200, f"add returned {r.status_code}: {r.text}"
        body = r.json()
        assert body.get("ok") is True
        # auto_added_to_universe is True only if it wasn't already present
        # (already-there case still legitimate after a prior test run)
        assert "auto_added_to_universe" in body

        # Universe must now include it
        u = api.get(f"{BASE_URL}/api/universe", timeout=TIMEOUT).json()
        syms = [r2.get("symbol") for r2 in u.get("rows", [])]
        assert sym in syms, f"{sym} not in universe after auto-extend"

        # Wait for background fetch+indicators
        bars = []
        for _ in range(8):  # up to ~24s
            time.sleep(3)
            sd = api.get(f"{BASE_URL}/api/symbol/{sym}", timeout=TIMEOUT)
            if sd.status_code == 200:
                jd = sd.json()
                if jd.get("available") and jd.get("bars"):
                    bars = jd["bars"]
                    break
        assert bars, f"no ohlcv bars returned for {sym} after backfill wait"
    finally:
        # Cleanup watchlist row (universe.csv stays — sticky on purpose)
        api.post(f"{BASE_URL}/api/watchlist/remove", json={"symbol": sym}, timeout=TIMEOUT)


def test_pipeline_backfill_starts(api):
    """Iteration 3: POST /api/pipeline/backfill kicks off backfill stage."""
    # If pipeline is already running, accept ok:false
    r = api.post(f"{BASE_URL}/api/pipeline/backfill", json={"days": 5}, timeout=TIMEOUT)
    assert r.status_code == 200, f"backfill returned {r.status_code}: {r.text}"
    body = r.json()
    assert "ok" in body
    # Snapshot status — should reference 'backfill' if it started
    time.sleep(1.5)
    s = api.get(f"{BASE_URL}/api/pipeline/status", timeout=TIMEOUT)
    assert s.status_code == 200
    sd = s.json()
    assert "current_stage" in sd
    assert "progress" in sd
    if body.get("ok") is True:
        # Either still running (backfill) or already finished and idle (None)
        assert sd.get("current_stage") in ("backfill", None)
