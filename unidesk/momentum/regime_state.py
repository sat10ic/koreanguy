"""Cross-run persistence for the R0 regime classifier's hysteresis memory.

``RegimeClassifier`` (momentum/regime.py) is deliberately stateful: it only
flips its emitted regime after ``hysteresis_days`` consecutive sessions
agree, so a flicker in breadth for one day does not relabel the whole
scan. The nightly pipeline (momentum/nightly.py), however, is a fresh
Python process every evening -- without something persisting
``current``/``pending``/``pending_days`` between runs, a brand-new
``RegimeClassifier()`` is constructed each night and the hysteresis memory
resets to a cold start every single time. That would make the hysteresis
protection meaningless in production (it would still work correctly inside
one process, e.g. a backtest loop, but never across nights).

This module is the minimal fix: one small JSON state file, read before the
classifier is used and written back after, following this project's
existing convention for small persisted state (top-level ``STATE.json`` --
facts, not intent, one round trip per run). If the state file is missing,
unreadable, or was written under a different classifier configuration
(different breadth thresholds or hysteresis window), this cold-starts
honestly rather than guessing at a resume.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from unidesk.momentum.regime import Regime, RegimeClassifier

STATE_FILENAME = "regime_state.json"


def _state_from_classifier(rc: RegimeClassifier, *, last_session: str) -> dict:
    return {
        "bull_breadth": rc.bull_breadth,
        "bear_breadth": rc.bear_breadth,
        "hysteresis_days": rc.hysteresis_days,
        "current": rc.current.value,
        "pending": rc._pending.value if rc._pending is not None else None,
        "pending_days": rc._pending_days,
        "started": rc._started,
        "source": rc.source,
        "last_session": last_session,
    }


def load_classifier(
    path: Path,
    *,
    bull_breadth: float = 0.60,
    bear_breadth: float = 0.40,
    hysteresis_days: int = 3,
) -> tuple[RegimeClassifier, Optional[str]]:
    """Build a ``RegimeClassifier``, restoring yesterday's hysteresis state
    from ``path`` when present and compatible. Returns
    ``(classifier, last_persisted_session)`` -- the caller uses the session
    to detect an idempotent re-run (same session scanned twice) and avoid
    double-counting a hysteresis day.
    """
    rc = RegimeClassifier(
        bull_breadth=bull_breadth, bear_breadth=bear_breadth, hysteresis_days=hysteresis_days,
    )
    path = Path(path)
    if not path.exists():
        return rc, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return rc, None
    if (
        raw.get("bull_breadth") != bull_breadth
        or raw.get("bear_breadth") != bear_breadth
        or raw.get("hysteresis_days") != hysteresis_days
    ):
        # Config changed since the state was written (e.g. a different
        # hysteresis window) -- resuming under a new rule would misrepresent
        # what actually happened, so cold-start instead (R12: honest gap,
        # not a silent reinterpretation).
        return rc, None
    try:
        rc.current = Regime(raw["current"])
        rc._pending = Regime(raw["pending"]) if raw.get("pending") else None
        rc._pending_days = int(raw.get("pending_days", 0))
        rc._started = bool(raw.get("started", False))
        rc.source = raw.get("source", "breadth_only")
    except (KeyError, ValueError):
        return RegimeClassifier(
            bull_breadth=bull_breadth, bear_breadth=bear_breadth, hysteresis_days=hysteresis_days,
        ), None
    return rc, raw.get("last_session")


def save_classifier(path: Path, rc: RegimeClassifier, *, last_session: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    state = _state_from_classifier(rc, last_session=last_session)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
