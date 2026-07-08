"""Debate context-pack builder (spec B1a).

Builds the shared context handed to every debate agent call: per-symbol compact
blocks (technicals/plan/gates), regime + regime age, base-rate chips from the
expectancy loop, a look-ahead-safe weekly close summary, India VIX (only if a
row actually exists), the lens files concatenated once, the AD11 India market
structure primer, and a lesson-digest slot (empty until D2 populates it).

Honesty rule (AD8/AD9/B1a): never fabricate a value. If underlying data is
absent (no VIX row, no expectancy cell, no lesson digest file), the field is
omitted or clearly marked no-data — it is never filled with a placeholder.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manas_os import config
from manas_os.scanner import expectancy

LENS_DIR = Path(__file__).resolve().parent.parent / "design" / "agents"
LESSON_DIGEST_PATH = LENS_DIR / "lessons" / "_digest.md"
WEEKLY_CLOSES_COUNT = 10

# AD11 — fixed India market-structure primer. Static text, versioned in the repo.
INDIA_STRUCTURE_PRIMER = """India market structure (fixed reference — do not need to reason about this):
- Settlement is T+1: shares/funds settle one trading day after the trade date.
- Weekly index options expire on Thursdays (shifts to the prior trading day on a Thursday holiday).
- India VIX bands: below 12 is LOW volatility, 12-20 is NORMAL, above 20 is DANGER (elevated risk regime).
- Small accounts bleed real edge to costs: STT, GST, and brokerage drag every round trip —
  size and frequency decisions must account for this, not just gross R.
- NSE trading hours are 9:15-15:30 IST for the normal market, with a 9:00-9:15 pre-open session
  used for price discovery (not continuous trading)."""


LENS_FILES_BY_KEY = {
    "EP": "LENS_EP.md",
    "HTF": "LENS_HTF.md",
    "IPO": "LENS_IPO.md",
    "PEAD": "LENS_PEAD.md",
    "STRONG_START": "LENS_STRONG_START.md",
}

LENS_KEYS_BY_FAMILY = {
    "catalyst": {"EP", "PEAD", "STRONG_START"},
    "base": {"STRONG_START", "HTF"},
    "pattern": {"STRONG_START", "HTF"},
    "ipo": {"IPO", "STRONG_START"},
    "ipo_base": {"IPO", "STRONG_START"},
}
DEFAULT_LENS_KEYS = {"STRONG_START"}


def _full_lens_notes_enabled() -> bool:
    return bool(config.get("agents.full_lens_notes", False))


def _lens_keys_for_families(families: set[str] | list[str] | tuple[str, ...] | None) -> set[str]:
    if not families:
        return set(DEFAULT_LENS_KEYS)
    keys: set[str] = set()
    for family in families:
        normalized = str(family or "").strip().lower()
        keys.update(LENS_KEYS_BY_FAMILY.get(normalized, DEFAULT_LENS_KEYS))
    return keys or set(DEFAULT_LENS_KEYS)


def _lens_paths(families: set[str] | list[str] | tuple[str, ...] | None = None) -> list[Path]:
    if _full_lens_notes_enabled():
        return sorted(LENS_DIR.glob("LENS_*.md"))
    wanted = _lens_keys_for_families(families)
    return sorted(
        LENS_DIR / filename
        for key, filename in LENS_FILES_BY_KEY.items()
        if key in wanted
    )


def _lens_text(families: set[str] | list[str] | tuple[str, ...] | None = None) -> str:
    parts = []
    for path in _lens_paths(families):
        try:
            parts.append(path.read_text(encoding="utf-8").strip())
        except OSError:
            continue
    return "\n\n---\n\n".join(parts)


def _lesson_digest() -> str:
    if not LESSON_DIGEST_PATH.exists():
        return ""
    try:
        return LESSON_DIGEST_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _regime_and_age(conn, scan_date: str) -> tuple[str | None, int]:
    """Current regime as-of scan_date + consecutive days it has held (counting backward)."""
    rows = conn.execute(
        "SELECT snapshot_date, market_mode FROM regime_snapshots "
        "WHERE snapshot_date <= ? ORDER BY snapshot_date DESC",
        (scan_date,),
    ).fetchall()
    if not rows:
        return None, 0
    current_mode = rows[0]["market_mode"]
    if not current_mode:
        return None, 0
    age = 0
    for row in rows:
        if row["market_mode"] == current_mode:
            age += 1
        else:
            break
    return current_mode, age


def _weekly_closes(conn, symbol: str, scan_date: str) -> list[dict[str, Any]]:
    """~10 weekly closes derived from daily_prices, strictly dated <= scan_date."""
    rows = conn.execute(
        "SELECT trade_date, close FROM daily_prices "
        "WHERE symbol = ? AND trade_date <= ? AND close IS NOT NULL "
        "ORDER BY trade_date DESC LIMIT 400",
        (symbol, scan_date),
    ).fetchall()
    if not rows:
        return []
    # rows are DESC by date; walk forward (oldest first) and keep the last trading
    # day seen for each ISO week, then take the most recent WEEKLY_CLOSES_COUNT.
    ordered = list(reversed(rows))
    by_week: dict[tuple[int, int], dict[str, Any]] = {}
    for row in ordered:
        d = row["trade_date"]
        try:
            from datetime import date
            y, m, dd = (int(x) for x in d.split("-"))
            iso_year, iso_week, _ = date(y, m, dd).isocalendar()
        except (ValueError, TypeError):
            continue
        by_week[(iso_year, iso_week)] = {"week_end": d, "close": row["close"]}
    weeks = sorted(by_week.items())[-WEEKLY_CLOSES_COUNT:]
    return [v for _, v in weeks]


def _india_vix(conn, scan_date: str) -> float | None:
    """India VIX latest value as-of scan_date. None if no row exists — never fabricated."""
    row = conn.execute(
        "SELECT close FROM sector_index_prices "
        "WHERE symbol IN ('INDIAVIX', 'INDIA VIX') AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT 1",
        (scan_date,),
    ).fetchone()
    if not row or row["close"] is None:
        return None
    return row["close"]


def _base_rates(conn, setup_family: str | None, regime: str | None) -> dict[str, Any] | None:
    """Base-rate chip via expectancy.chip_for; None (never fabricated) if no data."""
    if not setup_family or not regime:
        return None
    chip = expectancy.chip_for(conn, setup_family, regime)
    if not chip:
        return None
    return chip


def _symbol_block(conn, item: dict[str, Any], regime: str | None, regime_age_days: int, scan_date: str) -> dict[str, Any]:
    timing = item.get("timing") or {}
    score = item.get("score_breakdown") or {}
    symbol = item.get("symbol")
    setup_family = item.get("setup_family")

    block: dict[str, Any] = {
        "symbol": symbol,
        "setup": item.get("setup"),
        "setup_family": setup_family,
        "rank": item.get("rank"),
        "rank_of": item.get("rank_of"),
        "grade": item.get("grade"),
        "readiness": item.get("readiness"),
        "sector": item.get("sector"),
        "industry": item.get("industry"),
        "technicals": {
            "close": timing.get("close"),
            "dist_pivot": timing.get("dist_pivot"),
            "rvol": timing.get("rvol"),
            "delivery_pct": timing.get("delivery_pct"),
            "adr": timing.get("adr"),
            "exit_state": item.get("exit_state"),
            "sector_adj_momentum": score.get("sector_adj_momentum"),
        },
        "fundamentals": score.get("growth"),
        "evidence": item.get("evidence"),
        "gates": item.get("gates"),
        "plan_from_risk_plan": {
            "entry": item.get("entry"),
            "stop": item.get("stop"),
            "rr": item.get("rr"),
            "suggested_qty": item.get("suggested_qty"),
        },
        "regime": regime,
        "regime_age_days": regime_age_days,
    }

    base_rates = _base_rates(conn, setup_family, regime)
    if base_rates is not None:
        block["base_rates"] = base_rates
    else:
        block["base_rates"] = {"no_data": True}

    if symbol:
        weekly = _weekly_closes(conn, symbol, scan_date)
        if weekly:
            block["weekly_closes"] = weekly

    return block


def build_pack(
    conn,
    scan_date: str,
    shortlist: list[dict[str, Any]],
    families: set[str] | list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Build the shared debate context pack for a scan_date's shortlist.

    Never fabricates data: fields with no underlying rows are omitted or
    explicitly marked no-data rather than filled with placeholders.
    """
    regime, regime_age_days = _regime_and_age(conn, scan_date)
    vix = _india_vix(conn, scan_date)
    lens_families = families
    if lens_families is None:
        lens_families = sorted(
            {str(item.get("setup_family") or "").strip() for item in shortlist if item.get("setup_family")}
        )

    pack: dict[str, Any] = {
        "scan_date": scan_date,
        "regime": regime,
        "regime_age_days": regime_age_days,
        "shortlist": [
            _symbol_block(conn, item, regime, regime_age_days, scan_date)
            for item in shortlist
        ],
        "india_structure_primer": INDIA_STRUCTURE_PRIMER,
        "lens_notes": _lens_text(lens_families),
    }
    if vix is not None:
        pack["india_vix"] = vix
    digest = _lesson_digest()
    if digest:
        pack["lesson_digest"] = digest
    return pack


def build_pack_json(
    conn,
    scan_date: str,
    shortlist: list[dict[str, Any]],
    families: set[str] | list[str] | tuple[str, ...] | None = None,
) -> str:
    return json.dumps(build_pack(conn, scan_date, shortlist, families=families), indent=2, sort_keys=True, default=str)
