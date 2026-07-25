"""manas_os/integrity/ -- pipeline & data-integrity watchdog.

Grew out of a same-day measurement session (see RELIABILITY_AUDIT and the
`manas integrity` CLI docstring in manas_os/cli/__init__.py) that found the
daily pipeline silently stopping for two days with nothing surfacing it,
73 tunable numeric thresholds evaluated against a handful of independent
scan dates, LLM verdicts never getting graded against real outcomes, a
scanner card whose own JSON payload contradicted its own label, and
pipeline stages that report `status='skip', never fail` -- so failures are
invisible unless someone remembers to look.

checks.py holds the individual PASS/WARN/FAIL checks (pure functions over a
read-only sqlite3.Connection). report.py wires them into run_all() +
to_markdown() for `manas integrity` (cli/__init__.py::_cmd_integrity).

Every read in this package MUST go through a `file:...?mode=ro` URI
connection (sqlite3.connect(..., uri=True)) -- never db.connect()/
db.init_db(), which write on open and previously caused `manas scorecard`
to hit "database is locked" against the live pipeline. See report.run_all
for the one real-DB read-only connection this package opens.
"""
from __future__ import annotations

from manas_os.integrity.report import run_all, to_markdown

__all__ = ["run_all", "to_markdown"]
