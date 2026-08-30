"""Candidate store (N4 / P7.1): freeze every detector decision at as_of.

Stores VALID, INVALID, and INSUFFICIENT_DATA — a winners-only dataset is a
research defect. Outcomes are attached later from a future slice the
leakage suite owns; they are not computed at freeze time.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, Optional, Sequence

from unidesk.contracts.base import ContractError
from unidesk.contracts.research import ResearchEvent
from unidesk.momentum.data.corp_actions import confirmed_actions_content_hash
from unidesk.momentum.detectors.momentum_burst import Detection
from unidesk.momentum.scan import ScanResult, SymbolScan
from unidesk.research.costs import COSTS_VERSION, net_return_bps, round_trip_cost
from unidesk.research.labels import (
    OUTCOME_LABELS_VERSION, assert_future_only, breakout_hold, long_outcome,
)
from unidesk.research.walkforward import stop_aware_return_bps

SCHEMA_VERSION = "research-event-v1"


def _jsonable(value):
    if isinstance(value, Detection):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        try:
            return value.value
        except Exception:
            return str(value)
    return value


def _snapshot(scan: SymbolScan, *, ca_table_hash: str = "") -> dict:
    detectors = {
        name: {"detection": _jsonable(det), "failures": list(failures)}
        for name, (det, failures) in scan.detectors.items()
    }
    return {
        "close": scan.close,
        "sessions": scan.sessions,
        "ema21": scan.ema21,
        "ema50": scan.ema50,
        "trend": scan.trend.value if scan.trend is not None else None,
        "adr_pct": scan.adr_pct,
        "atr_pct": scan.atr_pct,
        "rvol": scan.rvol,
        "delivery_ratio": scan.delivery_ratio,
        "rs_rank": scan.rs_rank,
        "contraction": scan.contraction,
        "setup_inputs": dict(scan.setup_inputs or {}),
        "detectors": detectors,
        # Directive-1c: the adjustment basis this snapshot's features were
        # computed under -- carried forward so attach_outcomes (directive-1d)
        # can refuse to label against a future series computed under a
        # DIFFERENT basis (e.g. a CA table that changed between scan time
        # and outcome-attach time).
        "adjusted": bool(scan.adjusted),
        "ca_table_hash": ca_table_hash,
    }


def config_hash_for(scan: ScanResult, *, confirmed_actions_path: Optional[Path] = None) -> str:
    """Detector names PLUS the adjustment basis: the confirmed-actions
    table's CONTENT hash and the cost-assumptions version. Two scans that
    ran against different confirmed-actions content, or under a different
    cost model, must not collapse to the same config hash (directive-1c) --
    previously only detector names were hashed, so a CA table edit was
    invisible to config_hash_for."""
    payload = {
        "schema": SCHEMA_VERSION,
        "detector_names": sorted({
            name for s in scan.symbols for name in s.detectors
        }),
        "ca_table_hash": confirmed_actions_content_hash(confirmed_actions_path),
        "costs_version": COSTS_VERSION,
    }
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def freeze_scan(scan: ScanResult, *, config_hash: Optional[str] = None,
                confirmed_actions_path: Optional[Path] = None) -> list[ResearchEvent]:
    """One ResearchEvent per symbol. Failed and insufficient detections stay."""
    cfg = config_hash or config_hash_for(scan, confirmed_actions_path=confirmed_actions_path)
    ca_hash = confirmed_actions_content_hash(confirmed_actions_path)
    session = scan.last_session or scan.as_of.date().isoformat()
    as_of = scan.as_of
    events = []
    for row in scan.symbols:
        snap = _snapshot(row, ca_table_hash=ca_hash)
        # Keep events even when every detector is INVALID — that is the
        # negative class. Drop only symbols that ran no detectors at all.
        if not row.detectors:
            continue
        event_id = f"{row.symbol}:{session}"
        events.append(ResearchEvent(
            event_id=event_id,
            candidate_id=event_id,
            symbol=row.symbol,
            timestamp=as_of if isinstance(as_of, datetime) else scan.as_of,
            snapshot=snap,
            config_hash=cfg,
            research_schema_version=SCHEMA_VERSION,
            outcome_labels={},
        ))
    return events


def freeze_includes_negatives(events: list[ResearchEvent]) -> bool:
    """True if at least one frozen event has no VALID detector."""
    for ev in events:
        dets = (ev.snapshot or {}).get("detectors") or {}
        if dets and not any(v.get("detection") == Detection.VALID.value for v in dets.values()):
            return True
    return False


def _event_session(event: ResearchEvent) -> date:
    if ":" in event.event_id:
        return date.fromisoformat(event.event_id.rsplit(":", 1)[-1])
    return event.timestamp.date()


def future_after(
    sessions: Sequence[date],
    values: Sequence,
    decision_session: date,
) -> list:
    """Bars strictly after the decision session. The decision bar is not future."""
    if len(sessions) != len(values):
        raise ContractError("sessions and values must have equal length")
    out = []
    for session, value in zip(sessions, values):
        if session > decision_session:
            out.append(value)
    return out


def attach_outcomes(
    events: Sequence[ResearchEvent],
    future: Mapping[str, Mapping],
    *,
    horizon: int = 10,
    stop_atr_mult: float = 1.0,
    unconfirmed_ca_sessions: Optional[Mapping[str, Sequence[date]]] = None,
) -> list[ResearchEvent]:
    """Attach P7.2 labels from a caller-supplied future slice.

    ``future[symbol]`` must contain chronological ``sessions``, ``opens``,
    ``highs``, ``lows``, ``closes``, and MAY carry ``adjusted`` (bool) and
    ``ca_table_hash`` (str) describing the adjustment basis those future
    bars were computed under. Only sessions *after* the event date are used
    (next-bar fill). Missing ATR or empty future → UNRESOLVED, never a
    zeroed outcome.

    Directive-1d (adjustment-basis guard): if the future series' basis does
    not match the basis the snapshot's features were computed under
    (``event.snapshot["adjusted"]`` / ``["ca_table_hash"]``, set by
    ``freeze_scan``/``_snapshot``), the event is refused a real outcome and
    lands as ``UNRESOLVED`` / ``reason="adjustment_basis_mismatch"`` --
    following the same UNRESOLVED convention as the other guards below
    (never a fabricated MAE/MFE/R-multiple computed across a basis change,
    e.g. raw future bars scored against split-adjusted snapshot features).
    A basis is considered unstated (both sides default False/"") when the
    caller supplies neither key -- this keeps pre-existing callers that
    never set ``adjusted``/``ca_table_hash`` on either side working exactly
    as before.

    Directive-1e (unconfirmed corporate-action guard): ``unconfirmed_ca_sessions``
    (symbol -> gap sessions, from
    ``momentum.data.splits.unconfirmed_candidate_sessions``) is the "194
    unconfirmed open-gap candidates" backlog. If ANY session actually used
    to compute this event's outcome falls on one of those unconfirmed gap
    sessions, the event is refused a real outcome and lands as
    ``UNRESOLVED`` / ``reason="unconfirmed_corporate_action"`` -- never a
    fabricated MAE/MFE/R-multiple/stop-hit computed across an un-ratioed
    split. Omitting this parameter (None / empty) is a no-op -- it does not
    invent a backlog on its own.
    """
    if horizon < 1:
        raise ContractError("horizon must be >= 1")
    attached = []
    for event in events:
        decision = _event_session(event)
        series = future.get(event.symbol)
        if not series:
            labels = {"status": "UNRESOLVED", "reason": "no_future_series"}
            attached.append(_with_outcomes(event, labels))
            continue
        snapshot_adjusted = bool((event.snapshot or {}).get("adjusted", False))
        snapshot_ca_hash = (event.snapshot or {}).get("ca_table_hash", "")
        future_adjusted = bool(series.get("adjusted", False))
        future_ca_hash = series.get("ca_table_hash", "")
        basis_mismatch = future_adjusted != snapshot_adjusted or (
            snapshot_ca_hash and future_ca_hash and snapshot_ca_hash != future_ca_hash
        )
        if basis_mismatch:
            labels = {"status": "UNRESOLVED", "reason": "adjustment_basis_mismatch"}
            attached.append(_with_outcomes(event, labels))
            continue
        sessions = list(series["sessions"])
        opens = future_after(sessions, series["opens"], decision)
        highs = future_after(sessions, series["highs"], decision)
        lows = future_after(sessions, series["lows"], decision)
        closes = future_after(sessions, series["closes"], decision)
        # Directive-1b: assert every session about to feed a label is
        # strictly after the decision session, in addition to (not instead
        # of) future_after's own filter above -- defense-in-depth so a
        # future call site that bypasses future_after cannot silently feed
        # the decision bar (or an earlier one) into long_outcome/breakout_hold.
        assert_future_only(future_after(sessions, sessions, decision), decision)
        adv_value = None
        adv_series = series.get("adv_series") or []
        for i in range(len(sessions) - 1, -1, -1):
            if sessions[i] <= decision and i < len(adv_series) and adv_series[i] is not None:
                adv_value = adv_series[i]
                break
        if not opens:
            labels = {"status": "UNRESOLVED", "reason": "no_future_bars"}
            attached.append(_with_outcomes(event, labels))
            continue
        atr_pct = (event.snapshot or {}).get("atr_pct")
        close = event.snapshot.get("close")
        if atr_pct is None or not close:
            labels = {"status": "UNRESOLVED", "reason": "missing_atr_or_close"}
            attached.append(_with_outcomes(event, labels))
            continue
        entry = float(opens[0])  # next-bar fill, not the decision close
        stop = entry * (1.0 - (float(atr_pct) / 100.0) * stop_atr_mult)
        if stop >= entry:
            labels = {"status": "UNRESOLVED", "reason": "non_positive_risk"}
            attached.append(_with_outcomes(event, labels))
            continue
        window = min(horizon, len(highs), len(lows), len(closes))
        if window < 1:
            labels = {"status": "UNRESOLVED", "reason": "no_future_bars"}
            attached.append(_with_outcomes(event, labels))
            continue
        candidate_sessions = set((unconfirmed_ca_sessions or {}).get(event.symbol, ()))
        if candidate_sessions:
            future_sessions_used = future_after(sessions, sessions, decision)[:window]
            if any(s in candidate_sessions for s in future_sessions_used):
                labels = {"status": "UNRESOLVED", "reason": "unconfirmed_corporate_action"}
                attached.append(_with_outcomes(event, labels))
                continue
        outcome = long_outcome(
            entry=entry, stop=stop,
            highs=highs[:window], lows=lows[:window], horizon=window,
            opens=opens[:window],   # gap-through fills: exit at the gap open
        )
        hold, hold_reasons = breakout_hold(
            closes[:window], trigger=float(close), min_sessions=min(3, window),
        )
        gap_open = None
        if outcome.stop_hit:
            first_touch = next(i for i in range(len(lows[:window])) if lows[:window][i] <= stop)
            gap_open = float(opens[:window][first_touch])
        gross_bps = round(
            stop_aware_return_bps(
                entry, stop, closes[:window], window, stop_hit=outcome.stop_hit,
                gap_open=gap_open,
            ),
            4,
        )
        # Net-of-cost (2026-08-30, v4): net is the only accept/reject number
        # (research/costs.py). Order sized at 5% of trailing-20 ADV -- a
        # conservative research-scale assumption, not a real order book.
        # Missing ADV fails closed to None rather than fabricating a cost
        # (R12) -- an UNRESOLVED-adjacent gap on the cost fields only, the
        # outcome itself still resolves.
        net_bps = None
        cost_total_rt_bps = None
        if adv_value is not None and adv_value > 0:
            cost = round_trip_cost(order_value=0.05 * adv_value, adv_value=adv_value)
            net_bps = round(net_return_bps(gross_bps, cost), 4)
            cost_total_rt_bps = round(cost.total_rt_bps, 4)
        labels = {
            "status": "RESOLVED" if window >= horizon else "PARTIAL",
            "entry": round(entry, 4),
            "stop": round(stop, 4),
            "horizon": window,
            "mfe_pct": outcome.mfe_pct,
            "mae_pct": outcome.mae_pct,
            "stop_hit": outcome.stop_hit,
            "potential_r_multiple": outcome.potential_r_multiple,
            "r_multiple": outcome.r_multiple,
            "exit_price": outcome.exit_price,
            "gap_through": outcome.gap_through,
            "attained_1r": outcome.attained_1r,
            "attained_2r": outcome.attained_2r,
            "attained_3r": outcome.attained_3r,
            "gross_bps": gross_bps,
            "net_bps": net_bps,
            "cost_total_rt_bps": cost_total_rt_bps,
            "costs_version": COSTS_VERSION if net_bps is not None else None,
            "breakout_hold": hold,
            "breakout_hold_reasons": list(hold_reasons),
        }
        attached.append(_with_outcomes(event, labels))
    return attached


def _with_outcomes(event: ResearchEvent, labels: dict) -> ResearchEvent:
    # Every persisted outcome state, including a refusal, identifies the label
    # semantics that produced it. This lets archive maintenance detect stale
    # research output after a critical correction such as stop-aware returns.
    labels = {"label_version": OUTCOME_LABELS_VERSION, **labels}
    return ResearchEvent(
        event_id=event.event_id,
        candidate_id=event.candidate_id,
        symbol=event.symbol,
        timestamp=event.timestamp,
        snapshot=event.snapshot,
        config_hash=event.config_hash,
        research_schema_version=event.research_schema_version,
        outcome_labels=labels,
    )
