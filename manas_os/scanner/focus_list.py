"""STRONG START / ARORA FOCUS LIST -- deterministic backend for the SS RVOL
dashboard + Arora CH3.1 watchlist-elimination qualify rule.
design/STRONG_START_FOCUS_SPEC.md pins every number verbatim; nothing here is
invented or retuned.

Persistence: `focus_list` is a PERSISTENT table (NOT nightly-regenerated) --
a user/screener/LLM push that stays active until explicitly removed
(upsert on symbol; remove sets active=0). Distinct from scanner/focus.py
(the theme-of-the-day industry-rollup module, a different aggregation).

Row math reuses existing single-writer helpers rather than re-deriving them:
  - scanner.candidates.load_symbol_bars       -- OHLCV bars
  - scanner.screener.metrics_for_symbol       -- chg_pct/rs/pct_up_65d_low/
                                                  purple_dot_count_60d/adr20/
                                                  pct_off_52w_high
  - engine.eod_detectors.strong_start_today / rvol20  -- the two NEW EOD
                                                          detectors this
                                                          module adds
  - dist_20dma_pct below is the one new metric with no existing home.
"""
from __future__ import annotations

from typing import Any

from manas_os.engine import eod_detectors as ed

# ── ARORA STRONG-START QUALIFY thresholds ──────────────────────────────────
# STRONG_START_FOCUS_SPEC.md "ARORA STRONG-START QUALIFY" (4 conditions).
# Every number below carries its corpus cite; none is label-tuned.

# Condition 1 -- momentum today: SS-today OR RVOL20 >= ~1.5x (spec line 39;
# finallynitin SS RVOL Pine convention treats >=1.5x as a real volume surge).
ARORA_RVOL_MIN = 1.5

# Condition 2 -- buying power: pct_up_from_65d_low "strong" ("up strongly in
# last 3 months", spec line 40/21). Reuses the SAME >=30% floor
# scanner/focus.py's compute_focus already applies for pct_members_up65d_ge30
# (focus.py: "pct_up_vals ... v >= 30.0"), itself sourced from WK groww2/
# CH3.1 "stock up >=30-35% from its 3-month (65-day) low" (discovery_metrics.
# py pct_up_from_65d_low docstring). One floor, reused, not re-picked.
ARORA_BUYING_POWER_MIN_PCT = 30.0

# Condition 4 -- not over-extended: dist_20dma_pct <= K * adr20, scaled by
# the stock's OWN adr20 per the spec's explicit instruction ("scale by ADR
# per the corpus, not a fixed %", spec line 43). K=3.0 is chosen so a stock
# sitting at the corpus's own "12% acceptable" ceiling (spec line 26) at a
# typical ~4% ADR20 lands almost exactly on that boundary (3*4=12), while a
# volatile small-cap at ~8% ADR20 (3*8=24) still lands just under the
# corpus's explicit "25, 30, 40% -- I'm not touching that stock" avoid zone
# (spec line 26-27/43) -- the ADR-scaling and the absolute avoid-zone agree
# at the extremes instead of conflicting. ARORA_EXTENDED_ABS_CAP_PCT is a
# hard absolute ceiling pinned to the LOW edge of that avoid zone (25%) so an
# illiquid/very-high-ADR name can never qualify purely off a huge adr20
# denominator. ARORA_EXTENDED_FALLBACK_PCT (used only when adr20 is
# unavailable) is the corpus's flat "12% acceptable" number, not a fresh
# invention.
ARORA_EXTENDED_ADR_MULTIPLE = 3.0
ARORA_EXTENDED_ABS_CAP_PCT = 25.0
ARORA_EXTENDED_FALLBACK_PCT = 12.0

# "Near 52-week high" boolean cutoff -- reuses the SAME 15% nearness band
# already established in this repo for pool eligibility (OWNERS_GUIDE.md:62
# "within 15% of 52-week high (nearness >=0.85)"), not a fresh number.
NEAR_52W_HIGH_MAX_PCT = 15.0


def dist_20dma_pct(bars: list[dict[str, Any]]) -> float | None:
    """Signed % distance of the latest close from its 20-day SMA (positive =
    price above the 20DMA). Feeds ARORA condition 4 -- STRONG_START_FOCUS_
    SPEC.md "distance of price from the ... 20-day (daily) MA." None when
    there isn't a full 20-session close window."""
    closes: list[float | None] = []
    for b in bars:
        v = b.get("close")
        try:
            closes.append(float(v) if v is not None else None)
        except (TypeError, ValueError):
            closes.append(None)
    s20 = ed.sma(closes, 20)
    close = closes[-1] if closes else None
    base = s20[-1] if s20 else None
    if close is None or base is None or base == 0:
        return None
    return (close - base) / base * 100.0


def _extended_ceiling(adr20: float | None) -> float:
    if adr20 is None or adr20 <= 0:
        return ARORA_EXTENDED_FALLBACK_PCT
    return min(ARORA_EXTENDED_ADR_MULTIPLE * adr20, ARORA_EXTENDED_ABS_CAP_PCT)


def arora_strong_start_qualifies(metrics: dict[str, Any]) -> dict[str, Any]:
    """The 4-condition ARORA STRONG-START QUALIFY rule (STRONG_START_FOCUS_
    SPEC.md "ARORA STRONG-START QUALIFY"). `metrics` expects: ss_flag (bool),
    rvol20 (float|None), pct_up_from_65d_low (float|None),
    purple_dot_count_60d (int|None), dist_20dma_pct (float|None), adr20
    (float|None). A missing/None input FAILS that condition -- conservative
    by design, since the LLM push gate must never approve on an unknown.

    Returns {"qualifies": bool, "reasons": [...], "fails": [...]}.
    """
    reasons: list[str] = []
    fails: list[str] = []

    ss_flag = bool(metrics.get("ss_flag"))
    rvol = metrics.get("rvol20")
    momentum_ok = bool(ss_flag or (rvol is not None and rvol >= ARORA_RVOL_MIN))
    if momentum_ok:
        reasons.append("SS today" if ss_flag else f"RVOL20 {rvol:.2f}x >= {ARORA_RVOL_MIN}x")
    else:
        fails.append(f"no SS flag and RVOL20 ({rvol}) < {ARORA_RVOL_MIN}x")

    pct_up = metrics.get("pct_up_from_65d_low")
    buying_power_ok = pct_up is not None and pct_up >= ARORA_BUYING_POWER_MIN_PCT
    if buying_power_ok:
        reasons.append(f"up {pct_up:.1f}% from 65d low >= {ARORA_BUYING_POWER_MIN_PCT}%")
    else:
        fails.append(f"pct_up_from_65d_low ({pct_up}) < {ARORA_BUYING_POWER_MIN_PCT}%")

    dots = metrics.get("purple_dot_count_60d")
    dots_ok = dots is not None and dots > 0
    if dots_ok:
        reasons.append(f"{dots} purple dot(s) in the trailing 60d")
    else:
        fails.append("zero purple dots in the trailing 60d (Arora: skip regardless of setup)")

    dist = metrics.get("dist_20dma_pct")
    adr = metrics.get("adr20")
    ceiling = _extended_ceiling(adr)
    not_extended_ok = dist is not None and abs(dist) <= ceiling
    if not_extended_ok:
        reasons.append(f"dist-from-20DMA {dist:.1f}% within its ADR-scaled ceiling ({ceiling:.1f}%)")
    else:
        fails.append(f"dist-from-20DMA ({dist}) exceeds ADR-scaled ceiling ({ceiling:.1f}%) -- over-extended")

    qualifies = momentum_ok and buying_power_ok and dots_ok and not_extended_ok
    return {"qualifies": qualifies, "reasons": reasons, "fails": fails}

def tracking_age(conn, symbol: str, as_of: str) -> int:
    try:
        row = conn.execute(
            "SELECT MIN(scan_date) as d FROM agent_watchlist WHERE symbol = ? AND scan_date <= ?",
            (symbol.upper(), as_of)
        ).fetchone()
        if not row or not row["d"]:
            return 0
        from datetime import date as _date
        return max(0, (_date.fromisoformat(as_of) - _date.fromisoformat(row["d"])).days)
    except Exception:
        return 0


# ── Persistence ─────────────────────────────────────────────────────────────

def ensure_schema(conn) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS focus_list ("
        "symbol TEXT NOT NULL PRIMARY KEY, source TEXT NOT NULL, reason TEXT, "
        "added_at TEXT DEFAULT (datetime('now')), active INTEGER DEFAULT 1)"
    )


def add_symbol(conn, symbol: str, source: str, reason: str | None) -> None:
    """Upsert: a symbol can be added once. Re-adding an inactive (removed)
    symbol reactivates it and refreshes source/reason/added_at."""
    ensure_schema(conn)
    conn.execute(
        "INSERT INTO focus_list (symbol, source, reason, added_at, active) "
        "VALUES (?, ?, ?, datetime('now'), 1) "
        "ON CONFLICT(symbol) DO UPDATE SET source=excluded.source, reason=excluded.reason, "
        "added_at=datetime('now'), active=1",
        (symbol.upper(), source, reason),
    )


def remove_symbol(conn, symbol: str) -> None:
    ensure_schema(conn)
    conn.execute("UPDATE focus_list SET active = 0 WHERE symbol = ?", (symbol.upper(),))


def active_rows(conn) -> list[dict[str, Any]]:
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT symbol, source, reason, added_at FROM focus_list WHERE active = 1 ORDER BY symbol"
    ).fetchall()
    return [dict(r) for r in rows]


def metrics_for_qualify(conn, symbol: str, as_of: str) -> dict[str, Any] | None:
    """The raw metrics dict `arora_strong_start_qualifies` expects, for one
    symbol as-of `as_of`. None when there is no price row on that date."""
    from manas_os.scanner import candidates as scanner_candidates
    from manas_os.scanner import discovery_metrics as dm

    bars = scanner_candidates.load_symbol_bars(conn, symbol, as_of)
    if not bars or bars[-1].get("date") != as_of:
        return None
    return {
        "ss_flag": ed.strong_start_today(bars),
        "rvol20": ed.rvol20(bars),
        "pct_up_from_65d_low": dm.pct_up_from_65d_low(bars),
        "purple_dot_count_60d": dm.purple_dot_count_60d(bars),
        "dist_20dma_pct": dist_20dma_pct(bars),
        "adr20": dm.adr20(bars),
        "days_tracked": tracking_age(conn, symbol, as_of),
    }


def row_metrics(conn, symbol: str, as_of: str, rs_map: dict[str, dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """The full SS-RVOL dashboard row for one symbol as-of `as_of`
    (STRONG_START_FOCUS_SPEC.md GET /api/desk/focus-list contract). Reuses
    scanner.screener.metrics_for_symbol for the shared fields so this module
    never re-derives chg_pct/rs/adr20/pct_up_65d_low/purple-dots/52w-high a
    second way. None when there is no price row on `as_of`."""
    from manas_os.scanner import candidates as scanner_candidates
    from manas_os.scanner import screener as scanner_screener

    bars = scanner_candidates.load_symbol_bars(conn, symbol, as_of)
    if not bars or bars[-1].get("date") != as_of:
        return None
    m = scanner_screener.metrics_for_symbol(conn, symbol, as_of, bars=bars, rs_map=rs_map) or {}
    ss_flag = ed.strong_start_today(bars)
    rvol = ed.rvol20(bars)
    dist = dist_20dma_pct(bars)
    pct_off_52w_high = m.get("pct_off_52w_high")
    near_52w_high = pct_off_52w_high is not None and pct_off_52w_high <= NEAR_52W_HIGH_MAX_PCT

    qualify = arora_strong_start_qualifies({
        "ss_flag": ss_flag,
        "rvol20": rvol,
        "pct_up_from_65d_low": m.get("pct_up_from_65d_low"),
        "purple_dot_count_60d": m.get("purple_dot_count_60d"),
        "dist_20dma_pct": dist,
        "adr20": m.get("adr20"),
        "days_tracked": tracking_age(conn, symbol, as_of),
    })

    # Find the execution lens setup from discovery bucket and morning_setups
    setup = None
    morning = None
    try:
        b_row = conn.execute(
            "SELECT archetypes_json FROM discovery_bucket WHERE symbol = ? AND scan_date = ?",
            (symbol.upper(), as_of)
        ).fetchone()
        if b_row:
            import json
            arch = json.loads(b_row["archetypes_json"])
            if "d2_episodic" in arch:
                setup = "d2"
            elif "strong_start_ready" in arch:
                setup = "strong_start"
            elif "vcp_coil" in arch:
                setup = "vcp"
            elif "ep_ipo" in arch:
                setup = "ep_ipo"
                
        m_row = conn.execute(
            "SELECT * FROM morning_setups WHERE symbol = ? AND scan_date = ? LIMIT 1",
            (symbol.upper(), as_of)
        ).fetchone()
        if m_row:
            morning = {
                "setup_type": m_row["setup_type"],
                "branch": m_row["branch"],
                "entry_rule": m_row["entry_rule"],
                "stop_rule": m_row["stop_rule"],
            }
            if not setup:
                setup = m_row["setup_type"]
    except Exception:
        pass

    return {
        "symbol": symbol.upper(),
        "days_on_list": tracking_age(conn, symbol, as_of),
        "setup": setup,
        "morning": morning,
        "rvol20": round(rvol, 2) if rvol is not None else None,
        "chg_pct": m.get("pct_change_1d"),
        "ss_flag": ss_flag,
        "pct_up_65d_low": m.get("pct_up_from_65d_low"),
        "dist_20dma_pct": round(dist, 2) if dist is not None else None,
        "purple_dot_count": m.get("purple_dot_count_60d"),
        "near_52w_high": near_52w_high,
        "rs": m.get("rs"),
        "arora_qualifies": qualify["qualifies"],
        "arora_reasons": qualify["reasons"],
        "arora_fails": qualify["fails"],
    }
