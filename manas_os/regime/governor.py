"""regime/governor.py — regime as LAW, not display (Manas 2.0, plan T1.3).

One function answers "what is allowed today". The Setups API, EOD alerts,
risk sizing, and (Phase 4) Telegram all route through it — a single writer of
"is this allowed tonight" (anti-mashup). Values are the plan's LOCKED table.
"""
from __future__ import annotations

from typing import Any

from manas_os.risk.plan import PROFILES, MAX_NEW_POSITIONS_PER_DAY, active_profile

# Max cards the feed may SHOW (after ordinal ranking) — LOCKED
MAX_CARDS = {"RISK_ON": 8, "SELECTIVE": 4, "DEFENSIVE": 2, "NO_TRADE": 0}

# Allowed setup FAMILIES — mirrors scanner.gates.ALLOWED_FAMILIES (kept in
# gates.py for gate use; re-exported here for display/enforcement callers).
ALLOWED_FAMILIES = {
    "RISK_ON":   ["catalyst", "base/pattern", "momentum", "accumulation"],
    "SELECTIVE": ["catalyst", "base/pattern"],
    "DEFENSIVE": ["catalyst"],
    "NO_TRADE":  [],
}

NO_TRADE_MESSAGE = "NO_TRADE regime — 0 setups by design. Cash is a position."


def governor(market_mode: str, profile: str | None = None, conn=None) -> dict[str, Any]:
    """The day's law. Unknown/None mode degrades to NO_TRADE (never permissive)."""
    mode = (market_mode or "").upper()
    if mode not in MAX_CARDS:
        mode = "NO_TRADE"
    # Connection ownership stays with the caller. Falling back to the canonical
    # learning profile keeps this pure for tests/research; live request paths
    # pass their existing connection and therefore use the saved trader profile.
    prof_name = profile or (active_profile(conn) if conn is not None else "learning")
    prof = PROFILES[prof_name]
    base_risk, hard_max = prof["risk_per_trade"][mode]
    return {
        "market_mode": mode,
        "profile": prof_name,
        "max_cards": MAX_CARDS[mode],
        "allowed_families": ALLOWED_FAMILIES[mode],
        "risk_band": {"base_pct": base_risk, "hard_max_pct": hard_max},
        "open_risk_cap_pct": prof["open_risk_cap"][mode],
        "max_open_positions": prof["max_open_positions"],
        "max_new_positions": MAX_NEW_POSITIONS_PER_DAY[mode],
        "push_allowed": mode in ("RISK_ON", "SELECTIVE"),
        "message": NO_TRADE_MESSAGE if mode == "NO_TRADE" else None,
    }
