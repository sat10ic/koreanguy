"""Mechanical health checks.

The point: any model, at any time, can find out whether the tool works without
understanding the codebase or exercising judgment. Run it before you start
(so you know what was already broken) and after you finish (so you know you did
not break anything).

    python -m traderlog.checks

Every check returns one of:
    pass            everything it asserts is true
    fail: <reason>  something is wrong, exit code 1
    stale_<n>d      working, but the data is n days old
    not_built_yet   the wave that owns this check has not run yet
    dry_run         configured off deliberately

`not_built_yet` is honest during construction, but it means a green run does NOT
prove the tool works end to end. Each wave flips its own check to a real
assertion as part of that wave's done-test (audit finding I1). A check that is
still `not_built_yet` after its wave shipped is a defect in that wave.
"""
from __future__ import annotations

from .runner import CheckResult, run_all, write_state

__all__ = ["CheckResult", "run_all", "write_state"]
