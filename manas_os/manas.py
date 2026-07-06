#!/usr/bin/env python
"""Launcher so the CLI runs regardless of how the interpreter sets sys.path.

Run from anywhere:  python <path>/manas_os/manas.py init-db
It puts the koreanguy root (the parent of the manas_os package) on sys.path, then
dispatches to manas_os.cli.main.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]  # koreanguy/ — parent of the manas_os package
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from manas_os.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
