"""The seven subsystem checks, and the STATE.json writer."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from traderlog import config
from traderlog.db import DB_PATH, connect, count, init_db, table_names

_ROOT = Path(__file__).resolve().parents[1]
_STATE = _ROOT / "STATE.json"

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


def check_db(conn) -> CheckResult:
    have = table_names(conn)
    missing = REQUIRED_TABLES - have
    if missing:
        return _fail("db", f"{len(missing)} tables missing: {', '.join(sorted(missing))}")
    bad = [r[0] for r in conn.execute("PRAGMA foreign_key_check").fetchall()[:3]]
    if bad:
        return _fail("db", f"foreign key violations in: {', '.join(map(str, bad))}")
    return CheckResult("db", PASS, f"{len(have)} tables")


def check_ingest(conn) -> CheckResult:
    """Fresh posts for the active traders.

    W1 owns this. Until the fetcher exists there is nothing real to assert, so it
    reports not_built_yet rather than a misleading pass.
    """
    if not (_ROOT / "ingest" / "xfetch.py").exists():
        return CheckResult("ingest", NOT_BUILT, "ingest/xfetch.py not written (W1)")

    active = count(conn, "traders", "active = 1 AND is_mock = 0")
    if active == 0:
        return CheckResult("ingest", NOT_BUILT, "no real traders configured yet")

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
    if count(conn, "positions") == 0:
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

    return CheckResult("parse", PASS, f"{count(conn, 'positions')} positions, all cited")


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
    return CheckResult("golden", PASS, f"{len(fixtures)} fixtures")


def check_derive(conn) -> CheckResult:
    """Breadth + XP/MBI present for recent sessions (W4)."""
    if count(conn, "breadth_daily") == 0:
        return CheckResult("derive", NOT_BUILT, "no breadth ingested yet (W4)")

    rows = conn.execute(
        "SELECT trade_date, xp_value FROM regime_daily ORDER BY trade_date DESC LIMIT 5"
    ).fetchall()
    if len(rows) < 5:
        return CheckResult("derive", NOT_BUILT, f"only {len(rows)} regime_daily rows (W4)")
    missing_xp = [r["trade_date"] for r in rows if r["xp_value"] is None]
    if missing_xp:
        # XP is a recursion: one missing day breaks every day after it.
        return _fail("derive", f"xp_value null on {', '.join(missing_xp)} — recursion chain broken")
    return CheckResult("derive", PASS, "5 recent sessions have XP + MBI")


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
