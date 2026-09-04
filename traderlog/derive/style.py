"""derive/style.py -- per-trader style: the numbers behind the TRADERS screen.

## Design premise (why this module exists)
TRADERS ranks traders by derived style -- hold-time distribution, stated-exit
win rate, average R, and stop discipline (stated vs honoured). None of it
existed before W6: the ``trader_style`` table has been empty since schema
creation, and the screen honestly renders "too few" everywhere. This module is
the materialisation: one row per active real trader per computation date,
computed from what the reconciler already stored in ``positions`` /
``position_events`` (real rows only -- ``is_mock = 0``). It is PURE SQL +
Python over existing tables: no LLM calls, $0 cost, nothing invented, nothing
guessed.

Per CANONICAL.md §6 this module is the SOLE writer of ``trader_style``. No
other module may write it, and this module writes nothing else.

## Source selection
Rows are computed for every ACTIVE real trader (``traders.active = 1 AND
traders.is_mock = 0``). A trader with zero positions still gets a row: its
``n_positions`` is 0 and every distribution column is NULL -- the truthful
"nothing to see yet" state, not an absence of the trader.

Positions feed the numbers ONLY when ``positions.is_mock = 0``. Mock rows are
excluded from every count and every denominator -- production is real-data-only
and a seeded demo must never influence a roster ranking.

## Computation rules (the QC surface -- read before changing anything)
Let C(h) = the closed positions of handle h (``status = 'closed'``,
``is_mock = 0``).

  * n_positions       -- total real positions for the handle, any status.
  * median_hold_days  -- median of ``holding_days`` over C(h) where
    ``holding_days IS NOT NULL``; NULL when there are no such positions.
    Populated from one sample on: this is a distribution statistic, not a
    rate, so the 10-sample rate threshold does not apply to it.
  * stated_win_rate   -- wins / stated, where wins = closed positions with a
    STATED positive result (``net_result_pct > 0``) and stated = closed
    positions with a stated ``net_result_pct``. Stated means the denormalised
    ``positions.net_result_pct`` column is NOT NULL -- the reconciler populates
    it ONLY when the trader stated a result or both entry and exit were stated
    (CONTRACTS.md §3). Positions WITHOUT a stated result are excluded from the
    denominator and NEVER counted as losses.
  * avg_result_pct    -- mean of the stated ``net_result_pct`` values (same
    denominator as stated_win_rate).
  * avg_r             -- mean of R = (exit - entry) / (entry - stop) over C(h)
    where entry, stop AND exit prices are all stated (see "Price sources"
    below). A position missing any of the three contributes nothing -- never a
    guess, never a zero. ``entry - stop == 0`` is not computable (division by
    zero) and also contributes nothing.
  * stop_stated_pct   -- (C(h) with a stated stop) / |C(h)|. The share of
    closed positions where a stop price was stated at all.
  * stop_honored_pct  -- honoured / stated-stop-with-exit, where
    stated-stop-with-exit = C(h) with a stated stop AND a stated exit price,
    and honoured = those whose exit price is AT OR ABOVE the final stop (long
    convention; the corpus is long-only). Positions WITHOUT a stated exit are
    excluded from this denominator -- a position the trader never gave an exit
    price for says nothing about honouring the stop.
  * preach_score      -- ALWAYS NULL in W6. It depends on ``edu_links``,
    which is written by derive/preach.py (the W6 practice-vs-preach item) and
    is EMPTY today. NULL = "no measurement exists", never 0%.
  * sector_tilt_json / entry_type_json -- ALWAYS NULL in W6 v1. There is no
    reliable per-position sector field in the schema, and ``post_class``
    ``play_type`` coverage on positions is not yet credible (INS-4, design/
    INSIGHT_SURFACES_PLAN.md), so inventing either would be a guess. The
    traders API reads them null-safely (NULL -> {} on /api/traders/{handle})
    and the UI renders its empty states.

## Thresholds -- below a rate's denominator the row is NULL, never a percentage
design/REDESIGN_SCOUTING_WIRE.md §6 is explicit: a trader's rate requires 10
closed positions, and below that the UI renders "-- too few" FROM A NULL,
never a percentage. Enforced here as: any rate or mean column is NULL unless
ITS OWN denominator is >= RATE_MIN_CLOSED (10):

  * stated_win_rate / avg_result_pct  -- need >= 10 stated results.
  * avg_r                             -- needs >= 10 computable-R positions.
  * stop_stated_pct                   -- needs >= 10 closed positions (its
                                        denominator IS the closed count).
  * stop_honored_pct                  -- needs >= 10 stated-stop-with-exit
                                        positions (its own denominator).

``n_positions`` and ``median_hold_days`` always populate ("n/median/etc. still
populate"). Everything else stays NULL under the threshold. A genuine 0.0 win
rate (10 stated results, none positive) is stored as 0.0 -- a real measured
zero must not be confused with "no data" (a non-NULL 0 is not a NULL).

## Price sources -- state_json is the position
The reconciler serialises the complete position into ``positions.state_json``
("state_json is the position" -- db/schema.sql, CONTRACTS.md §3): ``entries``
(price, date, post_id), ``stop`` {price, post_id, moved_from} -- the FINAL
stop after any trail -- and ``exits`` (price, date, qty_pct, post_id). Those
are the prices used here, in this order:

  * entry price = the FIRST entry's price in state_json.entries.
  * final stop  = state_json.stop.price (the last stated stop, including any
                  moved_from trail -- "final stop" in the rules above).
  * exit price  = the LAST exit WITH a price in state_json.exits (the exit
                  that completed the position; an earlier partial exit is not
                  the closing price).

A price is "stated" only when it is a finite number (int/float, not bool);
anything else -- a missing key, a null, a non-number -- is "not stated".

``position_events`` is a fallback ONLY when ``state_json`` cannot be parsed at
all (missing, malformed, or legacy): then the equivalent event rows are
consulted (first ``entry`` event; last ``sl_set``/``sl_move`` event; last
``exit``/``partial_exit`` event -- each with a price). When state_json parses,
it is the sole source: a piece missing THERE is "not stated" even if an event
row carries a number, because state_json is the reconciler's final weighted
verdict over text and vision, and the event rows are generated from the same
result. This keeps one truth per position.

## Idempotency and history
``trader_style``'s primary key is (handle, as_of) -- schema.sql: "one row per
trader per computation date, so the profile itself has history and drift is
visible". Upserts therefore use ON CONFLICT(handle, as_of) DO UPDATE: a re-run
on the SAME run date refreshes that day's row in place (idempotent -- an
unchanged corpus writes the same values, never duplicates), and a run on a
LATER date appends that day's row, preserving history. (The wave brief asked
for "ON CONFLICT handle"; the schema's natural key is the pair, so the pair is
the conflict target -- same-day re-runs refresh, which is what the brief's
"re-runs refresh" requires.)

Only the handles computed on this run are written. Handles no longer active
are NOT updated and NOT deleted: their last row stays as the last measurement
of record, and drift shows when the computation stops advancing (brief rule:
"inactive handles keep their last row").

A run is one transaction: every row upserts, then pipeline_runs is logged
(stage ``derive.style``) and the transaction commits together; any failure
rolls back to the prior state and a ``fail`` outcome is logged before the
exception propagates (matching the house derive pattern). Re-running never
duplicates.

Public contract (matches the house derive pattern):
    run(conn, run_date) -> dict  # a counts/stats dict (the wave brief asks
                                  # for counts, not an int); always logs
                                  # pipeline_runs; never partially commits
    derive(conn)      -> (rows, stats)  # read-only; safe for dry-run reports
"""
from __future__ import annotations

import json
import math
import statistics
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from traderlog.db import now_iso

STAGE = "derive.style"

# ---------------------------------------------------------------------------
# Tunables -- named + commented so every threshold is auditable, not magic.
# ---------------------------------------------------------------------------

# design/REDESIGN_SCOUTING_WIRE.md §6: a trader's rate needs 10 closed
# positions; below it the UI renders "-- too few" from a NULL. Applied as:
# every rate/mean column is NULL unless its own denominator (documented per
# column in the module docstring "Thresholds") is at least this large.
RATE_MIN_CLOSED = 10

# Event kinds consulted in the position_events fallback path (only when
# state_json does not parse). "sl_set"/"sl_move" carry stated stop prices;
# "exit"/"partial_exit" carry stated exit prices; "entry" is the opening
# event. All other kinds (add, target_*, scratch, commentary) never carry an
# entry/stop/exit price for R purposes here.
_ENTRY_KINDS = ("entry",)
_STOP_KINDS = ("sl_set", "sl_move")
_EXIT_KINDS = ("exit", "partial_exit")


def _is_number(value) -> bool:
    """A stated price: a finite int/float. bools and junk are not prices."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


# ---------------------------------------------------------------------------
# Price extraction -- state_json first, events only when it does not parse.
# ---------------------------------------------------------------------------

def _parse_state_json(raw: str | None) -> dict | None:
    """Parse ``state_json``; None when missing or not a JSON object."""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _prices_from_state(state: dict) -> dict:
    """{entry, stop, exit} prices out of a parsed state_json, each a float or
    None. Entry = first entry with a price; stop = stop.price; exit = the LAST
    exit with a price (the position's closing price)."""
    entry: float | None = None
    for e in state.get("entries") or []:
        if isinstance(e, dict) and _is_number(e.get("price")):
            entry = float(e["price"])
            break
    stop: float | None = None
    s = state.get("stop")
    if isinstance(s, dict) and _is_number(s.get("price")):
        stop = float(s["price"])
    exit_price: float | None = None
    for x in reversed(state.get("exits") or []):
        if isinstance(x, dict) and _is_number(x.get("price")):
            exit_price = float(x["price"])
            break
    return {"entry": entry, "stop": stop, "exit": exit_price}


def _prices_from_events(conn, position_id: str) -> dict:
    """{entry, stop, exit} prices from position_events (fallback path)."""
    rows = conn.execute(
        "SELECT kind, price FROM position_events "
        "WHERE position_id = ? AND is_mock = 0 ORDER BY seq ASC",
        (position_id,),
    ).fetchall()
    entry: float | None = None
    stop: float | None = None
    exit_price: float | None = None
    for r in rows:
        if not _is_number(r["price"]):
            continue
        price = float(r["price"])
        if r["kind"] in _ENTRY_KINDS and entry is None:
            entry = price
        elif r["kind"] in _STOP_KINDS:
            stop = price  # last sl_set/sl_move wins -- the final stated stop
        elif r["kind"] in _EXIT_KINDS:
            exit_price = price  # last exit/partial_exit with a price wins
    return {"entry": entry, "stop": stop, "exit": exit_price}


def _prices(conn, row: dict) -> dict:
    """(entry, stop, exit) prices for one position row. state_json is the
    position; position_events are consulted ONLY when state_json does not
    parse (see module docstring "Price sources")."""
    state = _parse_state_json(row.get("state_json"))
    if state is None:
        return _prices_from_events(conn, row["position_id"])
    return _prices_from_state(state)


# ---------------------------------------------------------------------------
# Derivation core -- read-only. Builds every row to write plus a stats dict
# for logging/reporting, without issuing any write (safe to call repeatedly,
# e.g. for a dry-run report against the production DB).
# ---------------------------------------------------------------------------

def _active_real_handles(conn) -> list[str]:
    return [
        r["handle"]
        for r in conn.execute(
            "SELECT handle FROM traders WHERE active = 1 AND is_mock = 0 "
            "ORDER BY handle"
        )
    ]


def _closed_positions(conn, handle: str) -> list[dict]:
    return [
        dict(r)
        for r in conn.execute(
            "SELECT position_id, status, net_result_pct, holding_days, state_json "
            "FROM positions WHERE handle = ? AND is_mock = 0",
            (handle,),
        )
        if r["status"] == "closed"
    ]


def _aggregate(closed: list[dict], prices_fn) -> dict:
    """Raw aggregates over a handle's closed positions (denominators and
    numerators only -- threshold gating happens in ``_style_row``).

    ``prices_fn`` maps a position row to ``{entry, stop, exit}`` prices (the
    conn-bound ``_prices`` in ``derive()``); it is injectable so the math is
    unit-testable without a DB.
    """
    stated_values: list[float] = []
    wins = 0
    hold_days: list[float] = []
    r_values: list[float] = []
    stop_stated = 0
    honored_denom = 0
    honored = 0
    for p in closed:
        result = p["net_result_pct"]
        if _is_number(result):
            stated_values.append(float(result))
            if result > 0:
                wins += 1
        if _is_number(p["holding_days"]):
            hold_days.append(float(p["holding_days"]))
        prices = prices_fn(p)
        if prices["stop"] is not None:
            stop_stated += 1
        if prices["stop"] is not None and prices["exit"] is not None:
            honored_denom += 1
            if prices["exit"] >= prices["stop"]:
                honored += 1
        if (
            prices["entry"] is not None
            and prices["stop"] is not None
            and prices["exit"] is not None
            and prices["entry"] - prices["stop"] != 0
        ):
            r_values.append(
                (prices["exit"] - prices["entry"]) / (prices["entry"] - prices["stop"])
            )
    return {
        "stated_values": stated_values,
        "stated_results": len(stated_values),
        "wins": wins,
        "hold_days": hold_days,
        "r_values": r_values,
        "stop_stated": stop_stated,
        "honored_denom": honored_denom,
        "honored": honored,
    }


def _style_row(handle: str, n_positions: int, n_closed: int, agg: dict) -> dict:
    """One trader_style row's values (threshold-gated; as_of/ingested_at are
    stamped by ``run()``). Every rate/mean column is NULL unless its own
    denominator is >= RATE_MIN_CLOSED -- never a percentage under the bar."""
    n_stated = agg["stated_results"]
    n_r = len(agg["r_values"])
    row = {
        "handle": handle,
        "n_positions": n_positions,
        "median_hold_days": (
            statistics.median(agg["hold_days"]) if agg["hold_days"] else None
        ),
        "stated_win_rate": (
            (agg["wins"] / n_stated) if n_stated >= RATE_MIN_CLOSED else None
        ),
        "avg_result_pct": (
            (sum(agg["stated_values"]) / n_stated)
            if n_stated >= RATE_MIN_CLOSED
            else None
        ),
        "avg_r": (sum(agg["r_values"]) / n_r) if n_r >= RATE_MIN_CLOSED else None,
        # W6 v1: no reliable sector/source field yet (module docstring).
        # NULL over guess -- the API reads these null-safely.
        "sector_tilt_json": None,
        "entry_type_json": None,
        "stop_stated_pct": (
            (agg["stop_stated"] / n_closed) if n_closed >= RATE_MIN_CLOSED else None
        ),
        "stop_honored_pct": (
            (agg["honored"] / agg["honored_denom"])
            if agg["honored_denom"] >= RATE_MIN_CLOSED
            else None
        ),
        # W6: depends on edu_links (derive/preach.py), which is empty today.
        # NULL = "no measurement exists", never 0% (module docstring).
        "preach_score": None,
        "is_mock": 0,
    }
    return row


def derive(conn) -> tuple[list[dict], dict]:
    """Compute the full trader_style rebuild from positions/position_events.
    Pure read -- issues no writes, so it is safe to call on its own (e.g. for
    a stats-only preview) independent of ``run()``. Rows come back WITHOUT
    as_of/ingested_at; ``run()`` stamps them."""
    handles = _active_real_handles(conn)

    def _prices_for_row(row: dict) -> dict:
        return _prices(conn, row)

    rows: list[dict] = []
    per_handle: dict[str, dict] = {}
    n_positions_total = 0
    n_closed_total = 0

    for handle in handles:
        all_pos = conn.execute(
            "SELECT COUNT(*) AS n FROM positions WHERE handle = ? AND is_mock = 0",
            (handle,),
        ).fetchone()
        n_positions = int(all_pos["n"])
        n_positions_total += n_positions
        closed = _closed_positions(conn, handle)
        n_closed = len(closed)
        n_closed_total += n_closed

        agg = _aggregate(closed, _prices_for_row)
        row = _style_row(handle, n_positions, n_closed, agg)
        rows.append(row)
        per_handle[handle] = {
            "n_positions": n_positions,
            "closed": n_closed,
            "stated_results": agg["stated_results"],
            "wins": agg["wins"],
            "hold_samples": len(agg["hold_days"]),
            "computable_r": len(agg["r_values"]),
            "stop_stated": agg["stop_stated"],
            "honored_denom": agg["honored_denom"],
            "honored": agg["honored"],
            "values": {
                k: row[k]
                for k in (
                    "median_hold_days", "stated_win_rate", "avg_result_pct",
                    "avg_r", "stop_stated_pct", "stop_honored_pct",
                    "preach_score", "sector_tilt_json", "entry_type_json",
                )
            },
        }

    stats: dict = {
        "handles": len(handles),
        "rows": len(rows),
        "positions_total": n_positions_total,
        "closed_total": n_closed_total,
        "threshold": {
            "win_rate": [
                h for h, d in per_handle.items()
                if d["stated_results"] >= RATE_MIN_CLOSED
            ],
            "avg_r": [
                h for h, d in per_handle.items()
                if d["computable_r"] >= RATE_MIN_CLOSED
            ],
            "stop_stated": [
                h for h, d in per_handle.items() if d["closed"] >= RATE_MIN_CLOSED
            ],
            "stop_honored": [
                h for h, d in per_handle.items()
                if d["honored_denom"] >= RATE_MIN_CLOSED
            ],
        },
        "per_handle": per_handle,
    }
    return rows, stats


# ---------------------------------------------------------------------------
# Orchestration -- matches the house derive pattern's run(conn, run_date)
# contract: full transactional rebuild, pipeline_runs logging either way,
# never partially commits. Returns a counts dict (wave brief).
# ---------------------------------------------------------------------------

_INSERT_STYLE_SQL = (
    "INSERT INTO trader_style "
    "(handle, as_of, n_positions, median_hold_days, stated_win_rate, "
    " avg_result_pct, avg_r, sector_tilt_json, entry_type_json, "
    " stop_stated_pct, stop_honored_pct, preach_score, is_mock, ingested_at) "
    "VALUES (:handle, :as_of, :n_positions, :median_hold_days, "
    " :stated_win_rate, :avg_result_pct, :avg_r, :sector_tilt_json, "
    " :entry_type_json, :stop_stated_pct, :stop_honored_pct, :preach_score, "
    " :is_mock, :ingested_at) "
    "ON CONFLICT(handle, as_of) DO UPDATE SET "
    " n_positions=excluded.n_positions, "
    " median_hold_days=excluded.median_hold_days, "
    " stated_win_rate=excluded.stated_win_rate, "
    " avg_result_pct=excluded.avg_result_pct, "
    " avg_r=excluded.avg_r, "
    " sector_tilt_json=excluded.sector_tilt_json, "
    " entry_type_json=excluded.entry_type_json, "
    " stop_stated_pct=excluded.stop_stated_pct, "
    " stop_honored_pct=excluded.stop_honored_pct, "
    " preach_score=excluded.preach_score, "
    " is_mock=excluded.is_mock, "
    " ingested_at=excluded.ingested_at"
)


def _log_run(conn, run_date: str, status: str, rows: int, dur: float, detail: str) -> None:
    conn.execute(
        "INSERT INTO pipeline_runs (stage, run_date, status, rows, duration_ms, detail, ts) "
        "VALUES (?,?,?,?,?,?,?)",
        (STAGE, run_date, status, rows, int(dur * 1000), detail, now_iso()),
    )


def run(conn, run_date: str, _stats_out: dict | None = None) -> dict:
    """Full re-derivation of trader_style. Never raises without first logging
    and rolling back to a clean state.

    Idempotent: re-running with the same ``run_date`` refreshes that day's
    (handle, as_of) rows in place (see module docstring "Idempotency and
    history"); a later ``run_date`` appends that day's row, preserving
    history. Rows are only ever written for handles computed on this run --
    inactive handles keep their last row, never deleted.

    ``run_date`` stamps the pipeline_runs row AND the row's ``as_of``; this
    stage rebuilds from the WHOLE corpus every call and does not filter
    anything by ``run_date`` (matching the reconciler/watchlists full-rebuild
    discipline).

    ``_stats_out``, if given, is populated in place with derive()'s full
    stats dict (per-handle aggregates, threshold crossings) for callers that
    want more than the counts -- see run_style.py.

    Returns the counts/stats dict: ``{handles, rows, positions_total,
    closed_total, threshold, per_handle}`` (the wave brief asks for counts).
    """
    started = time.monotonic()
    try:
        rows, stats = derive(conn)
        if _stats_out is not None:
            _stats_out.update(stats)

        stamped = [
            dict(r, as_of=run_date, ingested_at=now_iso())
            for r in rows
        ]
        if stamped:
            conn.executemany(_INSERT_STYLE_SQL, stamped)

        dur = time.monotonic() - started
        detail = (
            f"handles={len(rows)} positions_total={stats['positions_total']} "
            f"closed_total={stats['closed_total']} "
            f"thresh_win={len(stats['threshold']['win_rate'])} "
            f"thresh_r={len(stats['threshold']['avg_r'])} "
            f"thresh_stop_stated={len(stats['threshold']['stop_stated'])} "
            f"thresh_stop_honored={len(stats['threshold']['stop_honored'])}"
        )
        _log_run(conn, run_date, "ok", len(rows), dur, detail)
        conn.commit()
        return stats
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        _log_run(conn, run_date, "fail", 0, time.monotonic() - started,
                 f"{type(exc).__name__}: {exc}")
        conn.commit()
        raise


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


if __name__ == "__main__":
    from traderlog.db import connect

    _conn = connect()
    _stats: dict = {}
    _n = run(_conn, date.today().isoformat(), _stats_out=_stats)
    print(f"trader_style rows written: {_n['rows']} "
          f"(active real traders: {_n['handles']}; "
          f"positions {_n['positions_total']}, closed {_n['closed_total']})")
    print("per-handle (n / closed / stated / wins / win% / median_hold / "
          "stop_stated% / stop_honored% / avg_r):")
    for handle in sorted(_n["per_handle"]):
        d = _n["per_handle"][handle]
        v = d["values"]
        print(
            f"  {handle:<18} {d['n_positions']:>4} / {d['closed']:>4} / "
            f"{d['stated_results']:>4} / {d['wins']:>4} / "
            f"{_fmt(v['stated_win_rate']):>7} / {_fmt(v['median_hold_days']):>5} / "
            f"{_fmt(v['stop_stated_pct']):>7} / {_fmt(v['stop_honored_pct']):>7} / "
            f"{_fmt(v['avg_r']):>6}"
        )