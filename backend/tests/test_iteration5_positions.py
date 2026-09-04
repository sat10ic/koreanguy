"""Iteration-5 tests: rs_grid NaN scrub fix + manual position management.

Covers:
- /api/rs_grid HTTP 200 + structure (16 grade keys)
- /api/positions/add (success + validation errors)
- /api/positions/{id}/update (success + 404)
- /api/positions/{id}/exit (success + invalid state)
- /api/positions/{id}/delete (success + 404)
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://friendly-finance-ui.preview.emergentagent.com").rstrip("/")


@pytest.fixture(scope="module")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---- RS Grid (previously crashing with NaN) -------------------------------
class TestRSGrid:
    def test_rs_grid_returns_200_after_pipeline(self, api):
        r = api.get(f"{BASE_URL}/api/rs_grid", timeout=20)
        assert r.status_code == 200, f"expected 200, got {r.status_code} body={r.text[:300]}"
        d = r.json()
        assert d.get("available") is True
        assert isinstance(d.get("counts"), dict) and len(d["counts"]) == 16, \
            f"counts must have 16 grade bands, got {len(d.get('counts',{}))}"
        assert isinstance(d.get("grades"), dict) and len(d["grades"]) == 16
        # Pick one grade band that has stocks; verify symbol records are JSON-serialisable (no NaN/Inf)
        non_empty = [g for g, lst in d["grades"].items() if lst]
        assert non_empty, "expected at least one grade band with stocks"
        sample = d["grades"][non_empty[0]][0]
        assert "symbol" in sample
        # Ensure no nan token shows up in the JSON-encoded payload
        assert "NaN" not in r.text and "Infinity" not in r.text


# ---- Position add ---------------------------------------------------------
class TestPositionAdd:
    def test_add_success(self, api, request):
        body = {
            "symbol": "TEST_LENSKART",
            "entry_price": 520,
            "stop_price": 485,
            "size_shares": 50,
            "entry_grade": "B",
            "regime_at_entry": "RISK_ON",
            "notes": "test",
        }
        r = api.post(f"{BASE_URL}/api/positions/add", json=body, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True and d["state"] == "ACTIVE" and isinstance(d["id"], int)
        pid = d["id"]
        request.config._created_pid = pid

        # GET /api/positions verifies persistence
        g = api.get(f"{BASE_URL}/api/positions", timeout=15).json()
        rows = g.get("rows", [])
        match = [r for r in rows if r["id"] == pid]
        assert len(match) == 1
        assert match[0]["symbol"] == "TEST_LENSKART"
        assert float(match[0]["entry_price"]) == 520
        assert float(match[0]["stop_price"]) == 485
        assert match[0]["state"] == "ACTIVE"

    def test_missing_symbol(self, api):
        r = api.post(f"{BASE_URL}/api/positions/add",
                     json={"entry_price": 100, "stop_price": 90}, timeout=10)
        assert r.status_code == 400

    def test_missing_entry_price(self, api):
        r = api.post(f"{BASE_URL}/api/positions/add",
                     json={"symbol": "X", "stop_price": 90}, timeout=10)
        assert r.status_code == 400

    def test_stop_above_entry(self, api):
        r = api.post(f"{BASE_URL}/api/positions/add",
                     json={"symbol": "X", "entry_price": 100, "stop_price": 110}, timeout=10)
        assert r.status_code == 400
        # Body must contain the message (fastapi default detail key)
        body_lower = r.text.lower()
        assert "must be below entry_price for a long".lower() in body_lower

    def test_invalid_state(self, api):
        r = api.post(
            f"{BASE_URL}/api/positions/add",
            json={"symbol": "X", "entry_price": 100, "stop_price": 90, "state": "BOGUS"},
            timeout=10,
        )
        assert r.status_code == 400


# ---- Position update / exit / delete -------------------------------------
class TestPositionLifecycle:
    @pytest.fixture(scope="class")
    def pid(self, api):
        body = {"symbol": "TEST_LIFECYCLE", "entry_price": 520, "stop_price": 485,
                "size_shares": 50, "entry_grade": "B", "regime_at_entry": "RISK_ON"}
        r = api.post(f"{BASE_URL}/api/positions/add", json=body, timeout=15)
        assert r.status_code == 200, r.text
        return r.json()["id"]

    def test_update_stop_price(self, api, pid):
        r = api.post(f"{BASE_URL}/api/positions/{pid}/update",
                     json={"stop_price": 495}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True and "stop_price" in d.get("updated_fields", [])

        # verify persistence
        g = api.get(f"{BASE_URL}/api/positions", timeout=15).json()
        row = [r for r in g["rows"] if r["id"] == pid][0]
        assert float(row["stop_price"]) == 495

    def test_update_404(self, api):
        r = api.post(f"{BASE_URL}/api/positions/9999999/update",
                     json={"stop_price": 100}, timeout=10)
        assert r.status_code == 404

    def test_exit_invalid_state(self, api, pid):
        r = api.post(f"{BASE_URL}/api/positions/{pid}/exit",
                     json={"exit_price": 545, "state": "EXITED_NOTREAL"}, timeout=10)
        # state must start with EXITED_ — EXITED_NOTREAL passes that check actually,
        # so our test should use a state that doesn't startswith EXITED_
        # Per review_request, EXITED_NOTREAL must return 400.
        # The implementation only blocks states not starting with EXITED_,
        # so EXITED_NOTREAL would be accepted. Verify behaviour:
        # Adjusting: review request says it must return 400; report if implementation differs.
        # We assert what the spec demands.
        assert r.status_code == 400, \
            f"spec says EXITED_NOTREAL must be rejected; got {r.status_code} body={r.text[:200]}"

    def test_exit_success(self, api, pid):
        r = api.post(f"{BASE_URL}/api/positions/{pid}/exit",
                     json={"exit_price": 545, "state": "EXITED_MANUAL"}, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["ok"] is True and d["state"] == "EXITED_MANUAL"
        # pnl_pct ≈ (545-520)/520 = 0.048077
        assert abs(d["pnl_pct"] - 0.048077) < 1e-4

        g = api.get(f"{BASE_URL}/api/positions", timeout=15).json()
        row = [r for r in g["rows"] if r["id"] == pid][0]
        assert row["state"] == "EXITED_MANUAL"
        assert row["exit_date"] is not None

    def test_delete_success(self, api, pid):
        r = api.post(f"{BASE_URL}/api/positions/{pid}/delete", timeout=10)
        assert r.status_code == 200, r.text
        assert r.json()["ok"] is True
        g = api.get(f"{BASE_URL}/api/positions", timeout=15).json()
        ids = [r["id"] for r in g.get("rows", [])]
        assert pid not in ids

    def test_delete_404(self, api):
        r = api.post(f"{BASE_URL}/api/positions/9999999/delete", timeout=10)
        assert r.status_code == 404


# ---- Cleanup -------------------------------------------------------------
def test_zzz_cleanup(api):
    """Best-effort cleanup of any leftover TEST_ rows."""
    g = api.get(f"{BASE_URL}/api/positions", timeout=15).json()
    for row in g.get("rows", []):
        if str(row.get("symbol", "")).startswith("TEST_") or str(row.get("symbol", "")) == "TESTPOS":
            api.post(f"{BASE_URL}/api/positions/{row['id']}/delete", timeout=10)
