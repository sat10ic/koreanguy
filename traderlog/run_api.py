"""sys.path shim for the API. See run_checks.py for why this exists.

    python traderlog/run_api.py     ->  http://127.0.0.1:8100
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traderlog.api.app import main  # noqa: E402

if __name__ == "__main__":
    main()
