"""Re-harvest one genuine base_breakout POSITIVE case under the corrected
room rule (2026-08-30) and append it to the gold fixture.

READ-ONLY over market data: ingests the D15 bhavcopy archive into an
in-memory store and runs scan_universe — writes NOTHING to the research
event store (which is under concurrent regeneration; see unidesk/HANDOFF.md).
The only file written is the gold fixture JSON itself.

The old fixture's single base_breakout positive (FILATEX) was a mislabel
produced by the inverted room rule (8.46 ADR underwater passed as a
breakout). Under the corrected ``overhead_room_adr <= max_room_adr`` rule
that case is INVALID, so the fixture needs a real positive harvested with
the fixed logic — otherwise the coverage gate (positives >= 1) fails.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from unidesk.momentum.data.bhavcopy import ingest_directory  # noqa: E402
from unidesk.momentum.data.market_store import InMemoryMarketStore  # noqa: E402
from unidesk.momentum.detectors.gold import (  # noqa: E402
    FIXTURE_PATH, evaluate_detector, load_gold_fixtures,
)
from unidesk.momentum.scan import scan_universe  # noqa: E402

BACKLOG = REPO_ROOT / "data" / "bhavcopy"
# Scan dates spread across the archive; the first date that yields a genuine
# corrected-rule positive wins.
DATES = [
    datetime(2026, 8, 28, 18, 30, tzinfo=timezone.utc),
    datetime(2026, 8, 20, 18, 30, tzinfo=timezone.utc),
    datetime(2026, 8, 10, 18, 30, tzinfo=timezone.utc),
    datetime(2026, 7, 3, 18, 30, tzinfo=timezone.utc),
]
# A genuine positive must clear the pivot with LIMITED overhead room: prefer
# blue_sky, else overhead_room_adr <= 0.5 ADR (well inside the 1.0 rule limit).
MAX_ROOM_FOR_PICK = 0.5
CANDIDATE_FIELDS = (
    "gap_pct", "rvol", "close_location", "delivery_ratio", "listing_age_sessions",
    "base_depth_pct", "contraction_ratio", "rs_rank", "distance_from_listing_high_pct",
    "is_inside_bar", "mother_range_pct", "volume_ratio_bar_to_mother",
    "breakout_rvol", "pre_breakout_pivot", "close_cleared_pivot",
    "base_breakout_depth_pct", "base_breakout_contraction_ratio",
    "blue_sky", "overhead_room_adr", "room_adr", "proximity_to_anchor_pct",
    "pullback_signed_anchor_pct", "pullback_from_high_pct",
    "pullback_volume_ratio", "adr_pct", "reclaimed", "volume_expansion",
    "rs_improving", "failed_breakdown", "avwap_extension_adr",
)


def main() -> int:
    store = InMemoryMarketStore()
    stats = ingest_directory(store, BACKLOG)
    print(f"[reharvest] ingested {stats}", flush=True)
    for as_of in DATES:
        result = scan_universe(store, as_of, apply_universe_gates=True)
        print(f"[reharvest] scan {as_of.date()} scanned={result.scanned}", flush=True)
        for s in result.symbols:
            det, det_inputs = s.detectors.get("base_breakout", (None, None))
            if det is None or det.value != "VALID":
                continue
            room = det_inputs and None
            # Prefer blue_sky or small overhead room so the harvested positive
            # is unambiguous under the corrected rule.
            inputs = s.setup_inputs
            blue = inputs.get("blue_sky")
            room_val = inputs.get("overhead_room_adr")
            if blue is not True and (room_val is None or room_val > MAX_ROOM_FOR_PICK):
                continue
            case = {
                "id": f"base_breakout-pos-{s.symbol}-{as_of.date().isoformat()}",
                "detector": "base_breakout",
                "polarity": "positive",
                "symbol": s.symbol,
                "session": as_of.date().isoformat(),
                "inputs": {k: inputs.get(k) for k in CANDIDATE_FIELDS},
                "expected": "VALID",
                "expected_failures": [],
                "note": (
                    "Harvested 2026-08-30 under the corrected room rule "
                    f"(blue_sky={blue}, overhead_room_adr={room_val}); "
                    "replaces the FILATEX mislabel produced by the inverted rule."
                ),
            }
            # Verify the case replays to VALID through the fixture machinery.
            replay_det, replay_failures = evaluate_detector("base_breakout", case["inputs"])
            if replay_det.value != "VALID":
                print(f"[reharvest] skip {s.symbol}: replay gave {replay_det.value} {replay_failures}", flush=True)
                continue
            doc = load_gold_fixtures()
            doc["cases"] = [c for c in doc["cases"] if c["id"] != case["id"]]
            doc["cases"].append(case)
            doc["coverage"]["base_breakout"]["positives"] = 1
            doc["source"] = doc["source"].replace(
                "; a genuine positive pending re-harvest under the fixed rule.",
                f"; genuine positive re-harvested {as_of.date()} ({s.symbol}, "
                f"blue_sky={blue}, room={room_val}).",
            )
            FIXTURE_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            print(f"[reharvest] wrote positive case {case['id']} -> {FIXTURE_PATH}", flush=True)
            return 0
    print("[reharvest] no genuine corrected-rule positive found on any date", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())