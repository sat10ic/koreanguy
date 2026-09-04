"""Backend Alpha outcome resolver for decision memories."""
from __future__ import annotations

import json
from datetime import datetime
from manas_os.alpha.memory import resolve_outcome, ensure_schema


def resolve_one_decision(conn, memory_id: str, decision_time: str, symbol: str, proposed_path_json: str | None) -> dict | None:
    """Resolve a single decision memory into its path-dependent outcomes.

    Returns the outcome dict to write if final, or None if the decision is still PENDING.
    """
    if not proposed_path_json:
        return {"status": "UNRESOLVABLE", "reason": "missing_plan_levels", "resolved_date": decision_time.split("T")[0]}
    try:
        proposed_path = json.loads(proposed_path_json)
    except Exception:
        return {"status": "UNRESOLVABLE", "reason": "invalid_plan_json", "resolved_date": decision_time.split("T")[0]}

    confirmation = proposed_path.get("confirmation")
    invalidation = proposed_path.get("invalidation")
    time_window = proposed_path.get("time_window", 5)

    decision_date = decision_time.split("T")[0]

    if confirmation is None or invalidation is None:
        return {"status": "UNRESOLVABLE", "reason": "missing_plan_levels", "resolved_date": decision_date}

    try:
        confirmation = float(confirmation)
        invalidation = float(invalidation)
        time_window = int(time_window)
    except Exception:
        return {"status": "UNRESOLVABLE", "reason": "invalid_plan_types", "resolved_date": decision_date}

    if confirmation <= invalidation:
        return {"status": "UNRESOLVABLE", "reason": "invalid_risk_levels", "resolved_date": decision_date}

    # Check if symbol exists in daily_prices
    has_prices = conn.execute("SELECT 1 FROM daily_prices WHERE symbol = ? LIMIT 1", (symbol,)).fetchone()
    if not has_prices:
        return {"status": "UNRESOLVABLE", "reason": "unknown_symbol", "resolved_date": decision_date}

    # Query future bars chronologically
    bars = conn.execute("""
        SELECT trade_date, open, high, low, close 
        FROM daily_prices 
        WHERE symbol = ? AND series = 'EQ' AND trade_date > ? 
        ORDER BY trade_date ASC
    """, (symbol, decision_date)).fetchall()

    if not bars:
        # If no future bars are found and the decision is more than 30 calendar days old,
        # it is unresolvable. Otherwise, it is pending.
        try:
            d_dt = datetime.fromisoformat(decision_date)
            days_old = (datetime.now() - d_dt).days
        except Exception:
            days_old = 0
        if days_old > 30:
            return {"status": "UNRESOLVABLE", "reason": "no_future_prices", "resolved_date": decision_date}
        return None  # PENDING

    # Step 1: Check trigger availability within the validity window (up to time_window sessions)
    triggered = False
    trigger_idx = -1
    entry_fill = 0.0
    entry_slippage = 0.0
    trigger_status = None

    for i in range(min(time_window, len(bars))):
        bar = bars[i]
        o, h, l, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])

        # Check if open gaps below invalidation (stop)
        if o <= invalidation:
            trigger_status = "GAP_OVER_INVALIDATION"
            trigger_idx = i
            break

        # Check if price triggers (high >= confirmation)
        # Note: Checked before low invalidation so same-day trigger-then-stop classifies as a trade fill
        if h >= confirmation:
            triggered = True
            trigger_idx = i
            entry_fill = max(o, confirmation)
            entry_slippage = entry_fill - confirmation
            break

        # Check if price invalidates before triggering
        if l <= invalidation:
            trigger_status = "INVALIDATED"
            trigger_idx = i
            break

    if not triggered and not trigger_status:
        # If we ran out of price data before time_window sessions
        if len(bars) < time_window:
            return None  # PENDING
        else:
            return {
                "status": "NO_TRIGGER",
                "sessions_elapsed": len(bars),
                "resolved_date": bars[time_window - 1]["trade_date"]
            }

    if trigger_status:
        return {
            "status": trigger_status,
            "trigger_date": bars[trigger_idx]["trade_date"],
            "resolved_date": bars[trigger_idx]["trade_date"]
        }

    # Step 2: We triggered! Simulate walk-forward exit up to 20 sessions
    R = confirmation - invalidation

    mfe_r = 0.0
    mae_r = 0.0
    time_to_1r = None
    time_to_2r = None
    time_to_stop = None
    sum_adverse_gaps_r = 0.0

    exit_idx = -1
    exit_price = 0.0
    exit_reason = None

    max_horizon_bars = 20
    trade_bars = bars[trigger_idx : trigger_idx + max_horizon_bars]

    for k in range(len(trade_bars)):
        bar = trade_bars[k]
        o, h, l, c = float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])

        # Check gap-down through invalidation at open
        if o <= invalidation:
            exit_idx = k
            exit_price = o
            exit_reason = "gap_through_stop"
            time_to_stop = k
            mae_r = min(mae_r, (o - entry_fill) / R)
            break

        # Check low <= invalidation during the day
        if l <= invalidation:
            exit_idx = k
            exit_price = invalidation
            exit_reason = "stop"
            time_to_stop = k
            mae_r = min(mae_r, (l - entry_fill) / R)
            mfe_r = max(mfe_r, (h - entry_fill) / R)
            break

        # Update MAE/MFE
        mae_r = min(mae_r, (l - entry_fill) / R)
        mfe_r = max(mfe_r, (h - entry_fill) / R)

        if time_to_1r is None and h >= entry_fill + R:
            time_to_1r = k
        if time_to_2r is None and h >= entry_fill + 2 * R:
            time_to_2r = k

        # Check adverse gaps
        if k == 0:
            if trigger_idx > 0:
                prev_c_ref = float(bars[trigger_idx - 1]["close"])
            else:
                prev_row = conn.execute("""
                    SELECT close FROM daily_prices 
                    WHERE symbol = ? AND series = 'EQ' AND trade_date <= ? 
                    ORDER BY trade_date DESC LIMIT 1
                """, (symbol, decision_date)).fetchone()
                prev_c_ref = float(prev_row["close"]) if prev_row and prev_row["close"] is not None else o
        else:
            prev_c_ref = float(trade_bars[k - 1]["close"])

        if prev_c_ref is not None:
            gap = o - prev_c_ref
            if gap < 0:
                sum_adverse_gaps_r += gap / R

    if not exit_reason:
        # If not stopped, check if we have the full 20 sessions to close the horizon
        if len(trade_bars) < 20:
            return None  # PENDING (still waiting for more bars)
        exit_idx = 19
        exit_price = float(trade_bars[19]["close"])
        exit_reason = "horizon_close"

    # Calculate terminal returns for T+5, T+10, T+20
    def get_horizon_r(H):
        if exit_reason and exit_reason != "horizon_close" and exit_idx < H:
            return (exit_price - entry_fill) / R
        else:
            if len(trade_bars) >= H:
                return (float(trade_bars[H - 1]["close"]) - entry_fill) / R
            return None

    fwd_r_5 = get_horizon_r(5)
    fwd_r_10 = get_horizon_r(10)
    fwd_r_20 = get_horizon_r(20)

    return {
        "status": "RESOLVED",
        "entry_date": trade_bars[0]["trade_date"],
        "entry_fill": round(entry_fill, 2),
        "entry_slippage": round(entry_slippage, 2),
        "exit_date": trade_bars[exit_idx]["trade_date"],
        "exit_price": round(exit_price, 2),
        "exit_reason": exit_reason,
        "mfe_r": round(mfe_r, 2),
        "mae_r": round(mae_r, 2),
        "time_to_1r": time_to_1r,
        "time_to_2r": time_to_2r,
        "time_to_stop": time_to_stop,
        "sum_adverse_gaps_r": round(sum_adverse_gaps_r, 3),
        "fwd_r_5": round(fwd_r_5, 2) if fwd_r_5 is not None else None,
        "fwd_r_10": round(fwd_r_10, 2) if fwd_r_10 is not None else None,
        "fwd_r_20": round(fwd_r_20, 2) if fwd_r_20 is not None else None,
        "resolved_date": trade_bars[exit_idx]["trade_date"]
    }


def resolve_all_outcomes(conn) -> int:
    """Resolve all pending decisions in the database.

    Returns the number of outcomes resolved and committed.
    """
    ensure_schema(conn)

    # Find pending decisions
    pending = conn.execute("""
        SELECT d.memory_id, d.decision_time, d.symbol, d.proposed_path_json
        FROM decision_memories d
        LEFT JOIN decision_memory_outcomes r ON r.memory_id = d.memory_id
        WHERE r.memory_id IS NULL
    """).fetchall()

    resolved_count = 0
    for row in pending:
        outcome = resolve_one_decision(
            conn,
            row["memory_id"],
            row["decision_time"],
            row["symbol"],
            row["proposed_path_json"],
        )
        if outcome is not None:
            available_at = outcome.get("resolved_date") or row["decision_time"].split("T")[0]
            available_at_iso = f"{available_at}T15:31:00+05:30"

            resolve_outcome(
                conn,
                memory_id=row["memory_id"],
                outcome_available_at=available_at_iso,
                outcome=outcome,
            )
            resolved_count += 1

    return resolved_count
