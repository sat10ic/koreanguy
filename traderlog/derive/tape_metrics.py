"""derive/tape_metrics.py -- stock-level tape metrics over ``daily_prices``.

Pure read/compute foundation for the per-symbol "what is this name doing on the
tape" layer: average daily range, tightness, volume character, a volatility
contraction (VCP) proxy, momentum bursts, inside bars, gap shape, and where the
price sits relative to its own history. Nothing here writes, calls an LLM, or
guesses a calendar -- every number is a deterministic function of the actual
``daily_prices`` rows it reads (``series = 'EQ'`` only). Consumers (UI screens,
run_recon-style reports) call these functions directly; there is no writer
contract, matching the derivation discipline of ``derive/radar.py``.

## Data rules (every function)

- Only rows with ``series = 'EQ'`` are used; other series are ignored entirely.
- ``as_of`` is an INCLUSIVE upper bound on ``trade_date`` (ISO 'YYYY-MM-DD').
  Sessions strictly after ``as_of`` are never read, so nothing here can look
  ahead. An ``as_of`` that is not itself a trading session (weekend, market
  holiday, suspended name) simply uses the most recent session at or before
  that date -- the "today" of every trailing window is that last session.
  A malformed ``as_of`` raises ``ValueError`` (a caller bug, not market data).
- Windows are CONTIGUOUS tails of the session list: a 20-session window
  requires the last 20 sessions to ALL be usable for that metric's fields.
  Unusable rows (NULL prices, ``high < low``, ``close <= 0``, NULL/0 volume)
  are never skipped and never imputed -- the affected field returns ``None``
  instead. This is the "nulls, never partial guesses" rule.
- Every metric returns ``None`` (or a ``None`` field) when its own minimum
  session count is not met, never a number computed from fewer sessions.
- Values are unrounded floats. Percent-point values are literal percent
  (``2.5`` means 2.5%); ratios are dimensionless decimals.
- ``conn`` may be any sqlite3 connection; all reads use positional binding, so
  the connection's row factory is irrelevant.

## Metric definitions (as implemented)

- ``adr`` -- mean of ``(high - low) / close`` over the last ``n`` sessions,
  in percent points (the default ``n = 20`` is the ADR window).
- ``tightness`` --
  ``ratio5v20`` = mean range (as a decimal, last 5 sessions) divided by the
  20-session ADR (as a decimal) -- dimensionless, ~1 means "current 5-day
  range equals the 20-day norm", << 1 means contracting.
  ``nr7`` = today's range is STRICTLY narrower than every one of the trailing
  6 sessions' ranges (narrowest of the trailing 7, ties do not count).
  ``nr4`` = same against the trailing 3 sessions.
- ``volume_character`` --
  ``dry_up`` = mean volume of the last 5 sessions divided by mean volume of
  the last 50 sessions (< 1: volume drying up).
  ``surge`` = today's volume divided by the mean volume of the last 20
  sessions (today included).
  ``surge_flag`` = ``surge >= 2.0``.
- ``vcp_proxy`` -- volatility-contraction proxy: successive pullback depths
  measured from CONFIRMED swing highs. Swing-high rule: a session is a swing
  high iff its high is strictly greater than the highs of the ``K`` sessions
  immediately before it AND strictly greater than the highs of the ``K``
  sessions immediately after it (``K = VCP_PIVOT_LOOKBACK = 3``; right-side
  bars are historical bars at or before ``as_of``, never future data --
  a peak in the last ``K`` bars is simply not yet confirmed, which is the
  honest as-of reading). Each swing high's pullback depth is
  ``(high - lowest low up to the next swing high) / high`` in percent;
  the last swing high's depth runs to the end of the lookback window
  (``VCP_LOOKBACK = 120`` sessions). ``depths`` are chronological;
  ``contracting`` is true iff every depth (after the first) is strictly less
  than its predecessor. Returns ``None`` when fewer than
  ``VCP_MIN_SESSIONS = 7`` (one confirmed swing high needs 3+1+3 bars) exist.
- ``momentum_burst`` --
  ``move_pct`` = today's close-to-close change in percent against the
  previous session's close (never the ``prev_close`` column -- that stored
  field is not the session-to-session change this metric means).
  ``vol_multiple`` = today's volume divided by the mean volume of the last 20
  sessions (identical construction to ``volume_character.surge``).
  ``fired`` = ``move_pct >= move_pct_min`` (default ``X = 3.0``, the
  documented burst threshold) AND ``vol_multiple >= 2.0``. When either input
  is missing, ``fired`` is False -- a burst is never claimed on missing data.
- ``inside_bars`` -- count of CONSECUTIVE inside bars ending at the last
  session; a session is inside iff ``high < prior high AND low > prior low``
  (strict containment; ties do not count). A single non-inside or unusable
  bar breaks the chain; today not being inside yields 0.
- ``gap_marker`` -- "earnings-style" gap shape, PRICE-BASED ONLY (gap-based,
  not earnings-confirmed: no news/calendar knowledge is used or implied):
  ``gap_pct`` = ``(open - prior session's high) / prior session's close`` in
  percent; ``gap_flag`` = ``open > prior high`` AND the gap exceeds or equals
  ``GAP_ADR_MULTIPLE = 1.0`` times the 20-session ADR.
- ``location`` --
  ``pct_from_52w_high`` = today's close relative to the highest HIGH of the
  trailing 252 sessions, in percent (negative below the high).
  ``above_sma10/20/50/200`` = today's close strictly above the simple mean of
  the trailing 10/20/50/200 closes.
- ``snapshot`` -- one dict combining every metric above plus the context
  fields ``symbol``, ``as_of``, ``series = 'EQ'``, ``as_of_session`` (the
  actual last session used), ``session_count``, and
  ``insufficient_history`` (True when fewer than ``SNAPSHOT_MIN_SESSIONS = 2``
  sessions exist -- no comparative tape at all). Individual fields inside the
  snapshot go null under their own window minimums regardless.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

# ---------------------------------------------------------------------------
# Tunables -- named + commented so every window/threshold is auditable.
# ---------------------------------------------------------------------------

ADR_DEFAULT_N = 20             # the ADR window (trailing sessions, today included)
TIGHTNESS_SHORT_WINDOW = 5     # the "current" range window inside ratio5v20
NR7_WINDOW = 7                 # narrowest-range flag window (trailing sessions)
NR4_WINDOW = 4
VOLUME_DRY_SHORT = 5           # dry-up numerator window (sessions)
VOLUME_DRY_LONG = 50           # dry-up denominator window (sessions)
SURGE_WINDOW = 20              # surge/vol_multiple average window, today included
SURGE_FLAG_MIN = 2.0           # surge >= this -> surge_flag True
VCP_LOOKBACK = 120             # how far back vcp_proxy scans for swing highs
VCP_PIVOT_LOOKBACK = 3         # bars of left+right confirmation for a swing high
VCP_MIN_SESSIONS = 7           # minimum sessions for even one measured pullback
MOMENTUM_MOVE_PCT_MIN = 3.0    # X: move_pct >= this (default burst threshold)
MOMENTUM_VOL_MULTIPLE_MIN = 2.0  # vol_multiple >= this for a burst
GAP_ADR_MULTIPLE = 1.0         # open-above-prior-high must be >= this x ADR
WEEK52_SESSIONS = 252          # 52 weeks of trading sessions
SMA_WINDOWS = (10, 20, 50, 200)  # location's simple-moving-average windows
SNAPSHOT_MIN_SESSIONS = 2      # below this there is no comparative tape at all


@dataclass(frozen=True)
class Bar:
    """One normalized daily_prices session (series='EQ' row)."""

    trade_date: str
    open: float | None
    high: float | None
    low: float | None
    close: float | None
    volume: float | None


# ---------------------------------------------------------------------------
# Loading + usability helpers
# ---------------------------------------------------------------------------

def _as_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number


def _load_sessions(conn, symbol: str, as_of: str) -> list[Bar]:
    """All ``series='EQ'`` sessions at or before ``as_of``, ascending.

    Reads with positional binding so the caller's row factory does not matter.
    Rows with an unparsable ``trade_date`` are skipped; the daily_prices
    primary key (symbol, trade_date) makes duplicates impossible.
    """
    if not isinstance(as_of, str):
        raise ValueError("as_of must be an ISO 'YYYY-MM-DD' date string")
    try:
        date.fromisoformat(as_of)
    except ValueError:
        raise ValueError(f"as_of is not an ISO 'YYYY-MM-DD' date: {as_of!r}") from None

    rows = conn.execute(
        "SELECT trade_date, open, high, low, close, volume "
        "FROM daily_prices "
        "WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? "
        "ORDER BY trade_date ASC",
        (symbol, as_of),
    ).fetchall()

    bars: list[Bar] = []
    for row in rows:
        raw_date = row[0]
        if not isinstance(raw_date, str):
            continue
        try:
            date.fromisoformat(raw_date)
        except ValueError:
            continue
        bars.append(
            Bar(
                trade_date=raw_date,
                open=_as_float_or_none(row[1]),
                high=_as_float_or_none(row[2]),
                low=_as_float_or_none(row[3]),
                close=_as_float_or_none(row[4]),
                volume=_as_float_or_none(row[5]),
            )
        )
    bars.sort(key=lambda bar: bar.trade_date)
    return bars


# Usability predicates -- each metric requires its OWN fields to be sane; a
# session that fails the predicate is never skipped or imputed (docstring
# "Data rules": the field goes null instead).
def _bar_price_ok(bar: Bar) -> bool:
    """Usable for range math: high/low/close present, high >= low, close > 0."""
    return (
        bar.high is not None
        and bar.low is not None
        and bar.close is not None
        and bar.close > 0
        and bar.high >= bar.low
    )


def _bar_hl_ok(bar: Bar) -> bool:
    """Usable for inside-bar math: high/low present and ordered."""
    return bar.high is not None and bar.low is not None and bar.high >= bar.low


def _bar_close_ok(bar: Bar) -> bool:
    return bar.close is not None and bar.close > 0


def _bar_open_ok(bar: Bar) -> bool:
    return bar.open is not None


def _bar_vol_ok(bar: Bar) -> bool:
    return bar.volume is not None and bar.volume > 0


def _range_ratio(bar: Bar) -> float:
    return (bar.high - bar.low) / bar.close  # type: ignore[operator]  # price-ok


def _tail(sessions: list[Bar], n: int, ok) -> list[Bar] | None:
    """The contiguous last ``n`` sessions if all satisfy ``ok``, else None."""
    if n < 1 or len(sessions) < n:
        return None
    tail = sessions[-n:]
    if not all(ok(bar) for bar in tail):
        return None
    return tail


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


# ---------------------------------------------------------------------------
# Public API -- every function is (conn, symbol, as_of) -> deterministic value
# ---------------------------------------------------------------------------

def adr(conn, symbol: str, as_of: str, n: int = ADR_DEFAULT_N) -> float | None:
    """Mean of ``(high - low) / close`` over the last ``n`` sessions, in percent.

    ``None`` when fewer than ``n`` usable sessions exist at or before ``as_of``.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    return _adr_from(_load_sessions(conn, symbol, as_of), n)


def _adr_from(sessions: list[Bar], n: int) -> float | None:
    tail = _tail(sessions, n, _bar_price_ok)
    if tail is None:
        return None
    return 100.0 * _mean([_range_ratio(bar) for bar in tail])


def tightness(conn, symbol: str, as_of: str) -> dict[str, Any]:
    """Range contraction read: ``ratio5v20`` plus NR7/NR4 narrow-range flags."""
    return _tightness_from(_load_sessions(conn, symbol, as_of))


def _tightness_from(sessions: list[Bar]) -> dict[str, Any]:
    ratio5v20: float | None = None
    nr7: bool | None = None
    nr4: bool | None = None

    five = _tail(sessions, TIGHTNESS_SHORT_WINDOW, _bar_price_ok)
    twenty = _tail(sessions, ADR_DEFAULT_N, _bar_price_ok)
    if five is not None and twenty is not None:
        five_mean = _mean([_range_ratio(bar) for bar in five])
        adr20 = _mean([_range_ratio(bar) for bar in twenty])
        ratio5v20 = five_mean / adr20 if adr20 > 0 else None

    seven = _tail(sessions, NR7_WINDOW, _bar_price_ok)
    if seven is not None:
        today_range = _range_ratio(seven[-1])
        prior = [_range_ratio(bar) for bar in seven[:-1]]
        nr7 = today_range < min(prior)

    four = _tail(sessions, NR4_WINDOW, _bar_price_ok)
    if four is not None:
        today_range = _range_ratio(four[-1])
        prior = [_range_ratio(bar) for bar in four[:-1]]
        nr4 = today_range < min(prior)

    return {"ratio5v20": ratio5v20, "nr7": nr7, "nr4": nr4}


def volume_character(conn, symbol: str, as_of: str) -> dict[str, Any]:
    """Volume regime: ``dry_up`` (5d vs 50d), ``surge`` (today vs 20d), flag."""
    return _volume_character_from(_load_sessions(conn, symbol, as_of))


def _volume_character_from(sessions: list[Bar]) -> dict[str, Any]:
    dry_up: float | None = None
    surge: float | None = None
    surge_flag = False

    short = _tail(sessions, VOLUME_DRY_SHORT, _bar_vol_ok)
    long_ = _tail(sessions, VOLUME_DRY_LONG, _bar_vol_ok)
    if short is not None and long_ is not None:
        short_mean = _mean([bar.volume for bar in short])  # type: ignore[arg-type]
        long_mean = _mean([bar.volume for bar in long_])  # type: ignore[arg-type]
        dry_up = short_mean / long_mean if long_mean > 0 else None

    twenty = _tail(sessions, SURGE_WINDOW, _bar_vol_ok)
    if twenty is not None:
        avg20 = _mean([bar.volume for bar in twenty])  # type: ignore[arg-type]
        today_volume = sessions[-1].volume  # type: ignore[union-attr]
        surge = today_volume / avg20 if avg20 > 0 else None
        surge_flag = surge is not None and surge >= SURGE_FLAG_MIN

    return {"dry_up": dry_up, "surge": surge, "surge_flag": surge_flag}


def vcp_proxy(conn, symbol: str, as_of: str) -> dict[str, Any] | None:
    """Volatility-contraction proxy: pullback depths from confirmed swing highs.

    Swing-high rule (also in the module docstring): a session is a swing high
    iff its high is strictly greater than the highs of the ``K`` sessions
    before AND after it within the lookback window (``K = 3``). Pullback depth
    for a swing high = ``(high - lowest low up to the next swing high) / high``
    in percent; the last swing high's depth runs to the window end. Returns
    ``None`` when fewer than ``VCP_MIN_SESSIONS`` sessions exist.
    """
    return _vcp_proxy_from(_load_sessions(conn, symbol, as_of))


def _vcp_proxy_from(sessions: list[Bar]) -> dict[str, Any] | None:
    window = [bar for bar in sessions[-VCP_LOOKBACK:] if _bar_price_ok(bar)]
    if len(window) < VCP_MIN_SESSIONS:
        return None

    pivots: list[int] = []
    last_pivot_start = len(window) - VCP_PIVOT_LOOKBACK
    for i in range(VCP_PIVOT_LOOKBACK, last_pivot_start):
        high_i = window[i].high  # type: ignore[union-attr]  # price-ok window
        left = [window[j].high for j in range(i - VCP_PIVOT_LOOKBACK, i)]  # type: ignore[misc]
        right = [window[j].high for j in range(i + 1, i + 1 + VCP_PIVOT_LOOKBACK)]  # type: ignore[misc]
        if high_i > max(left) and high_i > max(right):
            pivots.append(i)

    depths: list[float] = []
    for k, pivot in enumerate(pivots):
        end = pivots[k + 1] if k + 1 < len(pivots) else len(window) - 1
        low_min = min(window[j].low for j in range(pivot + 1, end + 1))  # type: ignore[misc]
        depths.append((window[pivot].high - low_min) / window[pivot].high * 100.0)  # type: ignore[operator]

    contracting = (
        len(depths) >= 2
        and all(depths[k] < depths[k - 1] for k in range(1, len(depths)))
    )
    return {"depths": depths, "contracting": contracting}


def momentum_burst(
    conn, symbol: str, as_of: str, move_pct_min: float = MOMENTUM_MOVE_PCT_MIN
) -> dict[str, Any]:
    """Momentum read: close-to-close move, volume multiple, burst flag.

    ``fired`` needs ``move_pct >= move_pct_min`` (default X = 3.0) AND
    ``vol_multiple >= 2.0``; missing inputs make it False, never a claim.
    """
    return _momentum_burst_from(_load_sessions(conn, symbol, as_of), move_pct_min)


def _momentum_burst_from(
    sessions: list[Bar], move_pct_min: float
) -> dict[str, Any]:
    move_pct: float | None = None
    vol_multiple: float | None = None

    if (
        len(sessions) >= 2
        and _bar_close_ok(sessions[-1])
        and _bar_close_ok(sessions[-2])
    ):
        prev_close = sessions[-2].close  # type: ignore[union-attr]
        today_close = sessions[-1].close  # type: ignore[union-attr]
        move_pct = (today_close / prev_close - 1.0) * 100.0

    twenty = _tail(sessions, SURGE_WINDOW, _bar_vol_ok)
    if twenty is not None:
        avg20 = _mean([bar.volume for bar in twenty])  # type: ignore[arg-type]
        today_volume = sessions[-1].volume  # type: ignore[union-attr]
        vol_multiple = today_volume / avg20 if avg20 > 0 else None

    fired = (
        move_pct is not None
        and vol_multiple is not None
        and move_pct >= move_pct_min
        and vol_multiple >= MOMENTUM_VOL_MULTIPLE_MIN
    )
    return {"move_pct": move_pct, "vol_multiple": vol_multiple, "fired": fired}


def inside_bars(conn, symbol: str, as_of: str) -> int | None:
    """Consecutive inside-bar count ending at the last session (0..n, None<2)."""
    return _inside_bars_from(_load_sessions(conn, symbol, as_of))


def _inside_bars_from(sessions: list[Bar]) -> int | None:
    if len(sessions) < 2:
        return None
    count = 0
    for j in range(len(sessions) - 1, 0, -1):
        today, prior = sessions[j], sessions[j - 1]
        if not (_bar_hl_ok(today) and _bar_hl_ok(prior)):
            break
        if today.high < prior.high and today.low > prior.low:  # type: ignore[operator]
            count += 1
        else:
            break
    return count


def gap_marker(conn, symbol: str, as_of: str) -> dict[str, Any]:
    """Earnings-STYLE gap shape, price-based only (never earnings-confirmed)."""
    return _gap_marker_from(_load_sessions(conn, symbol, as_of))


def _gap_marker_from(sessions: list[Bar]) -> dict[str, Any]:
    gap_pct: float | None = None
    gap_flag: bool | None = None

    twenty = _tail(sessions, ADR_DEFAULT_N, _bar_price_ok)
    if twenty is not None and _bar_open_ok(sessions[-1]):
        adr_ratio = _mean([_range_ratio(bar) for bar in twenty])
        today, prior = sessions[-1], sessions[-2]
        gap_ratio = (today.open - prior.high) / prior.close  # type: ignore[operator]
        gap_pct = gap_ratio * 100.0
        gap_flag = (
            today.open > prior.high  # type: ignore[operator]
            and gap_ratio >= GAP_ADR_MULTIPLE * adr_ratio
        )

    return {"gap_pct": gap_pct, "gap_flag": gap_flag}


def location(conn, symbol: str, as_of: str) -> dict[str, Any]:
    """Distance from the 52-week high and above/below SMA flags (10/20/50/200)."""
    return _location_from(_load_sessions(conn, symbol, as_of))


def _location_from(sessions: list[Bar]) -> dict[str, Any]:
    pct_from_52w_high: float | None = None
    above = {window: None for window in SMA_WINDOWS}

    year = _tail(sessions, WEEK52_SESSIONS, _bar_price_ok)
    if year is not None:
        high52 = max(bar.high for bar in year)  # type: ignore[arg-type]
        if high52 > 0:
            today_close = year[-1].close  # type: ignore[union-attr]
            pct_from_52w_high = (today_close / high52 - 1.0) * 100.0

    for window in SMA_WINDOWS:
        tail = _tail(sessions, window, _bar_close_ok)
        if tail is not None:
            sma = _mean([bar.close for bar in tail])  # type: ignore[arg-type]
            above[window] = tail[-1].close > sma  # type: ignore[operator]

    return {
        "pct_from_52w_high": pct_from_52w_high,
        "above_sma10": above[10],
        "above_sma20": above[20],
        "above_sma50": above[50],
        "above_sma200": above[200],
    }


def snapshot(conn, symbol: str, as_of: str) -> dict[str, Any]:
    """Combine every metric above into one dict, with context + insufficiency."""
    sessions = _load_sessions(conn, symbol, as_of)
    return {
        "symbol": symbol,
        "as_of": as_of,
        "series": "EQ",
        "as_of_session": sessions[-1].trade_date if sessions else None,
        "session_count": len(sessions),
        "insufficient_history": len(sessions) < SNAPSHOT_MIN_SESSIONS,
        "adr_pct": _adr_from(sessions, ADR_DEFAULT_N),
        "tightness": _tightness_from(sessions),
        "volume_character": _volume_character_from(sessions),
        "vcp_proxy": _vcp_proxy_from(sessions),
        "momentum_burst": _momentum_burst_from(sessions, MOMENTUM_MOVE_PCT_MIN),
        "inside_bars": _inside_bars_from(sessions),
        "gap_marker": _gap_marker_from(sessions),
        "location": _location_from(sessions),
    }