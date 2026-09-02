"""Trailing-30-day pipeline: run the full nightly reporting path
(scan -> markdown -> JSON) for every trading day in the trailing 30-day
window.

Uses the corrected path exactly as the live nightly does:
  * confirmed CA-4 table (51 auto-confirmed quarantined)
  * apply_universe_gates=True (price floor / turnover / ETF / circuit-lock)
  * trade geometry (trigger / invalidation / R:R) from detector structure
  * breadth analytics + regime note (breadth-only, labeled historical)

Deliberate scope boundary:
  * Does NOT mutate the persisted regime classifier (that state tracks the
    LIVE cadence; replaying 30 historical days through hysteresis would
    manufacture flip pressure).
  * Does NOT freeze events into the research archive. The archive's partitions
    for this window already exist from the earlier (CA-55) regen; re-freezing
    the same dates would duplicate rows. The correct archive rebuild is
    ``run_regen_full.py`` / ``archive_attach`` (CA-4 + gates), separately.
  * Writes BOTH ``tonight_<date>.md`` and ``tonight_<date>.json`` so the
    multi-date picker serves real nightly artifacts, not scan-only JSON.

Usage (repo root)::

    .venv-orderflow/Scripts/python.exe unidesk/run_30day_pipeline.py
"""
from __future__ import annotations

import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

REPO = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO / "data" / "market"
REPORTS_DIR = DATA_ROOT / "reports"
CSV_DIR = REPO / "data" / "bhavcopy"
IST = timezone(timedelta(hours=5, minutes=30))

TRAILING_DAYS = 30


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def trading_days(window_days: int = TRAILING_DAYS) -> list[date]:
    """Trading days with a CSV in data/bhavcopy within the trailing window."""
    today = date.today()
    cutoff = today - timedelta(days=window_days)
    out: set[date] = set()
    for p in CSV_DIR.iterdir():
        if p.suffix.lower() != ".csv" or "bhav" not in p.name.lower():
            continue
        ds = p.stem.rsplit("_", 1)[-1]  # DDMMYYYY
        if len(ds) == 8 and ds.isdigit():
            d = date(int(ds[4:8]), int(ds[2:4]), int(ds[0:2]))
            if cutoff <= d <= today:
                out.add(d)
    return sorted(out)


def main() -> int:
    days = trading_days()
    log(f"Trailing-{TRAILING_DAYS}-day window: {len(days)} trading days "
        f"({days[0]} -> {days[-1]})")
    if not days:
        log("No trading days in window")
        return 1

    # --- one ingest, then point-in-time scans per day ---------------------
    from unidesk.momentum.data.market_store import InMemoryMarketStore
    from unidesk.momentum.data.bhavcopy import parse_bhavcopy_file, load_into_store
    from unidesk.momentum.data.corp_actions import load_confirmed_actions
    from unidesk.momentum.scan import scan_universe
    from unidesk.momentum.report import build_nightly_report
    from unidesk.momentum.report_json import build_nightly_json

    sec_csvs = [
        p for p in CSV_DIR.iterdir()
        if p.suffix.lower() == ".csv" and "sec_bhavdata_full" in p.name
    ]

    def sort_key(p: Path) -> str:
        nm = p.stem.rsplit("_", 1)[-1]
        return nm[4:8] + nm[2:4] + nm[0:2]

    sec_csvs.sort(key=sort_key)
    recent_csvs = sec_csvs[-600:]

    log(f"Ingesting {len(recent_csvs)} files once ...")
    t0 = time.time()
    store = InMemoryMarketStore()
    seen: set = set()
    for path in recent_csvs:
        try:
            rows, _ = parse_bhavcopy_file(path)
            load_into_store(store, rows, seen=seen)
        except Exception as exc:
            log(f"  skip {path.name}: {exc}")
    log(f"Ingested in {time.time() - t0:.0f}s")

    actions = load_confirmed_actions()
    log(f"CA table: {len(actions)} confirmed actions")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    generated = 0
    skipped = 0
    for d in days:
        as_of = datetime(d.year, d.month, d.day, 18, 0, tzinfo=IST)
        try:
            scan = scan_universe(
                store, as_of, actions=actions,
                apply_universe_gates=True, run_detectors=True,
            )
        except Exception as exc:
            log(f"  {d}: scan failed: {exc}")
            skipped += 1
            continue

        session_tag = scan.last_session or d.isoformat()
        if session_tag != d.isoformat():
            log(f"  {d}: store resolved to session {session_tag} (skipping to avoid dup)")
            skipped += 1
            continue

        breadth_note = (
            f"{scan.pct_above_ema50:.1f}% above EMA50"
            if scan.pct_above_ema50 is not None else "breadth unavailable"
        )
        regime_note = (
            f"HISTORICAL 30-day backfill: CHOP/BULL/BEAR not persisted per day; "
            f"breadth {breadth_note}, {scan.scanned} symbols scanned, "
            f"CA-{len(actions)} applied, universe gates applied"
        )

        report = build_nightly_report(scan, regime_note=regime_note)
        report_json = build_nightly_json(scan, regime_note=regime_note)

        out_md = REPORTS_DIR / f"tonight_{session_tag}.md"
        out_json = REPORTS_DIR / f"tonight_{session_tag}.json"
        out_md.write_text(report, encoding="utf-8")
        out_json.write_text(json.dumps(report_json, indent=2), encoding="utf-8")
        n_geo = sum(1 for c in report_json["candidates"] if c.get("trigger"))
        log(f"  {session_tag}: {scan.scanned} symbols, "
            f"{len(report_json['candidates'])} candidates, "
            f"{n_geo} with trigger/invalidation -> .md + .json")
        generated += 1

    log(f"Done: {generated} artifacts (md+json), {skipped} skipped/errored, "
        f"in {REPORTS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())