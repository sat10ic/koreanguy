"""Archive-wide outcome attach (N4 / directive-1f, the last piece of the
research spine's core).

The trap this module exists to avoid (flagged by an Opus pre-flight review,
see HANDOFF.md 2026-08-30): ``attach_outcomes`` refuses
(``UNRESOLVED``/``adjustment_basis_mismatch``) any event whose future series'
stated basis (``adjusted``/``ca_table_hash``) does not match the basis the
snapshot's features were computed under. A future map built from RAW
bhavcopy bars, without stamping the same basis the original scan used, would
silently land every genuinely-adjusted symbol UNRESOLVED across the whole
archive. ``build_future_map`` below constructs the future series with
``momentum.data.corp_actions.adjust_ohlcv`` -- the SAME function
``momentum.scan.scan_universe`` calls -- against the SAME confirmed-actions
content, and stamps ``adjusted``/``ca_table_hash`` the same way
``research.candidates._snapshot`` does, so the two sides are basis-identical
by construction.
"""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Optional

from unidesk.momentum.data.corp_actions import (
    ConfirmedAction, adjust_ohlcv, confirmed_actions_content_hash, load_confirmed_actions,
)
from unidesk.momentum.data.market_store import InMemoryMarketStore
from unidesk.momentum.data.splits import scan_store_for_splits, unconfirmed_candidate_sessions
from unidesk.momentum.scan import MIN_SESSIONS_DEFAULT, scan_universe
from unidesk.research.candidates import attach_outcomes, config_hash_for, freeze_scan
from unidesk.research.event_store import load_events, persist_events
from unidesk.research.labels import OUTCOME_LABELS_VERSION

IST = timezone.utc  # available_at already carries the correct UTC instant; see below


def build_future_map(
    store: InMemoryMarketStore,
    actions: list[ConfirmedAction],
    *,
    confirmed_actions_path: Optional[Path] = None,
) -> dict[str, dict]:
    """Full chronological adjusted OHLCV per symbol, basis-stamped to match
    what ``freeze_scan``/``_snapshot`` stamp on the ResearchEvent side.

    One series per symbol covers every decision session for that symbol --
    ``attach_outcomes``/``future_after`` filters to sessions strictly after
    each event's own decision date, so a single full-archive future map
    serves every event regardless of which session it was frozen at.
    """
    by_symbol: dict[str, list] = {}
    for item in store._daily:
        by_symbol.setdefault(item.bar.symbol, []).append(item)
    ca_hash = confirmed_actions_content_hash(confirmed_actions_path)
    future: dict[str, dict] = {}
    for sym, bars in by_symbol.items():
        bars = sorted(bars, key=lambda b: b.bar.session)
        sessions = [b.bar.session for b in bars]
        adj = adjust_ohlcv(
            opens=[b.bar.open for b in bars],
            highs=[b.bar.high for b in bars],
            lows=[b.bar.low for b in bars],
            closes=[b.bar.close for b in bars],
            volumes=[float(b.bar.volume) for b in bars],
            sessions=sessions, symbol=sym, actions=actions,
        )
        future[sym] = {
            "sessions": sessions,
            "opens": adj["open"],
            "highs": adj["high"],
            "lows": adj["low"],
            "closes": adj["close"],
            # Directive-1d basis stamp: must equal what _snapshot() computed
            # for this same symbol under the same confirmed-actions content.
            "adjusted": bool(adj["adjusted"]),
            "ca_table_hash": ca_hash,
        }
    return future


def _as_of_for_session(session: date) -> datetime:
    """18:30 UTC on the session day -- strictly after bhavcopy's stated
    18:00 IST (12:30 UTC) availability, so every bar dated that session is
    visible."""
    return datetime.combine(session, time(18, 30), tzinfo=timezone.utc)


def archive_sessions(store: InMemoryMarketStore, *, min_sessions: int = MIN_SESSIONS_DEFAULT) -> list[date]:
    """Every session in the store from the point min_sessions of history
    exist (scan_universe's own honest floor) through the last session."""
    sessions = sorted({b.bar.session for b in store._daily})
    if len(sessions) < min_sessions:
        return []
    return sessions[min_sessions - 1:]


def sessions_needing_label_refresh(
    data_root: Path,
    *,
    expected_version: str = OUTCOME_LABELS_VERSION,
) -> list[str]:
    """Return persisted partitions not produced by the current label semantics.

    A partition qualifies only if every event has an outcome-label version equal
    to ``expected_version``. Empty or freeze-only partitions are intentionally
    stale too, so a resume/rebuild job cannot mistake an older partial pass for
    current research evidence.
    """
    base = Path(data_root) / "research" / "events"
    if not base.exists():
        return []
    stale = []
    for part in sorted(base.glob("date=*")):
        session = part.name.removeprefix("date=")
        events = load_events(data_root, session=session)
        if not events or any(
            event.outcome_labels.get("label_version") != expected_version
            for event in events
        ):
            stale.append(session)
    return stale


def run_archive_attach(
    *,
    backlog: Path,
    data_root: Path,
    confirmed_actions_path: Optional[Path] = None,
    horizon: int = 10,
    stop_atr_mult: float = 1.0,
    min_sessions: int = MIN_SESSIONS_DEFAULT,
    limit_sessions: Optional[int] = None,
    session_step: int = 1,
    progress_every: int = 10,
    store: Optional[InMemoryMarketStore] = None,
    only_sessions: Optional[list] = None,
) -> dict:
    """The directive-1f driver: ingest the real archive, freeze one
    candidate snapshot per eligible session, attach basis-correct outcomes
    with the unconfirmed-CA backlog wired in, persist, and report counts.

    ``store`` lets a caller (or a test) pass an already-ingested store to
    avoid re-ingesting 1M bars per call.
    """
    if store is None:
        from unidesk.momentum.data.bhavcopy import ingest_directory
        store = InMemoryMarketStore()
        ingest_directory(store, Path(backlog))

    actions = load_confirmed_actions(confirmed_actions_path)
    future = build_future_map(store, actions, confirmed_actions_path=confirmed_actions_path)

    candidates = scan_store_for_splits(store)
    ca_backlog = unconfirmed_candidate_sessions(candidates, actions)

    if only_sessions is not None:
        # Resume mode (directive-1f): re-derive the full eligible-session
        # list for validation, but process exactly the caller-supplied
        # subset -- used to pick a killed run back up without re-doing
        # already-persisted sessions or silently skipping any.
        eligible = set(archive_sessions(store, min_sessions=min_sessions))
        sessions = [s for s in only_sessions if s in eligible]
    else:
        sessions = archive_sessions(store, min_sessions=min_sessions)
        sessions = sessions[::session_step]
    if limit_sessions is not None:
        sessions = sessions[:limit_sessions]

    reason_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    total_events = 0
    total_partitions = 0
    for i, session in enumerate(sessions):
        as_of = _as_of_for_session(session)
        scan = scan_universe(store, as_of, min_sessions=min_sessions, actions=actions)
        cfg = config_hash_for(scan, confirmed_actions_path=confirmed_actions_path)
        events = freeze_scan(scan, config_hash=cfg, confirmed_actions_path=confirmed_actions_path)
        labeled = attach_outcomes(
            events, future,
            horizon=horizon, stop_atr_mult=stop_atr_mult,
            unconfirmed_ca_sessions=ca_backlog,
        )
        for ev in labeled:
            status = ev.outcome_labels.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
            if status == "UNRESOLVED":
                reason = ev.outcome_labels.get("reason", "unknown")
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
        stats = persist_events(labeled, data_root)
        total_events += len(labeled)
        total_partitions += stats["partitions"]
        if progress_every and (i % progress_every == 0 or i == len(sessions) - 1):
            print(f"[archive-attach] {i + 1}/{len(sessions)} session={session} "
                  f"events_so_far={total_events} status={status_counts}", flush=True)

    return {
        "sessions_processed": len(sessions),
        "total_events": total_events,
        "total_partitions": total_partitions,
        "status_counts": status_counts,
        "reason_counts": reason_counts,
        "unconfirmed_ca_symbols": len(ca_backlog),
        "unconfirmed_ca_sessions": sum(len(v) for v in ca_backlog.values()),
        "confirmed_actions": len(actions),
        "data_root": str(data_root),
    }
