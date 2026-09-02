"""Export the owner's broker trade history for the Desk screen (D-10).

Source: legacy/SwingEdge/output/broker_imports/trades_normalized.csv -- the
audited broker tradebook import (935 tradebook rows; see
manas_os/design/reports/BROKER_AUDIT_2026-07-18.md). Copied VERBATIM into a
dedicated UI namespace (src/data/broker/) -- this is a DIFFERENT source from
PART 1 scan data: different grain, different provenance, different trust.
It must never merge into scan output, candidate lists, or the research
archive; run_checks.py's data-authority check still passes because nothing
under data/market/ gains broker fields.

Also emits desk_said.json (D-09): for every report date on disk and every
symbol the owner traded OR the desk flagged, what the desk said that night
(candidate + detector / in-universe / not-in-universe). Derived from the real
tonight_*.json reports; "no report for that session" is the honest fallback
in the UI when a date is absent.

Output:
  unidesk_terminal/src/data/broker/trades.json
  unidesk_terminal/src/data/broker/desk_said.json
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "legacy" / "SwingEdge" / "output" / "broker_imports" / "trades_normalized.csv"
REPORTS = REPO / "data" / "market" / "reports"
OUT_DIR = REPO / "unidesk_terminal" / "src" / "data" / "broker"

TRADE_FIELDS = (
    "trade_date", "symbol", "side", "quantity", "price", "gross_value",
    "net_value", "fees_allocated", "product_type", "exchange",
)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    trades = []
    with SRC.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            trades.append({k: row[k] for k in TRADE_FIELDS})
    (OUT_DIR / "trades.json").write_text(
        json.dumps({
            "source": str(SRC.relative_to(REPO)).replace("\\", "/"),
            "provenance": "audited broker tradebook import (BROKER_AUDIT_2026-07-18.md); "
                          "distinct source from scan data -- never merged into PART 1 stores",
            "generator": "unidesk/run_export_broker_trades.py",
            "count": len(trades),
            "trades": trades,
        }, indent=1),
        encoding="utf-8",
    )
    print(f"[export] {len(trades)} broker trades -> trades.json")

    traded_symbols = sorted({t["symbol"] for t in trades})
    desk_said = {}
    for p in sorted(REPORTS.glob("tonight_*.json")):
        if p.suffix != ".json":
            continue
        try:
            raw = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        hf = raw.get("honesty_footer", {})
        universe = set(hf.get("universe_symbols") or [])
        # Older snapshots predate universe_symbols: fall back to the scan's
        # own candidate symbols + a scanned-count disclosure. Membership for
        # non-candidates is then unknown -- the UI must not claim
        # "in-universe" for those, and the entry carries universe_known=false.
        universe_known = bool(universe)
        cands = {c["symbol"]: c.get("detector") for c in raw.get("candidates", [])}
        watch = universe | set(cands) | (set(traded_symbols) if not universe_known else set())
        entry = {
            "universe_known": universe_known,
            "universe_count": hf.get("universe_scanned"),
            "candidates": {s: cands[s] for s in sorted(set(cands) & watch)},
            "in_universe": sorted(s for s in watch if s in universe and s not in cands),
        }
        desk_said[raw.get("session_date") or p.stem.removeprefix("tonight_")] = entry
    (OUT_DIR / "desk_said.json").write_text(
        json.dumps({
            "source": "data/market/reports/tonight_*.json",
            "generator": "unidesk/run_export_broker_trades.py",
            "sessions": desk_said,
        }, indent=0),
        encoding="utf-8",
    )
    print(f"[export] {len(desk_said)} sessions -> desk_said.json")


if __name__ == "__main__":
    main()
