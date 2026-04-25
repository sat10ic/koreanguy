"""Iteration-7 backend tests — /api/watchlist/add_bulk + /api/watchlist/ipo_basket."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # Fallback to frontend/.env
    from pathlib import Path
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip().rstrip("/")


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# Baseline watchlist (from agent context): DATAPATTNS, TRENT, GROWW, CUPID
# Test cleanup: remove anything we added
BASELINE = {"DATAPATTNS", "TRENT", "GROWW", "CUPID"}


def _cleanup(client, syms):
    for s in syms:
        if s in BASELINE:
            continue
        try:
            client.post(f"{BASE_URL}/api/watchlist/remove", json={"symbol": s}, timeout=10)
        except Exception:
            pass


# ---- /api/watchlist/ipo_basket --------------------------------------------
class TestIpoBasket:
    def test_ipo_basket_returns_15(self, client):
        r = client.get(f"{BASE_URL}/api/watchlist/ipo_basket", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["count"] == 15
        assert isinstance(data["symbols"], list)
        assert len(data["symbols"]) == 15

    def test_ipo_basket_contains_expected(self, client):
        r = client.get(f"{BASE_URL}/api/watchlist/ipo_basket", timeout=10)
        syms = set(r.json()["symbols"])
        for expected in ["ATHERENERGY", "LENSKART", "HYUNDAI", "SWIGGY", "OLAELEC"]:
            assert expected in syms, f"{expected} missing from basket"


# ---- /api/watchlist/add_bulk ----------------------------------------------
class TestAddBulk:
    def test_bulk_add_list_in_universe(self, client):
        # INFY/TCS already in universe → fast path (no yfinance)
        r = client.post(
            f"{BASE_URL}/api/watchlist/add_bulk",
            json={"symbols": ["INFY", "TCS"]},
            timeout=30,
        )
        try:
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["ok"] is True
            assert data["total"] == 2
            assert data["added"] >= 0  # may be 0 if already in watchlist
            assert isinstance(data["results"], list) and len(data["results"]) == 2
            # each result has ok and symbol
            for res in data["results"]:
                assert "symbol" in res and "ok" in res
                assert res["ok"] is True
        finally:
            _cleanup(client, ["INFY", "TCS"])

    def test_bulk_add_empty_list_400(self, client):
        r = client.post(
            f"{BASE_URL}/api/watchlist/add_bulk",
            json={"symbols": []},
            timeout=10,
        )
        assert r.status_code == 400
        data = r.json()
        assert "symbols list required" in (data.get("detail") or "").lower()

    def test_bulk_add_string_with_commas(self, client):
        r = client.post(
            f"{BASE_URL}/api/watchlist/add_bulk",
            json={"symbols": "INFY,TCS,WIPRO"},
            timeout=30,
        )
        try:
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["ok"] is True
            assert data["total"] == 3
            syms = sorted(r["symbol"] for r in data["results"])
            assert syms == ["INFY", "TCS", "WIPRO"]
        finally:
            _cleanup(client, ["INFY", "TCS", "WIPRO"])

    def test_bulk_add_partial_failure_no_crash(self, client):
        # One bogus + one real (already in universe)
        bogus = "ZZBOGUSXX123"
        r = client.post(
            f"{BASE_URL}/api/watchlist/add_bulk",
            json={"symbols": [bogus, "INFY"]},
            timeout=60,  # bogus triggers yfinance lookup
        )
        try:
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["ok"] is True
            assert data["total"] == 2
            res_map = {r["symbol"]: r for r in data["results"]}
            # Real one ok
            assert res_map["INFY"]["ok"] is True
            # Bogus should fail (or at least not crash). Accept either ok=False
            # or ok=True with an "auto_added_to_universe" if yfinance somehow
            # resolves a fake symbol — but typically it fails.
            assert bogus in res_map
            if not res_map[bogus]["ok"]:
                assert "error" in res_map[bogus]
        finally:
            _cleanup(client, ["INFY", bogus])


# ---- Regression: existing endpoints still alive ---------------------------
class TestRegression:
    def test_health(self, client):
        r = client.get(f"{BASE_URL}/api/health", timeout=10)
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_screen_has_buying_force_sort(self, client):
        r = client.get(
            f"{BASE_URL}/api/screen",
            params={"sort_by": "buying_force_score", "sort_desc": True, "limit": 10},
            timeout=15,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["available"] is True
        rows = data["rows"]
        assert len(rows) > 0
        # Top row should have buying_force_score field
        assert "buying_force_score" in rows[0]

    def test_candidates_endpoint(self, client):
        r = client.get(f"{BASE_URL}/api/candidates", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert "primary" in data and "secondary" in data

    def test_watchlist_baseline(self, client):
        r = client.get(f"{BASE_URL}/api/watchlist", timeout=20)
        assert r.status_code == 200
        data = r.json()
        rows = data["rows"]
        syms = {r["symbol"] for r in rows}
        # At least baseline present
        for b in BASELINE:
            assert b in syms, f"baseline {b} missing"
