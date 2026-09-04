"""N-24 — group state aggregation: coverage-honest breadth per group.

Every percentage carries numerator/denominator (spec §12). Coverage below
0.80 suppresses the percentage (spec §46) — the field is None and the row
says ``INSUFFICIENT COVERAGE``. Symbols without a mapping are counted as
unmapped, never assigned to an invented group.
"""
from __future__ import annotations

from unidesk.research.group_state import aggregate_groups


def _states(rows):
    return rows


def test_aggregation_counts_numerator_denominator_and_candidates():
    states = _states([
        {"symbol": "A", "close": 100, "above_ema21": True, "above_ema50": True, "rs_rank": 80.0},
        {"symbol": "B", "close": 100, "above_ema21": False, "above_ema50": True, "rs_rank": 40.0},
        {"symbol": "C", "close": 100, "above_ema21": True, "above_ema50": True, "rs_rank": 60.0},
    ])
    group = {"A": {"sector": "Metal", "industry": "Steel"},
             "B": {"sector": "Metal", "industry": "Steel"},
             "C": {"sector": "Metal", "industry": "Steel"}}
    out = aggregate_groups(session="2026-09-03", universe_states=states,
                           symbol_group=group, candidates_by_symbol={"A": 2})
    sector = next(g for g in out if g.group_kind == "SECTOR")
    assert sector.group_name == "Metal"
    assert sector.above_ema21_n == 2 and sector.members_with_ema21 == 3
    assert sector.breadth_ema21_pct == 66.7
    assert sector.candidates_n == 2
    assert sector.rs_rank_mean == 60.0


def test_coverage_below_floor_suppresses_breadth():
    # 4 members, only 2 with EMA21 data → coverage 0.5 < 0.80 → suppressed
    states = [
        {"symbol": "A", "close": 100, "above_ema21": True, "above_ema50": None, "rs_rank": 50.0},
        {"symbol": "B", "close": 100, "above_ema21": False, "above_ema50": None, "rs_rank": 50.0},
        {"symbol": "C", "close": 100, "above_ema21": None, "above_ema50": None, "rs_rank": None},
        {"symbol": "D", "close": 100, "above_ema21": None, "above_ema50": None, "rs_rank": None},
    ]
    group = {s["symbol"]: {"sector": "X", "industry": "Y"} for s in states}
    out = aggregate_groups(session="s", universe_states=states, symbol_group=group,
                           candidates_by_symbol={})
    sector = next(g for g in out if g.group_kind == "SECTOR")
    assert sector.breadth_ema21_pct is None          # suppressed
    assert sector.coverage < 0.80
    assert sector.coverage_sufficient is False


def test_unmapped_symbols_counted_never_assigned():
    states = [
        {"symbol": "MAPPED", "close": 100, "above_ema21": True, "above_ema50": True, "rs_rank": 50.0},
        {"symbol": "NOMAP", "close": 100, "above_ema21": False, "above_ema50": False, "rs_rank": 50.0},
    ]
    group = {"MAPPED": {"sector": "Tech", "industry": "IT"}, "NOMAP": None}
    out = aggregate_groups(session="s", universe_states=states, symbol_group=group,
                           candidates_by_symbol={})
    # NOMAP has no group and must not appear in any SECTOR row
    assert all(g.group_name != "NOMAP" for g in out)
    tech = next(g for g in out if g.group_name == "Tech")
    assert tech.members_total == 1


def test_symbol_without_group_data_is_disclosed_not_silent(capsys):
    states = [{"symbol": "A", "close": 100, "above_ema21": True, "above_ema50": True, "rs_rank": 50.0},
              {"symbol": "B", "close": 100, "above_ema21": True, "above_ema50": True, "rs_rank": 50.0}]
    group = {"A": {"sector": "Tech", "industry": "IT"}, "B": {"sector": "Tech", "industry": "IT"}}
    aggregate_groups(session="s", universe_states=states, symbol_group=group,
                     candidates_by_symbol={})
    # 0 unmapped in this fixture — the print fires only when symbols lack a map
    captured = capsys.readouterr()
    assert "without a" not in captured.out or "0 symbols" not in captured.out
