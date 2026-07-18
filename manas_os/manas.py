#!/usr/bin/env python
"""Compatibility launcher for the installed ``manas`` command.

Prefer ``manas <command>`` after ``pip install -e .``. This file remains for
existing callers but relies on the same installed package rather than path injection.
"""
from manas_os.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
