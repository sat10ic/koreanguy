"""Explicit operator entrypoint for the saved provisional Chrome capture."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traderlog.db import DB_PATH, init_db
from traderlog.ingest.provisional_import import (
    ProvisionalImportError,
    import_provisional,
    read_provisional_source,
)


_ROOT = Path(__file__).resolve().parent
_DEFAULT_SOURCE = _ROOT / "data" / "raw" / "chrome_captures" / "2026-08-23_30d_provisional.json"


def _readonly_connection(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import explicitly selected provisional Chrome captures.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="validate/count only; never write DB, archives, or media")
    mode.add_argument("--apply", action="store_true", help="perform archive-first import into the explicitly named DB")
    parser.add_argument("--handles", nargs="+", required=True, help="exact handles to import; no implicit all-handles mode")
    parser.add_argument("--source", type=Path, default=_DEFAULT_SOURCE)
    parser.add_argument("--db", type=Path, required=True, help="explicit TraderLog database path")
    args = parser.parse_args(argv)

    try:
        source = read_provisional_source(args.source)
        conn = _readonly_connection(args.db) if args.dry_run else init_db(args.db)
        try:
            report = import_provisional(conn, source, handles=args.handles, dry_run=args.dry_run)
        finally:
            conn.close()
    except (OSError, sqlite3.Error, ProvisionalImportError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report.as_dict(), sort_keys=True))
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
