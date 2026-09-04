"""Run the nightly pipeline in background and write PID + progress to a log file."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
LOG = Path(__file__).resolve().parents[1] / "data" / "market" / "reports" / "nightly_progress.log"
PIDFILE = Path(__file__).resolve().parents[1] / "data" / "market" / "reports" / "nightly_pid.txt"


def log(msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


if __name__ == "__main__":
    PIDFILE.write_text(str(__import__("os").getpid()))
    from datetime import datetime, timezone, date as _date
    from pathlib import Path as P

    repo = Path(__file__).resolve().parents[1]
    log("Starting nightly pipeline (MOST RECENT files only)...")

    # Get the most recent 600 sec_bhavdata_full_* files (consistent naming)
    csv_dir = repo / "data" / "bhavcopy"
    sec_csvs = [
        p for p in csv_dir.iterdir() if p.suffix.lower() == ".csv" and "sec_bhavdata_full" in p.name
    ]

    def sort_key(p):
        name = p.stem.split("_")[-1]  # DDMMYYYY
        return name[4:8] + name[2:4] + name[0:2]  # YYYYMMDD

    sec_csvs.sort(key=sort_key)
    recent_csvs = sec_csvs[-600:]
    log(f"Using {len(recent_csvs)} files: {recent_csvs[0].name} -> {recent_csvs[-1].name}")

    t0 = time.time()
    from unidesk.momentum.data.market_store import InMemoryMarketStore
    from unidesk.momentum.data.bhavcopy import parse_bhavcopy_file, load_into_store

    store = InMemoryMarketStore()
    seen: set = set()
    stats = {"files": 0, "skipped_files": 0, "bars_added": 0}
    for path in recent_csvs:
        try:
            rows, _ = parse_bhavcopy_file(path)
            delta, _ = load_into_store(store, rows, seen=seen)
            stats["bars_added"] += delta
            stats["files"] += 1
        except Exception as exc:
            stats["skipped_files"] += 1
            log(f"Skipped {path.name}: {exc}")

    log(
        f"Ingested {stats['bars_added']} bars from {stats['files']} files "
        f"({stats['skipped_files']} skipped)"
    )

    from unidesk.momentum.data.corp_actions import load_confirmed_actions
    from unidesk.momentum.regime_state import STATE_FILENAME, load_classifier, save_classifier
    from unidesk.momentum.scan import scan_universe
    from unidesk.momentum.report import build_nightly_report
    from unidesk.momentum.report_json import build_nightly_json
    from unidesk.research.candidates import freeze_scan
    from unidesk.research.event_store import persist_events

    moment = datetime.now(timezone.utc)
    actions = load_confirmed_actions()
    scan = scan_universe(store, moment, actions=actions, apply_universe_gates=True)

    gate_keys = {k: v for k, v in scan.skipped.items() if k.startswith("universe_gate_")}
    if gate_keys:
        total = sum(gate_keys.values())
        breakdown = ", ".join(
            f"{k.removeprefix('universe_gate_')}={v}" for k, v in sorted(gate_keys.items())
        )
        log(f"{total} symbols excluded from RS ranking ({breakdown})")

    breadth = scan.pct_above_ema50 if scan.scanned > 0 else 0.0
    breadth_frac = breadth / 100.0
    state_path = repo / "data" / "market" / STATE_FILENAME
    rc = load_classifier(state_path)
    last_session = scan.last_session
    if isinstance(rc, tuple):
        rc, last_session = rc
    if last_session == scan.last_session:
        regime_note = (
            f"{rc.current.value} (breadth {breadth:.1f}% above EMA50, {rc.source}; "
            f"{scan.last_session} already scored, state unchanged)"
        )
    else:
        row = rc.update(_date.fromisoformat(scan.last_session), breadth_frac)
        save_classifier(state_path, rc, last_session=scan.last_session)
        pending = (
            f", {row.hysteresis_pending} session(s) toward a flip"
            if row.hysteresis_pending
            else ""
        )
        regime_note = f"{row.regime.value} (breadth {breadth:.1f}% above EMA50, {row.source}{pending})"
    log(f"Regime: {regime_note}")

    report = build_nightly_report(scan, regime_note=regime_note)
    report_json = build_nightly_json(scan, regime_note=regime_note)

    if actions:
        log(f"{len(actions)} confirmed actions - {scan.adjusted_symbols} symbols adjusted")

    events = freeze_scan(scan)
    data_root = repo / "data" / "market"
    frozen = persist_events(events, data_root)
    log(f"Froze {frozen['rows']} events in {frozen['partitions']} partition(s) under {frozen['path']}")

    reports_dir = repo / "data" / "market" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    session_tag = scan.last_session or moment.date().isoformat()
    out = reports_dir / f"tonight_{session_tag}.md"
    out.write_text(report, encoding="utf-8")
    out_json = reports_dir / f"tonight_{session_tag}.json"
    out_json.write_text(json.dumps(report_json, indent=2), encoding="utf-8")
    log(f"Report: {out}")
    log(f"Report JSON: {out_json}")
    log(f"Scan: {scan.scanned} symbols - {scan.above_ema50} above EMA50 ({scan.pct_above_ema50:.1f}%)")

    elapsed = time.time() - t0
    log(f"Done in {elapsed:.0f}s")