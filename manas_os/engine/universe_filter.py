"""Universe tradeability gate — price/liquidity/ETF/circuit-lock filters.

Answers "is this symbol even worth scanning?" ahead of the setup/scan engines.
Two layers, deliberately kept separate:

  - `evaluate_symbol`: pure function, no DB access, takes a symbol's trailing
    bars and a `GateConfig` and returns a tradeable/excluded verdict with
    human-readable reasons. Fully unit-testable without a database.
  - `filter_universe`: thin DB wrapper that loads the trailing window per
    symbol (mirrors the trailing-window query pattern in
    `manas_os.sources.universe_breadth.compute_breadth`) and calls
    `evaluate_symbol` for each.

No black box: every gate that actually ran and failed appends a specific,
readable reason string. Gates that could not run (market cap — not present in
`daily_prices`) are never silently skipped-and-passed; they're surfaced in
`metrics` instead, so a symbol never looks "clean" because a check was quietly
never performed.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

# Heuristic, symbol-name-based ETF keyword list. NOT authoritative — matches on
# substrings of the trading symbol only, so it can both false-positive (e.g. a
# genuine company whose name happens to contain one of these strings) and
# false-negative (ETFs whose symbol doesn't carry any of these markers). Good
# enough as a cheap pre-filter; do not treat its verdict as ground truth.
_ETF_KEYWORDS = {
    "ETF",
    "BEES",        # Nippon India's *BEES family (NIFTYBEES, GOLDBEES, ...)
    "NIFTYBEES",
    "GOLDBEES",
    "LIQUIDBEES",
    "LIQUID",      # liquid/money-market ETFs, e.g. LIQUIDCASE
    "SETFNIF",     # SBI ETF Nifty
    "SETF",        # SBI ETF family generally
    "IETF",        # ICICI Prudential ETFs (e.g. ICICIB22, but many use IETF suffix)
    "NEXT50",      # NIFTY Next 50 trackers (HDFCNEXT50 leaked through 2026-07-06)
    "NIFTY",       # index-tracking units generally carry NIFTY in the symbol
    "SENSEX",
    "MOM50", "MOM100", "MOM30",  # momentum-index funds
    "TOP100", "TOP50",
    "GSEC",        # gilt funds (GSEC10ABSL, GSEC5IETF ... leaked into movers 2026-07-10)
    "LOWVOL",      # factor-index funds (LOWVOL, LOWVOL1)
    "ALPHAETF", "ALPHA50",
    "FANG",        # international trackers (MAFANG)
    "HDFCSML", "HDFCMID",  # index-fund units
    "ABSL",        # Aditya Birla Sun Life fund units
    "MID150", "SML250", "MIDCAPETF", "SMALLCAP250",
    "BANKADD",     # sector-bank fund units (PVTBANKADD, PSUBANKADD)
    "HDFCNIF", "MOVALUE", "MOQUALITY", "MOMENTUM", "QUAL30", "VAL30",
}


@dataclass
class GateConfig:
    """Tradeability gate thresholds — MODERATE preset (locked decisions).

    Do not change these defaults casually; they were chosen deliberately as
    the "moderate" tier of a stricter/looser spectrum.
    """
    min_price: float = 30.0                 # rupees
    min_avg_turnover_cr: float = 5.0        # rupee crore/day, avg over trailing 20 sessions
    min_market_cap_cr: float = 1000.0       # rupee crore — check SKIPPED, mcap not in daily_prices
    exclude_etf: bool = True


def is_probable_etf(symbol: str) -> bool:
    """Heuristic keyword check on the symbol string (e.g. 'GOLDBEES', 'NIFTYBEES').

    This is symbol-name pattern matching, NOT an authoritative ETF/instrument-type
    lookup — it can miss real ETFs and can misfire on non-ETF symbols that happen
    to contain one of the keywords. Treat it as a cheap heuristic pre-filter only.
    """
    sym = (symbol or "").upper()
    return any(kw in sym for kw in _ETF_KEYWORDS)


def circuit_locked(bars: list[dict]) -> bool:
    """Heuristic flag for a suspected circuit-lock / illiquid-freeze day.

    Not authoritative — real circuit-lock data would come from exchange
    surveillance flags, which we don't have. This infers it from OHLCV shape:

      - the latest bar has high == low (no intraday range at all), OR
      - at least 3 of the last 5 bars have high == low, OR
      - the latest bar's volume is 0 or None (no trading happened)

    `bars` must be ascending by trade_date; only the tail is inspected.
    """
    if not bars:
        return False
    latest = bars[-1]
    if _flat(latest):
        return True
    tail5 = bars[-5:]
    flat_count = sum(1 for b in tail5 if _flat(b))
    if flat_count >= 3:
        return True
    vol = latest.get("volume")
    if vol is None or vol == 0:
        return True
    return False


def _flat(bar: dict) -> bool:
    """True if a bar's high == low (both present)."""
    h, l = bar.get("high"), bar.get("low")
    return h is not None and l is not None and h == l


def evaluate_symbol(
    bars: list[dict],
    symbol: str,
    cfg: GateConfig,
    market_cap_cr: float | None = None,
) -> dict:
    """Evaluate one symbol's tradeability from its trailing bars. Pure, no DB access.

    `bars`: ascending by trade_date, each a dict with at least
    trade_date/open/high/low/close/prev_close/volume (delivery_qty/delivery_pct
    optional). Some fields may be missing/None — handled defensively.

    `market_cap_cr`: optional market-cap (rupee crore), typically resolved from
    `symbol_quality.market_cap_cr` by the caller. When a value IS supplied, the
    `cfg.min_market_cap_cr` floor is enforced as a real gate (fails + reason
    appended below the floor). When None, the check is SKIPPED and flagged —
    never silently treated as a pass — mirroring the existing
    "skipped: mcap unavailable" pattern.

    Returns {"symbol", "tradeable", "reasons_failed", "metrics"}.
    """
    reasons_failed: list[str] = []
    metrics: dict = {}

    if not bars:
        metrics["price"] = None
        metrics["avg_turnover_cr"] = None
        metrics["turnover_window_days"] = 0
        metrics["etf"] = is_probable_etf(symbol)
        metrics["circuit_locked"] = False
        if market_cap_cr is None:
            metrics["mcap_check"] = "skipped: mcap unavailable"
        else:
            metrics["mcap_check"] = f"checked: {market_cap_cr:.0f}cr"
            metrics["market_cap_cr"] = market_cap_cr
            if market_cap_cr < cfg.min_market_cap_cr:
                reasons_failed.append(
                    f"market cap ₹{market_cap_cr:.0f}cr < ₹{cfg.min_market_cap_cr:.0f}cr floor"
                )
        reasons_failed.append("no price history available")
        return {
            "symbol": symbol,
            "tradeable": False,
            "reasons_failed": reasons_failed,
            "metrics": metrics,
        }

    latest = bars[-1]
    price = latest.get("close")
    metrics["price"] = price

    # --- avg turnover over trailing min(20, len(bars)) sessions ---
    window = bars[-20:]
    turnovers = []
    for b in window:
        close = b.get("close")
        vol = b.get("volume")
        if close is None or vol is None:
            continue
        turnovers.append(close * vol / 1e7)
    avg_turnover_cr = (sum(turnovers) / len(turnovers)) if turnovers else None
    metrics["avg_turnover_cr"] = avg_turnover_cr
    metrics["turnover_window_days"] = len(window)

    # --- ETF heuristic ---
    etf = is_probable_etf(symbol)
    metrics["etf"] = etf

    # --- circuit-lock heuristic ---
    locked = circuit_locked(bars)
    metrics["circuit_locked"] = locked

    # --- market cap: not present in daily_prices; caller supplies it (e.g.
    # from symbol_quality.market_cap_cr) when available. When absent, SKIP and
    # flag rather than silently pass — a symbol never looks "clean" because
    # this check was quietly never performed. ---
    if market_cap_cr is None:
        metrics["mcap_check"] = "skipped: mcap unavailable"
    else:
        metrics["mcap_check"] = f"checked: {market_cap_cr:.0f}cr"
        metrics["market_cap_cr"] = market_cap_cr

    # --- gates ---
    if price is None:
        reasons_failed.append("price unavailable")
    elif price < cfg.min_price:
        reasons_failed.append(
            f"price ₹{price:.2f} < ₹{cfg.min_price:.2f} floor"
        )

    if avg_turnover_cr is None:
        reasons_failed.append("avg turnover unavailable")
    elif avg_turnover_cr < cfg.min_avg_turnover_cr:
        reasons_failed.append(
            f"avg turnover ₹{avg_turnover_cr:.2f}cr < "
            f"₹{cfg.min_avg_turnover_cr:.2f}cr floor"
        )

    if cfg.exclude_etf and etf:
        matched = next((kw for kw in _ETF_KEYWORDS if kw in (symbol or "").upper()), "?")
        reasons_failed.append(f"symbol looks like an ETF ({matched})")

    if market_cap_cr is not None and market_cap_cr < cfg.min_market_cap_cr:
        reasons_failed.append(
            f"market cap ₹{market_cap_cr:.0f}cr < ₹{cfg.min_market_cap_cr:.0f}cr floor"
        )

    if locked:
        latest_flat = _flat(latest)
        tail5 = bars[-5:]
        flat_count = sum(1 for b in tail5 if _flat(b))
        vol = latest.get("volume")
        if latest_flat:
            reasons_failed.append("circuit-locked: latest day high==low")
        elif flat_count >= 3:
            reasons_failed.append(f"circuit-locked: high==low {flat_count}/5 days")
        elif vol is None or vol == 0:
            reasons_failed.append("circuit-locked: latest volume is zero/None")

    return {
        "symbol": symbol,
        "tradeable": len(reasons_failed) == 0,
        "reasons_failed": reasons_failed,
        "metrics": metrics,
    }


def filter_universe(
    conn,
    as_of_date: str,
    symbols: list[str] | None = None,
    cfg: GateConfig | None = None,
    market_cap_by_symbol: dict[str, float] | None = None,
) -> dict:
    """Evaluate every EQ symbol's tradeability as of `as_of_date`.

    If `symbols` is None, pulls every distinct symbol with an EQ row on
    `as_of_date`. For each symbol, loads its trailing ~25 bars (series='EQ',
    trade_date <= as_of_date) via ORDER BY trade_date DESC LIMIT 25 then
    reverses in Python to get ascending order — mirrors the trailing-window
    pattern in `manas_os.sources.universe_breadth.compute_breadth`.

    `market_cap_by_symbol`: optional {symbol: market_cap_cr} lookup (e.g. from
    `symbol_quality`), passed straight through to `evaluate_symbol` per symbol.
    Symbols missing from this dict evaluate with market_cap_cr=None (mcap
    check SKIPPED+flagged, never silently passed).

    Does not close `conn` (caller owns the connection's lifecycle).

    Returns {"as_of", "tradeable": [symbols...], "excluded": [{"symbol",
    "reasons_failed"}...], "config": {...}}.
    """
    cfg = cfg or GateConfig()
    market_cap_by_symbol = market_cap_by_symbol or {}

    if symbols is None:
        rows = conn.execute(
            "SELECT DISTINCT symbol FROM daily_prices WHERE series='EQ' AND trade_date = ?",
            (as_of_date,),
        ).fetchall()
        symbols = [r["symbol"] for r in rows]

    tradeable: list[str] = []
    excluded: list[dict] = []

    for sym in symbols:
        rows = conn.execute(
            "SELECT trade_date, open, high, low, close, prev_close, volume, "
            "delivery_qty, delivery_pct FROM daily_prices "
            "WHERE series='EQ' AND symbol = ? AND trade_date <= ? "
            "ORDER BY trade_date DESC LIMIT 25",
            (sym, as_of_date),
        ).fetchall()
        bars = [dict(r) for r in reversed(rows)]
        result = evaluate_symbol(bars, sym, cfg, market_cap_cr=market_cap_by_symbol.get(sym))
        if result["tradeable"]:
            tradeable.append(sym)
        else:
            excluded.append({"symbol": sym, "reasons_failed": result["reasons_failed"]})

    return {
        "as_of": as_of_date,
        "tradeable": tradeable,
        "excluded": excluded,
        "config": asdict(cfg),
    }
