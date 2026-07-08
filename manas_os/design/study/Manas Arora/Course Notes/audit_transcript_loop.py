#!/usr/bin/env python
"""
Audit the Manas transcript-cleaning loop.

Checks:
- root course files that do not yet have obvious cleaned/master outputs
- unresolved flags in cleaned files
- query row IDs
- rough query/flag coverage by chapter

This script is read-only.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parent
CLEANED = BASE / "cleaned"
QUERIES = BASE / "TRANSCRIPT_QUERIES.md"


ROOT_SOURCE_RE = re.compile(r"^(CH|Ch|ch|6 |7\.|CH1|ss\.md$)", re.I)
FLAG_RE = re.compile(r"⚠|\[⚠|\[FLAG\b|<u>|ASR garble|unverified|suspect", re.I)
QUERY_ID_RE = re.compile(r"^\|\s*([A-Z]{1,3}-[a-z]|[0-9]+(?:\.[0-9]+)?-[a-z]|S-[0-9]+|[0-9]+-[a-z])\s*\|", re.M)


def word_count(path: Path) -> int:
    return len(re.findall(r"\S+", path.read_text(encoding="utf-8", errors="replace")))


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    root_sources = [
        p for p in BASE.iterdir()
        if p.is_file()
        and p.name not in {"TRANSCRIPT_CLEANING_LOOP.md", "TRANSCRIPT_QUERIES.md", "audit_transcript_loop.py"}
        and ROOT_SOURCE_RE.search(p.name)
    ]
    cleaned_files = sorted(p for p in CLEANED.glob("*.md") if not p.name.endswith("_correction_log.md"))
    cleaned_names = {p.name.lower() for p in cleaned_files}

    print("# Transcript Loop Audit")
    print()
    print("## Source files")
    print()
    for p in sorted(root_sources, key=lambda x: x.name.lower()):
        print(f"- {p.name} ({word_count(p)} words)")

    print()
    print("## Cleaned files")
    print()
    for p in cleaned_files:
        print(f"- {p.name} ({word_count(p)} words)")

    print()
    print("## Obvious missing cleaned masters")
    print()
    expected_masters = {
        "CH1 Fear Management.md": "Chapter_1.md",
        "CH 8.md": "Chapter_8.md",
        "CH 9.md": "Chapter_9.md",
        "CH10.md": "Chapter_10.md",
        "CH11.md": "Chapter_11.md",
        "ch12.md": "Chapter_12.md",
        "CH13.md": "Chapter_13.md",
        "ch14.md": "Chapter_14.md",
        "ch15.md": "Chapter_15.md",
        "ch16.md": "Chapter_16.md",
        "ss.md": "Strong_Start_Tightness_Study.md",
    }
    missing = []
    for raw, expected in expected_masters.items():
        if (BASE / raw).exists() and expected.lower() not in cleaned_names:
            missing.append((raw, expected))
            print(f"- {raw} -> missing cleaned/{expected}")
    if not missing:
        print("- None from expected CH1/CH8–CH11 set.")

    print()
    print("## Flags in cleaned files")
    print()
    flag_count = 0
    for p in cleaned_files:
        text = p.read_text(encoding="utf-8", errors="replace")
        for idx, line in enumerate(text.splitlines(), start=1):
            if line.startswith("*Cleaned course transcript") or line.startswith("*Master chapter"):
                continue
            if FLAG_RE.search(line):
                flag_count += 1
                print(f"- {p.name}:{idx}: {line[:220]}")
    if flag_count == 0:
        print("- No unresolved flags found.")
    else:
        print()
        print(f"Total flag lines: {flag_count}")

    print()
    print("## Query IDs")
    print()
    if QUERIES.exists():
        qtext = QUERIES.read_text(encoding="utf-8", errors="replace")
        ids = QUERY_ID_RE.findall(qtext)
        for qid in ids:
            print(f"- {qid}")
        print()
        print(f"Total query rows detected: {len(ids)}")
    else:
        print("- TRANSCRIPT_QUERIES.md missing.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
