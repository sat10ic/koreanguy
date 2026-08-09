"""manas_os/scanner/scorecard.py — funnel + forward-performance scorecard.

Answers the standing question: how many stocks were screened / shortlisted /
debated / given a pick-or-refuse call on a given scan_date, versus their
ACTUAL forward performance at T+1 / T+3 / T+5 / T+10 sessions. Read-only over
already-persisted tables; this module writes nothing to the DB. Built to feed
`manas scorecard` (see manas_os/cli/__init__.py), whose Markdown output is
meant to be handed to an LLM for a finetuning/gate-tuning review pass.

Tables read (none of them owned or modified by this module):
  universe          -- (symbol, as_of_date): point-in-time tradeable universe.
  discovery_bucket   -- (scan_date, symbol, classification): WAVE K sensitive
                        bucket. classification is 'DISCOVERY' or 'WATCH'
                        (WATCH is the anticipation pre-trigger lane and is
                        NOT unioned into the candidate/refusal cascade --
                        see scanner/candidates.py `_discovery_watch_pool`).
  scan_candidates    -- (scan_date, symbol, setup): gate-passed scan picks
                        (the deterministic refusal cascade's survivors).
  refusals           -- (scan_date, symbol, failed_gate, ...): hard-refused
                        names from the SAME cascade run. Created lazily by
                        scanner/candidates.py's `ensure_refusals_schema` (it
                        is NOT declared in db/schema.sql), so this module
                        guards its presence before querying it.
  agent_verdicts     -- (scan_date, symbol, agent, verdict, tier): one row
                        per model per debated symbol per night. `agent =
                        'chair'` is the two-stage council's final merged
                        verdict (agents/chair.py) -- verdict is 'TAKE' or
                        'SKIP' for chair rows specifically (other agents'
                        rows can carry 'OBSERVED'/'HOLD' too, which is why
                        pick/skip counts filter on agent='chair' rather than
                        counting raw verdict values across all agents).
  position_verdicts  -- (verdict_date, symbol, verdict, exit_state,
                        fired_rules_json, close_at_verdict): one row per open
                        position per day, written by /api/desk/positions
                        (manas_os/api/app.py::_persist_position_verdict) for
                        TODAY's date only, every time a coach verdict
                        (EXIT/HOLD/TRIM/...) is actually served. Created
                        lazily by that same call (NOT declared in
                        db/schema.sql -- same pattern as `refusals` above),
                        so this module guards its presence before querying
                        it. History only starts accumulating from the date
                        this wave shipped; earlier dates honestly have n=0.
  daily_prices       -- (symbol, trade_date, series, close): source of every
                        forward return computed here. series='EQ' only.

Cohorts (per scan_date), each a set of distinct symbols:
  scan_picks    -- scan_candidates
  watch         -- discovery_bucket where classification='WATCH'
  refused       -- refusals
  debated_pick  -- agent_verdicts where agent='chair' and verdict='TAKE'
  debated_skip  -- agent_verdicts where agent='chair' and verdict='SKIP'

Forward return per (scan_date, symbol, horizon): entry = daily_prices.close
where trade_date = scan_date (series='EQ'); exit = the close on the
`horizon`-th EQ session for THAT symbol strictly after scan_date (ROW_NUMBER
over trade_date ASC -- mirrors scanner/outcomes.py's `_horizon_close`
OFFSET pattern, so a symbol's own halts/no-trade gaps don't skew which
session counts as "N sessions out"). A symbol missing an entry close, or
missing a session at that offset (insufficient future history / data-edge
truncation), is simply excluded from that (cohort, horizon)'s sample --
n drops, nothing is imputed or invented.
"""
from __future__ import annotations

import statistics
from datetime import datetime, timezone
from typing import Any

HORIZONS: tuple[int, ...] = (1, 3, 5, 10)
BIG_MOVE_PCT = 5.0
MIN_RELIABLE_N = 10
PRICE_SERIES = "EQ"

# EXIT-VERDICT cohort (position_verdicts): forward return of the SYMBOL at
# T+1/T+3/T+5 from the verdict_date, grouped by the coach verdict actually
# served (EXIT/HOLD/TRIM). T+10 intentionally excluded -- a verdict grades
# the near-term call, not a month-out drift. Other verdict values the coach
# can emit (e.g. imported-holding-only 'MOVE_STOP') are outside this cohort
# set on purpose; they are not EXIT/HOLD/TRIM calls and mixing them in would
# blur the "should I have exited" question this cohort exists to answer.
VERDICT_HORIZONS: tuple[int, ...] = (1, 3, 5)
VERDICT_ORDER = ("EXIT", "HOLD", "TRIM")
VERDICT_LABELS = {
    "EXIT": "Coach verdict -- EXIT",
    "HOLD": "Coach verdict -- HOLD",
    "TRIM": "Coach verdict -- TRIM",
}

COHORT_ORDER = ("scan_picks", "watch", "refused", "debated_pick", "debated_skip")
COHORT_LABELS = {
    "scan_picks": "Scan picks (gate-passed)",
    "watch": "Anticipation WATCH",
    "refused": "Refused (hard gate)",
    "debated_pick": "Debated -- chair TAKE",
    "debated_skip": "Debated -- chair SKIP",
}
_COHORT_QUERIES = {
    "scan_picks": "SELECT DISTINCT symbol FROM scan_candidates WHERE scan_date = ?",
    "watch": (
        "SELECT DISTINCT symbol FROM discovery_bucket "
        "WHERE scan_date = ? AND classification = 'WATCH'"
    ),
    "refused": "SELECT DISTINCT symbol FROM refusals WHERE scan_date = ?",
    "debated_pick": (
        "SELECT DISTINCT symbol FROM agent_verdicts "
        "WHERE scan_date = ? AND agent = 'chair' AND verdict = 'TAKE'"
    ),
    "debated_skip": (
        "SELECT DISTINCT symbol FROM agent_verdicts "
        "WHERE scan_date = ? AND agent = 'chair' AND verdict = 'SKIP'"
    ),
}
# Mechanical "which cohort SHOULD outperform which" pairs for the signals
# section -- (weaker_expected, stronger_expected, label).
_SIGNAL_PAIRS = (
    ("refused", "scan_picks", "gate"),
    ("debated_skip", "debated_pick", "debate"),
    ("watch", "scan_picks", "anticipation-lane"),
    ("scan_picks", "debated_pick", "debate-value-add"),
)


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (name,)
    ).fetchone()
    return row is not None


def _chunks(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def _dates_in_range(conn, start_date: str, end_date: str) -> list[str]:
    """Union of scan_date values with any recorded activity across the four
    cascade tables in [start_date, end_date]. Dates with zero activity in
    every table (e.g. weekends, or gaps where the pipeline didn't run) are
    left out rather than padded in as all-zero funnel rows."""
    tables = ["scan_candidates", "discovery_bucket", "agent_verdicts"]
    if _table_exists(conn, "refusals"):
        tables.append("refusals")
    dates: set[str] = set()
    for t in tables:
        rows = conn.execute(
            f"SELECT DISTINCT scan_date FROM {t} WHERE scan_date BETWEEN ? AND ?",
            (start_date, end_date),
        ).fetchall()
        dates.update(r[0] for r in rows)
    return sorted(dates)


def _count_distinct(conn, sql: str, params: tuple) -> int:
    row = conn.execute(sql, params).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _funnel_for_date(conn, scan_date: str) -> dict[str, Any]:
    universe_n = _count_distinct(
        conn, "SELECT COUNT(DISTINCT symbol) FROM universe WHERE as_of_date = ?", (scan_date,)
    )
    bucket_n = _count_distinct(
        conn, "SELECT COUNT(DISTINCT symbol) FROM discovery_bucket WHERE scan_date = ?", (scan_date,)
    )
    watch_n = _count_distinct(
        conn,
        "SELECT COUNT(DISTINCT symbol) FROM discovery_bucket "
        "WHERE scan_date = ? AND classification = 'WATCH'",
        (scan_date,),
    )
    scan_n = _count_distinct(
        conn, "SELECT COUNT(DISTINCT symbol) FROM scan_candidates WHERE scan_date = ?", (scan_date,)
    )
    refused_n = 0
    if _table_exists(conn, "refusals"):
        refused_n = _count_distinct(
            conn, "SELECT COUNT(DISTINCT symbol) FROM refusals WHERE scan_date = ?", (scan_date,)
        )
    debated_n = _count_distinct(
        conn, "SELECT COUNT(DISTINCT symbol) FROM agent_verdicts WHERE scan_date = ?", (scan_date,)
    )
    pick_n = _count_distinct(
        conn,
        "SELECT COUNT(DISTINCT symbol) FROM agent_verdicts "
        "WHERE scan_date = ? AND agent = 'chair' AND verdict = 'TAKE'",
        (scan_date,),
    )
    skip_n = _count_distinct(
        conn,
        "SELECT COUNT(DISTINCT symbol) FROM agent_verdicts "
        "WHERE scan_date = ? AND agent = 'chair' AND verdict = 'SKIP'",
        (scan_date,),
    )
    return {
        "scan_date": scan_date,
        "universe_n": universe_n,
        "bucket_n": bucket_n,
        "watch_n": watch_n,
        "scan_n": scan_n,
        "refused_n": refused_n,
        "debated_n": debated_n,
        "pick_n": pick_n,
        "skip_n": skip_n,
    }


def _cohort_symbols(conn, scan_date: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for name, sql in _COHORT_QUERIES.items():
        if name == "refused" and not _table_exists(conn, "refusals"):
            out[name] = set()
            continue
        out[name] = {r[0] for r in conn.execute(sql, (scan_date,)).fetchall()}
    return out


def _sessions_after(conn, scan_date: str) -> int:
    """How many distinct EQ trading sessions exist strictly after scan_date,
    anywhere in daily_prices. Used only to flag horizon truncation honestly
    (a data-edge signal, not a per-symbol one)."""
    row = conn.execute(
        "SELECT COUNT(DISTINCT trade_date) FROM daily_prices "
        "WHERE series = ? AND trade_date > ?",
        (PRICE_SERIES, scan_date),
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def _forward_returns(conn, scan_date: str, symbols: set[str]) -> dict[str, dict[int, float]]:
    """symbol -> {horizon: forward_return_pct}. Only horizons with both a
    real entry close (on scan_date) and a real exit close (the horizon-th
    later EQ session for that symbol) are populated -- never imputed."""
    if not symbols:
        return {}
    ordered = sorted(symbols)
    entry: dict[str, float] = {}
    for chunk in _chunks(ordered, 400):
        placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f"SELECT symbol, close FROM daily_prices "
            f"WHERE series = ? AND trade_date = ? AND symbol IN ({placeholders})",
            (PRICE_SERIES, scan_date, *chunk),
        ).fetchall()
        for sym, close in rows:
            if close is not None:
                entry[sym] = float(close)

    max_h = max(HORIZONS)
    future: dict[str, dict[int, float]] = {}
    for chunk in _chunks(ordered, 400):
        placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f"SELECT symbol, rn, close FROM ("
            f"  SELECT symbol, close, "
            f"         ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY trade_date ASC) AS rn "
            f"  FROM daily_prices "
            f"  WHERE series = ? AND trade_date > ? AND symbol IN ({placeholders})"
            f") WHERE rn <= ?",
            (PRICE_SERIES, scan_date, *chunk, max_h),
        ).fetchall()
        for sym, rn, close in rows:
            if close is not None:
                future.setdefault(sym, {})[int(rn)] = float(close)

    out: dict[str, dict[int, float]] = {}
    for sym in ordered:
        e = entry.get(sym)
        if not e:
            continue
        fut = future.get(sym, {})
        per_h = {h: round((fut[h] - e) / e * 100.0, 4) for h in HORIZONS if h in fut}
        if per_h:
            out[sym] = per_h
    return out


def _stats_from_values(vals: list[float]) -> dict[str, Any]:
    n = len(vals)
    if n == 0:
        return {
            "n": 0, "median_pct": None, "mean_pct": None,
            "hit_rate": None, "big_win_rate": None, "big_loss_rate": None,
        }
    return {
        "n": n,
        "median_pct": round(statistics.median(vals), 3),
        "mean_pct": round(statistics.fmean(vals), 3),
        "hit_rate": round(sum(1 for v in vals if v > 0) / n, 4),
        "big_win_rate": round(sum(1 for v in vals if v >= BIG_MOVE_PCT) / n, 4),
        "big_loss_rate": round(sum(1 for v in vals if v <= -BIG_MOVE_PCT) / n, 4),
    }


def _verdict_dates_in_range(conn, start_date: str, end_date: str) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT verdict_date FROM position_verdicts WHERE verdict_date BETWEEN ? AND ?",
        (start_date, end_date),
    ).fetchall()
    return sorted(r[0] for r in rows)


def _verdict_symbols_for_date(conn, verdict_date: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {v: set() for v in VERDICT_ORDER}
    rows = conn.execute(
        "SELECT verdict, symbol FROM position_verdicts WHERE verdict_date = ? AND verdict IN (?, ?, ?)",
        (verdict_date, *VERDICT_ORDER),
    ).fetchall()
    for verdict, symbol in rows:
        out[verdict].add(symbol)
    return out


def _build_verdicts_section(conn, start_date: str, end_date: str) -> dict[str, Any]:
    """EXIT-VERDICT cohort: forward return of the symbol at T+1/T+3/T+5 from
    verdict_date, grouped by the coach verdict actually served that day.
    Mirrors the scan-cascade cohort math above (same _forward_returns /
    _stats_from_values), just keyed on position_verdicts instead of the
    scan-candidate tables. Absent entirely (available=False) when the table
    doesn't exist yet or has no rows in range -- this table only starts
    accumulating from whenever this wave first ran, so older ranges are
    honestly empty, not zero-filled."""
    if not _table_exists(conn, "position_verdicts"):
        return {
            "available": False,
            "reason": "position_verdicts table does not exist yet (no /api/desk/positions call has run since this wave shipped)",
            "order": list(VERDICT_ORDER),
            "labels": dict(VERDICT_LABELS),
            "horizons": list(VERDICT_HORIZONS),
            "per_date": {},
            "cumulative": {v: {h: _stats_from_values([]) for h in VERDICT_HORIZONS} for v in VERDICT_ORDER},
        }

    dates = _verdict_dates_in_range(conn, start_date, end_date)
    per_date: dict[str, dict[int, dict[str, Any]]] = {v: {} for v in VERDICT_ORDER}
    pooled: dict[str, dict[int, list[float]]] = {v: {h: [] for h in VERDICT_HORIZONS} for v in VERDICT_ORDER}

    for d in dates:
        symbols_by_verdict = _verdict_symbols_for_date(conn, d)
        union_symbols: set[str] = set()
        for syms in symbols_by_verdict.values():
            union_symbols |= syms
        fwd = _forward_returns(conn, d, union_symbols)

        for verdict, syms in symbols_by_verdict.items():
            per_h: dict[int, dict[str, Any]] = {}
            for h in VERDICT_HORIZONS:
                vals = [fwd[s][h] for s in syms if s in fwd and h in fwd[s]]
                per_h[h] = _stats_from_values(vals)
                pooled[verdict][h].extend(vals)
            per_date[verdict][d] = per_h

    cumulative = {
        v: {h: _stats_from_values(vals) for h, vals in by_h.items()}
        for v, by_h in pooled.items()
    }
    return {
        "available": bool(dates),
        "reason": None if dates else f"position_verdicts has no rows in [{start_date}, {end_date}]",
        "order": list(VERDICT_ORDER),
        "labels": dict(VERDICT_LABELS),
        "horizons": list(VERDICT_HORIZONS),
        "per_date": per_date,
        "cumulative": cumulative,
    }


def build(conn, start_date: str, end_date: str) -> dict[str, Any]:
    """Build the full scorecard result dict for [start_date, end_date] (inclusive,
    ISO 'YYYY-MM-DD'). Pure read; opens no transaction, writes nothing."""
    dates = _dates_in_range(conn, start_date, end_date)

    date_rows: list[dict[str, Any]] = []
    edge_notes: list[dict[str, Any]] = []
    cohort_per_date: dict[str, dict[str, dict[int, dict[str, Any]]]] = {
        c: {} for c in COHORT_ORDER
    }
    cohort_pooled: dict[str, dict[int, list[float]]] = {
        c: {h: [] for h in HORIZONS} for c in COHORT_ORDER
    }

    for d in dates:
        date_rows.append(_funnel_for_date(conn, d))

        sessions_after = _sessions_after(conn, d)
        truncated_horizons = [h for h in HORIZONS if sessions_after < h]
        if truncated_horizons:
            edge_notes.append({
                "scan_date": d,
                "sessions_after": sessions_after,
                "truncated_horizons": truncated_horizons,
            })

        symbols_by_cohort = _cohort_symbols(conn, d)
        union_symbols: set[str] = set()
        for syms in symbols_by_cohort.values():
            union_symbols |= syms
        fwd = _forward_returns(conn, d, union_symbols)

        for cohort, syms in symbols_by_cohort.items():
            per_h: dict[int, dict[str, Any]] = {}
            for h in HORIZONS:
                vals = [fwd[s][h] for s in syms if s in fwd and h in fwd[s]]
                per_h[h] = _stats_from_values(vals)
                cohort_pooled[cohort][h].extend(vals)
            cohort_per_date[cohort][d] = per_h

    cohort_cumulative: dict[str, dict[int, dict[str, Any]]] = {
        c: {h: _stats_from_values(vals) for h, vals in by_h.items()}
        for c, by_h in cohort_pooled.items()
    }

    verdicts = _build_verdicts_section(conn, start_date, end_date)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "dates": date_rows,
        "cohorts": {
            "order": list(COHORT_ORDER),
            "labels": dict(COHORT_LABELS),
            "per_date": cohort_per_date,
            "cumulative": cohort_cumulative,
        },
        "verdicts": verdicts,
        "horizons": list(HORIZONS),
        "data_edge": {
            "min_reliable_n": MIN_RELIABLE_N,
            "big_move_pct": BIG_MOVE_PCT,
            "truncated_dates": edge_notes,
            "refusals_table_present": _table_exists(conn, "refusals"),
        },
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def _fmt_pct(v: float | None) -> str:
    return "--" if v is None else f"{v:+.2f}%"


def _fmt_rate(v: float | None) -> str:
    return "--" if v is None else f"{v * 100:.1f}%"


def _fmt_cell(v: float | None, n: int) -> str:
    if v is None or n == 0:
        return "--"
    tag = "" if n >= MIN_RELIABLE_N else " (n<10)"
    return f"{v:+.2f}% (n={n}){tag}"


def _funnel_table(dates: list[dict[str, Any]]) -> str:
    if not dates:
        return "_No scan_date activity found in this range across scan_candidates, refusals, discovery_bucket, or agent_verdicts._\n"
    cols = ["scan_date", "universe_n", "bucket_n", "watch_n", "scan_n", "refused_n", "debated_n", "pick_n", "skip_n"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    totals = {c: 0 for c in cols[1:]}
    for row in dates:
        lines.append("| " + " | ".join(str(row[c]) for c in cols) + " |")
        for c in cols[1:]:
            totals[c] += row[c]
    lines.append("| **sum** | " + " | ".join(str(totals[c]) for c in cols[1:]) + " |")
    return "\n".join(lines) + "\n"


def _cumulative_cohort_table(cumulative: dict[int, dict[str, Any]], horizons: list[int]) -> str:
    header = ["horizon", "n", "median %", "mean %", "hit-rate (>0)", "big-win (>=+5%)", "big-loss (<=-5%)"]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for h in horizons:
        s = cumulative[h]
        flag = "" if s["n"] == 0 or s["n"] >= MIN_RELIABLE_N else " *(unreliable, n<10)*"
        lines.append(
            f"| T+{h} | {s['n']}{flag} | {_fmt_pct(s['median_pct'])} | {_fmt_pct(s['mean_pct'])} | "
            f"{_fmt_rate(s['hit_rate'])} | {_fmt_rate(s['big_win_rate'])} | {_fmt_rate(s['big_loss_rate'])} |"
        )
    return "\n".join(lines) + "\n"


def _per_date_cohort_table(per_date: dict[str, dict[int, dict[str, Any]]], horizons: list[int]) -> str:
    if not per_date:
        return "_no dates_\n"
    header = ["scan_date"] + [f"T+{h} median% (n)" for h in horizons]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for d in sorted(per_date):
        row = [d]
        for h in horizons:
            s = per_date[d][h]
            row.append(_fmt_cell(s["median_pct"], s["n"]))
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def _verdicts_section_md(verdicts: dict[str, Any]) -> list[str]:
    out: list[str] = []
    out.append("## Exit-verdict grading (coach verdicts vs. actual forward return)")
    out.append("")
    out.append(
        "Every EXIT/HOLD/TRIM verdict `/api/desk/positions` actually served (persisted "
        "same-day into `position_verdicts`) graded against the SYMBOL's own forward "
        "return -- so a miss (e.g. an EXIT the stock rallied through) shows up as a "
        "number here, not just in memory."
    )
    out.append("")
    if not verdicts["available"]:
        out.append(f"_{verdicts['reason']}_")
        out.append("")
        return out

    horizons = verdicts["horizons"]
    for v in verdicts["order"]:
        out.append(f"### {verdicts['labels'][v]}")
        out.append("")
        out.append(_cumulative_cohort_table(verdicts["cumulative"][v], horizons))
        s = verdicts["cumulative"][v][horizons[0]]
        if s["n"] >= MIN_RELIABLE_N and s["mean_pct"] is not None:
            out.append(
                f"- `{v}` verdicts preceded an average {s['mean_pct']:+.2f}% move at "
                f"T+{horizons[0]} (n={s['n']})."
            )
            out.append("")
    return out


def _signals(cumulative: dict[str, dict[int, dict[str, Any]]], horizons: list[int]) -> list[str]:
    lines: list[str] = []
    for weaker, stronger, label in _SIGNAL_PAIRS:
        for h in horizons:
            a = cumulative[weaker][h]
            b = cumulative[stronger][h]
            if a["n"] < MIN_RELIABLE_N or b["n"] < MIN_RELIABLE_N:
                continue
            if a["median_pct"] is None or b["median_pct"] is None:
                continue
            if a["median_pct"] >= b["median_pct"] or (a["hit_rate"] or 0) > (b["hit_rate"] or 0):
                lines.append(
                    f"- [{label}] `{weaker}` (median {_fmt_pct(a['median_pct'])}, "
                    f"hit-rate {_fmt_rate(a['hit_rate'])}, n={a['n']}) outperformed or matched "
                    f"`{stronger}` (median {_fmt_pct(b['median_pct'])}, hit-rate {_fmt_rate(b['hit_rate'])}, "
                    f"n={b['n']}) at T+{h} -- worth a second look at the {label} logic."
                )
    return lines


def render_md(result: dict[str, Any]) -> str:
    horizons = result["horizons"]
    cohorts = result["cohorts"]
    out: list[str] = []
    out.append(f"# Scorecard: {result['start_date']} .. {result['end_date']}")
    out.append("")
    out.append(f"Generated: {result['generated_at']}")
    out.append("")
    out.append(
        "Funnel + forward-performance report over the deterministic scan cascade "
        "(scan_candidates / refusals / discovery_bucket / agent_verdicts). Forward "
        "returns are close-to-close from `daily_prices`, entry = close on scan_date, "
        "exit = the close of the Nth later EQ session for that symbol."
    )
    out.append("")
    out.append("## Funnel (per scan date)")
    out.append("")
    out.append(_funnel_table(result["dates"]))

    out.append("## Cohort performance -- cumulative (pooled across the full range)")
    out.append("")
    for c in cohorts["order"]:
        out.append(f"### {cohorts['labels'][c]}")
        out.append("")
        out.append(_cumulative_cohort_table(cohorts["cumulative"][c], horizons))

    out.append("## Cohort performance -- per scan date (median % and n)")
    out.append("")
    for c in cohorts["order"]:
        out.append(f"### {cohorts['labels'][c]}")
        out.append("")
        out.append(_per_date_cohort_table(cohorts["per_date"][c], horizons))

    out.extend(_verdicts_section_md(result["verdicts"]))

    out.append("## Signals (mechanical only -- no LLM prose, n>=10 both sides required)")
    out.append("")
    signal_lines = _signals(cohorts["cumulative"], horizons)
    if signal_lines:
        out.extend(signal_lines)
    else:
        out.append("- No cohort pair met the n>=10-both-sides threshold with a notable reversal in this range.")
    out.append("")

    out.append("## Data caveats")
    out.append("")
    edge = result["data_edge"]
    if not edge["refusals_table_present"]:
        out.append("- `refusals` table did not exist in this DB -- refused_n and the refused cohort are 0/empty throughout (not a real zero-refusal day).")
    if edge["truncated_dates"]:
        out.append(f"- Horizon truncation at the data edge (fewer than N future EQ sessions exist yet for that scan_date):")
        for note in edge["truncated_dates"]:
            hz = ", ".join(f"T+{h}" for h in note["truncated_horizons"])
            out.append(f"  - {note['scan_date']}: only {note['sessions_after']} future EQ session(s) available -- {hz} incomplete/unavailable for names lacking that many sessions.")
    else:
        out.append("- No horizon truncation detected: every scan_date in range has enough later EQ sessions in `daily_prices` for all four horizons.")
    out.append(f"- Cohorts/horizons with n<10 in either the cumulative or per-date tables above are marked `(n<10)` / *(unreliable, n<10)* -- treat those cells as directional only, not evidence.")
    out.append("- Forward returns are unmanaged close-to-close (no stop/target simulation) -- this is a raw discovery/gate-quality signal, not a strategy backtest.")
    out.append("")

    return "\n".join(out)
