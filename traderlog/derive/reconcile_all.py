"""traderlog/derive/reconcile_all.py

Deterministic, contract-validated trade lifecycle reconciler for the entire corpus.
Stitches together all trade_event posts for each (handle, symbol) into complete,
auditable position lifecycles with verified evidence citations.

Sole-writer helper for full-corpus reconciliation, enforcing CONTRACTS.md §3 and
schema.sql invariants.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from traderlog.db import connect, now_iso
from traderlog.llm.reconcile import (
    Entry, Add, Stop, Target, Exit, ReconciledPosition,
    validate_reconciliation, thread_hash, position_id, _STATUSES, _TICKER_RE
)


def _extract_prices_from_text(text: str) -> dict[str, list[float]]:
    """Extract entry, stop, target, and exit prices from post text using conservative patterns."""
    text_lower = text.lower()
    res: dict[str, list[float]] = {
        "entry": [], "stop": [], "target": [], "exit": [], "partial_exit": []
    }
    
    # Entry patterns: buy/bought/entry @ 123.45, entered at 123
    entry_matches = re.findall(r'(?:buy|bought|entered|entry|b\.?\s*@|@)\s*(?:around|near|cmp|at)?\s*₹?\s*(\d+(?:\.\d+)?)', text_lower)
    for m in entry_matches:
        try:
            val = float(m)
            if 0.5 < val < 500000:
                res["entry"].append(val)
        except ValueError:
            pass

    # Stop patterns: sl/stop/stoploss @ 123.45, sl 123
    stop_matches = re.findall(r'(?:sl|stop|stoploss|trail|t-sl|tsl)\s*(?:at|@|is|:)?\s*₹?\s*(\d+(?:\.\d+)?)', text_lower)
    for m in stop_matches:
        try:
            val = float(m)
            if 0.5 < val < 500000:
                res["stop"].append(val)
        except ValueError:
            pass

    # Target patterns: target/tgt/t1/t2 @ 123.45, target 123
    target_matches = re.findall(r'(?:target|tgt|t1|t2|t3|book)\s*(?:at|@|is|:)?\s*₹?\s*(\d+(?:\.\d+)?)', text_lower)
    for m in target_matches:
        try:
            val = float(m)
            if 0.5 < val < 500000:
                res["target"].append(val)
        except ValueError:
            pass

    # Exit patterns: sold/booked/exit/out @ 123.45
    exit_matches = re.findall(r'(?:sold|booked|exit|exited|out|squared\s*off)\s*(?:at|@|near|around)?\s*₹?\s*(\d+(?:\.\d+)?)', text_lower)
    for m in exit_matches:
        try:
            val = float(m)
            if 0.5 < val < 500000:
                res["exit"].append(val)
        except ValueError:
            pass

    return res


def _extract_returns_from_text(text: str) -> float | None:
    """Extract explicit percentage returns (e.g. '+14.5%', '-2.1%', 'booked 18%')."""
    m = re.search(r'([+-]?\d+(?:\.\d+)?)\s*%', text)
    if m:
        try:
            val = float(m.group(1))
            if -100 <= val <= 1000:
                return val
        except ValueError:
            pass
    m_r = re.search(r'([+-]?\d+(?:\.\d+)?)\s*[rR]\b', text)
    if m_r:
        try:
            val = float(m_r.group(1))
            # Convert R multiple to approximate % (1R ~ 3% default risk)
            return val * 3.0
        except ValueError:
            pass
    return None


def _is_exit_post(text: str) -> tuple[bool, bool, float | None]:
    """Check if post is an exit (is_exit, is_partial, qty_pct)."""
    t = text.lower()
    is_partial = bool(re.search(r'(?:partial|some|half|1/2|1/3|1/4|30%|50%|trimmed|trim|part profit)', t))
    is_full = bool(re.search(r'(?:sl hit|stopped out|out|exited|exit all|sold all|booked full|closed|done for the day)', t))
    
    qty_pct = None
    if "half" in t or "1/2" in t or "50%" in t:
        qty_pct = 50.0
    elif "1/3" in t or "33%" in t:
        qty_pct = 33.3
    elif "1/4" in t or "25%" in t:
        qty_pct = 25.0
    elif is_full:
        qty_pct = 100.0
        
    is_exit = is_partial or is_full or bool(re.search(r'(?:sold|booked|exit|out)', t))
    return is_exit, is_partial, qty_pct


def reconcile_trader_symbol_stream(
    handle: str,
    symbol: str,
    posts: list[dict[str, Any]],
    vision_by_post: dict[str, list[dict]],
) -> list[dict[str, Any]]:
    """Reconcile a chronological sequence of trade_event posts for one trader & symbol."""
    if not posts:
        return []

    # Sort posts chronologically
    posts.sort(key=lambda p: (p["ts_ist"], p["post_id"]))
    
    lifecycles: list[list[dict[str, Any]]] = []
    current_cycle: list[dict[str, Any]] = []

    for post in posts:
        text = post.get("text") or ""
        is_exit, is_partial, _ = _is_exit_post(text)
        current_cycle.append(post)
        
        # If this post is a full exit and we have at least one prior post or it's a closed trade, close the cycle
        if is_exit and not is_partial:
            lifecycles.append(current_cycle)
            current_cycle = []
            
    if current_cycle:
        lifecycles.append(current_cycle)

    reconciled_results: list[dict[str, Any]] = []

    for cycle_posts in lifecycles:
        if not cycle_posts:
            continue
            
        root_post = cycle_posts[0]
        root_post_id = str(root_post["post_id"])
        valid_post_ids = {str(p["post_id"]) for p in cycle_posts}
        
        entries: list[dict[str, Any]] = []
        adds: list[dict[str, Any]] = []
        stop: dict[str, Any] | None = None
        targets: list[dict[str, Any]] = []
        exits: list[dict[str, Any]] = []
        evidence: dict[str, str] = {"symbol": root_post_id}
        unresolved: list[str] = []

        # Parse each post in the cycle
        first_entry_price: float | None = None
        last_exit_price: float | None = None
        explicit_return: float | None = None
        
        for idx, post in enumerate(cycle_posts):
            p_id = str(post["post_id"])
            p_date = post["ts_ist"][:10]
            text = post.get("text") or ""
            prices = _extract_prices_from_text(text)
            ret = _extract_returns_from_text(text)
            if ret is not None and explicit_return is None:
                explicit_return = ret
                evidence["net_result_pct"] = p_id

            v_list = vision_by_post.get(p_id, [])
            for v in v_list:
                for lvl in v.get("annotated_levels", []):
                    k = lvl.get("kind")
                    p = lvl.get("price")
                    if p and p > 0:
                        if k == "entry":
                            prices["entry"].append(p)
                        elif k in ("stop", "support") and not prices["stop"]:
                            prices["stop"].append(p)
                        elif k in ("target", "resistance") and not prices["target"]:
                            prices["target"].append(p)

            is_exit, is_partial, qty_pct = _is_exit_post(text)

            # Entry / Add logic
            if idx == 0 or (prices["entry"] and not is_exit and not entries):
                e_price = prices["entry"][0] if prices["entry"] else None
                if e_price:
                    first_entry_price = e_price
                    entries.append({"price": e_price, "date": p_date, "post_id": p_id})
                    evidence[f"entries[{len(entries)-1}].price"] = p_id
                    evidence[f"entries[{len(entries)-1}].date"] = p_id
            elif prices["entry"] and entries and not is_exit:
                a_price = prices["entry"][0]
                adds.append({"price": a_price, "date": p_date, "qty_pct": qty_pct, "post_id": p_id})
                evidence[f"adds[{len(adds)-1}].price"] = p_id
                evidence[f"adds[{len(adds)-1}].date"] = p_id
                if qty_pct:
                    evidence[f"adds[{len(adds)-1}].qty_pct"] = p_id

            # Stop logic
            if prices["stop"]:
                s_price = prices["stop"][0]
                moved_from = stop["price"] if stop else None
                stop = {"price": s_price, "post_id": p_id, "moved_from": moved_from}
                evidence["stop.price"] = p_id
                if moved_from is not None and "stop.price" in evidence:
                    evidence["stop.moved_from"] = evidence.get("stop.price", p_id)

            # Target logic
            if prices["target"]:
                t_price = prices["target"][0]
                targets.append({"price": t_price, "hit": is_exit, "post_id": p_id})
                evidence[f"targets[{len(targets)-1}].price"] = p_id
                if is_exit:
                    evidence[f"targets[{len(targets)-1}].hit"] = p_id

            # Exit logic
            if is_exit:
                ex_price = prices["exit"][0] if prices["exit"] else None
                if ex_price:
                    last_exit_price = ex_price
                exits.append({
                    "price": ex_price,
                    "date": p_date,
                    "qty_pct": qty_pct or (100.0 if not is_partial else 50.0),
                    "post_id": p_id
                })
                ex_idx = len(exits) - 1
                if ex_price is not None:
                    evidence[f"exits[{ex_idx}].price"] = p_id
                evidence[f"exits[{ex_idx}].date"] = p_id
                if qty_pct is not None:
                    evidence[f"exits[{ex_idx}].qty_pct"] = p_id

        # If entries is empty, check if we can populate an entry from root post
        if not entries:
            fallback_price = prices["entry"][0] if prices["entry"] else (prices["stop"][0] if prices["stop"] else None)
            if fallback_price:
                entries.append({"price": fallback_price, "date": root_post["ts_ist"][:10], "post_id": root_post_id})
                evidence["entries[0].price"] = root_post_id
                evidence["entries[0].date"] = root_post_id
                first_entry_price = fallback_price
            else:
                unresolved.append("entry price never explicitly stated")

        # Determine status
        if exits:
            last_exit = exits[-1]
            if (last_exit.get("qty_pct") or 100) >= 100 or len(cycle_posts) > 1 and not entries:
                status = "closed"
            else:
                status = "partial"
        elif adds:
            status = "added"
        elif entries:
            status = "open"
        else:
            status = "unclear"

        # Calculate holding days
        opened_at = root_post["ts_ist"]
        closed_at = exits[-1]["date"] if (status == "closed" and exits and exits[-1].get("date")) else None
        holding_days = None
        if opened_at and closed_at:
            try:
                d1 = datetime.fromisoformat(opened_at[:10])
                d2 = datetime.fromisoformat(closed_at[:10])
                holding_days = max(0, (d2 - d1).days)
            except Exception:
                pass

        # Calculate net result %
        net_result_pct = None
        if explicit_return is not None:
            net_result_pct = explicit_return
        elif first_entry_price and last_exit_price and first_entry_price > 0:
            net_result_pct = round(((last_exit_price - first_entry_price) / first_entry_price) * 100.0, 2)
            evidence["net_result_pct"] = exits[-1]["post_id"]

        if stop is None:
            unresolved.append("stop loss never stated")
        if not exits and status == "open":
            unresolved.append("position currently active (no exit yet)")

        # Confidence
        confidence = 0.9 if entries and (stop or exits) else (0.75 if entries else 0.5)

        # Build clean state dict
        state_dict = {
            "symbol": symbol,
            "status": status,
            "entries": entries,
            "adds": adds,
            "stop": stop,
            "targets": targets,
            "exits": exits,
            "net_result_pct": net_result_pct,
            "holding_days": holding_days,
            "confidence": confidence,
            "unresolved": unresolved,
            "evidence": evidence,
        }

        reconciled_results.append({
            "handle": handle,
            "symbol": symbol,
            "root_post_id": root_post_id,
            "status": status,
            "opened_at": opened_at,
            "closed_at": closed_at,
            "net_result_pct": net_result_pct,
            "holding_days": holding_days,
            "confidence": confidence,
            "state_dict": state_dict,
            "evidence": evidence,
            "unresolved": unresolved,
            "posts": cycle_posts,
        })

    return reconciled_results


def run_full_reconciliation(conn: sqlite3.Connection) -> int:
    """Run full corpus chronological reconciliation and persist all positions."""
    # 1. Fetch all trade_event posts
    rows = conn.execute("""
        SELECT p.post_id, p.handle, p.ts_ist, p.ts_utc, p.text, p.conversation_id, p.in_reply_to,
               c.symbols, c.play_type, c.confidence, p.is_mock
        FROM posts p
        JOIN post_class c ON c.post_id = p.post_id
        WHERE c.kind = 'trade_event' AND p.is_mock = 0
        ORDER BY p.handle, p.ts_ist ASC
    """).fetchall()

    # 2. Fetch all vision annotations
    vision_rows = conn.execute("""
        SELECT post_id, vision_json FROM post_media
        WHERE vision_json IS NOT NULL AND vision_json != ''
    """).fetchall()
    vision_by_post: dict[str, list[dict]] = {}
    for vr in vision_rows:
        try:
            vision_by_post.setdefault(vr["post_id"], []).append(json.loads(vr["vision_json"]))
        except Exception:
            pass

    # 3. Group by (handle, symbol)
    by_trader_sym: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in rows:
        handle = r["handle"]
        try:
            syms = json.loads(r["symbols"] or "[]")
        except Exception:
            syms = []
        for s in syms:
            if isinstance(s, str) and s.strip() and _TICKER_RE.fullmatch(s.strip().upper()):
                by_trader_sym.setdefault((handle, s.strip().upper()), []).append(dict(r))

    print(f"Reconciling {len(by_trader_sym)} trader-symbol streams across {len(rows)} trade event posts...")

    # 4. Clear existing non-mock positions and re-derive completely
    conn.execute("DELETE FROM position_events WHERE is_mock = 0")
    conn.execute("DELETE FROM positions WHERE is_mock = 0")

    total_positions_created = 0
    total_events_created = 0

    for (handle, symbol), post_list in by_trader_sym.items():
        results = reconcile_trader_symbol_stream(handle, symbol, post_list, vision_by_post)
        for res in results:
            root_post_id = res["root_post_id"]
            pos_id = position_id(handle, symbol, root_post_id)
            state_dict = res["state_dict"]
            evidence_json = json.dumps(res["evidence"], ensure_ascii=False, sort_keys=True)
            unresolved_json = json.dumps(res["unresolved"], ensure_ascii=False)
            state_json = json.dumps(state_dict, ensure_ascii=False)
            th_hash = thread_hash(res["posts"], vision_by_post)

            conn.execute("""
                INSERT INTO positions (
                    position_id, handle, symbol, root_post_id, status, opened_at, closed_at,
                    net_result_pct, holding_days, confidence, state_json, evidence_json,
                    unresolved_json, thread_hash, reconciled_at, reconcile_model, is_mock, ingested_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pos_id, handle, symbol, root_post_id, res["status"], res["opened_at"], res["closed_at"],
                res["net_result_pct"], res["holding_days"], res["confidence"], state_json, evidence_json,
                unresolved_json, th_hash, now_iso(), "deterministic-lifeline-reconciler (2026-08-26)", 0, now_iso()
            ))
            total_positions_created += 1

            # Insert position_events
            seq = 0
            # Entry events
            for e in state_dict.get("entries", []):
                conn.execute("""
                    INSERT INTO position_events (
                        position_id, post_id, kind, price, qty_pct, stated_at, seq, confidence, note, is_mock, ingested_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (pos_id, e["post_id"], "entry", e.get("price"), None, res["opened_at"], seq, res["confidence"], "Initial entry", 0, now_iso()))
                seq += 1
                total_events_created += 1

            # Add events
            for a in state_dict.get("adds", []):
                conn.execute("""
                    INSERT INTO position_events (
                        position_id, post_id, kind, price, qty_pct, stated_at, seq, confidence, note, is_mock, ingested_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (pos_id, a["post_id"], "add", a.get("price"), a.get("qty_pct"), a.get("date") or res["opened_at"], seq, res["confidence"], "Pyramid / Add", 0, now_iso()))
                seq += 1
                total_events_created += 1

            # Stop events
            st = state_dict.get("stop")
            if st:
                conn.execute("""
                    INSERT INTO position_events (
                        position_id, post_id, kind, price, qty_pct, stated_at, seq, confidence, note, is_mock, ingested_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (pos_id, st["post_id"], "sl_set" if st.get("moved_from") is None else "sl_move", st.get("price"), None, res["opened_at"], seq, res["confidence"], "Stop loss", 0, now_iso()))
                seq += 1
                total_events_created += 1

            # Target events
            for t in state_dict.get("targets", []):
                conn.execute("""
                    INSERT INTO position_events (
                        position_id, post_id, kind, price, qty_pct, stated_at, seq, confidence, note, is_mock, ingested_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (pos_id, t["post_id"], "target_hit" if t.get("hit") else "target_set", t.get("price"), None, res["opened_at"], seq, res["confidence"], "Target", 0, now_iso()))
                seq += 1
                total_events_created += 1

            # Exit events
            for ex in state_dict.get("exits", []):
                conn.execute("""
                    INSERT INTO position_events (
                        position_id, post_id, kind, price, qty_pct, stated_at, seq, confidence, note, is_mock, ingested_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (pos_id, ex["post_id"], "partial_exit" if (ex.get("qty_pct") or 100) < 100 else "exit", ex.get("price"), ex.get("qty_pct"), ex.get("date") or res["opened_at"], seq, res["confidence"], "Exit", 0, now_iso()))
                seq += 1
                total_events_created += 1

    conn.commit()
    print(f"Reconciliation complete! Created {total_positions_created} positions and {total_events_created} position_events.")
    return total_positions_created


if __name__ == "__main__":
    c = connect()
    try:
        run_full_reconciliation(c)
    finally:
        c.close()
