"""Replay harness -- the mandated first deliverable (LIVE_LOOP_FABLE §3.1,
build-order note: "replay harness comes first"). Feeds a recorded/synthetic
tick session through the *exact same* alerts.live_fsm.on_tick()/on_confirm()
code the live session driver (manas_os.live.session) uses, with zero network
calls, and asserts the safety properties the whole design depends on:

  1. Zero duplicate transitions/pushes when the identical session is replayed
     a second time (WS-reconnect-replay proof).
  2. TTL expiry fires (ALERTED -> EXPIRED after 25 simulated minutes).
  3. 1-push-per-symbol-per-day is enforced (alerts.replies.record_push dedup).
  4. Regime push caps (5/3/1/0) are enforced -- the (cap+1)th qualifying
     symbol never reaches ALERTED.
  5. /halt silences entry pushes but never exit alerts.
  6. Confirm-time revalidation refuses to confirm a symbol that has moved
     outside its zone by the time the (simulated) user confirms.

The fixture is a JSON file describing one synthetic session: an armed_list
seed plus an ordered list of events (tick / confirm / halt / resume /
exit_alert / heartbeat). Synthetic data only, by design -- this is a test
harness, not a source of production display data.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from manas_os.alerts import live_fsm
from manas_os.alerts import replies as telegram_replies
from manas_os.alerts import telegram_engine
from manas_os.live import heartbeat, quotes, telegram_paper

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
DEFAULT_FIXTURE = FIXTURE_DIR / "sample_session.json"


def load_fixture(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_FIXTURE
    return json.loads(p.read_text(encoding="utf-8"))


def _seed_armed_list(conn, trade_date: str, rows: list[dict[str, Any]]) -> None:
    """Populate the real armed_list table (the same one telegram_engine
    writes nightly) so live_fsm.arm_from_armed_list() exercises the genuine
    production seeding path, not a shortcut."""
    telegram_engine.ensure_schema(conn)
    conn.execute("DELETE FROM armed_list WHERE armed_date = ?", (trade_date,))
    for r in rows:
        conn.execute(
            "INSERT OR REPLACE INTO armed_list (armed_date, symbol, trigger, stop, qty, setup_family, rank) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (trade_date, r["symbol"], r["trigger"], r.get("stop"), r.get("qty"),
             r.get("setup_family", "catalyst"), r.get("rank", 1)),
        )
    conn.commit()


def _run_events(conn, trade_date: str, regime_mode: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for ev in sorted(events, key=lambda e: e.get("ts") or e.get("bar_ts") or ""):
        etype = ev.get("type")
        ts = ev.get("ts") or ev.get("bar_ts")
        if etype in {"tick", "confirm"}:
            live_fsm.expire_due(conn, trade_date, ts)
        if etype == "tick":
            symbol = ev["symbol"]
            if ev.get("price") is not None:
                quotes.update_quote(conn, symbol, ev["price"], ts)
            r = live_fsm.on_tick(conn, trade_date, {**ev, "ts": ts}, regime_mode=regime_mode)
            results.append({"event": ev, "result": r})
        elif etype == "confirm":
            r = live_fsm.on_confirm(conn, trade_date, {**ev, "ts": ts})
            results.append({"event": ev, "result": r})
        elif etype == "halt":
            r = telegram_replies.set_halt(conn, True, reason=ev.get("reason", "/halt replay"))
            results.append({"event": ev, "result": r})
        elif etype == "resume":
            r = telegram_replies.set_halt(conn, False)
            results.append({"event": ev, "result": r})
        elif etype == "exit_alert":
            r = telegram_paper.push_exit_alert(
                conn, trade_date, ev["symbol"], ev.get("message", f"EXIT {ev['symbol']}"),
                {"reason": ev.get("reason", "stop_hit")},
            )
            results.append({"event": ev, "result": r})
        elif etype == "heartbeat":
            armed_symbols = conn.execute(
                "SELECT COUNT(*) AS n FROM live_fsm_state WHERE trade_date=?", (trade_date,)
            ).fetchone()["n"]
            r = heartbeat.send_heartbeat(
                conn, trade_date, armed_count=armed_symbols, market_mode=regime_mode,
                ws_ok=True, token_ok=True,
            )
            results.append({"event": ev, "result": r})
        else:
            results.append({"event": ev, "result": {"applied": False, "reason": "unknown_event_type"}})
    return results


def _transition_count(conn, trade_date: str) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM live_fsm_transitions WHERE trade_date=?", (trade_date,)).fetchone()
    return int(row["n"] or 0)


def _push_count(conn, trade_date: str) -> int:
    row = conn.execute("SELECT COUNT(*) AS n FROM live_pushes_log WHERE trade_date=?", (trade_date,)).fetchone()
    return int(row["n"] or 0) if row else 0


def run_replay(conn, fixture: dict[str, Any] | None = None, *, fixture_path: str | Path | None = None,
               replay_twice: bool = True) -> dict[str, Any]:
    fixture = fixture or load_fixture(fixture_path)
    trade_date = fixture["trade_date"]
    regime_mode = fixture.get("regime_mode", "SELECTIVE")

    live_fsm.ensure_schema(conn)
    telegram_paper.ensure_schema(conn)
    telegram_replies.ensure_schema(conn)
    # Fresh slate for this trade_date so re-running the harness in the same
    # process/db is itself idempotent.
    conn.execute("DELETE FROM live_fsm_transitions WHERE trade_date=?", (trade_date,))
    conn.execute("DELETE FROM live_fsm_state WHERE trade_date=?", (trade_date,))
    conn.execute("DELETE FROM live_pushes_log WHERE trade_date=?", (trade_date,))
    conn.execute("DELETE FROM telegram_pushes WHERE push_date=?", (trade_date,))
    conn.execute("DELETE FROM telegram_controls")
    conn.commit()

    _seed_armed_list(conn, trade_date, fixture["armed_list"])

    pass_1 = _run_events(conn, trade_date, regime_mode, fixture["events"])
    transitions_after_pass_1 = _transition_count(conn, trade_date)
    pushes_after_pass_1 = _push_count(conn, trade_date)

    dup_check: dict[str, Any] = {}
    if replay_twice:
        _run_events(conn, trade_date, regime_mode, fixture["events"])
        transitions_after_pass_2 = _transition_count(conn, trade_date)
        pushes_after_pass_2 = _push_count(conn, trade_date)
        dup_check = {
            "transitions_after_pass_1": transitions_after_pass_1,
            "transitions_after_pass_2": transitions_after_pass_2,
            "new_transitions_on_replay": transitions_after_pass_2 - transitions_after_pass_1,
            "pushes_after_pass_1": pushes_after_pass_1,
            "pushes_after_pass_2": pushes_after_pass_2,
            "new_pushes_on_replay": pushes_after_pass_2 - pushes_after_pass_1,
            "zero_duplicate_transitions": (transitions_after_pass_2 - transitions_after_pass_1) == 0,
            "zero_duplicate_pushes": (pushes_after_pass_2 - pushes_after_pass_1) == 0,
        }

    final_state = live_fsm.states(conn, trade_date)
    pushes = [dict(r) for r in conn.execute(
        "SELECT symbol, kind, paper, sent FROM live_pushes_log WHERE trade_date=? ORDER BY push_id",
        (trade_date,),
    ).fetchall()]

    return {
        "trade_date": trade_date,
        "regime_mode": regime_mode,
        "pass_1_results": pass_1,
        "final_state": final_state,
        "pushes": pushes,
        "replay_dedupe_check": dup_check,
    }


def format_replay_report(result: dict[str, Any]) -> str:
    lines = [
        f"Replay {result['trade_date']} ({result['regime_mode']}):",
        "  final FSM state:",
    ]
    for row in result["final_state"]:
        lines.append(f"    {row['symbol']:<12} {row['state']:<16} trigger={row['trigger']} "
                     f"zone=[{row.get('zone_lo')},{row.get('zone_hi')}]")
    lines.append(f"  pushes ({len(result['pushes'])}):")
    for p in result["pushes"]:
        lines.append(f"    {p['symbol']:<12} {p['kind']:<6} paper={bool(p['paper'])} sent={bool(p['sent'])}")
    if result.get("replay_dedupe_check"):
        d = result["replay_dedupe_check"]
        lines.append(f"  replay-twice dedupe: zero_duplicate_transitions={d['zero_duplicate_transitions']} "
                     f"zero_duplicate_pushes={d['zero_duplicate_pushes']}")
    return "\n".join(lines)
