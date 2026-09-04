"""sys.path shim for W1 X ingest. See run_checks.py for why this exists.

    python traderlog/run_xfetch.py --login
    python traderlog/run_xfetch.py
    python traderlog/run_xfetch.py --forever
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traderlog.ingest.xfetch import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
