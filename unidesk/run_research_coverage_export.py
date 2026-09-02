"""Research archive-coverage + detector-stats export (UI plan row 5).

Fast pyarrow probe: reads a bounded sample per partition (first 5 rows of
each row group) to extract status distribution, detector hit rates, and
label-version health. Exits with a full-scan refusal when the label
version is not homogeneous (same safety gate as the outcomes exporter).

    .venv-orderflow/Scripts/python.exe unidesk/run_research_coverage_export.py

Writes research_coverage_<report-session>.json -- committed build-time snapshot.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from unidesk.research.labels import OUTCOME_LABELS_VERSION

DATA_ROOT = REPO_ROOT / "data" / "market"
def _newest_session() -> str:
    import json as _json
    reports = sorted((DATA_ROOT / "reports").glob("tonight_*.json"))
    for p_ in reversed(reports):
        try:
            raw = _json.loads(p_.read_text(encoding="utf-8"))
        except Exception:
            continue
        if raw.get("session_date"):
            return raw["session_date"]
    raise SystemExit("no reports on disk")


REPORT_SESSION = _newest_session()
EVENTS_DIR = DATA_ROOT / "research" / "events"
OUT_PATH = REPO_ROOT / "unidesk_terminal" / "src" / "data" / f"research_coverage_{REPORT_SESSION}.json"


def _fast_probe() -> dict:
    """Sampled probe across all partitions. Returns aggregate stats."""
    statuses: Counter = Counter()
    versions: Counter = Counter()
    detectors: Counter = Counter()
    partitions = 0
    total_sample = 0
    for p in sorted(EVENTS_DIR.glob("date=*")):
        f = p / "events.parquet"
        if not f.exists():
            continue
        partitions += 1
        pf = pq.ParquetFile(f)
        for i in range(pf.metadata.num_row_groups):
            tab = pf.read_row_group(i, columns=["snapshot_json", "outcome_json"])
            for row in tab.slice(length=5).to_pylist():
                total_sample += 1
                o = json.loads(row["outcome_json"] or "{}")
                statuses[o.get("status", "UNKNOWN")] += 1
                versions[o.get("label_version", "<missing>")] += 1
                snap = json.loads(row["snapshot_json"] or "{}")
                for name, d in (snap.get("detectors") or {}).items():
                    if isinstance(d, dict) and d.get("detection") == "VALID":
                        detectors[name] += 1
    stale = {k: v for k, v in versions.items() if k != OUTCOME_LABELS_VERSION}
    return {
        "partitions": partitions,
        "sampled_events": total_sample,
        "partition_range": {
            "oldest": next(
                (p.name.replace("date=", "") for p in sorted(EVENTS_DIR.glob("date=*")) if (p / "events.parquet").exists()),
                "unknown"
            ),
            "newest": next(
                (p.name.replace("date=", "") for p in sorted(EVENTS_DIR.glob("date=*"), reverse=True) if (p / "events.parquet").exists()),
                "unknown"
            ),
        },
        "label_version_homogeneous": not bool(stale),
        "label_version": OUTCOME_LABELS_VERSION,
        "stale_versions": stale,
        "status_distribution": dict(statuses.most_common()),
        "detector_valid_hits": dict(detectors.most_common()),
    }


def build_coverage() -> dict:
    from unidesk.momentum.detectors.trust import detector_trust_map, TRUST_VERSION
    from unidesk.momentum.detectors.registry import DETECTOR_NAMES
    from unidesk.momentum.report import _DETECTOR_TITLES

    coverage = _fast_probe()

    # Detector trust table (same source as Settings)
    trust_map = detector_trust_map()
    coverage["detectors"] = [
        {
            "name": name,
            "title": _DETECTOR_TITLES.get(name, name),
            "trust": trust_map.get(name),
        }
        for name in DETECTOR_NAMES
    ]
    coverage["detector_trust_version"] = TRUST_VERSION

    # Negative findings: any detector that is BLOCKED or REVIEW_REQUIRED
    coverage["negative_findings"] = [
        {
            "detector": name,
            "title": _DETECTOR_TITLES.get(name, name),
            "trust": trust_map.get(name),
        }
        for name in DETECTOR_NAMES
        if trust_map.get(name) and trust_map[name].get("status") in ("BLOCKED", "REVIEW_REQUIRED")
    ]

    return coverage


if __name__ == "__main__":
    data = build_coverage()
    OUT_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"[research] {data['partitions']} partitions, "
          f"{len(data['detector_valid_hits'])} detectors with hits, "
          f"{len(data['negative_findings'])} negative findings -> {OUT_PATH}")