"""R6 — Reactor Scale is context, never a risk input (N-8).

The score is descriptive: it renders as the `RSch` chip and the accumulation
panel, and nothing else. This test makes the rule mechanical, in both the
backend (scoring modules must not import or weigh activity) and the frontend
(`deriveState` and `compareCandidates` must not read it — those are the
protected decision surfaces; see KDE §10.1).

This is the class-level guard for the Reactor Scale specifically. The general
experimental-field containment lives in the published invariants (§10.4).
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCORING_DIR = REPO / "unidesk" / "momentum" / "scoring"
STATUS_TS = REPO / "unidesk_terminal" / "src" / "lib" / "status.ts"
CANDIDATES_TS = REPO / "unidesk_terminal" / "src" / "lib" / "candidates.ts"


def test_scoring_modules_never_reference_activity():
    """No scoring module may import or weigh the Reactor Scale. activity.py
    itself lives in features/ and is imported by scan.py for RENDERING —
    the scoring directory is the boundary."""
    offenders = []
    for path in SCORING_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "activity" in text.lower():
            offenders.append(path.name)
    assert not offenders, f"activity reached scoring modules: {offenders}"


def test_derive_state_never_reads_activity_score():
    """status.ts (deriveState + thresholds) is the promotion surface. The
    Reactor Scale must not appear in it in any spelling."""
    text = STATUS_TS.read_text(encoding="utf-8").lower()
    assert "activity" not in text, (
        "deriveState reads the Reactor Scale — R6 violation: context became "
        "a decision input"
    )


def test_compare_candidates_never_reads_activity_score():
    """compareCandidates is the ranking key. The Reactor Scale may render in
    candidates.ts (RSch chip, accumulation panel) but must not appear inside
    the comparator function body."""
    text = CANDIDATES_TS.read_text(encoding="utf-8")
    start = text.find("export function compareCandidates")
    assert start != -1, "compareCandidates not found — file layout changed, update this test"
    body = text[start:]
    end = body.find("\nfunction ") if "\nfunction " in body else len(body)
    if end:
        body = body[:body.find("\nfunction ")] if "\nfunction " in body else body
    comparator = body.split("\nexport ")[0]
    assert "activity" not in comparator.lower(), (
        "compareCandidates reads the Reactor Scale — R6 violation: a "
        "descriptive analogue is now the ranking key"
    )


def test_activity_module_documents_r6():
    """The rule must travel with the code: activity.py's docstring carries the
    R6 caveat verbatim enough to survive copy-paste drift."""
    doc = (REPO / "unidesk" / "momentum" / "features" / "activity.py").read_text(encoding="utf-8").lower()
    for needle in ("never", "risk input"):
        assert needle in doc, f"activity.py docstring lost the R6 caveat ({needle})"
