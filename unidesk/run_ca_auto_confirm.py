"""CA auto-confirmer: auto-accept split candidates within 0.5% tolerance.
WRITES to auto_confirmed_actions.csv (reference-only, never back-adjusts).
The confirmed_actions.csv (which back-adjusts price history) must only
contain owner-verified actions from an authoritative source.

This is a SCREENING tool, not a confirmation tool. Inferred ratios from
price gaps have at least five causes (split, bonus, demerger, rights issue,
crash). The detector cannot distinguish them. See corp_actions.py:5-12.
"""
from __future__ import annotations
import csv, sys
from datetime import datetime
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from unidesk.momentum.data.corp_actions import CLEAN_FACTORS

REVIEW = REPO / "unidesk" / "config" / "ca_review_queue.csv"
# Reference-only file — never back-adjusts price history
AUTO_CONFIRMED = REPO / "unidesk" / "config" / "auto_confirmed_actions.csv"
TOL = 0.5


def main():
    queue = list(csv.DictReader(open(REVIEW, encoding="utf-8-sig")))
    print(f"[ca] {len(queue)} candidates in review queue", flush=True)

    new = []
    for r in queue:
        sym = r["symbol"].strip().upper()
        try:
            ex_date = datetime.strptime(r["session"].strip(), "%Y-%m-%d").date()
        except ValueError:
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
        new.append((sym, ex_date, nm))

    if not new:
        print("[ca] no new auto-confirm candidates", flush=True)
        return 0

    # Append to reference-only file (never back-adjusts price history)
    file_exists = AUTO_CONFIRMED.exists()
    with open(AUTO_CONFIRMED, "a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        if not file_exists:
            w.writerow(["symbol", "ex_date", "factor", "source"])
        for sym, ex_date, factor in new:
            w.writerow([sym, ex_date.isoformat(), factor, "split_detector_auto_confirmed_v1"])

    print(f"[ca] wrote {len(new)} new candidates to {AUTO_CONFIRMED}", flush=True)
    print(f"[ca] WARNING: these are INFERRED from price gaps, not confirmed.", flush=True)
    print(f"[ca] They do NOT back-adjust price history. Only the 4 owner-verified", flush=True)
    print(f"[ca] actions in confirmed_actions.csv affect adjusted OHLCV.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())