"""sys.path shim so the checks run from a clone with no install step.

This machine's python runs with `safe_path` enabled and ignores PYTHONPATH, so
`python -m traderlog.checks` cannot find the package unless it has been pip
installed. Rather than make every future session debug that, run:

    python traderlog/run_checks.py

Same pattern as run_manas_api.py at the repo root. Once `pip install -e traderlog`
has been done, `python -m traderlog.checks` works too and is equivalent.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traderlog.checks.__main__ import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
