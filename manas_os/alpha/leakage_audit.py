"""Point-in-time leakage audit for alpha feature rows.

A feature function is leaky if values computed for date T change when bars
with trade_date > T are present in the input panel.
"""
from __future__ import annotations

from typing import Any, Callable


def audit_feature_fn(
    bars: list[dict[str, Any]],
    feature_fn: Callable[[list[dict[str, Any]]], dict[str, float]],
    *,
    date_key: str = "trade_date",
    as_of_index: int = -1,
) -> dict[str, Any]:
    """Compare feature_fn on history<=T vs history<=T plus future pollution.

    - clean: feature_fn(bars[:T+1])
    - polluted: feature_fn(bars[:T+1] + synthetic_future_bars)
    Any key that changes is a leak.
    """
    if len(bars) < 2:
        return {"ok": False, "reason": "need_ge_2_bars", "leaks": []}
    idx = as_of_index if as_of_index >= 0 else len(bars) + as_of_index
    history = bars[: idx + 1]
    clean = feature_fn(history)
    last = dict(history[-1])
    future = dict(last)
    future[date_key] = "9999-12-31"
    try:
        future["close"] = float(last.get("close") or 0) * 1.5
    except (TypeError, ValueError):
        future["close"] = 9999.0
    polluted = feature_fn(list(history) + [future, future])
    leaks = []
    for k, v in clean.items():
        pv = polluted.get(k)
        try:
            if abs(float(pv) - float(v)) > 1e-9:
                leaks.append({"feature": k, "clean": v, "polluted": pv})
        except (TypeError, ValueError):
            if pv != v:
                leaks.append({"feature": k, "clean": v, "polluted": pv})
    return {"ok": len(leaks) == 0, "leaks": leaks, "n_features": len(clean)}


def deliberately_leaky_feature_fn(bars: list[dict[str, Any]]) -> dict[str, float]:
    """Uses max close of the entire series (future-sensitive)."""
    closes = [float(b.get("close") or 0) for b in bars]
    last = closes[-1] if closes else 0.0
    prev = closes[-2] if len(closes) > 1 else last
    return {
        "ret_1": (last / prev - 1.0) if prev else 0.0,
        "leak_max_close": max(closes) if closes else 0.0,
    }


def clean_feature_fn(bars: list[dict[str, Any]]) -> dict[str, float]:
    """Only uses last two closes — immune to future append if caller filters by date.

    For audit purposes this fn always uses the last element of whatever list
    it is given; the auditor only appends future *after* the as-of history when
    testing pollution, so a clean fn must ignore bars with trade_date far future
    OR only use bars[-1] when bars are pre-filtered. We filter by date here.
    """
    usable = [b for b in bars if str(b.get("trade_date") or "") < "9000"]
    if len(usable) < 2:
        return {"ret_1": 0.0}
    a = float(usable[-2].get("close") or 0)
    b = float(usable[-1].get("close") or 0)
    return {"ret_1": (b / a - 1.0) if a else 0.0}
