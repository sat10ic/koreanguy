"""CA auto-confirmer: auto-accept split candidates within 0.5% tolerance.
Appends to confirmed_actions.csv; reads ca_review_queue.csv."""
from __future__ import annotations
import csv, sys
from datetime import datetime
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from unidesk.momentum.data.corp_actions import CLEAN_FACTORS, ConfirmedAction, load_confirmed_actions, persist_confirmed_actions

REVIEW = REPO / "unidesk" / "config" / "ca_review_queue.csv"
CONFIRMED = REPO / "unidesk" / "config" / "confirmed_actions.csv"
TOL = 0.5


def main():
    existing = load_confirmed_actions(CONFIRMED)
    existing_keys = {(a.symbol, a.ex_date) for a in existing}
    queue = list(csv.DictReader(open(REVIEW, encoding="utf-8-sig")))
    print(f"[ca] {len(queue)} candidates, {len(existing)} confirmed", flush=True)

    new = []
    for r in queue:
        sym = r["symbol"].strip().upper()
        try:
            ex_date = datetime.strptime(r["session"].strip(), "%Y-%m-%d").date()
        except ValueError:
            continue
        if (sym, ex_date) in existing_keys:
            continue
        try:
            d = float(r["clean_distance_pct"])
            nm = float(r["nearest_clean"])
        except (ValueError, KeyError):
            continue
        if d > TOL:
            continue
        if not any(abs(nm - c) < 1e-4 for c in CLEAN_FACTORS):
            continue
        new.append(ConfirmedAction(sym, ex_date, nm, "split_detector_auto_confirmed_v1"))

    if not new:
        print("[ca] no new candidates", flush=True)
        return 0

    passes = sum(1 for a in new[:5] for r in queue
                 if r["symbol"].strip().upper() == a.symbol
                 and r["session"].strip() == a.ex_date.isoformat()
                 and abs(float(r["implied_factor"]) - a.factor) <= a.factor * 0.15)
    if passes == 0:
        print(f"[ca] validation failed (0/{len(new[:5])})", file=sys.stderr)
        return 1

    with open(CONFIRMED, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        for a in new:
            w.writerow([a.symbol, a.ex_date.isoformat(), a.factor, a.source])
    all_a = load_confirmed_actions(CONFIRMED)
    persist_confirmed_actions(all_a, REPO / "data" / "market" / "reference" / "confirmed_actions.parquet")
    print(f"[ca] wrote {len(new)} new ({len(all_a)} total, {passes}/{len(new[:5])} validated)", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())