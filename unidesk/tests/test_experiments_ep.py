"""Experiment A/B engine + T5 EP signature tests (N5 prerequisites)."""
import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.detectors.ep_signature import ep_signature
from unidesk.research.experiments import Trade, book_stats, compare_edge


# ------------------------------------------------------------------ books


def T(sym, day, net):
    return Trade(symbol=sym, entry_session=day, net_bps=net)


def test_book_stats_hand_computed():
    s = book_stats([T("A", "2026-07-01", 200.0), T("B", "2026-07-01", -50.0),
                    T("C", "2026-07-02", 100.0)])
    assert s.n == 3
    assert s.net_expectancy_bps == pytest.approx(250.0 / 3)
    assert s.win_rate == pytest.approx(2 / 3, rel=1e-3)   # rounded to 4dp
    assert s.profit_factor == pytest.approx(300.0 / 50.0)
    assert s.avg_win_bps == pytest.approx(150.0)
    assert s.avg_loss_bps == pytest.approx(-50.0)


def test_book_stats_all_losses_profit_factor_zero():
    s = book_stats([T("A", "d1", -10.0)])
    assert s.profit_factor == 0.0


def test_book_stats_empty_rejected():
    with pytest.raises(ContractError):
        book_stats([])


def test_compare_edge_beats_baseline():
    cand = [T("A", "d1", 300.0)] * 40
    base = [T("B", "d1", 100.0)] * 40
    v = compare_edge(cand, base, label="T1-vs-breakout", min_n=30)
    assert v.beats_baseline_net is True
    assert v.verdict == "KEEP_CANDIDATE"


def test_insufficient_n_verdict():
    v = compare_edge([T("A", "d1", 300.0)] * 5, [T("B", "d1", 100.0)] * 40, min_n=30)
    assert v.verdict == "INSUFFICIENT_N"


def test_baseline_wins_verdict():
    v = compare_edge([T("A", "d1", 50.0)] * 40, [T("B", "d1", 100.0)] * 40, min_n=30)
    assert v.verdict == "BASELINE_WINS"


def test_baseline_wins_is_the_kill_rule_not_a_shame():
    """R-H: the whole point — the engine must be ABLE to rule against the
    candidate, and the verdict names it plainly."""
    v = compare_edge([T("A", "d1", -100.0)] * 40, [T("B", "d1", 10.0)] * 40, min_n=30)
    assert v.verdict == "BASELINE_WINS"


# ------------------------------------------------------------------ T5 S_ep


def test_ep_signature_strong_day_scores_high():
    d = ep_signature(symbol="X", session="2026-08-28", gap_pct=10.0, rvol=4.0,
                     close_loc=0.9, prior_compression_pctile=30.0,
                     delivery_shock=3.0)
    # gap 10% on the 5..12 band = 71.4; compression pctile 30 -> 62.5
    assert d.s_ep == pytest.approx(85.357, abs=0.01)
    assert d.climax_on_climax is None


def test_ep_signature_circuit_day_excludes_close_quality():
    d = ep_signature(symbol="X", session="2026-08-28", gap_pct=10.0, rvol=4.0,
                     close_loc=None, prior_compression_pctile=30.0,
                     delivery_shock=3.0, circuit_locked=True)
    assert d.circuit_ep is True
    assert d.components["close_quality"] is None
    assert "CIRCUIT_EP_CLOSE_NOT_INFORMATIVE" in d.unknowns
    # four available components: gap 71.4, rvol 100, compression 62.5, delivery 100
    assert d.s_ep == pytest.approx(81.696, abs=0.01)


def test_ep_signature_compression_inverted():
    low = ep_signature(symbol="X", session="s", gap_pct=8.0, rvol=3.0,
                       close_loc=0.8, prior_compression_pctile=30.0,
                       delivery_shock=2.0)
    high = ep_signature(symbol="X", session="s", gap_pct=8.0, rvol=3.0,
                        close_loc=0.8, prior_compression_pctile=80.0,
                        delivery_shock=2.0)
    assert low.s_ep > high.s_ep             # compressed pre-gap scores higher
    assert high.components["prior_compression"] == 0.0


def test_ep_signature_climax_guard_is_boolean_not_scored():
    calm = ep_signature(symbol="X", session="s", gap_pct=8.0, rvol=3.0,
                        close_loc=0.8, prior_compression_pctile=30.0,
                        delivery_shock=2.0, prior_20d_gain_pct=10.0)
    climax = ep_signature(symbol="X", session="s", gap_pct=8.0, rvol=3.0,
                          close_loc=0.8, prior_compression_pctile=30.0,
                          delivery_shock=2.0, prior_20d_gain_pct=45.0)
    assert calm.climax_on_climax is False
    assert climax.climax_on_climax is True
    assert calm.s_ep == climax.s_ep         # guard is a filter flag, not score math


def test_missing_inputs_reduce_ep_coverage():
    full = ep_signature(symbol="X", session="s", gap_pct=8.0, rvol=3.0,
                        close_loc=0.8, prior_compression_pctile=30.0,
                        delivery_shock=2.0)
    partial = ep_signature(symbol="X", session="s", gap_pct=8.0, rvol=None,
                           close_loc=0.8, prior_compression_pctile=30.0,
                           delivery_shock=2.0)
    assert partial.coverage < full.coverage
    assert "RVOL_UNAVAILABLE" in partial.unknowns
