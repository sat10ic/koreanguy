"""Export the regime history series for the UI (H1-10, 20-day regime strip).

Reads every real nightly report under data/market/reports/tonight_*.json and
emits one row per session: date, regime label (first word of the report's own
regime_note), and pct_above_ema50. Nothing is classified here -- the UI strip
renders what each night's classifier actually said.

Output: unidesk_terminal/src/data/regime_history.json (build-time snapshot,
same convention as tonight_<date>.json).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
REPORTS = REPO / "data" / "market" / "reports"
OUT = REPO / "unidesk_terminal" / "src" / "data" / "regime_history.json"

if __name__ == "__main__":
    rows = []
    for p in sorted(REPORTS.glob("tonight_*.json")):
        if p.name.endswith(".md"):
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[skip] {p.name}: {exc}", file=sys.stderr)
            continue
        hf = raw.get("honesty_footer", {})
        note = hf.get("regime_note") or ""
        first = note.split()[0] if note.split() else None
        # Only the classifier's own labels count. Batch drivers wrote prose
        # notes ("historical scan (past-month batch)") -- a strip cell for
        # those sessions must read "no classification", not a fake state.
        regime = first if first in ("BULL", "BEAR", "CHOP") else None
        ema21, ema21of = hf.get("above_ema21"), hf.get("above_ema21_of")
        rows.append({
            "date": raw.get("session_date") or p.stem.removeprefix("tonight_"),
            "regime": regime,
            "regime_note": note,
            "regime_built": bool(hf.get("regime_built")),
            "pct_above_ema50": hf.get("pct_above_ema50"),
            # participation fields for real 1D/5D deltas in the UI
            "pct_above_ema21": round(ema21 / ema21of * 100, 2) if (ema21 is not None and ema21of) else None,
            "near_highs_pct": hf.get("breadth", {}).get("near_highs_pct"),
            "near_lows_pct": hf.get("breadth", {}).get("near_lows_pct"),
        })
    rows.sort(key=lambda r: r["date"])

    # H1-10 second column: a REPLAY of the R0 classifier over the breadth
    # series every report already stores (pct_above_ema50). Same
    # deterministic classifier, default thresholds, cold-started at the
    # window start -- so a session with no at-the-time classification still
    # shows what R0 says on real stored inputs. The UI must label this as a
    # replay, never as the classifier's contemporaneous output.
    from unidesk.momentum.regime import RegimeClassifier
    rc = RegimeClassifier()
    for row in rows:
        pct = row.get("pct_above_ema50")
        if pct is None:
            row["regime_replayed"] = None
            continue
        from datetime import date as _date
        out = rc.update(_date.fromisoformat(row["date"]), pct / 100.0)
        row["regime_replayed"] = out.regime.value
    payload = {
        "source": "data/market/reports/tonight_*.json (honesty_footer.regime_note)",
        "generator": "unidesk/run_export_regime_history.py",
        "sessions": rows,
    }
    OUT.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"[export] {len(rows)} sessions -> {OUT}")
