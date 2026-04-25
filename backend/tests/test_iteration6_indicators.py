"""
Iteration-6 backend tests:
- Indicator fields: adr14_pct, adr20_pct, vol_ratio_20, buying_force_score, bf_score_30d_max
- Sector RS: sector_rs_pct (0..1), sector_rs_avg
- /api/symbol/{sym} bars include new fields
- /api/watchlist surfaces new screen fields
- _db.init_schemas idempotent
- Regression: rs_grid, watchlist add/remove/refresh_meta
"""
import os
import sys
import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://friendly-finance-ui.preview.emergentagent.com",
).rstrip("/")

sys.path.insert(0, "/app")


@pytest.fixture(scope="module")
def screen_payload():
    r = requests.get(f"{BASE_URL}/api/screen", timeout=30)
    assert r.status_code == 200, r.text
    return r.json()


# ---------- /api/screen new indicator + sector_rs columns ----------
class TestScreenIndicators:
    def test_screen_has_rows(self, screen_payload):
        assert "rows" in screen_payload
        assert len(screen_payload["rows"]) > 0

    def test_screen_indicator_fields_non_null(self, screen_payload):
        rows = screen_payload["rows"]
        for k in ["adr14_pct", "adr20_pct", "vol_ratio_20",
                  "buying_force_score", "bf_score_30d_max"]:
            non_null = [r for r in rows if r.get(k) is not None]
            assert len(non_null) > 0, f"{k} missing on every row"
            # numeric
            assert isinstance(non_null[0][k], (int, float))

    def test_screen_sector_rs_pct_in_unit_range(self, screen_payload):
        rows = screen_payload["rows"]
        bad = [r for r in rows if r.get("sector_rs_pct") is not None
               and not (0.0 <= r["sector_rs_pct"] <= 1.0)]
        assert not bad, f"sector_rs_pct out of [0,1]: {len(bad)}"
        # at least some non-null
        assert any(r.get("sector_rs_pct") is not None for r in rows)

    def test_screen_sector_rs_avg_numeric(self, screen_payload):
        rows = screen_payload["rows"]
        nums = [r["sector_rs_avg"] for r in rows if r.get("sector_rs_avg") is not None]
        assert nums, "sector_rs_avg never populated"
        assert all(isinstance(v, (int, float)) for v in nums)


# ---------- /api/symbol/{sym} bars carry new fields ----------
class TestSymbolDetailBars:
    def test_groww_bars_have_new_fields(self):
        r = requests.get(f"{BASE_URL}/api/symbol/GROWW?days=240", timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d.get("available") is True
        bars = d.get("bars", [])
        assert len(bars) > 50
        last = bars[-1]
        for k in ["adr14_pct", "adr20_pct", "vol_ratio_20",
                  "buying_force_score", "bf_score_30d_max"]:
            assert k in last, f"{k} missing from bar"
        # at least one bar should have non-null adr14_pct
        assert any(b.get("adr14_pct") is not None for b in bars)

    def test_groww_purple_dots_present(self):
        r = requests.get(f"{BASE_URL}/api/symbol/GROWW?days=30", timeout=30)
        d = r.json()
        # purple_dot column should exist (key present)
        assert "purple_dot" in d["bars"][-1]


# ---------- /api/watchlist enrichment ----------
class TestWatchlistEnrichment:
    def test_watchlist_rows_have_new_cols(self):
        r = requests.get(f"{BASE_URL}/api/watchlist", timeout=15)
        assert r.status_code == 200
        rows = r.json().get("rows", [])
        assert len(rows) >= 1
        for row in rows:
            for k in ["adr14_pct", "vol_ratio_20", "bf_score_30d_max", "sector_rs_pct"]:
                assert k in row, f"{k} missing from watchlist row {row.get('symbol')}"


# ---------- _db.init_schemas idempotent ----------
class TestDbSchemaIdempotent:
    def test_init_schemas_callable_twice(self):
        from scripts._db import init_schemas
        init_schemas()
        init_schemas()  # second call must not error (ALTER TABLE ADD COLUMN guarded)


# ---------- Regression ----------
class TestRegression:
    def test_rs_grid_ok(self):
        r = requests.get(f"{BASE_URL}/api/rs_grid", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("available") is True
        assert len(d.get("counts", {})) == 16

    def test_watchlist_refresh_meta(self):
        r = requests.post(f"{BASE_URL}/api/watchlist/refresh_meta", timeout=60)
        assert r.status_code == 200
        d = r.json()
        assert d.get("ok") is True

    def test_watchlist_add_remove_existing_symbol(self):
        # Add CUPID (already in baseline) → should be idempotent (200)
        r = requests.post(f"{BASE_URL}/api/watchlist/add",
                          json={"symbol": "CUPID"}, timeout=15)
        assert r.status_code == 200, r.text

    def test_positions_endpoint_alive(self):
        r = requests.get(f"{BASE_URL}/api/positions", timeout=10)
        assert r.status_code == 200
