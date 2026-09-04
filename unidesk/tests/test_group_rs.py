"""N-25 — group RS: JdK warm-up, percentile normalisation, acceleration."""
from __future__ import annotations

import math

import pytest

from unidesk.research.group_rs import (
    ema, jdk_rs_series, percentile_normalise, percentile_rank, rs_acceleration,
)


def _rising(n, start=100.0, step=1.0):
    return [start + step * i for i in range(n)]


def test_jdk_warmup_returns_none_never_partial():
    """~2m+k sessions before the first honest point (m=20, k=20 → ~60)."""
    g = _rising(200, 100.0, 0.5)
    b = _rising(200, 100.0, 0.5)  # identical → ratio flat 1.0
    series = jdk_rs_series(g, b, m=20, k=20)
    for i in range(58):
        ratio, momentum = series[i]
        assert ratio is None or momentum is None, f"partial value leaked at i={i}"
    # at some point within a few sessions of 2m+k it produces values
    tail_vals = [series[i] for i in range(120, 200)]
    assert all(r is not None and m is not None for r, m in tail_vals)


def test_jdk_identical_series_ratio_100():
    g = _rising(200)
    series = jdk_rs_series(g, g, m=20, k=20)
    ratio, momentum = series[-1]
    assert ratio == pytest.approx(100.0, abs=1e-9)
    assert momentum == pytest.approx(100.0, abs=1e-9)


def test_jdk_outperformer_has_ratio_above_100():
    group = [100.0 * (1.002 ** i) for i in range(200)]   # group rises faster
    bench = [100.0 * (1.0005 ** i) for i in range(200)]
    series = jdk_rs_series(group, bench, m=20, k=20)
    ratio, _ = series[-1]
    assert ratio > 100.0


def test_percentile_normalise_excludes_none_from_peer_set():
    groups = {
        "HIGH": (105.0, 120.0),
        "MID": (100.0, 100.0),
        "LOW": (95.0, 80.0),
        "WARMUP": (None, None),
    }
    out = percentile_normalise(session="s", groups=groups)
    assert out["HIGH"]["rs_ratio_pct"] == 100.0
    assert out["LOW"]["rs_ratio_pct"] == 0.0
    assert out["MID"]["rs_ratio_pct"] == 50.0
    assert out["WARMUP"]["rs_ratio_pct"] is None  # excluded, not fabricated
    assert out["WARMUP"]["rs_momentum_pct"] is None


def test_rs_acceleration_positive_when_short_steeper():
    rs = [1.0 + 0.001 * i for i in range(200)]  # steady rise, log-slope constant
    a = rs_acceleration(rs, 150)
    assert a is not None and abs(a) < 1e-4      # constant slope → accel ~0 (float tolerance)
    # accelerating: the slope change must sit inside the long window but
    # dominate the short window — transition at bar 195 (short covers 195-199)
    rs2 = ([1.0 + 0.0001 * i for i in range(195)]
           + [1.0195 + 0.002 * i for i in range(5)])
    a2 = rs_acceleration(rs2, 199)
    assert a2 is not None and a2 > 0, f"expected positive accel, got {a2}"


def test_rs_acceleration_incomplete_window_returns_none():
    rs = [1.0] * 10
    assert rs_acceleration(rs, 9, long=20) is None


def test_ema_warmup_is_none_not_zero():
    e = ema([5.0] * 30, span=20)
    assert all(v is None for v in e[:18])       # before span-1
    assert e[19] == pytest.approx(5.0)          # flat series converges
    assert all(v == pytest.approx(5.0) for v in e[19:])
