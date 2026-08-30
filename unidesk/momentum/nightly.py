"""The nightly EOD pipeline (Build Manual V2, wave N1).

Cadence: every trading evening after bhavcopy publication (~19:00 IST).

    .venv-orderflow/Scripts/python.exe -m unidesk.momentum.nightly             # download + full run
    .venv-orderflow/Scripts/python.exe -m unidesk.momentum.nightly --no-download --limit-files 5

Steps: (1) optionally download the day's bhavcopy via the owner's public
downloader, (2) ingest everything into the point-in-time store, (3) scan the
universe (features + detectors), (4) write the TONIGHT report under
``data/market/reports/``. No credentials. No orders. Honest gaps.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from unidesk.momentum.data.bhavcopy import ingest_directory
from unidesk.momentum.data.corp_actions import load_confirmed_actions
from unidesk.momentum.data.market_store import InMemoryMarketStore
from unidesk.momentum.report import build_nightly_report
from unidesk.momentum.report_json import build_nightly_json
from unidesk.momentum.scan import scan_universe
from unidesk.research.candidates import freeze_scan
from unidesk.research.event_store import persist_events

_REPO_ROOT = Path(__file__).resolve().parents[2]
Downloader = Path(_REPO_ROOT / "bhavcopy_extractor" / "download_bhavcopy.py")


def run_download(days: int, python_exe: str | None = None) -> bool:
    """Invoke the owner's public-mirror downloader. Returns True on success.
    Never handled by an agent interactively; public sources, no credentials."""
    exe = python_exe or sys.executable
    try:
        result = subprocess.run(
            [exe, str(Downloader), "--days", str(days)],
            cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=600,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"[download] failed: {exc}")
        return False
    if result.returncode != 0:
        print(f"[download] downloader exited {result.returncode}: {result.stderr[-400:]}")
        return False
    print("[download] ok")
    return True


def run_nightly(
    *,
    data_root: Path,
    backlog: Path,
    reports_dir: Path,
    download_days: int = 0,
    limit_files: int | None = None,
    python_exe: str | None = None,
    as_of: datetime | None = None,
) -> Path:
    if download_days > 0:
        run_download(download_days, python_exe)

    store = InMemoryMarketStore()
    seen: set = set()  # shared across corpus directories: dedupe overlaps
    stats = ingest_directory(store, Path(backlog), limit_files=limit_files, seen=seen)
    extra = Path(data_root) / "bhavcopy"
    if extra.is_dir() and extra.resolve() != Path(backlog).resolve():
        stats2 = ingest_directory(store, extra, limit_files=limit_files, seen=seen)
        stats = {"files": stats["files"] + stats2["files"],
                 "bars_added": stats["bars_added"] + stats2["bars_added"]}
    print(f"[ingest] {stats['bars_added']} bars from {stats['files']} files")

    moment = as_of or datetime.now(timezone.utc)
    actions = load_confirmed_actions()
    scan = scan_universe(store, moment, actions=actions)
    report = build_nightly_report(scan)
    # JSON sibling: same in-memory `scan`, not a re-derivation (see
    # design/UI_BACKEND_INTEGRATION_PLAN.md and momentum/report_json.py).
    report_json = build_nightly_json(scan)
    if actions:
        print(f"[ca] {len(actions)} confirmed actions · "
              f"{scan.adjusted_symbols} symbols adjusted (raw store untouched)")

    events = freeze_scan(scan)
    frozen = persist_events(events, data_root)
    print(f"[research] froze {frozen['rows']} events in {frozen['partitions']} "
          f"partition(s) under {frozen['path']}")

    reports_dir.mkdir(parents=True, exist_ok=True)
    session_tag = scan.last_session or moment.date().isoformat()
    out = reports_dir / f"tonight_{session_tag}.md"
    out.write_text(report, encoding="utf-8")
    out_json = reports_dir / f"tonight_{session_tag}.json"
    out_json.write_text(json.dumps(report_json, indent=2), encoding="utf-8")
    print(f"[report] {out}")
    print(f"[report] {out_json}")
    print(f"[scan] {scan.scanned} symbols scanned · "
          f"{scan.above_ema50} above EMA50 ({scan.pct_above_ema50:.1f}%)")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Nightly EOD pipeline (download → ingest → scan → report)")
    parser.add_argument("--download-days", type=int, default=1,
                        help="days of bhavcopy to download before ingest (0 = skip download)")
    parser.add_argument("--limit-files", type=int, default=None,
                        help="ingest only the first N backlog files (smoke runs)")
    parser.add_argument("--no-download", action="store_true", help="skip the download step")
    parser.add_argument("--data-root", type=Path, default=_REPO_ROOT / "data" / "market")
    parser.add_argument("--backlog", type=Path,
                        default=Path(_REPO_ROOT / "data" / "bhavcopy"),
                        help="EOD archive (D15: data/bhavcopy, the downloader's target)")
    parser.add_argument("--reports-dir", type=Path, default=_REPO_ROOT / "data" / "market" / "reports")
    parser.add_argument("--python-exe", default=None, help="interpreter for the downloader subprocess")
    args = parser.parse_args(argv)

    out = run_nightly(
        data_root=args.data_root, backlog=args.backlog, reports_dir=args.reports_dir,
        download_days=0 if args.no_download else args.download_days,
        limit_files=args.limit_files, python_exe=args.python_exe,
    )
    print(f"\nTonight's report: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
