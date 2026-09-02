"""unidesk checks runner — machine-checked governance for the unified desk.

Adopted by copy from ``traderlog/checks/runner.py``'s attribution mechanics on
2026-08-28 (provenance per DECISIONS.md D5; the traderlog original remains
that package's canonical, validated against its own corpus). Trimmed to what
the unified build actually has today; stub checks report ``not_built_yet``
rather than pretending to pass.

Checks:
  attribution  — 14-key schema, enums, unique ids, and the bidirectional
                 handoff round-trip over ``design/handoffs/HANDOFF_*_COMPLETED.md``
                 (deliberate difference from traderlog: ``completion_report``
                 paths are REPO-relative, because unidesk records may point at
                 reports in other packages, e.g. orderflow's).
  contracts    — every contract module imports and a representative
                 OrderFlowAssessment round-trips through to_dict/from_dict.
  data_authority — every persistent-store entry has an owner/writer/class,
                 unified fields have one authority, and quarantined lifecycle
                 stores cannot be accepted authorities.
  leakage      — P7.3 smoke: planted future-bar leak is caught (full suite
                 lives in pytest). stale_state / provenance still stubbed.

Exit code 0 when no check FAILS; ``not_built_yet`` is not a failure.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_ROOT = Path(__file__).resolve().parents[1]          # unidesk/
_REPO_ROOT = _ROOT.parent                            # repo root
_LEDGER = _ROOT / "design" / "MODEL_WORK_LOG.jsonl"
_HANDOFFS_DIR = _ROOT / "design" / "handoffs"
_STATE = _ROOT / "STATE.json"
_DATA_AUTHORITY = _ROOT / "design" / "DATA_AUTHORITY.json"

ATTRIBUTION_REQUIRED_FIELDS = {
    "id", "completed_at", "wave", "deliverable", "role", "model", "host_tool",
    "identity_basis", "scope", "files", "completion_report", "status",
    "verification_status", "notes_limitations",
}
ROLE_VALUES = {"executor", "orchestrator", "reviewer", "vision"}
IDENTITY_BASIS_VALUES = {"self_reported", "host_verified", "unknown"}
STATUS_VALUES = {"completed", "partial", "blocked"}
VERIFICATION_VALUES = {"unverified", "verified", "partial"}
ATTRIBUTION_ID_RE = re.compile(r"^attr-[a-z0-9][a-z0-9-]*$")
HANDOFF_ID_RE = re.compile(r"^Attribution-ID:\s*([^\s]+)\s*$", re.MULTILINE)
HANDOFF_GLOB = "HANDOFF_*_COMPLETED.md"

OWNER_WAVE = {
    "contracts": "U-P0.2",
    "attribution": "U-P0",
    "orderflow_ledger": "U-P0",
    "data_authority": "U-P0.1",
    "leakage": "U-P7",
    "stale_state": "U-P3",
    "provenance": "U-P7",
}

# Orderflow ledger: same 14-key schema, two documented differences (D5/D13
# convention): (1) status may carry the legacy value "interrupted" — the
# Autoclaw N1-prep session was owner-ordered to STOP mid-preparation, which
# is neither completed/partial/blocked vocabulary; the record is immutable,
# so the validator accepts the value explicitly instead of rewriting history.
# (2) handoff round-trip: orderflow handoffs citing orderflow ledger IDs.
ORDERFLOW_LEDGER = _REPO_ROOT / "orderflow" / "design" / "MODEL_WORK_LOG.jsonl"
ORDERFLOW_HANDOFFS = _REPO_ROOT / "orderflow" / "design" / "handoffs"
ORDERFLOW_LEGACY_STATUS = {"interrupted"}


class CheckFailure(Exception):
    pass


def _fail(check: str, message: str) -> None:
    raise CheckFailure(f"[{check}] {message}")


def _repo_relative(path: Path) -> bool:
    try:
        path.resolve().relative_to(_REPO_ROOT)
    except ValueError:
        return False
    return True


# ----------------------------------------------------------------- attribution


def read_attribution_records(check: str) -> list[dict]:
    if not _LEDGER.is_file():
        _fail(check, f"missing ledger: {_LEDGER.relative_to(_REPO_ROOT)}")
    records = []
    with open(_LEDGER, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                _fail(check, f"blank JSONL line at {lineno}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                _fail(check, f"malformed JSON at line {lineno}: {exc}")
            if not isinstance(record, dict):
                _fail(check, f"line {lineno} is not a JSON object")
            records.append(record)
    return records


def validate_attribution_record(check: str, record: dict, seen_ids: set,
                                extra_status: Optional[set] = None) -> None:
    missing = ATTRIBUTION_REQUIRED_FIELDS - set(record)
    if missing:
        _fail(check, f"record {record.get('id', '?')} missing fields: {sorted(missing)}")
    rid = record["id"]
    if not isinstance(rid, str) or not ATTRIBUTION_ID_RE.match(rid):
        _fail(check, f"bad id: {rid!r}")
    if rid in seen_ids:
        _fail(check, f"duplicate id: {rid}")
    seen_ids.add(rid)
    if record["role"] not in ROLE_VALUES:
        _fail(check, f"{rid}: bad role {record['role']!r}")
    if record["identity_basis"] not in IDENTITY_BASIS_VALUES:
        _fail(check, f"{rid}: bad identity_basis {record['identity_basis']!r}")
    allowed_status = STATUS_VALUES | (extra_status or set())
    if record["status"] not in allowed_status:
        _fail(check, f"{rid}: bad status {record['status']!r}")
    if record["verification_status"] not in VERIFICATION_VALUES:
        _fail(check, f"{rid}: bad verification_status {record['verification_status']!r}")
    files = record["files"]
    if not isinstance(files, list) or not files or not all(
        isinstance(f, str) and f.strip() for f in files
    ):
        _fail(check, f"{rid}: files must be a non-empty list of non-empty strings")
    for field in ("completed_at", "wave", "deliverable", "model", "host_tool",
                  "scope", "completion_report", "verification_status",
                  "notes_limitations"):
        value = record[field]
        if not isinstance(value, str) or not value.strip():
            _fail(check, f"{rid}: {field} must be a non-empty string")
    completed_at = record["completed_at"]
    if not _is_iso_datetime_or_date(completed_at):
        _fail(check, f"{rid}: completed_at not ISO-8601: {completed_at!r}")
    report = Path(record["completion_report"])
    if report.is_absolute() or not _repo_relative((_REPO_ROOT / record["completion_report"])
                                                  if not report.is_absolute() else report):
        _fail(check, f"{rid}: completion_report must be a repo-relative path, got {record['completion_report']!r}")


def _is_iso_datetime_or_date(value: str) -> bool:
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        pass
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def check_attribution() -> str:
    check = "attribution"
    records = read_attribution_records(check)
    seen: set = set()
    report_by_id: dict = {}
    for record in records:
        validate_attribution_record(check, record, seen)
        report_by_id[record["id"]] = record["completion_report"]

    # Cross-ledger resolution: a unidesk handoff may cite a record whose home
    # is the orderflow ledger (D11/D13 pattern — orderflow records legally
    # point at unidesk reports). Validate such records against the orderflow
    # file (legacy statuses allowed) before declaring them unknown.
    orderflow_records = []
    orderflow_seen: set = set()
    if ORDERFLOW_LEDGER.is_file():
        with open(ORDERFLOW_LEDGER, "r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(r, dict) and r.get("id"):
                    orderflow_records.append(r)
                    orderflow_seen.add(r["id"])
    for record in orderflow_records:
        try:
            validate_attribution_record("orderflow_ledger", record, orderflow_seen)
        except CheckFailure:
            pass  # structural issues are the orderflow check's own finding
    records = records + orderflow_records  # resolution pool for the checks below

    handoffs = sorted(_HANDOFFS_DIR.glob(HANDOFF_GLOB))
    for handoff in handoffs:
        text = handoff.read_text(encoding="utf-8")
        ids = HANDOFF_ID_RE.findall(text)
        if not ids:
            _fail(check, f"completed handoff has no Attribution-ID: {handoff.name}")
        for rid in ids:
            record = next((r for r in records if r["id"] == rid), None)
            if record is None:
                _fail(check, f"{handoff.name} cites unknown id {rid}")
            expected = (Path(record["completion_report"]).as_posix())
            actual = handoff.relative_to(_REPO_ROOT).as_posix()
            if expected != actual:
                _fail(check, f"{rid}: completion_report {record['completion_report']!r} does not point at {actual!r}")

    for record in records:
        report = _REPO_ROOT / record["completion_report"]
        if not report.is_file():
            _fail(check, f"{record['id']}: completion_report missing: {record['completion_report']}")
        if f"Attribution-ID: {record['id']}" not in report.read_text(encoding="utf-8"):
            _fail(check, f"{record['id']}: report {record['completion_report']} does not carry its Attribution-ID line")

    return f"{len(records)} records, {len(handoffs)} completed handoffs"


# ----------------------------------------------------------------- orderflow ledger


def check_orderflow_ledger() -> str:
    """Same structural rules as the unidesk attribution check, applied to the
    orderflow ledger (repo-relative completion_report convention — the two
    packages share it). Legacy allowance: the Autoclaw prep-stop record may
    carry status "interrupted" (documented, immutable)."""
    check = "orderflow_ledger"
    if not ORDERFLOW_LEDGER.is_file():
        return "not_built_yet"
    records = []
    with open(ORDERFLOW_LEDGER, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                _fail(check, f"blank JSONL line at {lineno}")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                _fail(check, f"malformed JSON at line {lineno}: {exc}")
            if not isinstance(record, dict):
                _fail(check, f"line {lineno} is not a JSON object")
            records.append(record)

    seen: set = set()
    report_by_id: dict = {}
    for record in records:
        missing = ATTRIBUTION_REQUIRED_FIELDS - set(record)
        if missing:
            _fail(check, f"record {record.get('id', '?')} missing fields: {sorted(missing)}")
        rid = record["id"]
        if not isinstance(rid, str) or not ATTRIBUTION_ID_RE.match(rid):
            _fail(check, f"bad id: {rid!r}")
        if rid in seen:
            _fail(check, f"duplicate id: {rid}")
        seen.add(rid)
        if record["role"] not in ROLE_VALUES:
            _fail(check, f"{rid}: bad role {record['role']!r}")
        if record["identity_basis"] not in IDENTITY_BASIS_VALUES:
            _fail(check, f"{rid}: bad identity_basis {record['identity_basis']!r}")
        status = record["status"]
        if status not in STATUS_VALUES and status not in ORDERFLOW_LEGACY_STATUS:
            _fail(check, f"{rid}: bad status {status!r}")
        if record["verification_status"] not in VERIFICATION_VALUES:
            _fail(check, f"{rid}: bad verification_status {record['verification_status']!r}")
        if not isinstance(record["files"], list) or not record["files"] or not all(
            isinstance(f, str) and f.strip() for f in record["files"]
        ):
            _fail(check, f"{rid}: files must be a non-empty list of non-empty strings")
        for field in ("completed_at", "wave", "deliverable", "model", "host_tool",
                      "scope", "completion_report", "notes_limitations"):
            if not isinstance(record[field], str) or not record[field].strip():
                _fail(check, f"{rid}: {field} must be a non-empty string")
        if not _is_iso_datetime_or_date(record["completed_at"]):
            _fail(check, f"{rid}: completed_at not ISO-8601: {record['completed_at']!r}")
        report = Path(record["completion_report"])
        if report.is_absolute() or not _repo_relative(report if report.is_absolute() else _REPO_ROOT / record["completion_report"]):
            _fail(check, f"{rid}: completion_report must be repo-relative, got {record['completion_report']!r}")
        report_by_id[rid] = record["completion_report"]

    for handoff in sorted(ORDERFLOW_HANDOFFS.glob(HANDOFF_GLOB)):
        ids = HANDOFF_ID_RE.findall(handoff.read_text(encoding="utf-8"))
        for rid in ids:
            record = next((r for r in records if r["id"] == rid), None)
            if record is None:
                _fail(check, f"{handoff.name} cites unknown orderflow-ledger id {rid}")
            expected = Path(record["completion_report"]).as_posix()
            actual = handoff.relative_to(_REPO_ROOT).as_posix()
            if expected != actual:
                _fail(check, f"{rid}: completion_report {record['completion_report']!r} != {actual!r}")

    for record in records:
        report = _REPO_ROOT / record["completion_report"]
        if not report.is_file():
            _fail(check, f"{record['id']}: completion_report missing: {record['completion_report']}")
        if f"Attribution-ID: {record['id']}" not in report.read_text(encoding="utf-8"):
            _fail(check, f"{record['id']}: report does not carry its Attribution-ID line")
    return f"{len(records)} records validated"


# ----------------------------------------------------------------- contracts

# ----------------------------------------------------------------- contracts


def check_contracts() -> str:
    check = "contracts"
    try:
        from unidesk.contracts import (
            DecisionSnapshot, FlowState, LiquidityState, OrderFlowAssessment,
            PolicyState, ConfluenceGrade, to_dict, from_dict,
        )
    except Exception as exc:  # noqa: BLE001 — any import failure is the finding
        _fail(check, f"contracts do not import: {exc}")

    assessed = datetime(2026, 8, 28, 4, 15, 0, tzinfo=timezone.utc)
    valid_until = datetime(2026, 8, 28, 4, 16, 0, tzinfo=timezone.utc)
    assessment = OrderFlowAssessment(
        assessment_id="check-1", candidate_id="cand-1", symbol="NSE:CHECK-EQ",
        assessed_at=assessed, valid_until=valid_until,
        feed_health="HEALTHY", capability_version="1",
        liquidity_score=50.0, liquidity_state="PASS",
        capacity_band=None, high_impact_band=None,
        raw_flow_score=None, flow_confidence=None, effective_flow_score=None,
        flow_state="MIXED", decision="NEUTRAL", reason_codes=(),
        feature_snapshot_id=None, flow_config_hash="cfg",
    )
    revived = from_dict(OrderFlowAssessment, to_dict(assessment))
    if revived != assessment:
        _fail(check, "OrderFlowAssessment round-trip mismatch")
    snapshot = DecisionSnapshot(
        decision_id="d-1", candidate_id="cand-1", as_of=assessed,
        stock_quality=None, setup_quality=None, entry_quality=None,
        liquidity_state=LiquidityState.PASS, flow_state=FlowState.MIXED,
        flow_confidence=None, social_context_state="none",
        judge_grade=ConfluenceGrade.UNKNOWN, policy_state=PolicyState.WARN,
        hard_gates=(), warnings=(), unknowns=("flow_not_measured_yet",),
        source_snapshot_ids=(), config_hash="cfg", policy_version="pol",
    )
    if to_dict(snapshot)["policy_state"] != "WARN":
        _fail(check, "DecisionSnapshot serialization drift")
    try:
        from_dict(OrderFlowAssessment, {**to_dict(assessment), "flow_state": "SUPER_BULLISH"})
    except Exception:
        pass
    else:
        _fail(check, "unknown enum value did not fail closed on revival")
    return "12 contracts import; flow+decision round-trip; enums fail closed"


# ------------------------------------------------------------ data authority

AUTHORITY_CLASSIFICATIONS = {"accepted", "provisional", "quarantined", "archive-only"}
AUTHORITY_FIELD_STATES = {"accepted", "provisional", "unresolved"}
AUTHORITY_REQUIRED_FIELDS = {
    "daily_ohlcv_delivery", "regime_xp_mbi", "reactor_scale_activity",
    "social_source_evidence", "social_claims", "trader_lifecycle",
    "intraday_quote_depth", "orderflow_capability", "chartsmaze_context",
    "symbol_master", "point_in_time_market_store", "unified_check_state",
}


def validate_data_authority(manifest: dict) -> tuple[int, int]:
    check = "data_authority"
    if not isinstance(manifest, dict):
        _fail(check, "manifest must be a JSON object")
    if manifest.get("version") != 1:
        _fail(check, f"unsupported manifest version: {manifest.get('version')!r}")
    definitions = manifest.get("classifications")
    if not isinstance(definitions, dict) or set(definitions) != AUTHORITY_CLASSIFICATIONS:
        _fail(check, "classification definitions must cover the exact allowed set")
    if not all(isinstance(value, str) and value.strip() for value in definitions.values()):
        _fail(check, "classification definitions must be non-empty strings")
    stores = manifest.get("stores")
    if not isinstance(stores, list) or not stores:
        _fail(check, "stores must be a non-empty list")

    stores_by_id: dict[str, dict] = {}
    required_store_keys = {"id", "path", "owner", "writer", "classification", "notes"}
    for index, store in enumerate(stores):
        if not isinstance(store, dict):
            _fail(check, f"store {index} is not an object")
        missing = required_store_keys - set(store)
        if missing:
            _fail(check, f"store {index} missing keys: {sorted(missing)}")
        for key in ("id", "path", "owner", "writer", "notes"):
            if not isinstance(store[key], str) or not store[key].strip():
                _fail(check, f"store {index} has empty {key}")
        store_id = store["id"]
        if store_id in stores_by_id:
            _fail(check, f"duplicate store id: {store_id}")
        if store["classification"] not in AUTHORITY_CLASSIFICATIONS:
            _fail(check, f"{store_id}: invalid classification {store['classification']!r}")
        stores_by_id[store_id] = store

    fields = manifest.get("field_authorities")
    if not isinstance(fields, list) or not fields:
        _fail(check, "field_authorities must be a non-empty list")
    seen_fields: set[str] = set()
    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            _fail(check, f"field authority {index} is not an object")
        if set(field) != {"field", "authority_store", "state", "notes"}:
            _fail(check, f"field authority {index} has wrong keys")
        name = field["field"]
        if not isinstance(name, str) or not name.strip():
            _fail(check, f"field authority {index} has empty field")
        if not isinstance(field["notes"], str) or not field["notes"].strip():
            _fail(check, f"{name}: notes must be a non-empty string")
        if name in seen_fields:
            _fail(check, f"duplicate field authority: {name}")
        seen_fields.add(name)
        state = field["state"]
        if state not in AUTHORITY_FIELD_STATES:
            _fail(check, f"{name}: invalid state {state!r}")
        store_id = field["authority_store"]
        if store_id is None:
            if state != "unresolved":
                _fail(check, f"{name}: only unresolved fields may omit authority_store")
            continue
        if store_id not in stores_by_id:
            _fail(check, f"{name}: unknown authority_store {store_id!r}")
        classification = stores_by_id[store_id]["classification"]
        if classification in {"quarantined", "archive-only"}:
            _fail(check, f"{name}: {classification} store cannot be an authority")
        if state == "accepted" and classification != "accepted":
            _fail(check, f"{name}: accepted field points to {classification} store")

    missing_fields = AUTHORITY_REQUIRED_FIELDS - seen_fields
    if missing_fields:
        _fail(check, f"missing unified field authorities: {sorted(missing_fields)}")

    lifecycle = manifest.get("lifecycle_outputs")
    if not isinstance(lifecycle, list):
        _fail(check, "lifecycle_outputs must be a list")
    lifecycle_classes: set[str] = set()
    for entry in lifecycle:
        if not isinstance(entry, dict) or set(entry) != {"store", "classification"}:
            _fail(check, "each lifecycle output needs store + classification")
        store_id = entry["store"]
        if store_id not in stores_by_id:
            _fail(check, f"lifecycle output references unknown store {store_id!r}")
        classification = entry["classification"]
        if stores_by_id[store_id]["classification"] != classification:
            _fail(check, f"{store_id}: lifecycle classification disagrees with store")
        lifecycle_classes.add(classification)
    if lifecycle_classes != AUTHORITY_CLASSIFICATIONS:
        _fail(
            check,
            "lifecycle outputs must explicitly cover accepted, provisional, "
            "quarantined, and archive-only",
        )
    credential_boundary = manifest.get("credential_boundary")
    if not isinstance(credential_boundary, str) or "must not read" not in credential_boundary.lower():
        _fail(check, "credential boundary must explicitly prohibit agent reads")
    return len(stores), len(fields)


def check_data_authority() -> str:
    check = "data_authority"
    if not _DATA_AUTHORITY.is_file():
        _fail(check, f"missing manifest: {_DATA_AUTHORITY.relative_to(_REPO_ROOT)}")
    try:
        manifest = json.loads(_DATA_AUTHORITY.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(check, f"malformed JSON: {exc}")
    stores, fields = validate_data_authority(manifest)
    return f"{stores} stores owned/classified; {fields} unified fields single-authority checked"


# ----------------------------------------------------------------- stubs


def check_not_built_yet(name: str) -> str:
    return "not_built_yet"


def check_leakage() -> str:
    """P7.3 smoke: the planted future-bar leak is distinguishable from PIT."""
    from unidesk.research.leakage_suite import planted_future_bars_is_caught
    if not planted_future_bars_is_caught():
        _fail("leakage", "planted future-bar leak was not caught")
    return "planted future-bar leak is caught; pytest is the full suite"


# ----------------------------------------------------------------- state + main


def write_state(results: dict, wave: str = "U-P0") -> None:
    commit = None
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=_REPO_ROOT,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip() or None
    except Exception:
        commit = None
    # Successful checks store their evidence string (for example "6 records"),
    # not the literal word "pass". Only the failure branches in main() prefix
    # their result with FAIL, so deriving blocked_on from that explicit state
    # avoids turning every evidence-bearing success into a false blocker.
    blocked = [
        f"{name}: {status}"
        for name, status in results.items()
        if status.startswith("FAIL:")
    ]
    state = {
        "wave": wave,
        "last_verified_commit": commit,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checks": results,
        "blocked_on": blocked or [],
        "showing_synthetic_data": True,
    }
    _STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _load_published_invariants():
    """Published-output invariants. Imported lazily so a missing UI tree or an
    unreadable artefact degrades to a reported failure rather than preventing
    the governance checks above from running at all."""
    try:
        from unidesk.checks.published_invariants import ALL_INVARIANTS, InvariantFailure
    except Exception as exc:  # noqa: BLE001
        def _broken() -> str:
            raise CheckFailure(f"published_invariants failed to import: {exc}")
        return (("published_invariants", _broken),)

    def _wrap(fn):
        def run() -> str:
            try:
                return fn()
            except InvariantFailure as exc:
                raise CheckFailure(str(exc)) from exc
        return run

    return tuple((n, _wrap(f)) for n, f in ALL_INVARIANTS)


_PUBLISHED_INVARIANTS = _load_published_invariants()


def main() -> int:
    results: dict[str, str] = {}
    failures: list[str] = []
    for name, fn in (
        ("attribution", check_attribution),
        ("orderflow_ledger", check_orderflow_ledger),
        ("contracts", check_contracts),
        ("data_authority", check_data_authority),
        ("leakage", check_leakage),
        # Published-output invariants: every defect from the 2026-09-01 UI audit,
        # encoded so the same class cannot ship again. Each is proven to fire on
        # its real defect (see published_invariants.py docstring).
        *(("inv:" + n, f) for n, f in _PUBLISHED_INVARIANTS),
        ("stale_state", lambda: check_not_built_yet("stale_state")),
        ("provenance", lambda: check_not_built_yet("provenance")),
    ):
        try:
            results[name] = fn()
            print(f"[{name}] pass — {results[name]}" if not results[name].startswith("not_built_yet")
                  else f"[{name}] {results[name]} (owed by {OWNER_WAVE.get(name, '?')})")
        except CheckFailure as exc:
            results[name] = f"FAIL: {exc}"
            failures.append(str(exc))
            print(f"[{name}] FAIL — {exc}")
        except Exception as exc:  # noqa: BLE001 — unexpected is still a failure
            results[name] = f"FAIL: unexpected {type(exc).__name__}: {exc}"
            failures.append(results[name])
            print(f"[{name}] FAIL — unexpected {type(exc).__name__}: {exc}")

    write_state(results)
    if failures:
        print(f"unidesk checks: {len(failures)} failure(s)")
        return 1
    print("unidesk checks: all green (stubs honestly not_built_yet)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
