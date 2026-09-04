"""Generate nightly reports for every trading day in the past month.

Ingests the store once, then scans at each trading day boundary to produce
real reports for the multi-date picker. Writes to reports_dir and skips
dates that already have a report."""
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

def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def find_trading_days(csv_dir: Path, months_back: int = 1) -> list[date]:
    """Find all trading days in the past N months from available CSV files."""
    from datetime import date as _date
    today = _date.today()
    cutoff = _date(today.year, today.month - months_back, 1) if today.month > months_back else _date(today.year - 1, 12 + (today.month - months_back), 1)

    # Find all CSV dates
    csv_dates: set[date] = set()
    for p in csv_dir.iterdir():
        if p.suffix.lower() != ".csv" or "bhav" not in p.name.lower():
            continue
        # Parse DDMMYYYY from filename
        name = p.stem
        parts = name.split("_")
        date_str = parts[-1]  # DDMMYYYY
        if len(date_str) == 8 and date_str.isdigit():
            d = _date(int(date_str[4:8]), int(date_str[2:4]), int(date_str[0:2]))
            if d >= cutoff:
                csv_dates.add(d)

    return sorted(csv_dates)

def main():
    log("Finding trading days in past month...")
    trading_days = find_trading_days(CSV_DIR)
    log(f"Found {len(trading_days)} trading days: {trading_days[0]} -> {trading_days[-1]}")

    # Skip dates that already have a report
    existing = set()
    for p in REPORTS_DIR.glob("tonight_*.json"):
        date_str = p.stem.replace("tonight_", "")
        try:
            existing.add(date.fromisoformat(date_str))
        except ValueError:
            pass
    log(f"{len(existing)} reports already exist, skipping them")

    pending = [d for d in trading_days if d not in existing]
    log(f"{len(pending)} reports to generate")

    if not pending:
        log("All dates already have reports. Done.")
        return

    # Ingest the store once (recent 600 files)
    from unidesk.momentum.data.market_store import InMemoryMarketStore
    from unidesk.momentum.data.bhavcopy import parse_bhavcopy_file, load_into_store
    from unidesk.momentum.data.corp_actions import load_confirmed_actions
    from unidesk.momentum.scan import scan_universe
    from unidesk.momentum.report_json import build_nightly_json
    from unidesk.research.candidates import freeze_scan
    from unidesk.research.event_store import persist_events

    # Use sec_bhavdata_full files only, sorted properly
    sec_csvs = [p for p in CSV_DIR.iterdir()
                if p.suffix.lower() == ".csv" and "sec_bhavdata_full" in p.name]
    def sort_key(p):
        nm = p.stem.split("_")[-1]
        return nm[4:8] + nm[2:4] + nm[0:2]
    sec_csvs.sort(key=sort_key)
    recent_csvs = sec_csvs[-600:]

    log(f"Ingesting {len(recent_csvs)} files...")
    t0 = time.time()
    store = InMemoryMarketStore()
    seen: set = set()
    for path in recent_csvs:
        try:
            rows, _ = parse_bhavcopy_file(path)
            load_into_store(store, rows, seen=seen)
        except Exception:
            pass
    log(f"Ingested in {time.time()-t0:.0f}s. Proceeding to scan each trading day...")

    actions = load_confirmed_actions()
    generated = 0
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    for d in pending:
        # Scan at 18:00 IST on that trading day
        as_of = datetime(d.year, d.month, d.day, 18, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        try:
            scan = scan_universe(store, as_of, actions=actions, apply_universe_gates=True, run_detectors=True)
        except Exception as exc:
            log(f"  {d}: scan failed: {exc}")
            continue

        if not scan.last_session or scan.last_session != d.isoformat():
            # The scan may return a different last session if the date doesn't have data
            if scan.last_session and scan.last_session in [dd.isoformat() for dd in pending]:
                # Use whatever session it found
                pass
            elif not scan.last_session:
                log(f"  {d}: no data at this date")
                continue

        session_tag = scan.last_session
        # Don't overwrite existing
        out_path = REPORTS_DIR / f"tonight_{session_tag}.json"
        if out_path.exists():
            log(f"  {session_tag}: already exists, skipping")
            continue

        report_json = build_nightly_json(scan, regime_note="historical scan (past-month batch)")
        out_path.write_text(json.dumps(report_json, indent=2), encoding="utf-8")
        log(f"  {session_tag}: {scan.scanned} symbols, {len(scan.symbols)} candidates -> {out_path.name}")
        generated += 1

    log(f"Generated {generated} new reports. Total: {len(existing) + generated} in {REPORTS_DIR}")

if __name__ == "__main__":
    main()