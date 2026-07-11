"""STRONG START / ARORA FOCUS LIST backend (manas_os/scanner/focus_list.py)
-- pure-function tests over the arora_strong_start_qualifies 4-condition
rule and dist_20dma_pct, per design/STRONG_START_FOCUS_SPEC.md."""
from manas_os.scanner import focus_list


def _qualifying_metrics(**overrides):
    metrics = {
        "ss_flag": True,
        "rvol20": 2.0,
        "pct_up_from_65d_low": 40.0,
        "purple_dot_count_60d": 3,
        "dist_20dma_pct": 8.0,
        "adr20": 4.0,
    }
    metrics.update(overrides)
    return metrics


def test_arora_qualifies_on_a_clean_fixture():
    result = focus_list.arora_strong_start_qualifies(_qualifying_metrics())
    assert result["qualifies"] is True
    assert not result["fails"]
    assert len(result["reasons"]) == 4


def test_arora_fails_momentum_condition_when_no_ss_and_low_rvol():
    result = focus_list.arora_strong_start_qualifies(
        _qualifying_metrics(ss_flag=False, rvol20=1.1)
    )
    assert result["qualifies"] is False
    assert any("RVOL20" in f for f in result["fails"])


def test_arora_fails_buying_power_condition():
    result = focus_list.arora_strong_start_qualifies(
        _qualifying_metrics(pct_up_from_65d_low=12.0)
    )
    assert result["qualifies"] is False
    assert any("pct_up_from_65d_low" in f for f in result["fails"])


def test_arora_fails_on_zero_purple_dots():
    result = focus_list.arora_strong_start_qualifies(
        _qualifying_metrics(purple_dot_count_60d=0)
    )
    assert result["qualifies"] is False
    assert any("zero purple dots" in f for f in result["fails"])


def test_arora_fails_when_over_extended_relative_to_adr():
    # adr20=4 -> ADR-scaled ceiling = min(3*4, 25) = 12%; 20% dist breaches it.
    result = focus_list.arora_strong_start_qualifies(
        _qualifying_metrics(dist_20dma_pct=20.0, adr20=4.0)
    )
    assert result["qualifies"] is False
    assert any("over-extended" in f for f in result["fails"])


def test_arora_extended_ceiling_scales_with_adr_but_never_exceeds_abs_cap():
    # A high-ADR small-cap (adr20=12) gets a wider ceiling (3*12=36) but it is
    # capped at the absolute 25% "not touching" floor -- 24% dist qualifies,
    # 30% dist (well past the corpus avoid-zone) does not.
    ok = focus_list.arora_strong_start_qualifies(
        _qualifying_metrics(dist_20dma_pct=24.0, adr20=12.0)
    )
    assert ok["qualifies"] is True

    over = focus_list.arora_strong_start_qualifies(
        _qualifying_metrics(dist_20dma_pct=30.0, adr20=12.0)
    )
    assert over["qualifies"] is False


def _bar(i, close, volume=1000):
    return {"date": f"2026-01-{i:02d}", "open": close, "high": close + 1,
            "low": close - 1, "close": close, "prev_close": close - 1, "volume": volume}


def test_dist_20dma_pct_reads_signed_distance_from_sma20():
    # 20 flat bars @100 then a jump to 110 -> 20DMA is still ~100.5, so dist
    # from the fresh close is clearly positive.
    bars = [_bar(i, 100) for i in range(1, 21)]
    bars.append(_bar(21, 110))
    dist = focus_list.dist_20dma_pct(bars)
    assert dist is not None
    assert dist > 0


def test_dist_20dma_pct_none_on_short_history():
    bars = [_bar(i, 100) for i in range(1, 5)]
    assert focus_list.dist_20dma_pct(bars) is None
