"""The eight subsystem checks, and the STATE.json writer."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from traderlog import config
from traderlog.db import DB_PATH, connect, count, init_db, table_names
from traderlog.ingest.archive import DEFAULT_MEDIA_ROOT

_ROOT = Path(__file__).resolve().parents[1]
_STATE = _ROOT / "STATE.json"
_ATTRIBUTION_DOC = _ROOT / "design" / "MODEL_ATTRIBUTION.md"
_ATTRIBUTION_LOG = _ROOT / "design" / "MODEL_WORK_LOG.jsonl"
_HANDOFFS_DIR = _ROOT / "design" / "handoffs"

# Which wave owns each check. A check still reading not_built_yet after its wave
# has shipped means that wave left the harness decorative.
OWNER_WAVE = {
    "db": "W0",
    "ingest": "W1",
    "parse": "W2",
    "golden": "W2",
    "derive": "W4",
    "ui": "W0",
    "telegram": "W7",
    "attribution": "W0",
}

PASS = "pass"
NOT_BUILT = "not_built_yet"


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str = ""

    @property
    def ok(self) -> bool:
        return not self.status.startswith("fail")


def _fail(name: str, reason: str) -> CheckResult:
    return CheckResult(name, f"fail: {reason}")


def _archive_path(value: str | None, root: Path = _ROOT) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else root / path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# ---------------------------------------------------------------------------
# individual checks
# ---------------------------------------------------------------------------

# Tables schema.sql must create. Kept explicit rather than derived so that a
# table silently disappearing from schema.sql is caught here.
REQUIRED_TABLES = {
    "traders", "posts", "post_media", "post_class",
    "positions", "position_events", "review_queue",
    "breadth_notes", "watch_ideas", "themes", "edu_items", "edu_links",
    "trader_style", "daily_prices", "breadth_daily", "breadth_counts",
    "regime_daily", "alpha_activity_signals",
    "symbol_attention", "attention_validation",
    "llm_runs", "pipeline_runs", "telegram_outbox", "settings",
}
# Aspirational long-run target is ~30 (TASKS.md), but that number assumes far
# more real posts than have been captured so far. W2 hand-verified every real
# trade-event thread available in the 12-post archive as of 2026-08-23 (2
# classifier fixtures + 3 reconciler fixtures = 5); a 4th conversation in that
# same archive (tradinghustlr's "Which Breakout you missed?") is not a trade
# thread and correctly yields no fixture. Raising this number back toward 30
# is an ingest-volume problem (more real posts), not a W2 problem -- do not
# raise it to make this check pass without more real fixtures behind it.
_GOLDEN_FIXTURE_TARGET = 5
_ATTRIBUTION_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "completed_at",
        "wave",
        "deliverable",
        "role",
        "model",
        "host_tool",
        "identity_basis",
        "scope",
        "files",
        "completion_report",
        "status",
        "verification_status",
        "notes_limitations",
    }
)
_ATTRIBUTION_ROLES = frozenset({"executor", "orchestrator", "reviewer", "vision"})
_IDENTITY_BASES = frozenset({"self_reported", "host_verified", "unknown"})
_ATTRIBUTION_STATUSES = frozenset({"completed", "partial", "blocked"})
_VERIFICATION_STATUSES = frozenset({"unverified", "verified", "partial"})
_ATTRIBUTION_ID = re.compile(r"attr-[a-z0-9][a-z0-9-]*$")
_ATTRIBUTION_ID_LINE = re.compile(r"^Attribution-ID:\s*([^\s]+)\s*$", re.MULTILINE)


def check_db(conn) -> CheckResult:
    have = table_names(conn)
    missing = REQUIRED_TABLES - have
    if missing:
        return _fail("db", f"{len(missing)} tables missing: {', '.join(sorted(missing))}")
    bad = [r[0] for r in conn.execute("PRAGMA foreign_key_check").fetchall()[:3]]
    if bad:
        return _fail("db", f"foreign key violations in: {', '.join(map(str, bad))}")
    return CheckResult("db", PASS, f"{len(have)} tables")


def check_ingest(
    conn, *, media_root: str | Path = DEFAULT_MEDIA_ROOT
) -> CheckResult:
    """Fresh posts for active real traders, all backed by immutable archives."""
    media_root = Path(media_root)
    missing_archives = []
    for row in conn.execute(
        "SELECT post_id, raw_path FROM posts WHERE is_mock=0"
    ).fetchall():
        path = _archive_path(row["raw_path"])
        if path is None or not path.is_file():
            missing_archives.append(row["post_id"])
    if missing_archives:
        sample = ", ".join(missing_archives[:3])
        return _fail(
            "ingest",
            f"{len(missing_archives)} real posts missing immutable archive: {sample}",
        )

    missing_media = []
    mismatched_media = []
    for row in conn.execute(
        "SELECT post_id,idx,local_path,sha256 FROM post_media WHERE is_mock=0"
    ).fetchall():
        label = f"{row['post_id']}:{row['idx']}"
        path = _archive_path(row["local_path"], media_root)
        if path is None or not path.is_file():
            missing_media.append(label)
        elif not row["sha256"] or _sha256(path) != row["sha256"]:
            mismatched_media.append(label)
    if missing_media:
        sample = ", ".join(missing_media[:3])
        return _fail(
            "ingest",
            f"{len(missing_media)} real media files missing archive: {sample}",
        )
    if mismatched_media:
        sample = ", ".join(mismatched_media[:3])
        return _fail(
            "ingest",
            f"{len(mismatched_media)} real media files failed sha256: {sample}",
        )

    active = count(conn, "traders", "active = 1 AND is_mock = 0")
    if active == 0:
        return CheckResult(
            "ingest", "stale_0d", "no active real traders configured for live validation"
        )

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    fresh = conn.execute(
        "SELECT COUNT(DISTINCT handle) FROM posts WHERE fetched_at >= ? AND is_mock = 0",
        (cutoff,),
    ).fetchone()[0]
    if fresh >= active * 0.8:
        return CheckResult("ingest", PASS, f"{fresh}/{active} traders fresh")

    row = conn.execute(
        "SELECT MAX(fetched_at) FROM posts WHERE is_mock = 0"
    ).fetchone()
    if not row or not row[0]:
        return _fail("ingest", "no real posts have ever been fetched")
    age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(row[0])).days
    return CheckResult("ingest", f"stale_{age_days}d", f"only {fresh}/{active} traders fresh")


def check_parse(conn) -> CheckResult:
    """The two data invariants: every field cites a post, every citation resolves.

    These are the assertions that keep the log factual. A position with a
    confidence but no evidence means a number was produced that no post
    justifies -- exactly the failure this project exists to avoid.
    """
    total_positions = count(conn, "positions")
    if total_positions == 0:
        return CheckResult("parse", NOT_BUILT, "no positions reconciled yet (W2)")

    uncited = count(
        conn, "positions",
        "confidence IS NOT NULL AND (evidence_json IS NULL OR evidence_json IN ('', '{}'))",
    )
    if uncited:
        return _fail("parse", f"{uncited} positions carry a confidence but no evidence map")

    orphans = conn.execute(
        "SELECT COUNT(*) FROM position_events e "
        "LEFT JOIN posts p ON p.post_id = e.post_id WHERE p.post_id IS NULL"
    ).fetchone()[0]
    if orphans:
        return _fail("parse", f"{orphans} position_events cite a post_id that does not exist")

    real_positions = count(conn, "positions", "is_mock = 0")
    if real_positions == 0:
        return CheckResult(
            "parse",
            NOT_BUILT,
            f"0 real positions reconciled; {total_positions} mock-only positions (W2)",
        )
    return CheckResult("parse", PASS, f"{real_positions} real positions, all cited")


def check_golden() -> CheckResult:
    """Frozen fixtures reproduce. The single most important test in the project.

    A model 'improving' a prompt and silently degrading extraction is the most
    likely way this project dies. These fixtures are the only thing that catches it.
    """
    fixtures = sorted((_ROOT / "tests" / "golden").glob("*.json"))
    if not fixtures:
        return CheckResult("golden", NOT_BUILT, "no fixtures yet (W2 builds ~30 from real posts)")
    proc = subprocess.run(
        ["python", "-m", "pytest", str(_ROOT / "tests"), "-q", "--no-header"],
        capture_output=True, text=True, cwd=_ROOT.parent,
    )
    if proc.returncode != 0:
        tail = (proc.stdout or proc.stderr).strip().splitlines()[-1:] or ["see pytest output"]
        return _fail("golden", tail[0][:160])
    if len(fixtures) < _GOLDEN_FIXTURE_TARGET:
        return CheckResult(
            "golden",
            NOT_BUILT,
            f"{len(fixtures)}/{_GOLDEN_FIXTURE_TARGET} fixtures verified",
        )

    # Prompt-drift detection. Without this the whole anti-drift mechanism is
    # decorative: a model edits a prompt, the fixtures still pass because they
    # are compared against their own stored expectations, and nobody learns that
    # the expectations were hand-verified against a DIFFERENT prompt.
    #
    # A fixture records the prompt hashes it was verified against. When the
    # prompt changes, the fixture is STALE -- its expected output may no longer
    # be what the current prompt should produce, and a human has to re-verify it.
    # That is a real finding, not a failure of the code, so it reports as a
    # distinct status rather than pass or fail.
    stale = _stale_fixtures(fixtures)
    if stale:
        names = ", ".join(sorted(stale)[:3])
        return CheckResult(
            "golden",
            f"stale_prompts_{len(stale)}",
            f"{len(stale)} fixture(s) verified against an older prompt: {names}",
        )
    return CheckResult("golden", PASS, f"{len(fixtures)} fixtures, prompts current")


def _attribution_failure(reason: str) -> CheckResult:
    return _fail("attribution", reason)


def _repo_path(value: str) -> Path | None:
    """Resolve a required relative repository path without allowing escape."""
    path = Path(value)
    if path.is_absolute():
        return None
    resolved = (_ROOT / path).resolve()
    try:
        resolved.relative_to(_ROOT.resolve())
    except ValueError:
        return None
    return resolved


def _read_attribution_records() -> tuple[list[dict], CheckResult | None]:
    if not _ATTRIBUTION_DOC.is_file():
        return [], _attribution_failure("MODEL_ATTRIBUTION.md missing")
    if not _ATTRIBUTION_LOG.is_file():
        return [], _attribution_failure("MODEL_WORK_LOG.jsonl missing")

    records: list[dict] = []
    for line_no, raw in enumerate(_ATTRIBUTION_LOG.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            return [], _attribution_failure(f"blank JSONL line {line_no}")
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            return [], _attribution_failure(f"malformed JSONL line {line_no}")
        if not isinstance(record, dict):
            return [], _attribution_failure(f"JSONL line {line_no} is not an object")
        records.append(record)
    return records, None


def _validate_attribution_record(record: dict, line_no: int, seen_ids: set[str]) -> str | None:
    missing = sorted(field for field in _ATTRIBUTION_REQUIRED_FIELDS if field not in record)
    if missing:
        return f"line {line_no} missing required fields: {', '.join(missing)}"
    record_id = record["id"]
    if not isinstance(record_id, str) or not _ATTRIBUTION_ID.fullmatch(record_id):
        return f"line {line_no} has invalid id"
    if record_id in seen_ids:
        return f"duplicate id: {record_id}"
    seen_ids.add(record_id)
    if record["role"] not in _ATTRIBUTION_ROLES:
        return f"line {line_no} has invalid role"
    if record["identity_basis"] not in _IDENTITY_BASES:
        return f"line {line_no} has invalid identity_basis"
    if record["status"] not in _ATTRIBUTION_STATUSES:
        return f"line {line_no} has invalid status"
    if record["verification_status"] not in _VERIFICATION_STATUSES:
        return f"line {line_no} has invalid verification_status"
    if not isinstance(record["files"], list) or not record["files"] or not all(
        isinstance(path, str) and path for path in record["files"]
    ):
        return f"line {line_no} has invalid files"
    for field in (
        "wave", "deliverable", "model", "host_tool", "scope", "completion_report", "notes_limitations"
    ):
        if not isinstance(record[field], str) or not record[field].strip():
            return f"line {line_no} has invalid {field}"
    completed_at = record["completed_at"]
    if not isinstance(completed_at, str):
        return f"line {line_no} has invalid completed_at"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", completed_at):
        try:
            date.fromisoformat(completed_at)
        except ValueError:
            return f"line {line_no} has invalid completed_at"
    else:
        try:
            timestamp = datetime.fromisoformat(completed_at)
        except ValueError:
            return f"line {line_no} has invalid completed_at"
        if timestamp.tzinfo is None:
            return f"line {line_no} completed_at has no timezone"
    if _repo_path(record["completion_report"]) is None:
        return f"line {line_no} has unsafe completion_report path"
    return None


def check_attribution() -> CheckResult:
    """Prove model-work provenance is explicit, append-only, and report-linked."""
    records, failure = _read_attribution_records()
    if failure:
        return failure
    if not records:
        return _attribution_failure("MODEL_WORK_LOG.jsonl has no records")

    seen_ids: set[str] = set()
    by_id: dict[str, dict] = {}
    for line_no, record in enumerate(records, 1):
        problem = _validate_attribution_record(record, line_no, seen_ids)
        if problem:
            return _attribution_failure(problem)
        by_id[record["id"]] = record

    completed_handoffs = sorted(_HANDOFFS_DIR.glob("HANDOFF_*_COMPLETED.md"))
    for handoff in completed_handoffs:
        report_ids = _ATTRIBUTION_ID_LINE.findall(handoff.read_text(encoding="utf-8"))
        if not report_ids:
            return _attribution_failure(f"completed handoff has no attribution ID: {handoff.name}")
        for record_id in report_ids:
            record = by_id.get(record_id)
            if record is None:
                return _attribution_failure(f"unknown attribution id: {record_id}")
            report_path = _repo_path(record["completion_report"])
            assert report_path is not None
            if report_path.resolve() != handoff.resolve():
                return _attribution_failure(f"report-path mismatch for id: {record_id}")

    for record in records:
        report_path = _repo_path(record["completion_report"])
        assert report_path is not None  # checked above; keeps the type narrow.
        if not report_path.is_file():
            return _attribution_failure(f"report missing for id: {record['id']}")
        report_ids = set(_ATTRIBUTION_ID_LINE.findall(report_path.read_text(encoding="utf-8")))
        if record["id"] not in report_ids:
            return _attribution_failure(f"report-path mismatch for id: {record['id']}")

    return CheckResult("attribution", PASS, f"{len(records)} records, {len(completed_handoffs)} completed handoffs")


def _stale_fixtures(fixtures: list[Path]) -> set[str]:
    """Fixture names whose recorded prompt hashes no longer match the prompts."""
    from traderlog.llm import prompts

    current = prompts.all_versions()
    stale: set[str] = set()
    for path in fixtures:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        recorded = data.get("prompt_versions") or {}
        for name, was in recorded.items():
            if name in current and current[name] != was:
                stale.add(path.stem)
    return stale


# How many calendar days old the latest regime_daily session may be before
# `derive` reports honest staleness instead of `pass`. Chosen from the real
# bhavcopy calendar (see adopted/xp.py's DEFAULT_GAP_THRESHOLD_DAYS note):
# every genuine NSE weekend/holiday gap is <=4 calendar days, so 5 gives one
# day of slack without hiding a pipeline that has actually gone stale.
_DERIVE_STALE_THRESHOLD_DAYS = 5


def check_derive(conn, *, now: datetime | None = None) -> CheckResult:
    """Breadth + XP/MBI present for recent sessions (W4), honest about staleness.

    Two independent things are checked, and neither is weakened to make the
    other pass:
    1. Coverage + chain integrity — the five newest breadth_daily dates must
       exactly equal the five newest regime_daily dates, and every one must
       carry XP, z-state, and the persisted MBI result. XP is a recursion
       (adopted/xp.py); any missing value means the chain genuinely broke.
    2. Freshness — how many days old the latest ingested session is relative
       to `now` (real current time by default; injectable for tests). W4's
       bhavcopy ingestion is not scheduled/live, so staleness is expected and
       reported honestly as `stale_<n>d` rather than hidden by a check that
       only ever looks at the newest rows already in the table regardless of
       how old they are.
    """
    if count(conn, "breadth_daily") == 0:
        return CheckResult("derive", NOT_BUILT, "no breadth ingested yet (W4)")

    breadth_rows = conn.execute(
        "SELECT trade_date FROM breadth_daily ORDER BY trade_date DESC LIMIT 5"
    ).fetchall()
    if len(breadth_rows) < 5:
        return CheckResult("derive", NOT_BUILT, f"only {len(breadth_rows)} breadth_daily rows (W4)")
    breadth_dates = [r["trade_date"] for r in breadth_rows]
    rows = conn.execute(
        "SELECT trade_date, xp_value, xp_z_state, mbi_day_color, mbi_score, warning_day "
        "FROM regime_daily ORDER BY trade_date DESC LIMIT 5"
    ).fetchall()
    regime_dates = [r["trade_date"] for r in rows]
    if breadth_dates != regime_dates:
        return _fail(
            "derive",
            "breadth/regime coverage mismatch: "
            f"breadth latest={', '.join(breadth_dates)}; regime latest={', '.join(regime_dates) or '-'}",
        )

    required_columns = ("xp_value", "xp_z_state", "mbi_day_color", "mbi_score", "warning_day")
    for column in required_columns:
        missing = [r["trade_date"] for r in rows if r[column] is None]
        if missing:
            return _fail("derive", f"{column} null on {', '.join(missing)}")

    latest = rows[0]["trade_date"]
    reference = now or datetime.now(timezone.utc)
    try:
        age_days = (reference.date() - date.fromisoformat(latest)).days
    except ValueError:
        age_days = None
    if age_days is not None and age_days > _DERIVE_STALE_THRESHOLD_DAYS:
        return CheckResult(
            "derive",
            f"stale_{age_days}d",
            f"latest regime_daily session {latest} is {age_days}d old; "
            "latest 5 breadth and regime sessions match with XP + MBI",
        )
    return CheckResult(
        "derive", PASS, f"latest 5 breadth and regime sessions match with XP + MBI, latest {latest}"
    )


def check_ui() -> CheckResult:
    """The UI builds. Cheap proxy for 'the screens still compile'."""
    ui = _ROOT / "ui"
    if not (ui / "package.json").exists():
        return CheckResult("ui", NOT_BUILT, "ui/ not scaffolded")
    if not (ui / "node_modules").exists():
        return CheckResult("ui", NOT_BUILT, "npm install not run in traderlog/ui")
    dist = ui / "dist" / "index.html"
    if not dist.exists():
        return CheckResult("ui", NOT_BUILT, "no build yet — run `npm run build` in traderlog/ui")
    screens = sorted((ui / "src" / "screens").glob("*.jsx"))
    if len(screens) < 6:
        return _fail("ui", f"expected 6 screens, found {len(screens)}")
    return CheckResult("ui", PASS, f"{len(screens)} screens, dist present")


def check_telegram(conn) -> CheckResult:
    if config.get("telegram.dry_run", True):
        return CheckResult("telegram", "dry_run", "sending disabled in config")
    stuck = conn.execute(
        "SELECT COUNT(*) FROM telegram_outbox WHERE state = 'delivery_ambiguous' "
        "AND created_at < datetime('now', '-1 hour')"
    ).fetchone()[0]
    if stuck:
        return _fail("telegram", f"{stuck} outbox rows stuck in delivery_ambiguous > 1h")
    return CheckResult("telegram", PASS)


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------

def run_all(db_path: str | Path | None = None) -> list[CheckResult]:
    # init_db is idempotent, so this both creates the DB on a fresh clone and
    # retrofits any tables added to schema.sql since the last run. That means
    # `check_db` is testing the schema as it exists on disk right now.
    conn = init_db(db_path)
    try:
        return [
            check_db(conn),
            check_ingest(conn),
            check_parse(conn),
            check_golden(),
            check_attribution(),
            check_derive(conn),
            check_ui(),
            check_telegram(conn),
        ]
    finally:
        conn.close()


def _counts(conn) -> dict[str, int]:
    return {
        "traders": count(conn, "traders"),
        "posts": count(conn, "posts"),
        "posts_real": count(conn, "posts", "is_mock = 0"),
        "posts_mock": count(conn, "posts", "is_mock = 1"),
        "posts_deleted": count(conn, "posts", "deleted_at IS NOT NULL"),
        "positions": count(conn, "positions"),
        "review_open": count(conn, "review_queue", "status = 'open'"),
        "edu_items": count(conn, "edu_items"),
        "llm_calls": count(conn, "llm_runs"),
    }


def _git_head() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=_ROOT.parent, timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _current_wave(results: list[CheckResult]) -> str:
    """Lowest-numbered wave whose check has not reached a real assertion."""
    by_name = {r.name: r for r in results}
    for wave in ("W1", "W2", "W4", "W7"):
        for name, owner in OWNER_WAVE.items():
            if owner == wave and by_name.get(name, CheckResult(name, NOT_BUILT)).status == NOT_BUILT:
                return wave
    return "W8"


def write_state(results: list[CheckResult], db_path: str | Path | None = None) -> dict:
    conn = connect(db_path)
    try:
        counts = _counts(conn)
        mock = count(conn, "posts", "is_mock = 1") > 0
    finally:
        conn.close()

    blocked = [f"{r.name}: {r.status}" for r in results if not r.ok]
    state = {
        "wave": _current_wave(results),
        "last_verified_commit": _git_head(),
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "checks": {r.name: r.status for r in results},
        "counts": counts,
        "showing_mock_data": mock,
        "blocked_on": blocked or None,
    }
    _STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state
