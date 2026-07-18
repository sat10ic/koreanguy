#!/usr/bin/env python
"""Compatibility launcher for the installed ``manas`` command.

Prefer ``manas <command>`` after ``pip install -e .``.
"""
import sys

from manas_os.cli import main

if __name__ == "__main__":
    sys.exit(main())
