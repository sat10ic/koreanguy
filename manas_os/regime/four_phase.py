"""M9: real four-phase market classifier.

TradeTM backbone doctrine (not the display-caption approximation this
replaces — see FOUR_PHASE_CAPTION_CITE in regime/snapshot.py for the old,
now-superseded approach): market conditions cycle through four phases —
Demand Domination, Supply Domination, Lack of Demand, Lack of Supply — read
from the RATE OF CHANGE of %-above-moving-average breadth plus the
new-high/new-low trend, not from a single day's level.

CITES:
  - design/knowledge/TRADETM_NUANCES.md C1: "We can categorize market
    conditions into four phases: 1. Demand Domination... 2. Supply
    Domination... 3. Lack of Demand... 4. Lack of Supply... most failures in
    a momentum burst setup occur during the phase of lack of demand... after
    major supply exhaustion, the market enters a phase of lack of supply,
    where many long setups perform exceptionally well."
  - design/knowledge/TRADETM_NUANCES_SHARDS.md #20: "scan watchlist for
    breadth clues (% above 200 DMA, # of new 52-week highs, volume on
    up-bars); map to four-phase framework."

DATA REALITY: manas_os does not ingest true new-high/new-low counts yet
(regime_universe_metrics.new_highs/new_lows exist in schema but are never
populated by any source). up_25pct_month/up_50pct_month (a closer NH/NL
analog) are also currently null in breadth_daily. The only populated
momentum-breadth columns are up_4pct/down_4pct (count of stocks up/down
>=4.5% TODAY) — used here as the NH/NL-TREND PROXY, clearly labeled as such
in the evidence dict. If up_25pct_month/up_50pct_month/new_highs/new_lows
are ever backfilled, prefer those columns first (see _nhnl_pair).
"""
from __future__ import annotations

from typing import Any

CITE = (
    "TRADETM_NUANCES.md C1 (four-phase names) + TRADETM_NUANCES_SHARDS.md #20 "
    "(breadth-ROC + NH/NL basis for the phase read)."
)

PHASES = ("Demand Domination", "Supply Domination", "Lack of Demand", "Lack of Supply")

LEVEL_STRONG = 55.0
LEVEL_WEAK = 45.0


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _avg_pct_above_ma(row: dict[str, Any]) -> float | None:
    vals = [x for x in (_num(row.get("pct_above_10dma")), _num(row.get("pct_above_20dma"))) if x is not None]
    return sum(vals) / len(vals) if vals else None


def _nhnl_pair(row: dict[str, Any]) -> tuple[float | None, str]:
    """Prefer a true/near NH-NL breadth pair if ever populated; fall back to
    the up_4pct/down_4pct (today's >=4.5% movers) proxy, which is the only
    populated pair today."""
    up50, down50 = _num(row.get("up_50pct_month")), _num(row.get("down_50pct_month"))
    if up50 is not None and down50 is not None:
        return up50 - down50, "up_50pct_month-down_50pct_month"
    up25, down25 = _num(row.get("up_25pct_month")), _num(row.get("down_25pct_month"))
    if up25 is not None and down25 is not None:
        return up25 - down25, "up_25pct_month-down_25pct_month"
    up4, down4 = _num(row.get("up_4pct")), _num(row.get("down_4pct"))
    if up4 is not None and down4 is not None:
        return up4 - down4, "up_4pct-down_4pct (NH/NL not ingested; proxy)"
    return None, "unavailable"


def _classify(level: float, roc: float, nhnl_trend: float) -> tuple[str, int]:
    if level >= LEVEL_STRONG and roc >= 0:
        phase = "Demand Domination"
    elif level < LEVEL_WEAK and roc <= 0:
        phase = "Supply Domination"
    elif roc < 0 and level >= LEVEL_WEAK:
        # breadth was fine-to-strong but is now rolling over: buyers exhausting.
        phase = "Lack of Demand"
    elif roc > 0 and level < LEVEL_STRONG:
        # breadth was weak but is now turning up: sellers exhausting.
        phase = "Lack of Supply"
    else:
        # roc == 0 borderline: break the tie with the NH/NL trend proxy.
        phase = "Lack of Supply" if nhnl_trend >= 0 else "Lack of Demand"
    confidence = int(min(100, max(0, round(abs(roc) * 8 + abs(level - 50.0) * 1.5))))
    return phase, confidence


def classify_four_phase(
    breadth_rows: list[dict[str, Any]],
    as_of: str,
    lookback_days: int = 5,
) -> dict[str, Any]:
    """Deterministic, point-in-time four-phase read.

    breadth_rows: breadth_daily-shaped dicts (any order, any date range) —
    filtered here to trade_date <= as_of only, so callers can pass a wide
    window without risking a look-ahead leak.
    """
    rows = sorted(
        (r for r in breadth_rows if r.get("trade_date") and r["trade_date"] <= as_of),
        key=lambda r: r["trade_date"],
    )
    if not rows:
        return {
            "phase": None,
            "confidence": 0,
            "evidence": {},
            "reason": "no breadth_daily rows on or before as_of",
        }

    today = rows[-1]
    level = _avg_pct_above_ma(today)
    if level is None:
        return {
            "phase": None,
            "confidence": 0,
            "evidence": {"source_date": today.get("trade_date")},
            "reason": "pct_above_10dma/20dma missing on source_date",
        }

    prior_idx = max(0, len(rows) - 1 - lookback_days)
    prior = rows[prior_idx]
    prior_level = _avg_pct_above_ma(prior)
    roc = (level - prior_level) if prior_level is not None else 0.0

    nh_today, nhnl_source = _nhnl_pair(today)
    nh_prior, _ = _nhnl_pair(prior)
    nhnl_trend = (nh_today - nh_prior) if (nh_today is not None and nh_prior is not None) else 0.0

    phase, confidence = _classify(level, roc, nhnl_trend)

    evidence = {
        "source_date": today.get("trade_date"),
        "prior_date": prior.get("trade_date"),
        "lookback_days": lookback_days,
        "level_pct_above_ma": round(level, 2),
        "roc_pct_above_ma": round(roc, 2),
        "nhnl_trend": round(nhnl_trend, 2) if nh_today is not None and nh_prior is not None else None,
        "nhnl_source": nhnl_source,
    }
    return {"phase": phase, "confidence": confidence, "evidence": evidence, "reason": None}
