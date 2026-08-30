"""P2.3 gold-fixture harvest and load.

Fixtures freeze real, point-in-time detector inputs (symbol + session +
computed features) plus the expected VALID/INVALID result. Tests replay the
frozen inputs through the detectors — they do not re-ingest the 646k-bar
store. Re-harvesting is an explicit maintenance step when feature math or
thresholds change.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from unidesk.momentum.detectors.momentum_burst import Detection
from unidesk.momentum.detectors.registry import DETECTOR_NAMES, evaluate_detector

UTC = timezone.utc
FIXTURE_PATH = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "p2_3_gold.json"
)
POSITIVES_PER = 2
NEGATIVES_PER = 2
MAX_NEGATIVE_FAILURES = 3


def load_gold_fixtures(path: Optional[Path] = None) -> dict:
    target = path or FIXTURE_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def replay_case(case: dict) -> tuple[Detection, tuple]:
    det, failures = evaluate_detector(case["detector"], case["inputs"])
    return det, failures


def _pick_cases(rows: list[dict], *, positives_per: int, negatives_per: int) -> list[dict]:
    """Pick up to N VALID and N near-miss INVALID rows per detector."""
    by_det: dict[str, list] = {n: [] for n in DETECTOR_NAMES}
    for row in rows:
        by_det[row["detector"]].append(row)
    picked: list[dict] = []
    for name in DETECTOR_NAMES:
        group = by_det[name]
        valids = [r for r in group if r["expected"] == "VALID"]
        invalids = [
            r for r in group
            if r["expected"] == "INVALID"
            and 1 <= len(r["expected_failures"]) <= MAX_NEGATIVE_FAILURES
        ]
        for r in valids[:positives_per]:
            picked.append(r)
        for r in invalids[:negatives_per]:
            picked.append(r)
    return picked


def harvest(
    store,
    as_of: datetime,
    *,
    min_sessions: int = 61,
    positives_per: int = POSITIVES_PER,
    negatives_per: int = NEGATIVES_PER,
) -> dict:
    """Scan the store at ``as_of`` and freeze one gold document.

    Relies on ``scan_universe`` so RS ranks and publication-time filtering
    match the nightly pipeline exactly.
    """
    from unidesk.momentum.scan import scan_universe

    result = scan_universe(store, as_of, min_sessions=min_sessions)
    rows: list[dict] = []
    session = result.last_session or as_of.date().isoformat()
    for scan in result.symbols:
        inputs = scan.setup_inputs or {}
        if not inputs:
            continue
        for name, (det, failures) in scan.detectors.items():
            if det is Detection.INSUFFICIENT_DATA:
                continue
            rows.append({
                "id": f"{name}-{'pos' if det is Detection.VALID else 'neg'}-{scan.symbol}-{session}",
                "detector": name,
                "polarity": "positive" if det is Detection.VALID else "negative",
                "symbol": scan.symbol,
                "session": session,
                "inputs": inputs,
                "expected": det.value,
                "expected_failures": list(failures),
            })
    cases = _pick_cases(rows, positives_per=positives_per, negatives_per=negatives_per)
    coverage = {
        name: {
            "positives": sum(1 for c in cases if c["detector"] == name and c["polarity"] == "positive"),
            "negatives": sum(1 for c in cases if c["detector"] == name and c["polarity"] == "negative"),
        }
        for name in DETECTOR_NAMES
    }
    return {
        "schema_version": 1,
        "as_of": session,
        "source": (
            "NSE bhavcopy EQ series, point-in-time scan; listing_age_sessions "
            "is store-length proxy (no listing calendar); avwap_extension_adr "
            "is None (no EOD AVWAP anchor); rs_improving is own 20d-return "
            "improvement, not cross-sectional rank change."
        ),
        "scanned": result.scanned,
        "coverage": coverage,
        "cases": cases,
    }


def write_gold_fixtures(doc: dict, path: Optional[Path] = None) -> Path:
    target = path or FIXTURE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(doc, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return target


def _merge_harvests(docs: list[dict]) -> dict:
    """Keep the first positives/negatives seen per detector across dates."""
    buckets: dict[str, dict[str, list]] = {
        n: {"positive": [], "negative": []} for n in DETECTOR_NAMES
    }
    scanned = 0
    as_ofs = []
    for doc in docs:
        scanned += doc.get("scanned", 0)
        as_ofs.append(doc["as_of"])
        for case in doc["cases"]:
            pol = case["polarity"]
            held = buckets[case["detector"]][pol]
            if len(held) < (POSITIVES_PER if pol == "positive" else NEGATIVES_PER):
                if all(h["id"] != case["id"] for h in held):
                    held.append(case)
    cases = []
    for name in DETECTOR_NAMES:
        cases.extend(buckets[name]["positive"])
        cases.extend(buckets[name]["negative"])
    coverage = {
        name: {
            "positives": len(buckets[name]["positive"]),
            "negatives": len(buckets[name]["negative"]),
        }
        for name in DETECTOR_NAMES
    }
    return {
        "schema_version": 1,
        "as_of": ",".join(as_ofs),
        "source": docs[0]["source"] if docs else "",
        "scanned": scanned,
        "coverage": coverage,
        "cases": cases,
    }


if __name__ == "__main__":
    from datetime import datetime, timezone
    from pathlib import Path
    from unidesk.momentum.data.bhavcopy import ingest_directory
    from unidesk.momentum.data.market_store import InMemoryMarketStore

    backlog = Path(__file__).resolve().parents[3] / "bhavcopy_extractor" / "data" / "bhavcopy"
    store = InMemoryMarketStore()
    stats = ingest_directory(store, backlog)
    print("ingest", stats, flush=True)
    dates = [
        datetime(2026, 6, 30, 18, 30, tzinfo=timezone.utc),
        datetime(2026, 7, 3, 18, 30, tzinfo=timezone.utc),
        datetime(2026, 5, 15, 18, 30, tzinfo=timezone.utc),
        datetime(2026, 4, 2, 18, 30, tzinfo=timezone.utc),
        datetime(2025, 11, 14, 18, 30, tzinfo=timezone.utc),
    ]
    docs = []
    for as_of in dates:
        doc = harvest(store, as_of)
        print("harvest", as_of.date(), "scanned", doc["scanned"],
              "coverage", doc["coverage"], flush=True)
        docs.append(doc)
    merged = _merge_harvests(docs)
    path = write_gold_fixtures(merged)
    print("wrote", path, "cases", len(merged["cases"]),
          "coverage", merged["coverage"], flush=True)
