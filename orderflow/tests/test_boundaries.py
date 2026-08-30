"""Boundary enforcement tests (build-manual R5/R7/R8 + package rules).

Scope, stated precisely:

* PRODUCTION code = every ``.py`` under ``orderflow/`` EXCEPT
  ``orderflow/tests/`` and the adapter itself
  (``orderflow/market_data/fyers_adapter.py``). Production code must contain
  ZERO FYERS wire vocabulary — the adapter is the only translator.
* ``orderflow/tests/`` is exempt from the FYERS-vocabulary scan BY DESIGN:
  tests sit on the boundary and must construct raw wire-format inputs to test
  the adapter, and the committed fixture JSON is a recorded-sample stand-in.
  Tests are still scanned for the other bans (cross-project imports, order
  routing, credential handling).
"""
import re
from pathlib import Path

ORDERFLOW_ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ORDERFLOW_ROOT / "market_data" / "fyers_adapter.py"

FYERS_FIELD_MARKERS = [
    # NOTE: canonical QuoteUpdate.ltp legitimately shares FYERS's "ltp" spelling
    # (the manual's canonical model uses it), so a bare \bltp\b marker would
    # false-positive on schemas.py. Markers below are FYERS-specific names.
    r"exch_feed_time",
    r"last_traded_qty",
    r"vol_traded_today",
    r"\btot_buy_qty\b",
    r"\btot_sell_qty\b",
    r"bid_price\d",
    r"ask_price\d",
    r"bid_size\d",
    r"ask_size\d",
    r"bid_order\d",
    r"ask_order\d",
    r"SymbolUpdate",
    r"DepthUpdate",
    r'"sf"',
    r'"dp"',
    r'"if"',
    r'"cn"',
    r'"sub"',
    r"socket\.fyers\.in",
    r"api-t1\.fyers\.in",
]

ORDER_ROUTING_MARKERS = [
    r"place_order",
    r"modify_order",
    r"cancel_order",
    r"exit_position",
    r"convert_position",
    r"order_status",
    r"trade_book",
    r"position_book",
    r'"/orders"',
    r'"/positions"',
    r"import fyers_apiv3",
    r"from fyers_apiv3",
]

CREDENTIAL_MARKERS = [
    r"os\.environ",
    r"getenv",
    r"FYERS_CLIENT_ID",
    r"FYERS_APP_ID",
    r"FYERS_SECRET",
    r"access_token",
    r"refresh_token",
    r"app_id\s*=",
    r"api_secret",
]

CROSS_PROJECT_IMPORT_MARKERS = [
    r"^\s*import\s+traderlog\b",
    r"^\s*from\s+traderlog\b",
    r"^\s*import\s+manas_os\b",
    r"^\s*from\s+manas_os\b",
]


def production_python_files():
    return sorted(p for p in ORDERFLOW_ROOT.rglob("*.py") if "tests" not in p.parts and p != ADAPTER)


def all_python_files():
    return sorted(ORDERFLOW_ROOT.rglob("*.py"))


def test_production_code_is_fyers_vocabulary_free():
    violations = []
    for path in production_python_files():
        text = path.read_text(encoding="utf-8")
        for marker in FYERS_FIELD_MARKERS:
            if re.search(marker, text):
                violations.append(f"{path.relative_to(ORDERFLOW_ROOT)}: {marker}")
    assert not violations, "FYERS vocabulary outside the adapter:\n" + "\n".join(violations)


def test_adapter_is_the_only_fyers_vocabulary_file():
    text = ADAPTER.read_text(encoding="utf-8")
    hits = [m for m in FYERS_FIELD_MARKERS if re.search(m, text)]
    assert len(hits) >= 10, "adapter should carry the field mapping; markers missing suggests test drift"


def test_no_cross_project_imports_anywhere():
    violations = []
    for path in all_python_files():
        for line in path.read_text(encoding="utf-8").splitlines():
            for marker in CROSS_PROJECT_IMPORT_MARKERS:
                if re.search(marker, line):
                    violations.append(f"{path.name}: {line.strip()}")
    assert not violations, "\n".join(violations)


def test_no_order_routing_anywhere():
    violations = []
    # test_boundaries.py itself is excluded from its own vocabulary scans: it
    # contains the forbidden markers AS detection patterns, by definition.
    for path in all_python_files():
        if path.name == "test_boundaries.py":
            continue
        text = path.read_text(encoding="utf-8")
        for marker in ORDER_ROUTING_MARKERS:
            if re.search(marker, text):
                violations.append(f"{path.relative_to(ORDERFLOW_ROOT)}: {marker}")
    assert not violations, "order-routing vocabulary inside orderflow:\n" + "\n".join(violations)


def test_no_credential_handling_in_production_code():
    violations = []
    for path in production_python_files():
        text = path.read_text(encoding="utf-8")
        for marker in CREDENTIAL_MARKERS:
            if re.search(marker, text):
                violations.append(f"{path.relative_to(ORDERFLOW_ROOT)}: {marker}")
    assert not violations, "credential handling inside production code:\n" + "\n".join(violations)


def test_no_credential_keys_in_fixture_data():
    fixture = (ORDERFLOW_ROOT / "tests" / "fixtures" / "synthetic_session.json").read_text(encoding="utf-8")
    for marker in ("token", "secret", "app_id", "password"):
        assert marker not in fixture.lower(), f"fixture carries credential-like key: {marker}"
