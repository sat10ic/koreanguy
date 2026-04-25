"""Iteration 4 — review_request specific tests.

Focus:
1. /api/watchlist/add with brand-new symbol (AVANTIFEED) — yfinance.info path
2. /api/watchlist/refresh_meta — with {} and with {symbol:CUPID}
3. /api/watchlist GET — rows have non-null sector/industry
4. /api/screen?sector=Financials — accepts filters w/o 500
5. Regression: existing endpoints don't crash (status 200, may be available:false)
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://friendly-finance-ui.preview.emergentagent.com").rstrip("/")
TIMEOUT = 60


@pytest.fixture(scope="session")
def api():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# -------- Endpoint regression: status 200 (available may be false) --------
@pytest.mark.parametrize("path", [
    "/api/health",
    "/api/regime",
    "/api/universe/summary",
    "/api/screen",
    "/api/rs_grid",
    "/api/candidates",
    "/api/positions",
    "/api/watchlist",
    "/api/pipeline/status",
    "/api/universe",
])
def test_endpoint_returns_200(api, path):
    r = api.get(f"{BASE_URL}{path}", timeout=TIMEOUT)
    assert r.status_code == 200, f"{path} returned {r.status_code}: {r.text[:200]}"
    j = r.json()
    assert isinstance(j, dict)


# -------- /api/screen accepts sector/industry/basic_industry filters --------
def test_screen_sector_filter_no_crash(api):
    r = api.get(f"{BASE_URL}/api/screen?sector=Financials", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    j = r.json()
    assert "rows" in j
    assert isinstance(j["rows"], list)


def test_screen_industry_filter_no_crash(api):
    r = api.get(f"{BASE_URL}/api/screen?industry=Brokerage", timeout=TIMEOUT)
    assert r.status_code == 200, r.text


def test_screen_basic_industry_filter_no_crash(api):
    r = api.get(f"{BASE_URL}/api/screen?basic_industry=Defense%20%26%20Aerospace", timeout=TIMEOUT)
    assert r.status_code == 200, r.text


# -------- /api/watchlist GET — rows have sector/industry --------
def test_watchlist_rows_have_sector_industry(api):
    r = api.get(f"{BASE_URL}/api/watchlist", timeout=TIMEOUT)
    assert r.status_code == 200
    rows = r.json().get("rows") or []
    # At minimum baseline 4 symbols
    found = {row["symbol"]: row for row in rows}
    expected = {
        "DATAPATTNS": ("Industrials", "Defense"),
        "TRENT": ("Consumer Discretionary", "Retail"),
        "CUPID": ("Consumer Defensive", "Household & Personal Products"),
        "GROWW": ("Financials", "Brokerage"),
    }
    for sym, (sec, ind) in expected.items():
        assert sym in found, f"{sym} missing from watchlist rows"
        assert found[sym].get("sector") == sec, f"{sym} sector = {found[sym].get('sector')!r}, expected {sec}"
        assert found[sym].get("industry") == ind, f"{sym} industry = {found[sym].get('industry')!r}, expected {ind}"


# -------- /api/watchlist/add for brand-new symbol — yfinance.info enriches --------
def test_watchlist_add_avantifeed_real_sector_industry(api):
    sym = "AVANTIFEED"
    # cleanup prior state
    api.post(f"{BASE_URL}/api/watchlist/remove", json={"symbol": sym}, timeout=TIMEOUT)
    try:
        r = api.post(f"{BASE_URL}/api/watchlist/add", json={"symbol": sym}, timeout=TIMEOUT)
        assert r.status_code == 200, f"add failed: {r.status_code} {r.text}"
        body = r.json()
        assert body.get("ok") is True

        # Now verify it shows up in GET /api/watchlist with real sector/industry
        # Allow brief settle for the universe.csv merge
        time.sleep(1.0)
        wr = api.get(f"{BASE_URL}/api/watchlist", timeout=TIMEOUT)
        assert wr.status_code == 200
        rows = wr.json().get("rows") or []
        found = next((row for row in rows if row.get("symbol") == sym), None)
        assert found is not None, f"{sym} not in /api/watchlist rows"
        sector = found.get("sector")
        industry = found.get("industry")
        assert sector and sector != "Uncategorised", f"{sym} sector still Uncategorised: {sector!r}"
        assert industry and industry != "Uncategorised", f"{sym} industry still Uncategorised: {industry!r}"
    finally:
        api.post(f"{BASE_URL}/api/watchlist/remove", json={"symbol": sym}, timeout=TIMEOUT)
        # also remove from universe.csv to keep state clean
        try:
            import csv
            path = "/app/universe.csv"
            with open(path) as f:
                rdr = list(csv.reader(f))
            kept = [r for r in rdr if r and r[0] != sym]
            with open(path, "w", newline="") as f:
                csv.writer(f).writerows(kept)
        except Exception as e:
            print(f"universe cleanup failed: {e}")


# -------- /api/watchlist/refresh_meta empty body — idempotent on good rows --------
def test_refresh_meta_empty_body_returns_ok(api):
    r = api.post(f"{BASE_URL}/api/watchlist/refresh_meta", json={}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert "updated" in body
    assert isinstance(body["updated"], list)


def test_refresh_meta_specific_symbol(api):
    r = api.post(f"{BASE_URL}/api/watchlist/refresh_meta", json={"symbol": "CUPID"}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("ok") is True
    assert "updated" in body
