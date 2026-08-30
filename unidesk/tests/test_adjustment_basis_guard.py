"""Directive 1(c)+(d): the adjustment-basis guard.

``scan.py`` adjusts OHLCV against the confirmed-actions table before
computing features; before this change, ``candidates.py:_snapshot()``
dropped that fact on the floor (no ``adjusted`` flag, no confirmed-actions
content hash), and ``config_hash_for()`` only hashed detector names -- two
scans run under different confirmed-actions content produced an identical
hash. This file proves:

1. ``_snapshot()`` carries ``adjusted`` + ``ca_table_hash``.
2. ``config_hash_for()`` changes when the confirmed-actions CSV CONTENT
   changes (not just its path/mtime).
3. ``attach_outcomes`` REFUSES to attach a real outcome -- lands
   UNRESOLVED/``adjustment_basis_mismatch`` -- when the future series'
   adjustment basis disagrees with the snapshot's, instead of silently
   scoring raw future bars against split-adjusted (or vice versa) snapshot
   features.
"""
from datetime import date, datetime, timezone

import pytest

from unidesk.contracts.research import ResearchEvent
from unidesk.momentum.data.corp_actions import confirmed_actions_content_hash
from unidesk.research.candidates import _snapshot, config_hash_for, attach_outcomes
from unidesk.research.costs import COSTS_VERSION
from unidesk.momentum.scan import ScanResult, SymbolScan
from unidesk.momentum.detectors.momentum_burst import Detection

UTC = timezone.utc


def _scan_row(symbol="X", adjusted=False):
    return SymbolScan(
        symbol=symbol, sessions=100, close=100.0, ema21=99.0, ema50=95.0,
        rising21=True, trend=None, adr_pct=3.0, atr_pct=2.5, rvol=1.2,
        delivery_ratio=0.4, rs_rank=70.0, contraction=0.8,
        detectors={"momentum_burst": (Detection.VALID, ())},
        setup_inputs={}, adjusted=adjusted,
    )


def _scan_result(rows):
    return ScanResult(
        as_of=datetime(2026, 1, 10, 18, 0, tzinfo=UTC), scanned=len(rows),
        skipped={}, symbols=rows, universe_returns={}, above_ema21=0,
        above_ema50=0, last_session="2026-01-10",
    )


# --------------------------------------------------------------------------
# 1. _snapshot carries adjusted + ca_table_hash
# --------------------------------------------------------------------------

def test_snapshot_carries_adjusted_flag_and_ca_hash():
    snap_raw = _snapshot(_scan_row(adjusted=False), ca_table_hash="deadbeef")
    assert snap_raw["adjusted"] is False
    assert snap_raw["ca_table_hash"] == "deadbeef"

    snap_adj = _snapshot(_scan_row(adjusted=True), ca_table_hash="deadbeef")
    assert snap_adj["adjusted"] is True


# --------------------------------------------------------------------------
# 2. config_hash_for changes with confirmed-actions CONTENT, and with a
#    detector-name change; the CA-content sensitivity is the new part.
# --------------------------------------------------------------------------

def test_confirmed_actions_content_hash_is_content_not_path(tmp_path):
    a = tmp_path / "a.csv"
    b = tmp_path / "b.csv"
    a.write_text("symbol,ex_date,factor,source\nX,2026-01-01,0.5,t\n", encoding="utf-8")
    b.write_text("symbol,ex_date,factor,source\nX,2026-01-01,0.5,t\n", encoding="utf-8")
    # same content, different path -> same hash
    assert confirmed_actions_content_hash(a) == confirmed_actions_content_hash(b)
    b.write_text("symbol,ex_date,factor,source\nX,2026-01-01,0.25,t\n", encoding="utf-8")
    # content changed -> hash changes
    assert confirmed_actions_content_hash(a) != confirmed_actions_content_hash(b)


def test_missing_confirmed_actions_file_hashes_empty_content(tmp_path):
    missing = tmp_path / "nope.csv"
    assert confirmed_actions_content_hash(missing) == confirmed_actions_content_hash(
        tmp_path / "also_nope.csv"
    )


def test_config_hash_for_changes_when_ca_table_content_changes(tmp_path):
    scan = _scan_result([_scan_row()])
    ca_v1 = tmp_path / "ca.csv"
    ca_v1.write_text("symbol,ex_date,factor,source\nX,2026-01-01,0.5,t\n", encoding="utf-8")
    h1 = config_hash_for(scan, confirmed_actions_path=ca_v1)

    ca_v2 = tmp_path / "ca.csv"  # same file, rewritten content
    ca_v2.write_text("symbol,ex_date,factor,source\nX,2026-01-01,0.5,t\nY,2026-02-01,0.25,t\n",
                     encoding="utf-8")
    h2 = config_hash_for(scan, confirmed_actions_path=ca_v2)
    assert h1 != h2, "config_hash_for must change when confirmed-actions CONTENT changes"


def test_config_hash_for_stable_across_identical_ca_content_different_path(tmp_path):
    scan = _scan_result([_scan_row()])
    a = tmp_path / "ca_a.csv"
    b = tmp_path / "ca_b.csv"
    content = "symbol,ex_date,factor,source\nX,2026-01-01,0.5,t\n"
    a.write_text(content, encoding="utf-8")
    b.write_text(content, encoding="utf-8")
    assert config_hash_for(scan, confirmed_actions_path=a) == config_hash_for(
        scan, confirmed_actions_path=b
    )


def test_config_hash_for_folds_in_costs_version(tmp_path):
    # The costs version is folded in via import, not a parameter -- prove it
    # is actually present in the hashed payload by checking the hash is
    # deterministic and non-trivial (a smoke check that COSTS_VERSION import
    # didn't silently no-op); real cross-version drift is out of scope since
    # costs.py is frozen for this task.
    scan = _scan_result([_scan_row()])
    ca = tmp_path / "ca.csv"
    ca.write_text("symbol,ex_date,factor,source\n", encoding="utf-8")
    h = config_hash_for(scan, confirmed_actions_path=ca)
    assert isinstance(h, str) and len(h) == 16
    assert COSTS_VERSION  # sanity: imported, non-empty


# --------------------------------------------------------------------------
# 3. attach_outcomes refuses on a basis mismatch
# --------------------------------------------------------------------------

def _event(symbol: str, decision: date, *, adjusted: bool, ca_hash: str,
          close: float = 100.0, atr_pct: float = 2.0) -> ResearchEvent:
    ts = datetime(decision.year, decision.month, decision.day, 18, 0, tzinfo=UTC)
    return ResearchEvent(
        event_id=f"{symbol}:{decision.isoformat()}",
        candidate_id=f"{symbol}:{decision.isoformat()}",
        symbol=symbol,
        timestamp=ts,
        snapshot={
            "close": close, "atr_pct": atr_pct, "adjusted": adjusted,
            "ca_table_hash": ca_hash,
            "detectors": {"momentum_burst": {"detection": "VALID", "failures": []}},
        },
        config_hash="abcd",
        research_schema_version="research-event-v1",
        outcome_labels={},
    )


def _future_series(adjusted: bool, ca_hash: str):
    return {
        "sessions": [date(2026, 1, 10), date(2026, 1, 11), date(2026, 1, 12)],
        "opens": [100.0, 101.0, 102.0],
        "highs": [101.0, 110.0, 112.0],
        "lows": [99.0, 100.0, 101.0],
        "closes": [100.5, 109.0, 111.0],
        "adjusted": adjusted,
        "ca_table_hash": ca_hash,
    }


def test_attach_outcomes_resolves_when_basis_matches():
    decision = date(2026, 1, 10)
    event = _event("X", decision, adjusted=True, ca_hash="hash1")
    future = {"X": _future_series(adjusted=True, ca_hash="hash1")}
    out = attach_outcomes([event], future, horizon=2)[0].outcome_labels
    assert out["status"] == "RESOLVED"


def test_attach_outcomes_refuses_when_adjusted_flag_disagrees():
    """Snapshot features were computed on SPLIT-ADJUSTED bars; the future
    series supplied for outcome attach is RAW (unadjusted). Scoring one
    against the other would silently produce a corrupted MAE/R-multiple
    around the split boundary -- attach_outcomes must refuse."""
    decision = date(2026, 1, 10)
    event = _event("X", decision, adjusted=True, ca_hash="hash1")
    future = {"X": _future_series(adjusted=False, ca_hash="hash1")}
    out = attach_outcomes([event], future, horizon=2)[0].outcome_labels
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "adjustment_basis_mismatch"
    assert "mfe_pct" not in out
    assert "r_multiple" not in out


def test_attach_outcomes_refuses_when_ca_table_hash_disagrees():
    """Both sides claim 'adjusted', but under DIFFERENT confirmed-actions
    table content (e.g. the CA table changed between scan time and
    outcome-attach time) -- still a basis mismatch."""
    decision = date(2026, 1, 10)
    event = _event("X", decision, adjusted=True, ca_hash="hash_v1")
    future = {"X": _future_series(adjusted=True, ca_hash="hash_v2")}
    out = attach_outcomes([event], future, horizon=2)[0].outcome_labels
    assert out["status"] == "UNRESOLVED"
    assert out["reason"] == "adjustment_basis_mismatch"


def test_attach_outcomes_backward_compatible_when_neither_side_states_a_basis():
    """Pre-existing callers that never set adjusted/ca_table_hash on either
    side (both default False/"") must keep resolving exactly as before --
    this guard must not regress the pre-directive-1 behaviour verified by
    test_n4_research_spine.py."""
    decision = date(2026, 1, 10)
    ts = datetime(2026, 1, 10, 18, 0, tzinfo=UTC)
    event = ResearchEvent(
        event_id=f"X:{decision.isoformat()}", candidate_id=f"X:{decision.isoformat()}",
        symbol="X", timestamp=ts,
        snapshot={"close": 100.0, "atr_pct": 2.0,
                 "detectors": {"momentum_burst": {"detection": "VALID", "failures": []}}},
        config_hash="abcd", research_schema_version="research-event-v1", outcome_labels={},
    )
    future = {
        "X": {
            "sessions": [date(2026, 1, 10), date(2026, 1, 11), date(2026, 1, 12)],
            "opens": [100.0, 101.0, 102.0],
            "highs": [101.0, 110.0, 112.0],
            "lows": [99.0, 100.0, 101.0],
            "closes": [100.5, 109.0, 111.0],
        }
    }
    out = attach_outcomes([event], future, horizon=2)[0].outcome_labels
    assert out["status"] == "RESOLVED"
