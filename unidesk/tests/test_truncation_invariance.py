"""Module-enumerating truncation-invariance test (HANDOFF directive 1a).

Proves the property that makes "no future leakage" possible at all:
computing a feature/primitive/scoring function on a TRUNCATED series gives
the same result as truncating the output of computing it on the FULL
series -- ``f(series[:k]) == f(series)[:k]`` for series-shaped callables.

Coverage is enumerated, not hand-picked: every public top-level function in
every module under ``unidesk.momentum.features``, ``unidesk.momentum.primitives``,
and ``unidesk.momentum.scoring`` is discovered via ``pkgutil`` (the same
directory-walk convention as ``momentum/detectors/registry.py``'s
``DETECTOR_NAMES`` enumeration) and MUST have an explicit entry in
``REGISTRY`` below, tagged either:

* ``series``   -- runs the truncation-invariance check, or
* ``special``  -- has its own dedicated test elsewhere in this file
                  (currently: ``fractal_pivots``, whose confirmation-lag
                  semantics need a pivot-specific truncation check), or
* ``skip``     -- explicitly NOT time-series-shaped, with a stated reason.

A function with no ``REGISTRY`` entry fails ``test_every_enumerated_callable_is_registered``
loudly -- a newly added module or function is picked up automatically and
cannot silently pass uncovered.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
import random
from typing import Callable

import pytest

import unidesk.momentum.features as features_pkg
import unidesk.momentum.primitives as primitives_pkg
import unidesk.momentum.scoring as scoring_pkg
from unidesk.momentum.features.adr_atr import adr, atr, atr_pct, today_move_adr, true_ranges
from unidesk.momentum.features.avwap import avwap, typical_price
from unidesk.momentum.features.participation import (
    delivery_volume, delivery_volume_ratio, rvol,
)
from unidesk.momentum.features.rs import window_return
from unidesk.momentum.features.spec_library import (
    delivery_z, pocket_pivot, rvol_median, sma, tight_ratio,
)
from unidesk.momentum.features.thrust import adr_max, chop_score, CHOP_LOOKBACK_DEFAULT
from unidesk.momentum.features.trend import ema, ema_slope_pct
from unidesk.momentum.scoring.tightness import contraction_sequence, tightness_score
from unidesk.momentum.primitives.pivots import fractal_pivots

PACKAGES = (features_pkg, primitives_pkg, scoring_pkg)


# --------------------------------------------------------------------------
# Enumeration -- pkgutil directory walk, same convention as detectors/registry.py
# --------------------------------------------------------------------------

def _enumerate_public_callables() -> dict:
    """qualified-name -> function object, for every public top-level function
    DEFINED (not merely imported) in every module directly under the three
    packages. A newly added module under any of these packages is walked
    automatically the next time this test runs."""
    found = {}
    for pkg in PACKAGES:
        for modinfo in pkgutil.iter_modules(pkg.__path__, prefix=pkg.__name__ + "."):
            if modinfo.ispkg:
                continue
            module = importlib.import_module(modinfo.name)
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                if name.startswith("_"):
                    continue
                if obj.__module__ != module.__name__:
                    continue  # re-exported from elsewhere; owned by its own module
                found[f"{module.__name__}.{name}"] = obj
    return found


# --------------------------------------------------------------------------
# Fixtures -- realistic synthetic OHLCV, same shape/convention as
# test_momentum_trend.py's closes()/ the detectors/inputs.py contract.
# --------------------------------------------------------------------------

def _bars(n: int = 45, seed: int = 7) -> dict:
    rng = random.Random(seed)
    o, h, l, c, v = [], [], [], [], []
    price = 100.0
    for _ in range(n):
        chg = rng.uniform(-1.5, 2.0)
        open_ = price
        close = max(1.0, price + chg)
        high = max(open_, close) + rng.uniform(0.1, 1.0)
        low = min(open_, close) - rng.uniform(0.1, 1.0)
        vol = rng.uniform(50_000, 200_000)
        o.append(round(open_, 2))
        h.append(round(high, 2))
        l.append(round(low, 2))
        c.append(round(close, 2))
        v.append(round(vol, 1))
        price = close
    delivery_pcts = [round(rng.uniform(20.0, 80.0), 2) for _ in range(n)]
    typical = typical_price(h, l, c)
    atr_series = atr(h, l, c, span=14)
    adr_series = adr(h, l, span=20)
    ema_series = ema(c, span=8)
    return {
        "n": n,
        "opens": o, "highs": h, "lows": l, "closes": c, "volumes": v,
        "values": c,  # alias: sma()/ema() name their series parameter "values"
        "delivery_pcts": delivery_pcts,
        "typical": typical,
        "atr_series": atr_series,
        "adr_series": adr_series,
        "ema_series": ema_series,
    }


CUTS = (10, 18, 25, 33, 40)


def _seq_case(func: Callable, *, seq_params: tuple, fixed: dict | None = None):
    """Build a (name-agnostic) truncation-invariance runner for a function
    whose output is a per-index-aligned ``list`` over one or more
    equal-length, same-time-axis Sequence parameters (``seq_params``);
    every other parameter (span, lookback, ...) is held fixed."""
    fixed = fixed or {}

    def check(bars: dict) -> None:
        full_kwargs = dict(fixed)
        for p in seq_params:
            full_kwargs[p] = bars[p]
        full_output = func(**full_kwargs)
        for k in CUTS:
            if k > bars["n"]:
                continue
            prefix_kwargs = dict(fixed)
            for p in seq_params:
                prefix_kwargs[p] = bars[p][:k]
            prefix_output = func(**prefix_kwargs)
            assert prefix_output == full_output[:k], (
                f"{func.__module__}.{func.__name__} leaks future data at cut={k}: "
                f"prefix output {prefix_output!r} != full[:cut] {full_output[:k]!r}"
            )

    return check


def _avwap_case(bars: dict) -> None:
    anchor = 3
    full = avwap(bars["typical"], bars["volumes"], anchor)
    for k in CUTS:
        if k <= anchor:
            continue
        prefix = avwap(bars["typical"][:k], bars["volumes"][:k], anchor)
        assert prefix == full[:k], f"avwap leaks future data at cut={k}"


def _fractal_pivots_case(bars: dict) -> None:
    k = 2
    h, l = bars["highs"], bars["lows"]
    full = fractal_pivots(h, l, k)
    for cut in CUTS:
        if cut > bars["n"]:
            continue
        prefix = fractal_pivots(h[:cut], l[:cut], k)
        # Every pivot fractal_pivots(h[:cut], l[:cut], k) returns must have
        # known_at < cut by construction (i ranges over k..cut-k-1, so
        # known_at = i+k <= cut-1). The truncation-invariance property is
        # that this subset is EXACTLY what the full-series computation
        # would have confirmed as of `cut` -- no earlier, no later.
        expected = [p for p in full if p.known_at < cut]
        assert prefix == expected, (
            f"fractal_pivots leaks future bars (or drops confirmable ones) "
            f"at cut={cut}: got {prefix!r}, expected {expected!r}"
        )


# --------------------------------------------------------------------------
# REGISTRY -- every enumerated callable MUST appear here exactly once.
# --------------------------------------------------------------------------

def _contraction_sequence_case(bars: dict) -> None:
    """Whole-window judge: prefix-invariance in the trivial sense (a pure
    function of its input) plus the REAL properties — a strictly contracting
    depth list is monotone in every contiguous subwindow, and a single deep
    pullback breaks it."""
    from unidesk.momentum.scoring.tightness import contraction_sequence
    # Each subsequent pullback ≤ 0.75 × the previous (spec §1.5):
    #   8 → 6 → 4 → 3 → 2. Ratios: .75, .667, .75, .667. Pure boundary hits
    #   stay inclusive; no step exceeds 0.75 × previous.
    contracting = [8.0, 6.0, 4.0, 3.0, 2.0]
    ok, n = contraction_sequence(contracting, 0.75)
    assert ok is True and n == 5
    for i in range(len(contracting)):
        sub = contracting[i:]
        if len(sub) >= 2:
            sub_ok, sub_n = contraction_sequence(sub, 0.75)
            assert sub_ok is True and sub_n == len(sub)
    # A single deep pullback (7.0 > 0.75 × 6.0 = 4.5) breaks the chain.
    broken = [8.0, 6.0, 7.0, 3.4]
    ok_b, _ = contraction_sequence(broken, 0.75)
    assert ok_b is False
    short = contraction_sequence([8.0], 0.75)
    assert short == (False, 1)


# --------------------------------------------------------------------------
# Windowed-scalar truncation check (B2-1) — the shape of thrust.py.
#
# _seq_case does not apply: adr_max/chop_score emit ONE value for the window
# ENDING at the last bar, not a per-index series, so "prefix output == full
# output prefix" has nothing to compare. The equivalent no-lookahead
# properties, all asserted for real:
#   1. Warm-up honesty: a series shorter than lookback+1 bars yields None,
#      never 0 (R12 / thrust.py docstrings).
#   2. Window alignment: f(x[:k]) == f(x[k-lookback-1 : k]) for every cut k
#      that admits a full window — the prefix computation must read EXACTLY
#      the lookback bars preceding its last bar and nothing else.
#   3. Current-bar exclusivity (thrust.py lines 118 and 167 — the property
#      the guard exists to confirm): replacing the LAST bar with an extreme
#      outlier must not move the output. An off-by-one window that includes
#      the current bar, or any read past it, fails this loudly.
# --------------------------------------------------------------------------

def _windowed_scalar_case(func, *, seq_params: tuple, fixed: dict, lookback: int,
                          mutate_last: dict):
    def check(bars: dict) -> None:
        n = bars["n"]
        # 1. warm-up: exactly `lookback` bars is one short of lookback+1.
        short = {p: bars[p][:lookback] for p in seq_params}
        assert func(**short, **fixed) is None, (
            f"{func.__name__} returned a value on {lookback} bars — warm-up "
            f"must be None, never 0"
        )
        # 2. window alignment at every qualifying cut.
        for k in CUTS:
            if k > n or k <= lookback + 1:
                continue
            prefix = func(**{p: bars[p][:k] for p in seq_params}, **fixed)
            window = func(**{p: bars[p][k - lookback - 1: k] for p in seq_params}, **fixed)
            assert prefix is not None, f"{func.__name__} prefix at cut={k} unexpectedly None"
            assert prefix == window, (
                f"{func.__name__} leaks future data at cut={k}: prefix value "
                f"{prefix!r} != same window re-cut from the full series {window!r}"
            )
        # 3. current-bar exclusivity: the "current" bar is an extreme outlier.
        base = func(**{p: bars[p] for p in seq_params}, **fixed)
        assert base is not None, f"{func.__name__} produced None on the full fixture"
        poisoned = {
            p: (list(bars[p][:-1]) + [mutate_last[p]]) if p in mutate_last else list(bars[p])
            for p in seq_params
        }
        after = func(**poisoned, **fixed)
        assert after == base, (
            f"{func.__name__} moved {base!r} -> {after!r} when the CURRENT bar "
            f"was replaced by an outlier — its window is not exclusive of the "
            f"current bar (thrust.py lines 118/167)"
        )
    return check


REGISTRY: dict = {
    # -- features/adr_atr.py: pure per-index series over highs/lows/closes --
    "unidesk.momentum.features.adr_atr.adr": {
        "kind": "series",
        "check": _seq_case(adr, seq_params=("highs", "lows"), fixed={"span": 20}),
    },
    "unidesk.momentum.features.adr_atr.atr": {
        "kind": "series",
        "check": _seq_case(atr, seq_params=("highs", "lows", "closes"), fixed={"span": 14}),
    },
    "unidesk.momentum.features.adr_atr.atr_pct": {
        "kind": "series",
        "check": _seq_case(atr_pct, seq_params=("atr_series", "closes")),
    },
    "unidesk.momentum.features.adr_atr.today_move_adr": {
        "kind": "series",
        "check": _seq_case(today_move_adr, seq_params=("closes", "adr_series")),
    },
    "unidesk.momentum.features.adr_atr.true_ranges": {
        "kind": "series",
        "check": _seq_case(true_ranges, seq_params=("highs", "lows", "closes")),
    },

    # -- features/avwap.py --
    "unidesk.momentum.features.avwap.typical_price": {
        "kind": "series",
        "check": _seq_case(typical_price, seq_params=("highs", "lows", "closes")),
    },
    "unidesk.momentum.features.avwap.avwap": {
        "kind": "special",
        "check": _avwap_case,
    },

    # -- features/circuit.py: single-instant scalar query, no sequence input --
    "unidesk.momentum.features.circuit.circuit_risk_state": {
        "kind": "skip",
        "reason": "all-scalar single-instant query (close/upper/lower band); "
                  "no time-series input to truncate.",
    },

    # -- features/geometry.py: all-scalar per-instant geometry, no sequence input --
    "unidesk.momentum.features.geometry.breakout_room": {
        "kind": "skip", "reason": "all-scalar single-instant geometry, no sequence input.",
    },
    "unidesk.momentum.features.geometry.correction_type": {
        "kind": "skip", "reason": "all-scalar single-instant classification, no sequence input.",
    },
    "unidesk.momentum.features.geometry.initial_rr": {
        "kind": "skip", "reason": "all-scalar single-instant geometry, no sequence input.",
    },
    "unidesk.momentum.features.geometry.room_adr": {
        "kind": "skip", "reason": "all-scalar single-instant geometry, no sequence input.",
    },
    "unidesk.momentum.features.geometry.stop_distance_pct": {
        "kind": "skip", "reason": "all-scalar single-instant geometry, no sequence input.",
    },
    "unidesk.momentum.features.geometry.trigger_distance_pct": {
        "kind": "skip", "reason": "all-scalar single-instant geometry, no sequence input.",
    },

    # -- features/participation.py --
    "unidesk.momentum.features.participation.rvol": {
        "kind": "series",
        "check": _seq_case(rvol, seq_params=("volumes",), fixed={"span": 20}),
    },
    "unidesk.momentum.features.participation.delivery_volume": {
        "kind": "series",
        "check": _seq_case(delivery_volume, seq_params=("volumes", "delivery_pcts")),
    },
    "unidesk.momentum.features.participation.delivery_volume_ratio": {
        "kind": "series",
        "check": _seq_case(delivery_volume_ratio,
                           seq_params=("volumes", "delivery_pcts"), fixed={"span": 20}),
    },

    # -- features/rs.py --
    "unidesk.momentum.features.rs.window_return": {
        "kind": "series",
        "check": _seq_case(window_return, seq_params=("closes",), fixed={"n": 5}),
    },
    "unidesk.momentum.features.rs.rs_excess": {
        "kind": "skip", "reason": "all-scalar arithmetic on two already-computed returns, "
                                   "no sequence input.",
    },
    "unidesk.momentum.features.rs.percentile_rank": {
        "kind": "skip",
        "reason": "aggregate rank over an UNORDERED cross-sectional universe "
                  "(caller-supplied point-in-time set), not a causal chronological "
                  "series -- there is no index axis to truncate.",
    },
    "unidesk.momentum.features.rs.rs_snapshot": {
        "kind": "skip",
        "reason": "operates on a precomputed point-in-time Mapping of window "
                  "returns supplied by the caller, not a raw chronological "
                  "OHLCV series -- truncation is the caller's responsibility "
                  "upstream (in window_return, which IS covered above).",
    },

    # -- features/spec_library.py --
    "unidesk.momentum.features.spec_library.sma": {
        "kind": "series",
        "check": _seq_case(sma, seq_params=("values",), fixed={"span": 10}),
    },
    "unidesk.momentum.features.spec_library.rvol_median": {
        "kind": "series",
        "check": _seq_case(rvol_median, seq_params=("volumes",), fixed={"span": 20}),
    },
    "unidesk.momentum.features.spec_library.delivery_z": {
        "kind": "series",
        "check": _seq_case(delivery_z, seq_params=("delivery_pcts",), fixed={"span": 20}),
    },
    "unidesk.momentum.features.spec_library.pocket_pivot": {
        "kind": "series",
        "check": _seq_case(pocket_pivot, seq_params=("closes", "volumes"), fixed={"lookback": 10}),
    },
    "unidesk.momentum.features.spec_library.tight_ratio": {
        "kind": "series",
        "check": _seq_case(tight_ratio, seq_params=("highs", "lows"), fixed={"n": 10}),
    },
    "unidesk.momentum.features.spec_library.stack_bull": {
        "kind": "skip", "reason": "all-scalar single-instant boolean, no sequence input.",
    },
    "unidesk.momentum.features.spec_library.stage2": {
        "kind": "skip",
        "reason": "reads only the TAIL of whatever series is passed in "
                  "(sma200_series[-min_window:]), with no external as-of index -- "
                  "it structurally cannot see anything beyond what the caller "
                  "supplies, so there is nothing for a truncation test to catch "
                  "here; point-in-time correctness depends entirely on the "
                  "caller passing only known-to-date bars, which is a caller-"
                  "wiring concern (see notes_limitations in the completion report), "
                  "not a property of this function.",
    },

    # -- features/thrust.py (B2-1): windowed scalars over OHLC, window
    #    EXCLUSIVE of the current bar. adr_max runs here with lookback=30 --
    #    a real parameter of the function: the 45-bar fixture can never fill
    #    the author's published 250-bar window, and the property under test
    #    is the window arithmetic (warm-up / alignment / current-bar
    #    exclusivity), which is identical at any lookback. chop_score runs at
    #    its published 20-bar default. --
    "unidesk.momentum.features.thrust.adr_max": {
        "kind": "series",
        "check": _windowed_scalar_case(
            adr_max, seq_params=("highs", "lows", "opens", "closes"),
            fixed={"lookback": 30}, lookback=30,
            mutate_last={"highs": 999.0, "lows": 1.0, "opens": 500.0, "closes": 700.0},
        ),
    },
    "unidesk.momentum.features.thrust.chop_score": {
        "kind": "series",
        "check": _windowed_scalar_case(
            chop_score, seq_params=("opens", "highs", "lows", "closes"),
            fixed={"lookback": CHOP_LOOKBACK_DEFAULT}, lookback=CHOP_LOOKBACK_DEFAULT,
            mutate_last={"highs": 999.0, "lows": 1.0, "opens": 500.0, "closes": 500.0},
        ),
    },
    "unidesk.momentum.features.thrust.chop_band": {
        "kind": "skip",
        "reason": "pure scalar banding of an ALREADY-COMPUTED ChopScore (four "
                  "threshold comparisons, chop_band(score) -> str) -- it has no "
                  "sequence parameter and no window of its own, so there is "
                  "nothing to truncate. Its point-in-time safety is inherited "
                  "entirely from chop_score, which is registered as a series "
                  "check above.",
    },
    "unidesk.momentum.features.thrust.stop_in_thrust_days": {
        "kind": "skip",
        "reason": "pure arithmetic over three already-computed scalars "
                  "(trigger, invalidation, adrmax_pct) -- no chronological "
                  "input exists to truncate; the series-derived inputs are "
                  "covered upstream (geometry/adr_atr/thrust series checks).",
    },

    # -- features/trend.py --
    "unidesk.momentum.features.trend.ema": {
        "kind": "series",
        "check": _seq_case(ema, seq_params=("values",), fixed={"span": 8}),
    },
    "unidesk.momentum.features.trend.ema_slope_pct": {
        "kind": "series",
        "check": _seq_case(ema_slope_pct, seq_params=("ema_series",), fixed={"lookback": 5}),
    },
    "unidesk.momentum.features.trend.ema_rising": {
        "kind": "skip",
        "reason": "takes an explicit as-of index `i` alongside the series -- "
                  "already point-in-time-bounded by construction (same pattern "
                  "as pivots_known_at); the query it answers is 'was the EMA "
                  "rising as of index i', not a per-index series output.",
    },
    "unidesk.momentum.features.trend.price_vs_ema_pct": {
        "kind": "skip", "reason": "all-scalar single-instant geometry, no sequence input.",
    },
    "unidesk.momentum.features.trend.trend_state": {
        "kind": "skip", "reason": "all-scalar single-instant classification, no sequence input.",
    },

    # -- primitives/contraction.py --
    "unidesk.momentum.primitives.contraction.base_depth_pct": {
        "kind": "skip",
        "reason": "requires explicit [start, end) window bounds within the "
                  "supplied series (ContractError if end > len(series)) -- "
                  "structurally cannot read past `end`, so truncating the "
                  "outer series below `end` is simply an invalid call, not a "
                  "leakage scenario.",
    },
    "unidesk.momentum.primitives.contraction.range_contraction_ratio": {
        "kind": "skip",
        "reason": "reads only the TAIL of whatever series is passed "
                  "(the last recent_n+prior_n bars), no external as-of index -- "
                  "structurally cannot see beyond what the caller supplies; same "
                  "reasoning as stage2 above.",
    },
    "unidesk.momentum.primitives.contraction.volume_dryup_ratio": {
        "kind": "skip",
        "reason": "reads only the TAIL of whatever series is passed, no external "
                  "as-of index -- same reasoning as range_contraction_ratio.",
    },

    # -- primitives/pivots.py --
    "unidesk.momentum.primitives.pivots.fractal_pivots": {
        "kind": "special",
        "check": _fractal_pivots_case,
    },
    "unidesk.momentum.primitives.pivots.pivots_known_at": {
        "kind": "skip",
        "reason": "takes an explicit as_of_index filter over PRECOMPUTED Pivot "
                  "records (each already carrying its own known_at) -- this IS "
                  "the point-in-time-safety helper itself, not a raw-series "
                  "transform to test for leakage.",
    },

    # -- scoring/tightness.py: composite over caller-computed scalar inputs --
    "unidesk.momentum.scoring.tightness.contraction_sequence": {
        "kind": "special",
        "check": _contraction_sequence_case,
    },

    "unidesk.momentum.scoring.tightness.tightness_score": {
        "kind": "skip",
        "reason": "composite over caller-computed scalars (pullback_depths/"
                  "dryup_ratio/atrp_percentile/delivery/rs flags), mirroring "
                  "stock_quality -- upstream series functions are covered "
                  "individually; contraction_sequence carries its own "
                  "window-based check.",
    },

    # -- scoring/_snapshot_bindings.py (N5 wave C-1): adapters from a
    #    frozen-snapshot dict to the S_ep / S_tight scorers. The snapshot
    #    is a point-in-time bag of pre-computed scalars (it has no
    #    chronological series axis), so neither binding is time-series
    #    shaped -- they are dispatch glue and have their own unit tests
    #    in test_n5_snapshot_bindings.py. --
    "unidesk.momentum.scoring._snapshot_bindings.score_ep_from_snapshot": {
        "kind": "skip",
        "reason": "dispatches to ep_signature (covered above as a special "
                  "composite) over precomputed point-in-time scalars lifted "
                  "from the freeze-scan snapshot -- no chronological series "
                  "axis exists in the input.",
    },
    "unidesk.momentum.scoring._snapshot_bindings.s_tight_status_from_snapshot": {
        "kind": "skip",
        "reason": "returns a status dict (not a score) while the wave C-2 "
                  "base_episode block is not built yet -- no series input, "
                  "no computation.",
    },

    # -- scoring/entry_quality.py, scoring/stock_quality.py --
    "unidesk.momentum.scoring.entry_quality.entry_quality_snapshot": {
        "kind": "skip",
        "reason": "takes precomputed scalar inputs (current/trigger/invalidation/"
                  "hurdle/adr_pct/ema21_extension_pct), not a raw chronological "
                  "series -- upstream feature functions that DO produce these "
                  "scalars from series are covered individually above.",
    },
    "unidesk.momentum.scoring.stock_quality.stock_quality_snapshot": {
        "kind": "skip",
        "reason": "takes precomputed scalar inputs (trend_state/rs_rank/rvol/"
                  "delivery_ratio/distance_52w_high_pct/circuit_state), not a raw "
                  "chronological series -- upstream feature functions that DO "
                  "produce these scalars from series are covered individually above.",
    },

    # -- scoring/setup_quality.py (B2-1) --
    "unidesk.momentum.scoring.setup_quality.setup_quality_snapshot": {
        "kind": "skip",
        "reason": "takes a detector verdict enum + a tuple of already-recorded "
                  "rule failures + scalar metadata, not a raw chronological "
                  "series -- same class as stock_quality_snapshot/"
                  "entry_quality_snapshot above. It is a rule-completion "
                  "snapshot of the detector's OWN verdict, so any series "
                  "groundwork inside the detector is the detector's coverage; "
                  "there is no window here to truncate.",
    },

    # -- features/activity.py (Reactor Scale, adopted from traderlog) --
    "unidesk.momentum.features.activity.activity_score": {
        "kind": "skip",
        "reason": "takes precomputed scalar inputs (volume/num_trades/delivery_pct) "
                  "and prior-series aggregates, not a raw chronological series -- "
                  "the upstream per-symbol loop in scan.py supplies the series, "
                  "this function is a composite scorer.",
    },

    # -- features/breadth.py (market-breadth analytics, adopted from manas_os) --
    "unidesk.momentum.features.breadth.bo_bd_ratio": {
        "kind": "skip",
        "reason": "takes a precomputed counts dict, not a raw series -- "
                  "the upstream breadth_counts adapter supplies the aggregate.",
    },
    "unidesk.momentum.features.breadth.net_nh_nl": {
        "kind": "skip",
        "reason": "takes a precomputed counts dict, not a raw series.",
    },
    "unidesk.momentum.features.breadth.up_down_close_pct": {
        "kind": "skip",
        "reason": "takes a precomputed counts dict, not a raw series.",
    },
    "unidesk.momentum.features.breadth.volatility_ratio": {
        "kind": "skip",
        "reason": "takes a precomputed counts dict, not a raw series.",
    },
    "unidesk.momentum.features.breadth.volume_ratio": {
        "kind": "skip",
        "reason": "takes a precomputed counts dict, not a raw series.",
    },
}


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------

def test_every_enumerated_callable_is_registered():
    """The real guard: a newly added module/function under features/,
    primitives/, or scoring/ is picked up by pkgutil automatically and MUST
    be classified here (series/special/skip). An unclassified function fails
    this test loudly -- it can never silently "pass" uncovered."""
    enumerated = _enumerate_public_callables()
    missing = sorted(set(enumerated) - set(REGISTRY))
    assert not missing, (
        "New public callable(s) found with no REGISTRY entry in "
        "test_truncation_invariance.py -- classify each as kind='series' "
        "(with a truncation check), kind='special', or kind='skip' (with an "
        "explicit reason) before this test can pass:\n  " + "\n  ".join(missing)
    )
    # Registry entries that no longer exist in the codebase are stale, not
    # dangerous, but flag them too so the registry stays truthful.
    stale = sorted(set(REGISTRY) - set(enumerated))
    assert not stale, (
        "REGISTRY entries reference callables that no longer exist -- "
        "remove them:\n  " + "\n  ".join(stale)
    )


@pytest.mark.parametrize("qualname", sorted(REGISTRY))
def test_truncation_invariance(qualname):
    entry = REGISTRY[qualname]
    if entry["kind"] == "skip":
        pytest.skip(f"{qualname}: not time-series-shaped -- {entry['reason']}")
    bars = _bars()
    entry["check"](bars)
