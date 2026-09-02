"""Thrust and price-action-quality features: ADRMAX and ChopScore.

Both are CLEAN-ROOM reimplementations from the authors' public descriptions —
the same convention this package already uses for ``detectors/base_pattern.py``
(BananaPatterns) and ``features/activity.py`` (Reactor Scale). No vendor code
was read or copied, and no parity with the originals is claimed.

Sources of the ideas (descriptions only):
  ADRMAX    — TradingView script ``jtmullSY-ADRMAX`` by Arvin (@selfunmade);
              the Pine source is PROTECTED, but the author published the full
              algorithm and its defaults on X (thread of 2026-06-29/30,
              x.com/selfunmade/status/1939395099252924614). Verbatim:

                "ADRMAX is the average percentage range (high to low) of top
                 big green days. Lookback is the number of past days the
                 script checks. % Data sets how much of the biggest daily
                 moves (from the lookback) are used."

              His worked example fixes the exact semantics: "out of the last
              250 Days (Lookback) 50% are green candles. The script will make
              and sort a list [of] the 125 green candles by size in descending
              order. Only 15% (%Data) of [the] sorted list of 125 green
              candles are used ... 18.75 -> rounded to 19 candles."

              Note the percentage applies to the count of GREEN candles found,
              NOT to the lookback length, and the count is ROUNDED. Both are
              implemented that way below.

              His rationale for preferring it to ADR: "ADR ... includes narrow
              range candles red candles etc. This why it is not optimal to use
              ADR for judging thrust power of a stock."
  ChopScore — TradingView script ``ylJMNraw-ChopScore`` (open source, not
              read). Described as a custom choppiness score from "the ratio of
              the candle body to its full range", smoothed over a lookback,
              measuring price-action cleanliness and shakeout risk.

WHY ADRMAX EARNS ITS PLACE BESIDE ADR
Plain ADR is symmetric average volatility. ADRMAX measures UPSIDE EXPANSION
capacity, which is the reachability question for the reward side of a trade:
"can this name plausibly travel to its target inside the horizon?" Measured on
the 2026-09-01 cohort they are related but not redundant — Spearman 0.81, with
ADRMAX a median 1.75x of ADR20.

PARAMETER PROVENANCE (read before changing the defaults)
The defaults below are the AUTHOR'S OWN stated values (250 / 15%), not guesses.
That distinction matters here: a sensitivity study on the 2026-09-01 cohort
over a plausible grid (lookback 40/60/90 x top 15/25/33%) showed the
cross-sectional ranking is **not** robust to these choices — worst pairwise
Spearman 0.73, driven mainly by lookback. Because the ranking moves with the
parameters, using the author's real values rather than an invented pair is
what makes the metric comparable to his published output.

A 250-session lookback means recently-listed names (IPO bases especially) will
return ``None`` until they have the history. That is correct fail-closed
behaviour, not a gap to paper over.

Point-in-time: every window is EXCLUSIVE of the current bar, matching
``adr_atr.adr``. Warm-up returns ``None``, never 0 (R12).
"""
from __future__ import annotations

from typing import Optional, Sequence

from unidesk.contracts.base import ContractError

from .participation import _series  # shared strict-series helper

# --- frozen defaults (R14). ADRMAX values are the AUTHOR'S published ones. ---
ADRMAX_LOOKBACK_DEFAULT = 250     # author's stated Lookback
ADRMAX_TOP_PCT_DEFAULT = 0.15     # author's stated "% Data"
ADRMAX_MIN_BULLISH_BARS = 4     # below this the average is noise, so refuse

CHOP_LOOKBACK_DEFAULT = 20
CHOP_MIN_BARS = 10

# Interpretation bands for ChopScore. These are OUR bands calibrated on the
# 2026-09-01 NSE cohort (median 56.7, p25 51.7, p75 60.4), NOT the original
# author's colour thresholds — our scaling is clean-room and may not align.
CHOP_BAND_CLEAN = 52.0
CHOP_BAND_MODERATE = 57.0
CHOP_BAND_MESSY = 62.0


def adr_max(
    highs: Sequence[float],
    lows: Sequence[float],
    opens: Sequence[float],
    closes: Sequence[float],
    *,
    lookback: int = ADRMAX_LOOKBACK_DEFAULT,
    top_pct: float = ADRMAX_TOP_PCT_DEFAULT,
) -> Optional[float]:
    """Mean of the largest BULLISH daily ranges, as % of the bar's low.

    "Thrust power": how far this name expands on its strong days, which bounds
    what a target can plausibly ask for inside a fixed horizon.

    Window is the ``lookback`` bars BEFORE the last bar (exclusive), so the
    current session never sits in its own baseline. Returns ``None`` when the
    window is unavailable or holds fewer than ``ADRMAX_MIN_BULLISH_BARS``
    bullish bars — never a fabricated 0.
    """
    if lookback < 1:
        raise ContractError("lookback must be >= 1")
    if not 0.0 < top_pct <= 1.0:
        raise ContractError("top_pct must be in (0, 1]")
    h = _series(highs, "highs")
    l = _series(lows, "lows")
    o = _series(opens, "opens")
    c = _series(closes, "closes")
    if not (len(h) == len(l) == len(o) == len(c)):
        raise ContractError("highs, lows, opens, closes must have equal length")
    n = len(c)
    if n < lookback + 1:
        return None

    moves: list = []
    for i in range(n - lookback - 1, n - 1):     # exclusive of the last bar
        if c[i] <= o[i]:
            continue                              # bullish bars only
        if l[i] <= 0:
            continue
        rng = h[i] - l[i]
        if rng < 0:
            raise ContractError("negative daily range in input data")
        moves.append(rng / l[i] * 100.0)

    if len(moves) < ADRMAX_MIN_BULLISH_BARS:
        return None
    moves.sort(reverse=True)
    k = max(1, int(round(len(moves) * top_pct)))
    return sum(moves[:k]) / k


def chop_score(
    opens: Sequence[float],
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    *,
    lookback: int = CHOP_LOOKBACK_DEFAULT,
) -> Optional[float]:
    """0-100 price-action choppiness. HIGH = choppy (shakeout-prone).

    Mean of ``|close - open| / (high - low)`` over the prior ``lookback`` bars,
    inverted and scaled: a bar that closes far from its open relative to its
    range is decisive; one that closes mid-range after a wide swing is not.
    Direction-agnostic by construction — it says nothing about trend.

    Independent of reward geometry on the cohort it was validated against
    (median R:R 1.13 for the cleanest half vs 1.12 for the choppiest), which is
    the point: it adds a dimension rather than restating one.
    """
    if lookback < 1:
        raise ContractError("lookback must be >= 1")
    o = _series(opens, "opens")
    h = _series(highs, "highs")
    l = _series(lows, "lows")
    c = _series(closes, "closes")
    if not (len(o) == len(h) == len(l) == len(c)):
        raise ContractError("opens, highs, lows, closes must have equal length")
    n = len(c)
    if n < lookback + 1:
        return None

    ratios: list = []
    for i in range(n - lookback - 1, n - 1):     # exclusive of the last bar
        rng = h[i] - l[i]
        if rng <= 0:
            continue                              # a doji-flat bar carries no info
        ratios.append(abs(c[i] - o[i]) / rng)
    if len(ratios) < CHOP_MIN_BARS:
        return None
    return (1.0 - sum(ratios) / len(ratios)) * 100.0


def chop_band(score: Optional[float]) -> Optional[str]:
    """Named band for a ChopScore. ``None`` in, ``None`` out (never a guess)."""
    if score is None:
        return None
    if score < CHOP_BAND_CLEAN:
        return "CLEAN"
    if score < CHOP_BAND_MODERATE:
        return "MODERATE"
    if score < CHOP_BAND_MESSY:
        return "MESSY"
    return "VERY_CHOPPY"


def stop_in_thrust_days(
    trigger: Optional[float],
    invalidation: Optional[float],
    adrmax_pct: Optional[float],
) -> Optional[float]:
    """Risk expressed in the stock's own thrust-days.

    ``(trigger - invalidation) / trigger`` as a percent, divided by ADRMAX.
    A value below ~1.0 means ordinary upside expansion is the same size as the
    entire risk budget — the stop sits inside the noise of a normal strong day.

    This is the diagnostic that explained the cohort's poor R:R: the median stop
    sits 0.90 thrust-days away while the median R:R is 1.13.
    """
    if trigger is None or invalidation is None or adrmax_pct is None:
        return None
    if trigger <= 0 or adrmax_pct <= 0:
        return None
    stop_pct = (trigger - invalidation) / trigger * 100.0
    if stop_pct <= 0:
        return None
    return stop_pct / adrmax_pct
