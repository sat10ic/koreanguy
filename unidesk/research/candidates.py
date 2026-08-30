"""Candidate store (N4 / P7.1): freeze every detector decision at as_of.

Stores VALID, INVALID, and INSUFFICIENT_DATA — a winners-only dataset is a
research defect. Outcomes are attached later from a future slice the
leakage suite owns; they are not computed at freeze time.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Mapping, Optional, Sequence

from unidesk.contracts.base import ContractError
from unidesk.contracts.research import ResearchEvent
from unidesk.momentum.detectors.momentum_burst import Detection
from unidesk.momentum.scan import ScanResult, SymbolScan
from unidesk.research.labels import breakout_hold, long_outcome
from unidesk.research.walkforward import captured_return_bps

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


def _snapshot(scan: SymbolScan) -> dict:
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
    }


def config_hash_for(scan: ScanResult) -> str:
    payload = {
        "schema": SCHEMA_VERSION,
        "detector_names": sorted({
            name for s in scan.symbols for name in s.detectors
        }),
    }
    blob = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()[:16]


def freeze_scan(scan: ScanResult, *, config_hash: Optional[str] = None) -> list[ResearchEvent]:
    """One ResearchEvent per symbol. Failed and insufficient detections stay."""
    cfg = config_hash or config_hash_for(scan)
    session = scan.last_session or scan.as_of.date().isoformat()
    as_of = scan.as_of
    events = []
    for row in scan.symbols:
        snap = _snapshot(row)
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
) -> list[ResearchEvent]:
    """Attach P7.2 labels from a caller-supplied future slice.

    ``future[symbol]`` must contain chronological ``sessions``, ``opens``,
    ``highs``, ``lows``, ``closes``. Only sessions *after* the event date
    are used (next-bar fill). Missing ATR or empty future → UNRESOLVED,
    never a zeroed outcome.
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
        sessions = list(series["sessions"])
        opens = future_after(sessions, series["opens"], decision)
        highs = future_after(sessions, series["highs"], decision)
        lows = future_after(sessions, series["lows"], decision)
        closes = future_after(sessions, series["closes"], decision)
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
        outcome = long_outcome(
            entry=entry, stop=stop,
            highs=highs[:window], lows=lows[:window], horizon=window,
        )
        hold, hold_reasons = breakout_hold(
            closes[:window], trigger=float(close), min_sessions=min(3, window),
        )
        labels = {
            "status": "RESOLVED" if window >= horizon else "PARTIAL",
            "entry": round(entry, 4),
            "stop": round(stop, 4),
            "horizon": window,
            "mfe_pct": outcome.mfe_pct,
            "mae_pct": outcome.mae_pct,
            "stop_hit": outcome.stop_hit,
            "r_multiple": outcome.r_multiple,
            "attained_1r": outcome.attained_1r,
            "attained_2r": outcome.attained_2r,
            "attained_3r": outcome.attained_3r,
            "gross_bps": round(captured_return_bps(entry, closes[:window], window), 4),
            "breakout_hold": hold,
            "breakout_hold_reasons": list(hold_reasons),
        }
        attached.append(_with_outcomes(event, labels))
    return attached


def _with_outcomes(event: ResearchEvent, labels: dict) -> ResearchEvent:
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
