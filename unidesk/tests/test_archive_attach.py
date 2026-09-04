"""Directive-1f basis-correctness proof: the archive-wide outcome attach
must not fall into the trap flagged by the 2026-08-30 Opus pre-flight --
a future map built without the same adjustment basis as the frozen
snapshot silently lands every adjusted symbol UNRESOLVED.

Real archive data only (``data/bhavcopy``), no synthetic fixtures. One
ingest, shared across the module (ingest is ~20-30s; re-ingesting per test
would multiply that for no benefit -- the store is read-only after ingest).

Three real cases, per directive-1f:
1. BEML -- IS in confirmed_actions.csv (ex_date 2025-11-03). Both snapshot
   and future map must carry adjusted=True with the SAME ca_table_hash, and
   the event must resolve to a real outcome (not adjustment_basis_mismatch).
2. AMIORG -- IS in the 190-session unconfirmed-CA backlog (detector-flagged
   gap on 2025-04-25, unconfirmed). A decision session whose outcome window
   spans that gap must land UNRESOLVED/unconfirmed_corporate_action, never
   a fabricated MAE/loss.
3. TITAN -- plain symbol, no CA history at all (not in
   confirmed_actions.csv, not in the unconfirmed backlog; verified: zero
   detector flags over its full EQ history). Both sides'
   basis default to adjusted=False (a no-op basis match) and the event
   resolves normally.
   (B2-2, 2026-09-03: this case previously used TCS, assumed plain — but
   TCS carries a REAL unconfirmed 1:1 bonus ex-date 2018-05-31 that the
   detector flags correctly; see the test's own docstring.)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from unidesk.momentum.data.bhavcopy import ingest_directory
from unidesk.momentum.data.corp_actions import load_confirmed_actions
from unidesk.momentum.data.market_store import InMemoryMarketStore
from unidesk.momentum.data.splits import scan_store_for_splits, unconfirmed_candidate_sessions
from unidesk.momentum.scan import scan_universe
from unidesk.research.archive_attach import _as_of_for_session, build_future_map
from unidesk.research.candidates import attach_outcomes, config_hash_for, freeze_scan

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKLOG = REPO_ROOT / "data" / "bhavcopy"


@pytest.fixture(scope="module")
def real_store():
    if not BACKLOG.is_dir():
        pytest.skip(f"real archive not present at {BACKLOG}")
    store = InMemoryMarketStore()
    stats = ingest_directory(store, BACKLOG)
    if stats["bars_added"] < 100_000:
        pytest.skip("real archive too small to be the actual corpus")
    return store


@pytest.fixture(scope="module")
def real_actions():
    return load_confirmed_actions()


@pytest.fixture(scope="module")
def real_future_map(real_store, real_actions):
    return build_future_map(real_store, real_actions)


@pytest.fixture(scope="module")
def real_ca_backlog(real_store, real_actions):
    candidates = scan_store_for_splits(real_store)
    return unconfirmed_candidate_sessions(candidates, real_actions)


def _sessions_for(store: InMemoryMarketStore, symbol: str) -> list:
    return sorted(b.bar.session for b in store._daily if b.bar.symbol == symbol)


def _event_for(store, actions, symbol, decision_session, future_map, backlog, horizon=10):
    as_of = _as_of_for_session(decision_session)
    scan = scan_universe(store, as_of, actions=actions)
    row = next((s for s in scan.symbols if s.symbol == symbol), None)
    assert row is not None, f"{symbol} not scanned at {decision_session} (insufficient history?)"
    cfg = config_hash_for(scan)
    events = freeze_scan(scan, config_hash=cfg)
    ev = next(e for e in events if e.symbol == symbol)
    labeled = attach_outcomes(
        [ev], future_map, horizon=horizon, unconfirmed_ca_sessions=backlog,
    )
    return labeled[0], row


def test_confirmed_action_symbol_gets_real_outcome_not_basis_mismatch(
    real_store, real_actions, real_future_map, real_ca_backlog,
):
    symbol = "BEML"
    assert symbol in {a.symbol for a in real_actions}, "fixture assumption: BEML is confirmed"
    sessions = _sessions_for(real_store, symbol)
    decision = sessions[300]
    labeled, row = _event_for(
        real_store, real_actions, symbol, decision, real_future_map, real_ca_backlog,
    )
    # Snapshot and future map must agree on the adjustment basis.
    assert row.adjusted is True, "BEML should be CA-adjusted at this scan (confirmed action applies)"
    assert real_future_map[symbol]["adjusted"] is True
    assert labeled.snapshot["ca_table_hash"] == real_future_map[symbol]["ca_table_hash"]
    # The trap this test guards against: a basis mismatch would silently
    # land this UNRESOLVED with reason adjustment_basis_mismatch.
    assert labeled.outcome_labels.get("reason") != "adjustment_basis_mismatch", labeled.outcome_labels
    assert labeled.outcome_labels["status"] in ("RESOLVED", "PARTIAL"), labeled.outcome_labels
    assert "r_multiple" in labeled.outcome_labels


def test_unconfirmed_backlog_symbol_lands_unconfirmed_not_fabricated_loss(
    real_store, real_actions, real_future_map, real_ca_backlog,
):
    symbol = "AMIORG"
    assert symbol in real_ca_backlog, "fixture assumption: AMIORG is in the unconfirmed backlog"
    gap_sessions = real_ca_backlog[symbol]
    sessions = _sessions_for(real_store, symbol)
    # A decision 5 sessions before the flagged gap puts the gap inside a
    # horizon=10 outcome window without falling off the end of AMIORG's
    # short real history.
    gap_idx = min(sessions.index(g) for g in gap_sessions if g in sessions)
    decision_idx = gap_idx - 5
    assert decision_idx >= 61, "need enough prior history for scan_universe's floor"
    decision = sessions[decision_idx]
    labeled, row = _event_for(
        real_store, real_actions, symbol, decision, real_future_map, real_ca_backlog,
    )
    assert labeled.outcome_labels["status"] == "UNRESOLVED", labeled.outcome_labels
    assert labeled.outcome_labels["reason"] == "unconfirmed_corporate_action", labeled.outcome_labels
    # Negative control: without the backlog wired in, the same event would
    # NOT be caught by this guard (proves the guard is load-bearing, not
    # a tautology of some other refusal reason).
    as_of = _as_of_for_session(decision)
    scan = scan_universe(real_store, as_of, actions=real_actions)
    cfg = config_hash_for(scan)
    events = freeze_scan(scan, config_hash=cfg)
    ev = next(e for e in events if e.symbol == symbol)
    unguarded = attach_outcomes([ev], real_future_map, horizon=10)[0]
    assert unguarded.outcome_labels.get("reason") != "unconfirmed_corporate_action"


def test_plain_symbol_no_ca_history_resolves_with_no_op_basis(
    real_store, real_actions, real_future_map, real_ca_backlog,
):
    """Directive-1f case 3: a symbol with genuinely NO corporate-action
    history resolves with a no-op (adjusted=False on both sides) basis.

    B2-2 correction (2026-09-03): the fixture symbol here was TCS, assumed
    "plain symbol, no CA history at all". That assumption is FALSE against
    the real corpus — TCS gapped -50.7% at the open on 2018-05-31 (the
    ex-date of its real 1:1 bonus), on ~3x volume, and never recovered.
    The bar-shape detector therefore flags TCS CORRECTLY: it is a real
    corporate action that confirmed_actions.csv does not carry. The ratio
    source is owner-gated (ratios are never inferred from price gaps), so
    no agent may add that action; until the owner confirms it from an
    official source, TCS must stay UNRESOLVED — that is the guard working,
    not a detector false positive. The full-corpus sweep found ~1,598
    flagged sessions across 934 symbols against a 4-row confirmed table;
    tightening the detector to unflag TCS would unflag equally-shaped real
    actions (AMIORG) and was rejected. TITAN is the verified-plain fixture:
    zero detector flags over its full 4,034-bar EQ history, no confirmed
    action.
    """
    symbol = "TITAN"
    assert symbol not in {a.symbol for a in real_actions}
    assert symbol not in real_ca_backlog
    sessions = _sessions_for(real_store, symbol)
    decision = sessions[300]
    labeled, row = _event_for(
        real_store, real_actions, symbol, decision, real_future_map, real_ca_backlog,
    )
    assert row.adjusted is False
    assert real_future_map[symbol]["adjusted"] is False
    assert labeled.outcome_labels.get("reason") != "adjustment_basis_mismatch"
    assert labeled.outcome_labels["status"] in ("RESOLVED", "PARTIAL"), labeled.outcome_labels

    # Regression guard for the finding above: TCS's 2018-05-31 1:1 bonus is a
    # TRUE detector positive. If this ever flips because the detector was
    # loosened on bar shape alone, real unconfirmed actions would silently
    # flow into outcome labels as fabricated losses/gains.
    assert "TCS" in real_ca_backlog
