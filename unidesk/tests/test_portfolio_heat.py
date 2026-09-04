"""N-44 — Portfolio Heat: four distinct fields, never one number called risk."""
from __future__ import annotations

from unidesk.research.portfolio_heat import OpenPosition, compute_heat


def _pos(sym, sector, entry, stop, qty, cur, planned_risk):
    return OpenPosition(symbol=sym, sector=sector, entry=entry, stop=stop,
                        quantity=qty, current_price=cur, planned_risk=planned_risk,
                        unrealised_pnl=(cur - entry) * qty)


def test_four_fields_are_distinct():
    positions = [
        _pos("A", "Metal", 100, 95, 100, 105, 500),   # in profit
        _pos("B", "Tech", 50, 48, 200, 49, 400),      # underwater
    ]
    heat = compute_heat(positions, equity=50_000)
    # planned = 500 + 400 = 900
    assert heat.planned_risk == 900.0
    # stress: A gap = (5 + 10) * 100 = 1500; B gap = (2 + 5) * 200 = 1400 → 2900
    assert heat.stress_risk == 2900.0
    # open risk = only B (underwater): 400
    assert heat.open_risk == 400.0
    # profit at risk = A: (105 - 95) * 100 = 1000
    assert heat.profit_at_risk == 1200.0  # A: 1000 + B: 200 (B is also above its stop)
    # all four are distinct values
    assert len({heat.planned_risk, heat.stress_risk, heat.open_risk, heat.profit_at_risk}) == 4


def test_sector_clusters_aggregated():
    positions = [
        _pos("A", "Metal", 100, 95, 100, 105, 500),
        _pos("B", "Metal", 50, 48, 200, 49, 400),
        _pos("C", "Tech", 200, 190, 50, 210, 500),
    ]
    heat = compute_heat(positions, equity=50_000)
    assert heat.sector_clusters["Metal"]["planned_risk"] == 900.0
    assert heat.sector_clusters["Metal"]["count"] == 2
    assert heat.sector_clusters["Tech"]["planned_risk"] == 500.0


def test_empty_portfolio():
    heat = compute_heat([], equity=50_000)
    assert heat.planned_risk == 0.0
    assert heat.stress_risk == 0.0


def test_planned_risk_zero_when_no_positions():
    heat = compute_heat([], equity=50_000)
    assert heat.planned_risk == 0.0 and heat.stress_risk == 0.0
    assert heat.open_risk == 0.0 and heat.profit_at_risk == 0.0
