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
from manas_os.engine import manas_indicators
from manas_os.ml import stock_hmm
from manas_os.scanner import expectancy

LENS_DIR = Path(__file__).resolve().parent.parent / "design" / "agents"
LESSON_DIGEST_PATH = LENS_DIR / "lessons" / "_digest.md"
WEEKLY_CLOSES_COUNT = 10
INDICATOR_BAR_LIMIT = 420
MSWING_INDEX_SYMBOLS = ("NIFTYMIDSML400", "NIFTY MIDSML 400", "Nifty Midsml 400")

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

# TradeTM backbone lens — injected for EVERY debated name, before family lenses
# (four-phase regime read, RS-then-momentum sequencing, circuit constraints,
# persistent-vs-absolute execution split, trade-management template selection).
CORE_LENS_KEY = "TRADETM_CORE"
CORE_LENS_FILE = "LENS_TRADETM_CORE.md"

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
    core_path = LENS_DIR / CORE_LENS_FILE
    if _full_lens_notes_enabled():
        rest = [p for p in sorted(LENS_DIR.glob("LENS_*.md")) if p != core_path]
        return [core_path] + rest if core_path.exists() else rest
    wanted = _lens_keys_for_families(families)
    rest = sorted(
        LENS_DIR / filename
        for key, filename in LENS_FILES_BY_KEY.items()
        if key in wanted
    )
    # Core lens is always the backbone, injected first, ahead of family lenses.
    return ([core_path] if core_path.exists() else []) + rest


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


def _indicator_bars(conn, symbol: str, scan_date: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT trade_date, open, high, low, close, volume FROM daily_prices "
        "WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "AND open IS NOT NULL AND high IS NOT NULL AND low IS NOT NULL AND close IS NOT NULL "
        "ORDER BY trade_date DESC LIMIT ?",
        (str(symbol).upper(), scan_date, INDICATOR_BAR_LIMIT),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]


def _mswing_index_bars(conn, scan_date: str) -> list[dict[str, Any]]:
    placeholders = ",".join("?" for _ in MSWING_INDEX_SYMBOLS)
    rows = conn.execute(
        "SELECT trade_date, close FROM sector_index_prices "
        f"WHERE symbol IN ({placeholders}) AND trade_date <= ? AND close IS NOT NULL "
        "ORDER BY trade_date DESC LIMIT ?",
        (*MSWING_INDEX_SYMBOLS, scan_date, INDICATOR_BAR_LIMIT),
    ).fetchall()
    if not rows:
        rows = conn.execute(
            "SELECT trade_date, close FROM daily_prices "
            f"WHERE symbol IN ({placeholders}) AND trade_date <= ? AND close IS NOT NULL "
            "ORDER BY trade_date DESC LIMIT ?",
            (*MSWING_INDEX_SYMBOLS, scan_date, INDICATOR_BAR_LIMIT),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def _round_value(value: Any, digits: int = 1) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def _latest(series: list[Any]) -> Any | None:
    return series[-1] if series else None


def _set_indicator_field(out: dict[str, Any], field: str, compute) -> None:
    try:
        value = compute()
    except Exception:  # noqa: BLE001 - context packs must omit bad fields, not crash debate.
        return
    if value is not None:
        out[field] = value


def _manas_indicators(conn, symbol: str | None, scan_date: str) -> dict[str, Any]:
    if not symbol:
        return {}
    try:
        bars = _indicator_bars(conn, symbol, scan_date)
    except Exception:  # noqa: BLE001
        return {}
    if not bars:
        return {}

    out: dict[str, Any] = {}

    _set_indicator_field(
        out,
        "burst_power",
        lambda: manas_indicators.burst_power(bars, 63).get("rounded"),
    )

    def pocket_pivot() -> dict[str, Any] | None:
        volume = manas_indicators.simple_volume(bars)
        latest = _latest(volume)
        if not latest:
            return None
        return {
            "state_today": latest.get("state"),
            "blue_streak_2": bool(volume.blue_streak(2)),
        }

    _set_indicator_field(out, "pocket_pivot", pocket_pivot)

    def persistency() -> dict[str, Any] | None:
        bundle = manas_indicators.persistency_ema_bundle(bars)
        ema10 = _latest(bundle.get("ema10") or [])
        ema21 = _latest(bundle.get("ema21") or [])
        ema50 = _latest(bundle.get("ema50") or [])
        if not ema10 or not ema21 or not ema50:
            return None
        return {
            "p10": ema10.get("count"),
            "p21": ema21.get("count"),
            "p50": ema50.get("count"),
            "pending_exit_21": bool(ema21.get("pending_exit")),
        }

    _set_indicator_field(out, "persistency", persistency)

    def mswing() -> dict[str, Any] | None:
        index_bars = _mswing_index_bars(conn, scan_date)
        if not index_bars:
            return None
        latest = _latest(manas_indicators.mswing(bars, index_bars))
        if not latest or latest.get("mswing") is None or latest.get("index_mswing") is None:
            return None
        return {
            "stock": _round_value(latest.get("mswing")),
            "index": _round_value(latest.get("index_mswing")),
            "color": latest.get("color"),
        }

    _set_indicator_field(out, "mswing", mswing)

    def rmv() -> dict[str, Any] | None:
        latest = _latest(manas_indicators.rmv(bars))
        if not latest or latest.get("rmv") is None:
            return None
        rank = latest.get("rank")
        tier = "tight" if rank in (1, 2) else "loose"
        return {"value": _round_value(latest.get("rmv")), "tier": f"{tier} rank{rank}"}

    _set_indicator_field(out, "rmv", rmv)

    def rvol() -> float | None:
        latest = _latest(manas_indicators.ss_rvol(bars))
        return _round_value(latest.get("rvol")) if latest else None

    _set_indicator_field(out, "rvol", rvol)

    def strong_start() -> bool | None:
        latest = _latest(manas_indicators.ss_rvol(bars))
        return bool(latest.get("strong_start")) if latest else None

    _set_indicator_field(out, "strong_start", strong_start)

    def purple_dot() -> bool | None:
        latest = _latest(manas_indicators.purple_dot(bars))
        return bool(latest) if latest is not None else None

    _set_indicator_field(out, "purple_dot", purple_dot)
    if out:
        line = _manas_indicators_line(out)
        if line:
            out["prompt_line"] = line
    return out


def _manas_indicators_line(indicators: dict[str, Any]) -> str:
    parts: list[str] = []
    if "burst_power" in indicators:
        parts.append(f"burst {indicators['burst_power']}")
    pp = indicators.get("pocket_pivot")
    if pp:
        streak = " x2" if pp.get("blue_streak_2") else ""
        parts.append(f"PP {pp.get('state_today')}{streak}")
    persist = indicators.get("persistency")
    if persist:
        parts.append(f"persist 10/21/50={persist.get('p10')}/{persist.get('p21')}/{persist.get('p50')}")
        if persist.get("pending_exit_21"):
            parts.append("p21 exit?")
    mswing = indicators.get("mswing")
    if mswing:
        parts.append(f"mswing {mswing.get('stock')} vs {mswing.get('index')} {mswing.get('color')}")
    rmv = indicators.get("rmv")
    if rmv:
        parts.append(f"RMV {rmv.get('value')} {rmv.get('tier')}")
    if "rvol" in indicators:
        parts.append(f"RVOL {indicators['rvol']}")
    if "strong_start" in indicators:
        parts.append(f"SS {'yes' if indicators['strong_start'] else 'no'}")
    if indicators.get("purple_dot"):
        parts.append("purple yes")
    return f"manas: {' - '.join(parts)}" if parts else ""


def _india_vix(conn, scan_date: str) -> float | None:
    """India VIX latest value as-of scan_date. None if no row exists — never fabricated."""
    row = conn.execute(
        "SELECT close FROM sector_index_prices "
        "WHERE symbol IN ('INDIAVIX', 'INDIA VIX', 'India VIX') AND trade_date <= ? "
        "ORDER BY trade_date DESC LIMIT 1",
        (scan_date,),
    ).fetchone()
    if not row or row["close"] is None:
        return None
    return row["close"]


def _ml_direction(conn, symbol: str | None, scan_date: str) -> dict[str, Any] | None:
    """SHIP-1 #7: read-only lookup of the (EXPERIMENTAL) LightGBM P(up 10d)
    fact from ml_scores, if the ml_direction stage has scored this symbol
    for this scan_date. Never computed here, never used to gate/size/rank
    (AD8) — purely an additive informational line for the debate context.
    """
    if not symbol:
        return None
    try:
        row = conn.execute(
            "SELECT p_up_10d, top_drivers_json FROM ml_scores WHERE scan_date=? AND symbol=?",
            (scan_date, symbol),
        ).fetchone()
    except Exception:
        return None
    if row is None or row["p_up_10d"] is None:
        return None
    drivers = json.loads(row["top_drivers_json"]) if row["top_drivers_json"] else []
    drivers_str = ", ".join(drivers) if drivers else "n/a"
    return {
        "p_up_10d": row["p_up_10d"],
        "drivers": drivers,
        "experimental": True,
        "line": f"ML: P(up 10d)={row['p_up_10d']:.2f} [EXPERIMENTAL] drivers: {drivers_str}",
    }


_DELIVERY_LINES = {
    "ACCUMULATION": "delivery: ACCUMULATION - rising delivery on up days",
    "DISTRIBUTION": "delivery: DISTRIBUTION - rising delivery on down days",
}


def _delivery_flag(conn, symbol: str | None, scan_date: str) -> dict[str, Any] | None:
    """SHIP-1 #9: read-only lookup of the delivery% accumulation/distribution
    tag written by engine/indicators.py (the one writer of this metric).
    Fact-only — never claims edge; lift validation is pending (LEARNINGS.md).
    Omits the field entirely for NEUTRAL/None (nothing to say).
    """
    if not symbol:
        return None
    try:
        row = conn.execute(
            "SELECT feature_json FROM features_daily WHERE symbol=? AND trade_date<=? "
            "ORDER BY trade_date DESC LIMIT 1",
            (symbol, scan_date),
        ).fetchone()
    except Exception:  # noqa: BLE001 - context packs must omit bad fields, not crash debate.
        return None
    if row is None or not row["feature_json"]:
        return None
    try:
        bag = json.loads(row["feature_json"])
    except json.JSONDecodeError:
        return None
    flag = bag.get("delivery_flag")
    if flag not in _DELIVERY_LINES:
        return None
    return {"flag": flag, "line": _DELIVERY_LINES[flag]}


def _stock_hmm(conn, symbol: str | None, scan_date: str) -> dict[str, Any] | None:
    """Per-stock 3-state HMM regime read (see ml/stock_hmm.py) — fact-only,
    EXPERIMENTAL, cached by (symbol, as_of). None (never fabricated/guessed)
    when the symbol doesn't have >=150 clean bars yet."""
    if not symbol:
        return None
    try:
        payload = stock_hmm.get_or_compute(conn, symbol, scan_date)
    except Exception:  # noqa: BLE001 - context packs must omit bad fields, not crash debate.
        return None
    line = stock_hmm.summary_line(payload)
    if not line:
        return None
    current = payload.get("current") or {}
    return {"state": current.get("state"), "confidence": current.get("confidence"), "line": line}


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
        # G1: tier tags whether this item is a gate survivor or a shortlist-floor
        # fill from refusals — NEAR_MISS carries its failure so the debate
        # argues with full honesty instead of treating it like a clean pass.
        "tier": item.get("tier") or "PASSED",
    }
    if block["tier"] == "NEAR_MISS":
        block["near_miss"] = {
            "failed_gate": item.get("failed_gate"),
            "reason": item.get("near_miss_reason"),
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
        indicators = _manas_indicators(conn, symbol, scan_date)
        if indicators:
            block["manas_indicators"] = indicators
        ml = _ml_direction(conn, symbol, scan_date)
        if ml:
            block["ml"] = ml
        delivery = _delivery_flag(conn, symbol, scan_date)
        if delivery:
            block["delivery"] = delivery
        hmm = _stock_hmm(conn, symbol, scan_date)
        if hmm:
            block["stock_hmm"] = hmm

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
