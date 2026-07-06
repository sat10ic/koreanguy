#!/usr/bin/env python
"""Run the Manas OS API regardless of `-m` module-resolution quirks in this env.

Equivalent to `python -m manas_os.api`, but explicitly puts the repo root
(parent of the manas_os package) on sys.path first.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("manas_os.api.app:app", host="127.0.0.1", port=8000, reload=False)
