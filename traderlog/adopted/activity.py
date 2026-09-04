"""Reactor Scale core — direction-neutral EOD abnormal-activity analogue.

Adopted from ``manas_os/alpha/activity.py`` on 2026-08-25 per
DECISIONS.md 2026-08-22 "volume reverse-engineering" adoption (TASKS.md W5).
The universe-tradeability helpers below are ported from
``manas_os/engine/universe_filter.py`` (same adoption, same date). Once copied
this file is TraderLog's own; drift from the manas_os originals is expected and
fine (CANONICAL.md §5). There is no ``import manas_os`` anywhere in this package
and there must never be one.

The original is a sat10ic-owned, shadow-only approximation built from official
NSE bhavcopy fields, deliberately NOT named "Reactor Scale" because the
proprietary formula and order/tick footprint are unavailable: the output must
never be presented as institutional identity, trade direction, or a risk input.
That caveat carries over verbatim.

Formula (unchanged, frozen coefficients — V2 calibration fit on 60 constraints
from the user-supplied 2026-07-01/10 SMF screenshots; see the original file's
comment block):

    avg_trade_qty(session) = volume / num_trades        # shares per trade
    q_ratio  = avg_trade_qty(today)  / mean(avg_trade_qty over prior 20 sessions)
    d_ratio  = delivery_pct(today)   / mean(delivery_pct over prior 19 sessions)
    activity_score = Q*q_ratio + D*d_ratio + I*(q_ratio*d_ratio)^E + intercept
    Q=1.165335  D=1.04631  I=1.152161  E=0.84  intercept=-0.213928
    storage rounding: q_ratio/d_ratio -> 6 dp, activity_score -> 2 dp

Drift from the manas_os original — the load-bearing part of this adoption
(documented per CANONICAL.md §5; every deviation is intentional and tested,
never silent):

  * **q window is exclusive prior-20.** The original's ``avg_trade_qty_ratio20``
    divides today's avg trade qty by an INCLUSIVE-20 mean (current session
    inside the denominator). TraderLog's ``alpha_activity_signals.q_ratio``
    divides by the mean of the 20 PRIOR sessions only (current excluded), per
    the W5 brief's warm-up rule — a symbol/date with fewer than 20 prior
    sessions is SKIPPED (not written), so the prior-20 mean is always defined.
    This is a deliberate brief-driven change, not a data-forced one: the two
    projects' ``daily_prices`` carry IDENTICAL NSE bhavcopy semantics
    (``volume`` = TTL_TRD_QNTY shares, ``num_trades`` = NO_OF_TRADES,
    ``delivery_pct`` = DELIV_PER, all non-NULL for EQ rows — verified on the
    TraderLog production DB 2026-08-26), so no unit adaptation was required.
  * **Warm-up threshold.** Original ``_score`` required 20 rows total (19
    prior); TraderLog requires >= 20 PRIOR sessions (21 rows total) — the
    W5 brief's XP/C8 warm-up lesson: never persist half-baked ratios.
  * **Universe filter applied inline.** The original ``compute()`` only applies
    the ETF-name guard plus a point-in-time classified-stock membership check
    against a ``universe`` snapshot table. TraderLog has NO ``universe`` table,
    so the base universe is the NSE-master validation
    (``SELECT DISTINCT symbol FROM daily_prices WHERE series='EQ'`` — the same
    master ``derive/watchlists.py`` validates against), and the brief requires
    the ported ``engine/universe_filter.py`` tradeability gates to restrict
    which symbol-dates get signals: price floor, avg-turnover floor, ETF-name
    exclusion, circuit-lock. manas_os applies those gates upstream in its
    scanner; TraderLog has no scanner stage, so this pipeline applies them
    inline (placement difference, not a numbers difference). The market-cap
    gate is SKIPPED (no market-cap source in ``daily_prices``) and surfaced in
    ``metrics`` — never silently passed, matching the original's stance.
  * **Not persisted here:** the original's percentile/state/persistence_sessions
    and the per-trade diagnostic columns have no place in TraderLog's
    ``alpha_activity_signals`` (symbol, trade_date, q_ratio, d_ratio,
    activity_score, formula_version, ingested_at) — the brief's table shape,
    ``db/schema.sql`` (untouched). ``ABNORMAL_LEVEL``/``EXTREME_LEVEL`` remain
    as documented threshold vocabulary for reporting only (run_w5.py).
"""

from __future__ import annotations

WARMUP_PRIOR_SESSIONS = 20  # >= this many PRIOR sessions required before a signal
DELIVERY_WINDOW = 19        # prior-19 mean, identical to the original

FORMULA_VERSION = "reactor-v1-adapted-20260825"
# V2 calibration: 15 exact score rows plus their previous-day/four-day/ten-day
# aggregates from the user-supplied 2026-07-01/10 SMF screenshots provided 60
# constraints across 150 underlying sessions; the two dates were also fitted in
# opposite train/test directions. Coefficients frozen; do not tune casually.
Q_COEFFICIENT = 1.165335
D_COEFFICIENT = 1.04631
INTERACTION_COEFFICIENT = 1.152161
INTERACTION_EXPONENT = 0.84
INTERCEPT = -0.213928
SOURCE_NOTE = (
    "Abnormal activity; direction unresolved. Uses aggregate NSE bhavcopy, "
    "not individual orders, aggressor side, or participant identity."
)
# Threshold vocabulary only (TraderLog's table has no state column): used by
# run_w5.py to report how many signals clear each level.
ABNORMAL_LEVEL = 3.5
EXTREME_LEVEL = 8.0

# ---------------------------------------------------------------------------
# Universe tradeability gates — ported from manas_os/engine/universe_filter.py
# (2026-08-25). MODERATE preset thresholds: locked decisions in manas_os ("do
# not change these defaults casually" — the turnover floor 5.0->2.0cr change
# was evidence-driven on 2026-07-30, a 2nd-place recall killer at 27% of 436
# refused winners, sized for a retail trader whose turnover headroom is ~13x
# the 2cr floor). Kept as module constants, not config keys: this wave exposes
# no tunable.
# ---------------------------------------------------------------------------

MIN_PRICE = 30.0                 # rupees
MIN_AVG_TURNOVER_CR = 2.0        # rupee crore/day, avg over trailing 20 sessions
MIN_MARKET_CAP_CR = 1000.0       # rupee crore — check SKIPPED, no mcap in daily_prices
EXCLUDE_ETF = True

# Heuristic, symbol-name-based ETF keyword list (verbatim port). NOT
# authoritative — substring match on the trading symbol only, so it can both
# false-positive (a genuine company whose name contains one of these strings)
# and false-negative (ETFs whose symbol carries none of these markers). Good
# enough as a cheap pre-filter; never treat its verdict as ground truth.
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


def is_probable_etf(symbol: str) -> bool:
    """Keyword heuristic on the symbol string (e.g. 'GOLDBEES', 'NIFTYBEES').

    Symbol-name pattern matching, NOT an authoritative ETF/instrument-type
    lookup — it can miss real ETFs and can misfire on non-ETF symbols that
    happen to contain one of the keywords. Cheap heuristic pre-filter only.
    """
    sym = (symbol or "").upper()
    return any(kw in sym for kw in _ETF_KEYWORDS)


def _flat(bar: dict) -> bool:
    """True if a bar's high == low (both present)."""
    h, l = bar.get("high"), bar.get("low")
    return h is not None and l is not None and h == l


def circuit_locked(bars: list[dict]) -> bool:
    """Heuristic flag for a suspected circuit-lock / illiquid-freeze day.

    Not authoritative — real circuit-lock data would come from exchange
    surveillance flags, which aren't available. Inferred from OHLCV shape:

      - the latest bar has high == low (no intraday range at all), OR
      - at least 3 of the last 5 bars have high == low, OR
      - the latest bar's volume is 0 or None (no trading happened)

    ``bars`` must be ascending by trade_date; only the tail is inspected.
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


def universe_verdict(
    bars: list[dict],
    symbol: str,
    *,
    min_price: float = MIN_PRICE,
    min_avg_turnover_cr: float = MIN_AVG_TURNOVER_CR,
    exclude_etf: bool = EXCLUDE_ETF,
) -> dict:
    """Tradeability verdict for one symbol from its trailing bars (pure).

    Ported from ``manas_os/engine/universe_filter.py::evaluate_symbol``
    (2026-08-25). ``bars`` ascending by trade_date; each bar needs at least
    trade_date/open/high/low/close/volume (delivery fields optional). ``bars``
    should be the trailing window as-of the date being judged — the pipeline
    passes the up-to-20 sessions INCLUDING the judged date (the original's
    ``bars[-20:]`` convention).

    Market cap can't be checked (no source in ``daily_prices``): the check is
    SKIPPED and surfaced in ``metrics["mcap_check"]`` — never silently treated
    as a pass (same stance as the original: a symbol never looks clean because
    a check was quietly never performed).

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
        metrics["mcap_check"] = "skipped: mcap unavailable"
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

    # --- avg turnover over trailing min(20, len(bars)) sessions, rupees crore ---
    # Same estimate as the original: close * volume / 1e7, NOT the stored
    # turnover column (TURNOVER_LACS) — kept identical so numbers match.
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

    # --- market cap: skipped, never silently passed ---
    metrics["mcap_check"] = "skipped: mcap unavailable"

    # --- gates ---
    if price is None:
        reasons_failed.append("price unavailable")
    elif price < min_price:
        reasons_failed.append(f"price ₹{price:.2f} < ₹{min_price:.2f} floor")

    if avg_turnover_cr is None:
        reasons_failed.append("avg turnover unavailable")
    elif avg_turnover_cr < min_avg_turnover_cr:
        reasons_failed.append(
            f"avg turnover ₹{avg_turnover_cr:.2f}cr < "
            f"₹{min_avg_turnover_cr:.2f}cr floor"
        )

    if exclude_etf and etf:
        matched = next((kw for kw in _ETF_KEYWORDS if kw in (symbol or "").upper()), "?")
        reasons_failed.append(f"symbol looks like an ETF ({matched})")

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


# ---------------------------------------------------------------------------
# Reactor Scale scoring core — pure, unit-testable without a DB.
# ---------------------------------------------------------------------------

def avg_trade_qty(volume, num_trades) -> float | None:
    """Shares per trade for a session, or None when not computable.

    Same definition as the original: volume (TTL_TRD_QNTY shares) divided by
    num_trades (NO_OF_TRADES). A missing/zero denominator is not a number —
    None, never a fabricated one.
    """
    try:
        v = float(volume)
        n = float(num_trades)
    except (TypeError, ValueError):
        return None
    if v <= 0 or n <= 0:
        return None
    return v / n


def q_ratio_for(today_avg_qty: float, prior_avg_qtys: list[float]) -> float | None:
    """Today's avg trade qty vs the mean of the prior 20 sessions (exclusive).

    None when fewer than ``WARMUP_PRIOR_SESSIONS`` prior sessions exist or the
    prior-20 mean is <= 0 — a non-positive denominator is refused, not stored
    (XP/C8 warm-up lesson: never persist half-baked ratios).
    """
    if len(prior_avg_qtys) < WARMUP_PRIOR_SESSIONS:
        return None
    window = prior_avg_qtys[-WARMUP_PRIOR_SESSIONS:]
    mean = sum(window) / len(window)
    if mean <= 0 or today_avg_qty <= 0:
        return None
    return today_avg_qty / mean


def d_ratio_for(today_delivery_pct: float, prior_delivery_pcts: list[float]) -> float | None:
    """Today's delivery% vs the mean of the prior 19 sessions (exclusive).

    Identical window to the original (prior-19). None when fewer than 19 prior
    sessions exist or the prior-19 mean is <= 0.
    """
    if len(prior_delivery_pcts) < DELIVERY_WINDOW:
        return None
    window = prior_delivery_pcts[-DELIVERY_WINDOW:]
    mean = sum(window) / len(window)
    if mean <= 0 or today_delivery_pct <= 0:
        return None
    return today_delivery_pct / mean


def raw_activity_score(q_ratio: float, d_ratio: float) -> float:
    """Unrounded Reactor Scale activity score: Q*q + D*d + I*(q*d)^E + intercept."""
    return (
        Q_COEFFICIENT * q_ratio
        + D_COEFFICIENT * d_ratio
        + INTERACTION_COEFFICIENT * ((q_ratio * d_ratio) ** INTERACTION_EXPONENT)
        + INTERCEPT
    )


def session_signal(
    symbol: str,
    trade_date: str,
    *,
    volume,
    num_trades,
    delivery_pct,
    prior_avg_qtys: list[float],
    prior_delivery_pcts: list[float],
) -> dict | None:
    """Build one alpha_activity_signals-shaped row for a symbol-date, or None.

    Pure: no I/O. Returns None (skipped, NOT a zero score) when any of:
      * today's bar is not computable (volume/num_trades <= 0 or missing),
      * fewer than ``WARMUP_PRIOR_SESSIONS`` (20) prior sessions exist,
      * a ratio denominator is <= 0 (guards mirror the original's
        ``inclusive_qty_mean <= 0 / prior_delivery_mean <= 0`` checks, applied
        to the adopted exclusive windows).
    The caller (activity_pipeline.backfill) decides warm-up/universe/guard
    bookkeeping; this function is the pure per-session math.
    """
    today_avg = avg_trade_qty(volume, num_trades)
    if today_avg is None:
        return None
    q = q_ratio_for(today_avg, prior_avg_qtys)
    if q is None:
        return None
    try:
        today_deliv = float(delivery_pct)
    except (TypeError, ValueError):
        return None
    d = d_ratio_for(today_deliv, prior_delivery_pcts)
    if d is None:
        return None
    raw = raw_activity_score(q, d)
    return {
        "symbol": symbol,
        "trade_date": trade_date,
        "q_ratio": round(q, 6),
        "d_ratio": round(d, 6),
        "activity_score": round(raw, 2),
        "raw_score": raw,
        "avg_trade_qty": round(today_avg, 4),
    }