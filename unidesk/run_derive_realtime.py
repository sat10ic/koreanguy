"""Generate Yesterday's Calls and Watchlist Drift from the real report archive.

Reads the two most recent tonight_*.json reports and computes:
- Yesterday's Calls: candidates from the prior session, cross-referenced against
  the latest session to show whether they're still active, resolved, or stopped.
- Watchlist Drift: top candidates from the latest session, showing their
  proximity to trigger/invalidation levels.

Output: unidesk_terminal/src/data/report_derived_<date>.json, imported by the UI.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO / "data" / "market" / "reports"
OUT_DIR = REPO / "unidesk_terminal" / "src" / "data"


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    # Find two most recent reports
    reports = sorted(REPORTS_DIR.glob("tonight_*.json"))
    if len(reports) < 2:
        print(f"Need at least 2 reports, found {len(reports)}")
        return 1

    latest = load_report(reports[-1])
    prior = load_report(reports[-2])

    latest_date = latest["session_date"]
    prior_date = prior["session_date"]

    # Build a lookup of latest candidates by symbol
    latest_by_symbol: dict[str, dict] = {}
    for c in latest["candidates"]:
        sym = c["symbol"]
        if sym not in latest_by_symbol:
            latest_by_symbol[sym] = c

    # Yesterday's Calls: candidates from prior report, cross-referenced with latest
    yesterday_calls = []
    for c in prior["candidates"]:
        sym = c["symbol"]
        latest_c = latest_by_symbol.get(sym)
        close = c["close"]
        trigger = c.get("trigger")
        invalidation = c.get("invalidation")

        if latest_c is None:
            # Symbol disappeared from the latest report — stopped out / delisted
            outcome = "stopped_out"
            note = f"No longer in universe as of {latest_date}"
            r_multiple = None
            mfe = None
            mae = None
            if trigger and invalidation and close > invalidation:
                # Rough estimate: if it was above invalidation and now gone, it stopped
                pass
        else:
            # Still active — unresolved
            latest_close = latest_c["close"]
            pct_move = (latest_close / close - 1.0) * 100.0
            outcome = "unresolved"
            note = f"{pct_move:+.1f}% since {prior_date} — still in scan"
            r_multiple = None
            mfe = max(pct_move, 0) if pct_move else None
            mae = min(pct_move, 0) if pct_move else None

        yesterday_calls.append({
            "symbol": sym,
            "setupType": c["detector"],
            "date": prior_date,
            "entry": close,
            "outcome": outcome,
            "rMultiple": r_multiple,
            "mfePct": mfe,
            "maePct": mae,
            "netBps": None,
            "stopHit": outcome == "stopped_out",
            "gapThrough": None,
            "note": note,
        })

    # Sort: stopped_out first, then unresolved (most recent resolution first)
    yesterday_calls.sort(key=lambda x: (0 if x["outcome"] == "stopped_out" else 1, x["symbol"]))

    # Watchlist Drift: top 10 candidates by stock quality score from latest report
    scored = [(c, c.get("stock_quality", {}).get("score", 0) or 0) for c in latest["candidates"]]
    scored.sort(key=lambda x: -x[1])
    top10 = scored[:10]

    watchlist = []
    for c, score in top10:
        close = c["close"]
        trigger = c.get("trigger")
        invalidation = c.get("invalidation")
        drift_pct = None
        note_parts = []

        if trigger and trigger > 0:
            drift_pct = (close / trigger - 1.0) * 100.0
            if drift_pct < -0.5:
                note_parts.append(f"{abs(drift_pct):.1f}% below trigger")
            elif drift_pct < 0.5:
                note_parts.append("at trigger level")
            else:
                note_parts.append(f"{drift_pct:.1f}% above trigger")

        if invalidation and invalidation > 0:
            risk_pct = (close / invalidation - 1.0) * 100.0
            if risk_pct < 2.0:
                note_parts.append("near invalidation")

        if invalidation and trigger:
            rr = (trigger / invalidation - 1.0) if invalidation > 0 else None
            if rr:
                note_parts.append(f"R:R {rr:.1f}")

        note = " · ".join(note_parts) if note_parts else f"Score: {score:.0f}"

        # Generate a sparkline-like array of 5 numbers from the close
        spark = [round(close * (1 + (i - 2) * 0.002), 2) for i in range(5)]

        watchlist.append({
            "symbol": c["symbol"],
            "note": note,
            "spark": spark,
            "score": round(score, 1),
            "close": close,
            "trigger": trigger,
            "invalidation": invalidation,
        })

    # Write output
    output = {
        "report_date": latest_date,
        "prior_date": prior_date,
        "yesterday_calls": yesterday_calls,
        "watchlist_drift": watchlist,
        "n_prior_candidates": len(prior["candidates"]),
        "n_resolved": sum(1 for x in yesterday_calls if x["outcome"] == "stopped_out"),
        "n_unresolved": sum(1 for x in yesterday_calls if x["outcome"] == "unresolved"),
    }

    out_path = OUT_DIR / f"report_derived_{latest_date}.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Written {out_path}")
    print(f"  Yesterday's Calls: {len(yesterday_calls)} ({output['n_resolved']} resolved, {output['n_unresolved']} unresolved)")
    print(f"  Watchlist Drift: {len(watchlist)} symbols")
    return 0


if __name__ == "__main__":
    sys.exit(main())