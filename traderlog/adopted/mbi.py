"""MBI score — the Stocksgeeks Market Breadth Indicator.

Adopted (copied, not imported) from ``manas_os/regime/snapshot.py`` lines
53-162 ONLY, on 2026-08-23 for TraderLog W4, per DECISIONS.md 2026-08-23
"Adopt the XP and MBI scores, but not the regime governor" and
CANONICAL.md §5. Exact functions taken: ``ratio_from_pct_above``,
``burst_ratio``, ``band_ratio``, ``band_r50``, ``xp_band``, ``band_r4p5``,
``compute_mbi``, plus the threshold constants they need (lines 22-28 and
33-35 of the source file) and the small ``_num`` helper (source lines 44-50)
that those functions call — ``_num`` sits just outside the 53-162 line range
but is a required dependency with no substitute, so it is included too.

Deliberately NOT taken (the governor layer — out of scope by decision):
``compute_pillars``, ``market_mode``/``classify_market_mode``,
``compute_quadrant``, ``four_phase.py``, ``choppy_brake.py``, ``run()``. That
code gates the user's OWN trades; TraderLog scores other people's market
reads and never gates anybody's trades.

Once copied this file is TraderLog's own; drift from the manas_os original is
expected and fine. No changes were needed beyond the extraction itself — every
function here is pure (stdlib only, no I/O), so nothing about TraderLog's
different table shapes required an edit.

MBI: r10/r20/r50 from percent-above-DMA, r4p5 as the 4%-up/4%-down burst
ratio, each banded GREEN/WHITE/RED (r50 uses its own 85/60 cutoffs), summed
into a day color and a warning-day flag when >=3 bands are red. Source notes:
``manas_os/design/knowledge/SG_MBI_DIGEST.md`` (read-only reference).
"""
from __future__ import annotations

from typing import Any

RATIO_GREEN_MIN = 75.0
RATIO_WHITE_MIN = 50.0
R50_GREEN_MIN = 85.0
R50_WHITE_MIN = 60.0
R4_RED_MAX = 50.0
R4_GREEN_MIN = 200.0
R4_ORANGE_MIN = 400.0

# XP bands — beginner one-liner + label surfaced next to the XP dial value.
# Tuned so a "typical" quiet market sits in building/strong, and only genuine
# blow-off breadth reads as extreme.
XP_BAND_LOW_MAX = 15.0
XP_BAND_BUILDING_MAX = 40.0
XP_BAND_STRONG_MAX = 100.0


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ratio_from_pct_above(pct_above: float | None) -> float | None:
    """20R-style ratio: above / below * 100, from a percent-above input."""
    pct = _num(pct_above)
    if pct is None or pct < 0 or pct > 100:
        return None
    below = 100.0 - pct
    if below <= 0:
        return None
    return (pct / below) * 100.0


def burst_ratio(up_count: float | None, down_count: float | None) -> float | None:
    up = _num(up_count)
    down = _num(down_count)
    if up is None or down is None or down <= 0:
        return None
    return (up / down) * 100.0


def band_ratio(value: float | None) -> str | None:
    if value is None:
        return None
    if value >= RATIO_GREEN_MIN:
        return "GREEN"
    if value >= RATIO_WHITE_MIN:
        return "WHITE"
    return "RED"


def band_r50(value: float | None) -> str | None:
    """50R band — separate thresholds from 20R/10R (>=85 green, 60-85 white, <60 red)."""
    if value is None:
        return None
    if value >= R50_GREEN_MIN:
        return "GREEN"
    if value >= R50_WHITE_MIN:
        return "WHITE"
    return "RED"


def xp_band(value: float | None) -> str | None:
    """Beginner-facing XP strength band: low / building / strong / extreme."""
    if value is None:
        return None
    if value < XP_BAND_LOW_MAX:
        return "LOW"
    if value < XP_BAND_BUILDING_MAX:
        return "BUILDING"
    if value < XP_BAND_STRONG_MAX:
        return "STRONG"
    return "EXTREME"


def band_r4p5(value: float | None) -> str | None:
    if value is None:
        return None
    if value < R4_RED_MAX:
        return "RED"
    if value < R4_GREEN_MIN:
        return "WHITE"
    if value < R4_ORANGE_MIN:
        return "GREEN"
    return "ORANGE"


def compute_mbi(row: dict[str, Any]) -> dict[str, Any]:
    """Compute MBI ratios, color, and warning flag from breadth_daily columns."""
    r10 = ratio_from_pct_above(row.get("pct_above_10dma"))
    r20 = ratio_from_pct_above(row.get("pct_above_20dma"))
    r50 = ratio_from_pct_above(row.get("pct_above_50dma"))
    r4p5 = burst_ratio(row.get("up_4pct"), row.get("down_4pct"))

    bands = {
        "r10": band_ratio(r10),
        "r20": band_ratio(r20),
        "r50": band_r50(r50),
        "r4p5": band_r4p5(r4p5),
    }
    score = 0
    red_count = 0
    scored = 0
    for band in bands.values():
        if band is None:
            continue
        scored += 1
        if band in {"GREEN", "ORANGE"}:
            score += 1
        elif band == "RED":
            score -= 1
            red_count += 1

    if scored and score >= 3:
        day_color = "GREEN"
    elif scored and score <= -3:
        day_color = "RED"
    else:
        day_color = "WHITE"

    return {
        "r10": r10,
        "r20": r20,
        "r50": r50,
        "r4p5": r4p5,
        "bands": bands,
        "mbi_day_color": day_color,
        "warning_day": red_count >= 3,
        "red_count": red_count,
        "score": score,
    }
