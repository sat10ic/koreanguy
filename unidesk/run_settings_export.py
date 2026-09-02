r"""Settings / config / detector-trust export for the terminal (UI_BACKEND_
INTEGRATION_PLAN.md row 6 "Settings" + the per-detector trust flag the
trading-logic audit called for).

Pure READ of committed configuration and code constants. It does NOT touch
the research event store (which is under regeneration by other sessions --
see unidesk/HANDOFF.md -- and must not be written from here), does NOT spawn
a scan, and does NOT run nightly.py (nightly freezes events into the event
store; running it here would collide with those writers).

    & ".venv-orderflow/Scripts/python.exe" unidesk/run_settings_export.py

Writes ``unidesk_terminal/src/data/settings_<report-session>.json`` --
committed build-time snapshot, same convention as ``tonight_<date>.json``
and ``stock_history_<date>.json`` (a static Vite bundle, no runtime fetch).

Every field below is read from its single source of truth (the frozen
config file or the module constant), never typed in by hand, so the
terminal cannot drift from what the backend actually runs (R-F: config,
not code; R-B: code owns numbers).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# The report session the terminal currently shows -- matches the committed
# tonight_<date>.json / stock_history_<date>.json snapshots.
def _newest_session() -> str:
    import json as _json
    data_root = REPO_ROOT / "data" / "market"
    reports = sorted((data_root / "reports").glob("tonight_*.json"))
    for p_ in reversed(reports):
        try:
            raw = _json.loads(p_.read_text(encoding="utf-8"))
        except Exception:
            continue
        if raw.get("session_date"):
            return raw["session_date"]
    raise SystemExit("no reports on disk")


REPORT_SESSION = _newest_session()
OUT_PATH = REPO_ROOT / "unidesk_terminal" / "src" / "data" / f"settings_{REPORT_SESSION}.json"

# Source of truth for the frozen cost model (swing-edges spec §1.4 / D14):
# the committed config file, not a hand copy.
COSTS_YAML = REPO_ROOT / "unidesk" / "config" / "costs.yaml"


def _read_costs_yaml() -> dict:
    """Tiny flat-YAML reader for costs.yaml (it is a flat ``key: value``
    file). Falls back to the dataclass defaults if the file ever moves."""
    out: dict[str, object] = {}
    try:
        for line in COSTS_YAML.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            value = value.strip()
            out[key.strip()] = float(value) if _is_float(value) else value
    except OSError:
        from unidesk.research.costs import CostAssumptions  # noqa: PLC0415
        a = CostAssumptions()
        out = {
            "version": a.version, "brokerage_gst_rt_bps": a.brokerage_gst_rt_bps,
            "stt_rt_bps": a.stt_rt_bps, "exchange_sebi_stamp_rt_bps": a.exchange_sebi_stamp_rt_bps,
            "impact_cap_bps_side": a.impact_cap_bps_side, "impact_coef_bps": a.impact_coef_bps,
            "gap_slippage_bps": a.gap_slippage_bps,
        }
    return out


def _is_float(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def build_settings() -> dict:
    from unidesk.momentum.detectors.trust import (  # noqa: PLC0415
        TRUST_VERSION, detector_trust_map,
    )
    from unidesk.momentum.report import _DETECTOR_TITLES  # noqa: PLC0415
    from unidesk.momentum.universe.gates import (  # noqa: PLC0415
        EXCLUDE_ETF, MIN_AVG_TURNOVER_CR, MIN_PRICE,
    )
    from unidesk.research.costs import COSTS_VERSION  # noqa: PLC0415
    from unidesk.research.event_store import SCHEMA_VERSION  # noqa: PLC0415
    from unidesk.research.labels import OUTCOME_LABELS_VERSION  # noqa: PLC0415

    costs = _read_costs_yaml()
    trust = detector_trust_map()
    return {
        "report_session": REPORT_SESSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "sources": [
            "unidesk/config/costs.yaml (frozen cost model)",
            "unidesk/research/costs.py (COSTS_VERSION)",
            "unidesk/research/labels.py (OUTCOME_LABELS_VERSION)",
            "unidesk/research/event_store.py (SCHEMA_VERSION)",
            "unidesk/momentum/detectors/trust.py (detector trust table)",
            "unidesk/momentum/universe/gates.py (universe gate defaults)",
            "unidesk/momentum/report.py (_DETECTOR_TITLES)",
        ],
        "schema_version": 1,
        "costs": {
            "version": costs.get("version") or COSTS_VERSION,
            "assumptions_bps": costs,
        },
        "labels": {
            "outcome_labels_version": OUTCOME_LABELS_VERSION,
        },
        "research": {
            "schema_version": SCHEMA_VERSION,
        },
        "universe_gates": {
            "min_price_rs": MIN_PRICE,
            "min_avg_turnover_cr": MIN_AVG_TURNOVER_CR,
            "exclude_etf": EXCLUDE_ETF,
        },
        "detector_trust_version": TRUST_VERSION,
        "detectors": [
            {
                "name": name,
                "title": _DETECTOR_TITLES.get(name, name),
                "trust": trust.get(name),
            }
            for name in sorted(trust)
        ],
    }


if __name__ == "__main__":
    data = build_settings()
    OUT_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    blocked = sum(1 for d in data["detectors"] if d["trust"] and not d["trust"]["rankable"])
    print(f"[settings] {len(data['detectors'])} detectors, {blocked} not-rankable, "
          f"costs {data['costs']['version']}, labels {data['labels']['outcome_labels_version']}")
    print(f"[settings] wrote {OUT_PATH}")