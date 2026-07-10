"""M9: real four-phase classifier — one fixture per phase, deterministic."""
from manas_os.regime.four_phase import classify_four_phase


def _row(date, above10, above20, up4=None, down4=None):
    return {
        "trade_date": date,
        "pct_above_10dma": above10,
        "pct_above_20dma": above20,
        "up_4pct": up4,
        "down_4pct": down4,
    }


def test_demand_domination_high_breadth_rising():
    rows = [
        _row("2026-06-30", 40, 42, 3, 3),
        _row("2026-07-01", 45, 48, 3, 3),
        _row("2026-07-02", 50, 52, 3, 3),
        _row("2026-07-03", 55, 58, 4, 2),
        _row("2026-07-06", 60, 63, 4, 2),
        _row("2026-07-07", 65, 68, 5, 1),
    ]
    result = classify_four_phase(rows, "2026-07-07")
    assert result["phase"] == "Demand Domination"
    assert result["confidence"] > 0
    assert result["evidence"]["roc_pct_above_ma"] > 0


def test_supply_domination_low_breadth_falling():
    rows = [
        _row("2026-06-30", 60, 62, 3, 3),
        _row("2026-07-01", 55, 56, 3, 3),
        _row("2026-07-02", 50, 50, 3, 3),
        _row("2026-07-03", 42, 40, 2, 4),
        _row("2026-07-06", 35, 33, 1, 5),
        _row("2026-07-07", 30, 28, 1, 6),
    ]
    result = classify_four_phase(rows, "2026-07-07")
    assert result["phase"] == "Supply Domination"
    assert result["evidence"]["roc_pct_above_ma"] < 0


def test_lack_of_demand_rolling_over_from_strength():
    rows = [
        _row("2026-06-30", 55, 58, 4, 2),
        _row("2026-07-01", 62, 65, 4, 2),
        _row("2026-07-02", 68, 70, 5, 1),
        _row("2026-07-03", 63, 64, 3, 3),
        _row("2026-07-06", 58, 60, 3, 3),
        _row("2026-07-07", 52, 55, 2, 4),
    ]
    result = classify_four_phase(rows, "2026-07-07")
    assert result["phase"] == "Lack of Demand"
    assert result["evidence"]["roc_pct_above_ma"] < 0


def test_lack_of_supply_turning_up_from_weakness():
    rows = [
        _row("2026-06-30", 35, 32, 2, 4),
        _row("2026-07-01", 30, 28, 1, 5),
        _row("2026-07-02", 32, 30, 2, 4),
        _row("2026-07-03", 38, 36, 3, 3),
        _row("2026-07-06", 44, 42, 4, 2),
        _row("2026-07-07", 50, 48, 4, 2),
    ]
    result = classify_four_phase(rows, "2026-07-07")
    assert result["phase"] == "Lack of Supply"
    assert result["evidence"]["roc_pct_above_ma"] > 0


def test_point_in_time_ignores_future_rows():
    rows = [
        _row("2026-07-01", 40, 42),
        _row("2026-07-02", 45, 48),
        _row("2026-12-31", 90, 95),  # far-future row must not leak in
    ]
    result = classify_four_phase(rows, "2026-07-02")
    assert result["evidence"]["source_date"] == "2026-07-02"


def test_no_breadth_data_returns_null_phase():
    result = classify_four_phase([], "2026-07-07")
    assert result["phase"] is None
    assert result["confidence"] == 0


def test_nhnl_proxy_documents_source_when_only_up4_down4_present():
    rows = [
        _row("2026-07-01", 40, 42, 3, 3),
        _row("2026-07-07", 45, 48, 4, 2),
    ]
    result = classify_four_phase(rows, "2026-07-07")
    assert "proxy" in result["evidence"]["nhnl_source"]
