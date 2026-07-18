"""Chart-level price-action autopsy of imported broker round trips.

Read-only with respect to the database: for every closed ``journal_trades``
row with ``source='zerodha_import'`` this loads point-in-time daily bars (up
to, and never past, the entry/exit date being scored) and runs them through
the tool's OWN detectors -- ``engine.eod_detectors``,
``scanner.discovery_metrics``, ``scanner.gates`` -- to build a mechanical
mistake taxonomy. No new technical-analysis rule is invented here; every tag
below is a direct read of an existing LOCKED threshold or detector function,
cited in each tag's comment. Statistical buckets already exist
(``design/reports/BROKER_AUDIT_2026-07-18.md``); this is the missing
chart-level layer -- WAS the entry/exit chart-quality, not just the P&L.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sqlite3
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Sequence

from manas_os.engine import eod_detectors
from manas_os.scanner import discovery_metrics, gates
from manas_os.scanner.candidates import load_symbol_bars
from manas_os.tools.broker_audit import Report, _fmt_money, _fmt_pct

Bar = dict[str, Any]

# --- tag thresholds --------------------------------------------------------
# Every number below is reused from an existing LOCKED constant/detector; none
# is invented for this tool.
EXTENDED_ENTRY_PCT = gates.EXT21_STALE          # 8.0 -- gates.py LOCKED "stale/extended" cut
NO_BASE_TIGHTNESS_PCTILE = 60.0                 # spec: tightness pctile > 60 AND no contraction
IN_BASE_DEPTH_PCT = 15.0                        # spec: correction depth <= 15%
IN_BASE_TIGHTNESS_PCTILE = 40.0                 # spec: tightness pctile <= 40
LATE_IN_MOVE_PCT = 80.0                         # spec: > 80% up from the 65d low
LATE_EXIT_SESSIONS = 3                          # spec: Broken first fired >= 3 sessions before exit
LATE_EXIT_LOOKBACK_CAP = 40                     # walk-back cap; see HONEST CAVEATS in the report
SOLD_WINNER_EXTENSION_PCT = gates.EXT21_STALE   # same 8% "not extended" band, reused at the exit side
RECOVERY_SESSIONS = 10                          # spec: 10 sessions after a PANIC_EXIT
BAR_LIMIT = 300                                 # >=252 (52w) + margin for the 60/65d windows used below


# --- entry-quality read -----------------------------------------------------

def entry_quality(bars: list[Bar], entry_date: str) -> dict[str, Any]:
    """Point-in-time entry read. ``bars`` must already be sliced on-or-before
    ``entry_date`` (candidates.load_symbol_bars) -- this function never looks
    past the last bar it is handed."""
    if not bars or bars[-1].get("date") != entry_date:
        return {"ok": False}
    closes = [b.get("close") for b in bars]
    close = bars[-1].get("close")

    # extension_21: eod_detectors.ema, gates.EXT21_STALE LOCKED cut.
    ema21 = eod_detectors.ema(closes, 21)[-1]
    extension_21 = None if not ema21 else (close / ema21 - 1.0) * 100.0
    extended_entry = bool(extension_21 is not None and extension_21 > EXTENDED_ENTRY_PCT)

    # base context: discovery_metrics.prev_day_tightness_pctile / range_contraction_flag /
    # correction_depth_from_leg_high.
    tightness_pctile = discovery_metrics.prev_day_tightness_pctile(bars)
    contraction = discovery_metrics.range_contraction_flag(bars)
    depth = discovery_metrics.correction_depth_from_leg_high(bars)
    no_base = bool(
        tightness_pctile is not None and tightness_pctile > NO_BASE_TIGHTNESS_PCTILE and not contraction
    )
    in_base = bool(
        depth is not None and depth <= IN_BASE_DEPTH_PCT
        and tightness_pctile is not None and tightness_pctile <= IN_BASE_TIGHTNESS_PCTILE
    )

    # trend template: gates.gate_trend_template, family='momentum' (journal_trades does not
    # record which setup family the trader believed they were in -- see HONEST CAVEATS).
    trend = gates.gate_trend_template(bars, "momentum", None)
    counter_trend = not trend["pass"]
    trend_objections = [o.get("code") for o in (trend.get("evidence") or {}).get("objections", [])]

    # day character (informational only, no tag): entry-day change% and volume vs its own
    # trailing 20d average -- eod_detectors._day_rvol is the exact "today's volume / 20d avg"
    # primitive already used by strong_start_ready/d2_ready; reused rather than re-derived.
    prev_close = bars[-1].get("prev_close")
    if prev_close is None and len(bars) > 1:
        prev_close = bars[-2].get("close")
    change_pct = None
    if prev_close and close is not None:
        change_pct = (close - prev_close) / prev_close * 100.0
    day_rvol = eod_detectors._day_rvol(bars)

    # 65d-low distance: discovery_metrics.pct_up_from_65d_low.
    pct_65 = discovery_metrics.pct_up_from_65d_low(bars)
    late_in_move = bool(pct_65 is not None and pct_65 > LATE_IN_MOVE_PCT)

    tags: list[str] = []
    if extended_entry:
        tags.append("EXTENDED_ENTRY")
    if no_base:
        tags.append("NO_BASE")
    if in_base:
        tags.append("IN_BASE")
    if counter_trend:
        tags.append("COUNTER_TREND")
    if late_in_move:
        tags.append("LATE_IN_MOVE")

    return {
        "ok": True,
        "extension_21": None if extension_21 is None else round(extension_21, 2),
        "extended_entry": extended_entry,
        "tightness_pctile": None if tightness_pctile is None else round(tightness_pctile, 1),
        "range_contraction": bool(contraction),
        "correction_depth_pct": None if depth is None else round(depth, 2),
        "no_base": no_base,
        "in_base": in_base,
        "trend_pass": bool(trend["pass"]),
        "trend_reason": trend.get("reason"),
        "trend_objections": trend_objections,
        "counter_trend": counter_trend,
        "entry_day_change_pct": None if change_pct is None else round(change_pct, 2),
        "day_rvol": None if day_rvol is None else round(day_rvol, 2),
        "pct_up_from_65d_low": None if pct_65 is None else round(pct_65, 2),
        "late_in_move": late_in_move,
        "tags": tags,
    }


# --- exit-quality read -------------------------------------------------------

def _first_broken_gap(bars: list[Bar]) -> int | None:
    """Walk backward from the last bar (assumed already Broken) through prior
    sessions' ``eod_detectors.exit_state`` until the state was not Broken.
    Returns the number of trading sessions the Broken run persisted before the
    last bar (0 = first Broken day IS the last bar). Capped at
    LATE_EXIT_LOOKBACK_CAP sessions for cost/robustness (HONEST CAVEATS)."""
    exit_idx = len(bars) - 1
    first_broken_idx = exit_idx
    idx = exit_idx - 1
    floor = max(1, exit_idx - LATE_EXIT_LOOKBACK_CAP)
    while idx >= floor:
        prior_state = eod_detectors.exit_state(bars[: idx + 1])["state"]
        if prior_state != "Broken":
            break
        first_broken_idx = idx
        idx -= 1
    return exit_idx - first_broken_idx


def exit_quality(bars: list[Bar], exit_date: str, pnl: float | None) -> dict[str, Any]:
    """Point-in-time exit read. ``bars`` must already be sliced on-or-before
    ``exit_date``."""
    if not bars or bars[-1].get("date") != exit_date:
        return {"ok": False}
    state_result = eod_detectors.exit_state(bars)
    state = state_result["state"]
    fired_rules = [r["rule"] for r in state_result.get("fired_rules", [])]

    closes = [b.get("close") for b in bars]
    close = bars[-1].get("close")
    ema21 = eod_detectors.ema(closes, 21)[-1]
    above_ema21 = bool(ema21 is not None and close is not None and close >= ema21)
    extension_at_exit = None if not ema21 else (close / ema21 - 1.0) * 100.0

    is_loss = bool(pnl is not None and pnl < 0)
    is_gain = bool(pnl is not None and pnl > 0)

    # PANIC_EXIT: Intact (nothing fired) + still above 21EMA + closed at a loss.
    panic_exit = bool(state == "Intact" and above_ema21 and is_loss)
    # STRUCTURE_EXIT: Broken/Weakening with >=2 rules firing on the exit day itself.
    structure_exit = bool(state in ("Broken", "Weakening") and len(fired_rules) >= 2)

    # LATE_EXIT: Broken state had already been running for >= LATE_EXIT_SESSIONS
    # sessions before the actual exit day.
    late_exit = False
    first_broken_gap: int | None = None
    if state == "Broken" and len(bars) >= 2:
        first_broken_gap = _first_broken_gap(bars)
        late_exit = bool(first_broken_gap >= LATE_EXIT_SESSIONS)

    # SOLD_WINNER_EARLY: closed at a gain, Intact, and not even extended -- no
    # mechanical reason (per the tool's own exit rules) to have sold.
    sold_winner_early = bool(
        state == "Intact" and is_gain
        and extension_at_exit is not None and extension_at_exit < SOLD_WINNER_EXTENSION_PCT
    )

    tags: list[str] = []
    if panic_exit:
        tags.append("PANIC_EXIT")
    if structure_exit:
        tags.append("STRUCTURE_EXIT")
    if late_exit:
        tags.append("LATE_EXIT")
    if sold_winner_early:
        tags.append("SOLD_WINNER_EARLY")

    return {
        "ok": True,
        "exit_state": state,
        "fired_rules": fired_rules,
        "above_ema21_at_exit": above_ema21,
        "extension_21_at_exit": None if extension_at_exit is None else round(extension_at_exit, 2),
        "panic_exit": panic_exit,
        "structure_exit": structure_exit,
        "late_exit": late_exit,
        "first_broken_gap_sessions": first_broken_gap,
        "sold_winner_early": sold_winner_early,
        "tags": tags,
    }


def price_recovery_after_exit(
    conn: sqlite3.Connection, symbol: str, exit_date: str, exit_close: float | None,
    sessions: int = RECOVERY_SESSIONS,
) -> dict[str, Any]:
    """What the name did in the ``sessions`` trading sessions AFTER the exit
    (deliberately post-exit, retrospective-only -- never fed back into the
    exit tags above)."""
    rows = conn.execute(
        "SELECT trade_date, close FROM daily_prices WHERE symbol=? AND series='EQ' "
        "AND trade_date > ? ORDER BY trade_date ASC LIMIT ?",
        (symbol.upper(), exit_date, sessions),
    ).fetchall()
    if not rows or exit_close in (None, 0):
        return {"n_sessions": len(rows), "last_date": rows[-1][0] if rows else None, "pct_change": None}
    last_close = rows[-1][1]
    pct_change = None if last_close is None else (last_close - exit_close) / exit_close * 100.0
    return {
        "n_sessions": len(rows),
        "last_date": rows[-1][0],
        "pct_change": None if pct_change is None else round(pct_change, 2),
    }


# --- per-trade assembly ------------------------------------------------------

@dataclass
class TradeRow:
    trade_id: int
    symbol: str
    entry_date: str
    entry_price: float | None
    exit_date: str
    exit_price: float | None
    qty: float | None
    pnl: float | None
    return_pct: float | None
    holding_days: int | None
    entry: dict[str, Any] = field(default_factory=dict)
    exit: dict[str, Any] = field(default_factory=dict)
    recovery: dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)
    skip_reason: str | None = None


def load_trades(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT trade_id, symbol, trade_date AS entry_date, entry AS entry_price, "
        "exit_date, exit AS exit_price, qty, broker_realized_pnl AS pnl, "
        "broker_return_pct AS return_pct, broker_holding_days AS holding_days "
        "FROM journal_trades WHERE source='zerodha_import' AND exit_date IS NOT NULL "
        "AND entry IS NOT NULL AND exit IS NOT NULL ORDER BY trade_date, trade_id"
    ).fetchall()


def autopsy_trade(conn: sqlite3.Connection, row: sqlite3.Row) -> TradeRow:
    symbol = row["symbol"]
    entry_bars = load_symbol_bars(conn, symbol, row["entry_date"], limit=BAR_LIMIT)
    exit_bars = load_symbol_bars(conn, symbol, row["exit_date"], limit=BAR_LIMIT)
    entry_q = entry_quality(entry_bars, row["entry_date"])
    exit_q = exit_quality(exit_bars, row["exit_date"], row["pnl"])

    skips = []
    if not entry_q.get("ok"):
        skips.append(f"no point-in-time entry bar for {row['entry_date']}")
    if not exit_q.get("ok"):
        skips.append(f"no point-in-time exit bar for {row['exit_date']}")
    skip_reason = "; ".join(skips) or None

    tags = list(entry_q.get("tags", [])) + list(exit_q.get("tags", []))
    recovery = None
    if "PANIC_EXIT" in tags:
        recovery = price_recovery_after_exit(conn, symbol, row["exit_date"], row["exit_price"])

    return TradeRow(
        trade_id=row["trade_id"], symbol=symbol, entry_date=row["entry_date"],
        entry_price=row["entry_price"], exit_date=row["exit_date"], exit_price=row["exit_price"],
        qty=row["qty"], pnl=row["pnl"], return_pct=row["return_pct"], holding_days=row["holding_days"],
        entry=entry_q, exit=exit_q, recovery=recovery, tags=tags, skip_reason=skip_reason,
    )


def build_autopsy(db_path: str | Path) -> tuple[list[TradeRow], list[str]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        warnings: list[str] = []
        results: list[TradeRow] = []
        for row in load_trades(conn):
            tr = autopsy_trade(conn, row)
            if tr.skip_reason:
                warnings.append(
                    f"{tr.symbol} {tr.entry_date}->{tr.exit_date} (trade_id={tr.trade_id}): {tr.skip_reason}"
                )
            results.append(tr)
        return results, warnings
    finally:
        conn.close()


# --- report rendering ---------------------------------------------------------

def _pnl(row: TradeRow) -> float:
    return row.pnl if row.pnl is not None else 0.0


def _taxonomy_table(rows: Sequence[TradeRow]) -> list[tuple[Any, ...]]:
    by_tag: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        for tag in row.tags:
            by_tag[tag].append(_pnl(row))
    out = []
    for tag in sorted(by_tag):
        pnls = by_tag[tag]
        out.append((tag, len(pnls), _fmt_money(sum(pnls)), _fmt_money(statistics.mean(pnls))))
    return out


def _cohort_stats(rows: Sequence[TradeRow], predicate) -> tuple[int, float | None, float, float | None]:
    group = [row for row in rows if predicate(row)]
    n = len(group)
    if n == 0:
        return 0, None, 0.0, None
    wins = sum(1 for row in group if _pnl(row) > 0)
    total = sum(_pnl(row) for row in group)
    return n, wins / n * 100.0, total, total / n


def _cross_table(report: Report, title: str, rows: Sequence[TradeRow], tag: str) -> None:
    report.heading(f"{tag} x outcome", 3)
    n_yes, win_yes, total_yes, avg_yes = _cohort_stats(rows, lambda r: tag in r.tags)
    n_no, win_no, total_no, avg_no = _cohort_stats(rows, lambda r: tag not in r.tags)
    report.table(
        ("Cohort", "N", "Win rate", "Total P&L", "Avg P&L"),
        (
            (tag, n_yes, _fmt_pct(win_yes), _fmt_money(total_yes), _fmt_money(avg_yes)),
            (f"not {tag}", n_no, _fmt_pct(win_no), _fmt_money(total_no), _fmt_money(avg_no)),
        ),
    )


def _fmt_num(value: Any, suffix: str = "") -> str:
    return "no data" if value is None else f"{value}{suffix}"


def _exemplar_block(report: Report, rank_label: str, row: TradeRow) -> None:
    report.heading(f"{rank_label} -- {row.symbol} (trade_id {row.trade_id})", 4)
    entry_px = "no data" if row.entry_price is None else f"{row.entry_price:.2f}"
    exit_px = "no data" if row.exit_price is None else f"{row.exit_price:.2f}"
    report.text(
        f"- P&L {_fmt_money(row.pnl)} ({_fmt_pct(row.return_pct)}), qty {row.qty}, "
        f"held {row.holding_days if row.holding_days is not None else 'no data'} calendar days"
    )
    report.text(f"- ENTRY {row.entry_date} @ {entry_px}")
    e = row.entry
    if e.get("ok"):
        report.text(
            f"    - extension_21 {_fmt_num(e['extension_21'], '%')} (> {EXTENDED_ENTRY_PCT:.0f}% => EXTENDED_ENTRY) -> "
            f"{'EXTENDED_ENTRY' if e['extended_entry'] else 'not extended'}"
        )
        report.text(
            f"    - tightness pctile {_fmt_num(e['tightness_pctile'])}, range_contraction={e['range_contraction']}, "
            f"correction depth {_fmt_num(e['correction_depth_pct'], '%')} -> "
            f"{'NO_BASE' if e['no_base'] else ('IN_BASE' if e['in_base'] else 'neither')}"
        )
        report.text(
            f"    - trend-template pass={e['trend_pass']}"
            + (f" reason={e['trend_reason']}" if not e['trend_pass'] else "")
            + f" objections={e['trend_objections']} -> {'COUNTER_TREND' if e['counter_trend'] else 'trend ok'}"
        )
        report.text(
            f"    - day change {_fmt_num(e['entry_day_change_pct'], '%')}, rvol {_fmt_num(e['day_rvol'], 'x')}, "
            f"pct up from 65d low {_fmt_num(e['pct_up_from_65d_low'], '%')} -> "
            f"{'LATE_IN_MOVE' if e['late_in_move'] else 'not late'}"
        )
    else:
        report.text("    - no point-in-time entry bar match (skipped)")
    report.text(f"- EXIT {row.exit_date} @ {exit_px}")
    x = row.exit
    if x.get("ok"):
        report.text(f"    - exit_state={x['exit_state']}, fired_rules={x['fired_rules'] or 'none'}")
        fired_exit_tags = [t for t in ("PANIC_EXIT", "STRUCTURE_EXIT", "LATE_EXIT", "SOLD_WINNER_EARLY") if t in row.tags]
        report.text(f"    - exit tags: {fired_exit_tags or 'none'}")
        if x.get("first_broken_gap_sessions") is not None:
            report.text(f"    - Broken persisted {x['first_broken_gap_sessions']} sessions before this exit")
    else:
        report.text("    - no point-in-time exit bar match (skipped)")
    if row.recovery:
        rec = row.recovery
        report.text(
            f"    - 10-session-after-exit read: {rec['n_sessions']} sessions observed, "
            f"pct change {rec['pct_change']}% by {rec['last_date']}"
        )


def render_report(rows: Sequence[TradeRow], warnings: Sequence[str]) -> str:
    report = Report()
    report.text("# Trade Autopsy -- Zerodha Import Round Trips")
    report.text("")
    report.text(
        "Chart-level price-action read of every closed zerodha_import round trip, using the "
        "tool's own detectors (eod_detectors / discovery_metrics / gates) point-in-time at the "
        "entry and exit date. This is the missing chart layer for BROKER_AUDIT_2026-07-18.md's "
        "statistical buckets."
    )
    entered = [row for row in rows if row.entry.get("ok")]
    exited = [row for row in rows if row.exit.get("ok")]
    report.text(
        f"Round trips analyzed: {len(rows)}. Entry point-in-time bar matched: {len(entered)}. "
        f"Exit point-in-time bar matched: {len(exited)}."
    )

    report.heading("TAXONOMY")
    report.table(("Tag", "Count", "Total P&L", "Avg P&L"), _taxonomy_table(rows))

    report.heading("CROSS-ANALYSIS")
    _cross_table(report, "EXTENDED_ENTRY", rows, "EXTENDED_ENTRY")
    _cross_table(report, "IN_BASE", rows, "IN_BASE")

    report.heading("STRUCTURE_EXIT vs PANIC_EXIT", 3)
    n_struct, win_struct, total_struct, avg_struct = _cohort_stats(rows, lambda r: "STRUCTURE_EXIT" in r.tags)
    n_panic, win_panic, total_panic, avg_panic = _cohort_stats(rows, lambda r: "PANIC_EXIT" in r.tags)
    report.table(
        ("Exit tag", "N", "Win rate", "Total P&L", "Avg P&L"),
        (
            ("STRUCTURE_EXIT", n_struct, _fmt_pct(win_struct), _fmt_money(total_struct), _fmt_money(avg_struct)),
            ("PANIC_EXIT", n_panic, _fmt_pct(win_panic), _fmt_money(total_panic), _fmt_money(avg_panic)),
        ),
    )

    report.heading(f"PANIC_EXIT recovery ({RECOVERY_SESSIONS} sessions after exit)", 3)
    panics = [row for row in rows if "PANIC_EXIT" in row.tags]
    recovered = [row.recovery["pct_change"] for row in panics if row.recovery and row.recovery["pct_change"] is not None]
    n_rec = len(recovered)
    median_rec = statistics.median(recovered) if recovered else None
    up_count = sum(1 for v in recovered if v > 0)
    report.text(
        f"PANIC_EXIT trades: {len(panics)}. With a usable {RECOVERY_SESSIONS}-session-after read: {n_rec}. "
        f"Median % change by session {RECOVERY_SESSIONS} (or last available): "
        f"{'no data' if median_rec is None else f'{median_rec:.2f}%'}. "
        f"Recovered (positive) count: {up_count}/{n_rec if n_rec else 'no data'}."
    )

    report.heading("EXEMPLARS")
    closed = [row for row in rows if row.pnl is not None]
    losers = sorted(closed, key=lambda r: r.pnl)[:10]
    winners = sorted(closed, key=lambda r: r.pnl, reverse=True)[:5]
    worst_panics = sorted(panics, key=lambda r: _pnl(r))[:5]

    report.heading("10 biggest losers", 3)
    for idx, row in enumerate(losers, 1):
        _exemplar_block(report, f"Loser #{idx}", row)
    report.heading("5 biggest winners", 3)
    for idx, row in enumerate(winners, 1):
        _exemplar_block(report, f"Winner #{idx}", row)
    report.heading("5 worst PANIC_EXITs", 3)
    if not worst_panics:
        report.text("No PANIC_EXIT trades found.")
    for idx, row in enumerate(worst_panics, 1):
        _exemplar_block(report, f"Worst PANIC_EXIT #{idx}", row)

    report.heading("HONEST CAVEATS")
    report.text(
        "- Point-in-time only: every entry/exit read uses daily_prices up to and including that "
        "exact date; there is no intraday data anywhere in this tool, so time-of-day entries "
        "(order_execution_time is on the raw broker tradebook, not on journal_trades) are not read."
    )
    report.text(
        "- Every tag is a mechanical reproduction of an existing gate/detector threshold "
        "(gates.EXT21_STALE, the spec's own NO_BASE/IN_BASE/LATE_IN_MOVE cutoffs, "
        "eod_detectors.exit_state's fired rules); none of it is a judgment of trader intent."
    )
    report.text(
        "- The trend-template read always calls gate_trend_template with setup_family='momentum' "
        "(journal_trades does not record which setup family the trader believed they were "
        "trading), which is the more permissive family for the early-uptrend objection path -- a "
        "base/pattern read would COUNTER_TREND more names."
    )
    report.text(
        f"- LATE_EXIT's backward walk stops after {LATE_EXIT_LOOKBACK_CAP} trading sessions; a "
        f"Broken run older than that is reported as exactly {LATE_EXIT_LOOKBACK_CAP}, not its true age."
    )
    report.text(
        "- range_contraction_flag returns False (not unknown) when fewer than 65 bars of history "
        "exist; combined with a tightness percentile computed off a thin window, NO_BASE can fire "
        "on genuinely undecidable early-history names rather than a confirmed non-base."
    )
    report.text(
        "- PANIC_EXIT recovery uses daily closes only (no intraday high), and truncates to however "
        "many trading sessions actually exist in daily_prices within the window -- a short window "
        "is reported honestly via n_sessions, not padded."
    )
    if warnings:
        report.heading("Skipped trades (no point-in-time bar match)", 3)
        for warning in warnings:
            report.text(f"- {warning}")
    return report.render()


# --- CLI ------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chart-level price-action autopsy of imported broker trades")
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True, help="Markdown output path; a JSON twin is written alongside it")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rows, warnings = build_autopsy(args.db)
        content = render_report(rows, warnings)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        json_path = out_path.with_suffix(".json")
        json_path.write_text(json.dumps([asdict(row) for row in rows], indent=2, default=str), encoding="utf-8")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {out_path}")
    print(f"wrote {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
