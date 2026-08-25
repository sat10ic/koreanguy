"""INS-2 tape-after-mention: IST-anchored forward close returns.

Pure derivation with no database I/O. The /api/radar endpoint owns fetching the
symbol's `daily_prices` rows and the anchor post's `ts_ist`; every decision
rule lives here so it can be unit-tested against synthetic series without a
database.

Anchor policy (locked by design/INSIGHT_SURFACES_PLAN.md §INS-2 and the
implementation spec; the IST session boundary is 09:00):

  - The post's Asia/Kolkata (IST) wall clock decides the anchor. `ts_ist` is
    stored in IST; an aware timestamp is converted to IST, a naive one is
    treated as already IST.
  - Strictly BEFORE 09:00 IST on a session whose trade_date equals the post's
    IST date -> the anchor session IS that day. A pre-open post may anchor to
    that session's open (the plan explicitly permits this; the open is the
    first print of the day, so no close-to-close ambiguity exists and no later
    information is used).
  - Everything else (09:00:00 IST or later, or the post's IST date has no
    session in the symbol's series) -> the NEXT available session strictly
    after the post's IST date. Sessions come from the symbol's own
    `daily_prices` rows, so weekends and market holidays fall out naturally;
    nothing is calendar-guessed.
  - The anchor is always an OPEN. Forward CLOSE returns are
    `close[i + k] / open[anchor] - 1` at +1, +5, +10, +20 trading sessions of
    the same series. A horizon with no session (series ended) or a null close
    is null, never zero. The anchor session's own close is never used, so the
    computation cannot be read as a close-to-close statement.
  - No direction, right/wrong, or win/loss label is produced anywhere in this
    module -- only the raw signed returns plus eligible/missing counts. The
    kill condition ("if a symbol lacks price rows, show 'no NSE price history'
    instead of percentages") surfaces as the `tape_state` field.

Row contract (attached to each /api/radar co_attention row):
  anchor_date   str | None      anchor session trade_date (ISO 'YYYY-MM-DD')
  anchor_open   float | None    anchor session open
  ret_1d/5d/10d/20d  float|None decimal forward close returns (0.0421 = +4.21%)
  n_eligible    int             horizons with a computable return (0..4)
  n_missing     int             horizons without one (4 - n_eligible)
  tape_state    str             computed | no_nse_price_history |
                                no_forward_session | missing_timestamp | capped
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Any, Iterable, Mapping
from zoneinfo import ZoneInfo

_KOLKATA = ZoneInfo("Asia/Kolkata")

# The locked IST session boundary: post times strictly before 09:00 IST may use
# that day's open; 09:00:00 IST and later always anchor to the next session.
OPEN_BOUNDARY = time(9, 0)

# Forward close-return horizons, in trading sessions of the symbol's own series.
HORIZONS = (1, 5, 10, 20)

# Per-request cap for the endpoint's batch tape computation. The Radar ranked
# list is naturally small (page windows are bounded), but a pathological
# days=730/min_traders=1 request must not balloon into one giant symbol list;
# rows past the cap are marked `capped` rather than silently omitted.
MAX_TAPE_SYMBOLS = 200

STATE_COMPUTED = "computed"
STATE_NO_NSE_HISTORY = "no_nse_price_history"
STATE_NO_FORWARD_SESSION = "no_forward_session"
STATE_MISSING_TIMESTAMP = "missing_timestamp"
STATE_CAPPED = "capped"

TAPE_FIELDS = (
    "anchor_date",
    "anchor_open",
    "ret_1d",
    "ret_5d",
    "ret_10d",
    "ret_20d",
    "n_eligible",
    "n_missing",
)


@dataclass(frozen=True)
class Tape:
    """One symbol's tape-after-mention computation."""

    anchor_date: str | None
    anchor_open: float | None
    ret_1d: float | None
    ret_5d: float | None
    ret_10d: float | None
    ret_20d: float | None
    n_eligible: int
    n_missing: int
    state: str


def _parse_ist(value: Any) -> datetime | None:
    """Parse a posts.ts_ist value into an aware Asia/Kolkata datetime.

    Naive values are treated as already IST (the schema stores IST everywhere);
    aware values are converted to IST. Absent or malformed values return None,
    which the caller surfaces as the `missing_timestamp` state.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=_KOLKATA)
    return parsed.astimezone(_KOLKATA)


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


def _normalize_sessions(
    sessions: Iterable[Mapping[str, Any]],
) -> list[tuple[date, str, float | None, float | None]]:
    """Normalize daily_prices rows to sorted (date, raw_date, open, close).

    Rows with an unparsable trade_date are skipped (daily_prices rows are keyed
    by 'YYYY-MM-DD' and always parse). Sorting keeps the function deterministic
    regardless of the caller's row order.
    """
    ordered: list[tuple[date, str, float | None, float | None]] = []
    for row in sessions:
        raw_date = row.get("trade_date")
        if not isinstance(raw_date, str):
            continue
        try:
            parsed_date = date.fromisoformat(raw_date)
        except ValueError:
            continue
        ordered.append(
            (
                parsed_date,
                raw_date,
                _as_float_or_none(row.get("open")),
                _as_float_or_none(row.get("close")),
            )
        )
    ordered.sort(key=lambda item: item[0])
    return ordered


def _anchor_index(
    ordered: list[tuple[date, str, float | None, float | None]],
    post_dt: datetime,
) -> int | None:
    """Return the anchor session index, or None when no session can anchor.

    The daily_prices primary key is (symbol, trade_date), so at most one row
    can share the post's IST date.
    """
    post_day = post_dt.date()
    same_day: int | None = None
    for i, (session_date, _raw, _open, _close) in enumerate(ordered):
        if session_date == post_day:
            same_day = i
            break
    if post_dt.time() < OPEN_BOUNDARY and same_day is not None:
        return same_day
    for i, (session_date, _raw, _open, _close) in enumerate(ordered):
        if session_date > post_day:
            return i
    return None


def _forward_returns(
    ordered: list[tuple[date, str, float | None, float | None]],
    anchor_index: int,
    anchor_open: float,
) -> tuple[float | None, float | None, float | None, float | None]:
    """close[i+k] / open[anchor] - 1 for each horizon; None when unavailable."""
    values: list[float | None] = []
    for k in HORIZONS:
        index = anchor_index + k
        if index >= len(ordered):
            values.append(None)
            continue
        close = ordered[index][3]
        values.append((close / anchor_open) - 1.0 if close is not None else None)
    return tuple(values)  # type: ignore[return-value]


def _blank(state: str) -> Tape:
    return Tape(
        anchor_date=None,
        anchor_open=None,
        ret_1d=None,
        ret_5d=None,
        ret_10d=None,
        ret_20d=None,
        n_eligible=0,
        n_missing=len(HORIZONS),
        state=state,
    )


def compute_tape(
    sessions: Iterable[Mapping[str, Any]],
    post_ts_ist: Any,
) -> Tape:
    """Compute one symbol's tape-after-mention from its price sessions.

    ``sessions`` is any iterable of mappings with ``trade_date`` (ISO date),
    ``open`` and ``close`` keys -- exactly the /api/symbol price projection.
    ``post_ts_ist`` is the anchor post's ``posts.ts_ist`` value.
    """
    post_dt = _parse_ist(post_ts_ist)
    if post_dt is None:
        return _blank(STATE_MISSING_TIMESTAMP)

    ordered = _normalize_sessions(sessions)
    if not ordered:
        return _blank(STATE_NO_NSE_HISTORY)

    anchor_index = _anchor_index(ordered, post_dt)
    if anchor_index is None:
        return _blank(STATE_NO_FORWARD_SESSION)

    anchor_date, raw_date, anchor_open, _close = ordered[anchor_index]
    if anchor_open is None or anchor_open == 0:
        ret_1d = ret_5d = ret_10d = ret_20d = None
    else:
        ret_1d, ret_5d, ret_10d, ret_20d = _forward_returns(
            ordered, anchor_index, anchor_open
        )

    returns = (ret_1d, ret_5d, ret_10d, ret_20d)
    eligible = sum(1 for value in returns if value is not None)
    return Tape(
        anchor_date=raw_date,
        anchor_open=anchor_open,
        ret_1d=ret_1d,
        ret_5d=ret_5d,
        ret_10d=ret_10d,
        ret_20d=ret_20d,
        n_eligible=eligible,
        n_missing=len(HORIZONS) - eligible,
        state=STATE_COMPUTED,
    )


def apply_tape(
    rows: list[Mapping[str, Any]],
    *,
    ts_ist_by_post_id: Mapping[str | None, Any],
    sessions_by_symbol: Mapping[str, Iterable[Mapping[str, Any]]],
    max_symbols: int = MAX_TAPE_SYMBOLS,
) -> None:
    """Attach the INS-2 tape fields to ranked Radar rows, in place.

    Each row's anchor post is its first evidence item (the symbol's first
    mention inside the window -- evidence is chronological), idempotent with
    the /api/radar `first_mention_ts` semantics. ``ts_ist_by_post_id`` maps the
    anchor post_id to its posts.ts_ist; ``sessions_by_symbol`` maps each symbol
    to its daily_prices rows. Rows past ``max_symbols`` are marked ``capped``.
    Rows with no evidence get the missing-timestamp state, matching the INS-2
    kill condition: when timestamp alignment is unavailable, percentages are
    omitted rather than invented.
    """
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        if index >= max_symbols:
            _set_tape(row, _blank(STATE_CAPPED))
            continue
        evidence = row.get("evidence") or []
        first = evidence[0] if evidence else None
        post_id = first.get("post_id") if isinstance(first, Mapping) else None
        ts_ist = ts_ist_by_post_id.get(post_id) if post_id is not None else None
        sessions = sessions_by_symbol.get(row.get("symbol"), [])
        _set_tape(row, compute_tape(sessions, ts_ist))


def _set_tape(row: dict[str, Any], tape: Tape) -> None:
    for field in TAPE_FIELDS:
        row[field] = getattr(tape, field)
    row["tape_state"] = tape.state