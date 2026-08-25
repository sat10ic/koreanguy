"""Disposable-database tests for run_recon.py, the recon conductor.

Every test pins one audited contract of the conductor: stage skips via flags,
the classify scope rule (posts that already have a post_class row are never
re-processed even when run_id IS NULL), the reconcile scope rule (roots that
already have a positions row are skipped), the pool-cooldown resume on
consecutive ProviderExhausted, and the --yes production gate. Every database
is a disposable tmp_path one; the production DB is never opened, and the
provider is always a monkeypatched chat_fn so no network call can happen.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from traderlog.db import init_db, now_iso
from traderlog.llm.provider import ProviderExhausted, ProviderResult
from traderlog.llm.reconcile import apply_verified_reconciliation
from traderlog.run_recon import (
    STAGE_CLASSIFY,
    STAGE_INSIGHT,
    STAGE_LINK,
    STAGE_RECONCILE,
    main,
)

TS_1 = "2026-08-01T09:00:00+05:30"
TS_2 = "2026-08-02T09:00:00+05:30"
TS_3 = "2026-08-03T09:00:00+05:30"


def _never_chat(**kwargs):
    raise AssertionError("run_recon must not call the provider here")


def _assert_eq(actual, expected):
    assert actual == expected, f"expected {expected!r}, got {actual!r}"


# ---------------------------------------------------------------------------
# seeding helpers -- FK-correct inserts into a disposable init_db'd database
# ---------------------------------------------------------------------------


def _seed_trader(conn, handle: str = "alice") -> None:
    conn.execute(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        (handle, 1, 0, now_iso()),
    )


def _seed_post(conn, post_id: str, text: str, *, ts: str = TS_1,
               handle: str = "alice") -> None:
    conn.execute(
        "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,"
        "ts_utc,ts_ist,text,url,fetched_at,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (post_id, handle, None, None, ts, ts, text,
         f"https://x.com/{handle}/status/{post_id}", now_iso(), 0, now_iso()),
    )


def _seed_class(conn, post_id: str, *, kind: str, symbols: list[str],
                model: str = "test/manual", run_id: int | None = None) -> None:
    conn.execute(
        "INSERT INTO post_class (post_id,kind,confidence,symbols,play_type,"
        "conviction_words,model,run_id,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (post_id, kind, 0.9, json.dumps(symbols), "unclear", "[]",
         model, run_id, 0, now_iso()),
    )
    conn.commit()


def _class_payload(symbol: str = "XYZ") -> dict:
    return {
        "kind": "trade_event",
        "confidence": 0.91,
        "symbols": [symbol],
        "play_type": "unclear",
        "conviction_words": [],
        "reason": "states a position",
    }


def _reconcile_payload(root_post_id: str, symbol: str = "XYZ") -> dict:
    return {
        "symbol": symbol,
        "status": "open",
        "entries": [{"price": 100, "date": None, "size_note": None,
                     "post_id": root_post_id}],
        "adds": [], "stop": None, "targets": [], "exits": [],
        "net_result_pct": None, "holding_days": None, "confidence": 0.88,
        "unresolved": [], "evidence": {
            "symbol": root_post_id,
            "entries[0].price": root_post_id,
        },
    }


def _db_arg(tmp_path: Path) -> str:
    return str(tmp_path / "traderlog.db")


# ---------------------------------------------------------------------------
# (a) stage skips via flags
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "skip_flag,seed,check",
    [
        (
            "--skip-classify",
            lambda conn: _seed_post(conn, "p-un", "Watching XYZ for a breakout."),
            lambda conn: _assert_eq(conn.execute(
                "SELECT COUNT(*) FROM post_class").fetchone()[0], 0),
        ),
        (
            "--skip-reconcile",
            lambda conn: (
                _seed_post(conn, "p-root", "Bought XYZ at 100, stop at 95.", ts=TS_2),
                _seed_class(conn, "p-root", kind="trade_event", symbols=["XYZ"]),
                None,
            ),
            lambda conn: _assert_eq(conn.execute(
                "SELECT COUNT(*) FROM positions").fetchone()[0], 0),
        ),
        (
            "--skip-link",
            lambda conn: (
                _seed_post(conn, "p-root", "Bought XYZ at 100, stop at 95.", ts=TS_2),
                _seed_class(conn, "p-root", kind="trade_event", symbols=["XYZ"]),
                apply_verified_reconciliation(conn, "p-root", _reconcile_payload("p-root")),
                _seed_post(conn, "p-cand", "Booked XYZ at 130.", ts=TS_3),
                _seed_class(conn, "p-cand", kind="trade_event", symbols=["XYZ"]),
                None,
            ),
            lambda conn: _assert_eq(conn.execute(
                "SELECT COUNT(*) FROM review_queue").fetchone()[0], 0),
        ),
        (
            "--skip-insight",
            lambda conn: (
                _seed_post(conn, "p-breadth", "Market stays weak; staying light.", ts=TS_2),
                _seed_class(conn, "p-breadth", kind="breadth", symbols=[]),
                None,
            ),
            lambda conn: _assert_eq(conn.execute(
                "SELECT COUNT(*) FROM breadth_notes").fetchone()[0], 0),
        ),
    ],
)
def test_stage_skips_via_flag(
    tmp_path: Path,
    skip_flag: str,
    seed,
    check,
):
    conn = init_db(tmp_path / "traderlog.db")
    _seed_trader(conn)
    seed(conn)
    conn.commit()
    other_skips = [f for f in ("--skip-classify", "--skip-reconcile",
                               "--skip-link", "--skip-insight") if f != skip_flag]
    rc = main(["--db", _db_arg(tmp_path), "--pacing", "0", skip_flag, *other_skips],
              chat_fn=_never_chat, sleep=lambda _: None)
    assert rc == 0
    check(conn)  # the skipped stage must not have acted
    conn.close()


def test_all_stages_skippable_at_once(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _seed_trader(conn)
    _seed_post(conn, "p-un", "Watching XYZ for a breakout.")
    conn.commit()
    rc = main(
        ["--db", _db_arg(tmp_path), "--skip-classify", "--skip-reconcile",
         "--skip-link", "--skip-insight", "--pacing", "0"],
        chat_fn=_never_chat, sleep=lambda _: None,
    )
    assert rc == 0
    assert conn.execute("SELECT COUNT(*) FROM post_class").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0] == 0
    conn.close()


# ---------------------------------------------------------------------------
# (b) classify does NOT touch posts that already have a post_class row
# ---------------------------------------------------------------------------


def test_classify_skips_posts_with_existing_post_class_rows(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _seed_trader(conn)
    # p-a has an AUDITED post_class row with run_id IS NULL -- must stay untouched
    _seed_post(conn, "p-a", "Holding XYZ, stop at 90.")
    _seed_class(conn, "p-a", kind="trade_event", symbols=["XYZ"],
                model="manual", run_id=None)
    # p-b has no post_class row at all -- the only scope member
    _seed_post(conn, "p-b", "Bought XYZ at 100, stop at 95.", ts=TS_2)
    conn.commit()
    calls: list[str] = []

    def chat_fn(**kwargs):
        calls.append(kwargs["ref_id"])
        return ProviderResult(content=_class_payload(), model="test/cheap",
                              provider="test", run_id=1)

    rc = main(["--db", _db_arg(tmp_path), "--skip-reconcile", "--skip-link",
               "--skip-insight", "--pacing", "0"], chat_fn=chat_fn,
              sleep=lambda _: None)

    assert rc == 0
    assert calls == ["p-b"]  # only the post with NO post_class row saw a call
    row = conn.execute("SELECT model, run_id, kind FROM post_class "
                       "WHERE post_id='p-a'").fetchone()
    assert (row["model"], row["run_id"]) == ("manual", None)  # audited row untouched
    assert conn.execute("SELECT COUNT(*) FROM post_class").fetchone()[0] == 2
    pr = conn.execute("SELECT stage, status, rows FROM pipeline_runs "
                      "WHERE stage='recon.classify'").fetchone()
    assert pr is not None and pr["status"] == "ok" and pr["rows"] == 1
    conn.close()


# ---------------------------------------------------------------------------
# (c) reconcile skips roots that already have positions
# ---------------------------------------------------------------------------


def test_reconcile_skips_roots_that_already_have_positions(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _seed_trader(conn)
    # root A already reconciled (positions row exists) -- must NOT be re-called
    _seed_post(conn, "p-root-a", "Bought XYZ at 100, stop at 95.")
    _seed_class(conn, "p-root-a", kind="trade_event", symbols=["XYZ"])
    apply_verified_reconciliation(conn, "p-root-a", _reconcile_payload("p-root-a"))
    # root B has a classification but no position -- the only candidate
    _seed_post(conn, "p-root-b", "Bought XYZ at 110, stop at 100.", ts=TS_2)
    _seed_class(conn, "p-root-b", kind="trade_event", symbols=["XYZ"])
    # root C is a standalone trade_event with NO symbols -- never a candidate
    _seed_post(conn, "p-root-c", "Trimmed the position today.", ts=TS_3)
    _seed_class(conn, "p-root-c", kind="trade_event", symbols=[])
    conn.commit()
    calls: list[str] = []

    def chat_fn(**kwargs):
        calls.append(kwargs["ref_id"])
        return ProviderResult(content=_reconcile_payload(kwargs["ref_id"]),
                              model="test/smart", provider="test", run_id=1)

    rc = main(["--db", _db_arg(tmp_path), "--skip-classify", "--skip-link",
               "--skip-insight", "--pacing", "0"], chat_fn=chat_fn,
              sleep=lambda _: None)

    assert rc == 0
    assert calls == ["p-root-b"]  # only the root WITHOUT a position was reconciled
    assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM positions WHERE "
                        "root_post_id='p-root-b'").fetchone()[0] == 1
    pr = conn.execute("SELECT stage, status, rows FROM pipeline_runs "
                      "WHERE stage='recon.reconcile'").fetchone()
    assert pr is not None and pr["status"] == "ok" and pr["rows"] == 1
    conn.close()


# ---------------------------------------------------------------------------
# (d) consecutive-exhaustion cooldown triggers and resumes the same item
# ---------------------------------------------------------------------------


def test_pool_cooldown_triggers_and_resumes_on_consecutive_exhaustion(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _seed_trader(conn)
    _seed_post(conn, "p-un", "Watching XYZ for a breakout.")
    conn.commit()
    attempts = {"n": 0}
    sleeps: list[float] = []

    def chat_fn(**kwargs):
        attempts["n"] += 1
        if attempts["n"] <= 2:
            raise ProviderExhausted("cheap", [("fake/model", "rate limited")])
        return ProviderResult(content=_class_payload(), model="test/cheap",
                              provider="test", run_id=1)

    rc = main(
        ["--db", _db_arg(tmp_path), "--skip-reconcile", "--skip-link",
         "--skip-insight", "--pacing", "0"],
        chat_fn=chat_fn, sleep=sleeps.append,
        cooldown_threshold=2, cooldown_base_s=0.01, cooldown_cap_s=1.0,
    )

    assert rc == 0
    assert attempts["n"] == 3      # 2 exhausted attempts + 1 resumed success
    assert any(abs(s - 0.01) < 1e-9 for s in sleeps)  # a cooldown sleep fired
    assert conn.execute("SELECT COUNT(*) FROM post_class "
                        "WHERE post_id='p-un'").fetchone()[0] == 1
    conn.close()


# ---------------------------------------------------------------------------
# (e) --yes gate refuses production without the flag
# ---------------------------------------------------------------------------


def test_production_gate_refuses_without_yes(tmp_path: Path):
    # default DB is production: without --yes the runner must refuse BEFORE
    # opening any database.
    rc = main(["--skip-classify", "--skip-reconcile", "--skip-link",
               "--skip-insight"])
    assert rc == 2

    # the same flags against a disposable --db are allowed without --yes
    rc2 = main(["--db", _db_arg(tmp_path), "--skip-classify",
                "--skip-reconcile", "--skip-link", "--skip-insight", "--pacing", "0"],
               chat_fn=_never_chat, sleep=lambda _: None)
    assert rc2 == 0


# ---------------------------------------------------------------------------
# reporting: vision backlog + per-stage pipeline_runs rows
# ---------------------------------------------------------------------------


def test_summary_reports_vision_backlog_count(tmp_path: Path, capsys):
    conn = init_db(tmp_path / "traderlog.db")
    _seed_trader(conn)
    # trade_event media WITHOUT vision_json -> counted as backlog
    _seed_post(conn, "p-trade", "Bought XYZ at 100, stop at 95.")
    _seed_class(conn, "p-trade", kind="trade_event", symbols=["XYZ"])
    conn.execute(
        "INSERT INTO post_media (post_id,idx,local_path,sha256,media_type,"
        "is_mock,ingested_at) VALUES (?,?,?,?,?,?,?)",
        ("p-trade", 0, "x/trade.png", "abc", "image", 0, now_iso()),
    )
    # noise media without vision -> NOT backlog (kind gate)
    _seed_post(conn, "p-noise", "Nice weather today.", ts=TS_2)
    _seed_class(conn, "p-noise", kind="noise", symbols=[])
    conn.execute(
        "INSERT INTO post_media (post_id,idx,local_path,sha256,media_type,"
        "is_mock,ingested_at) VALUES (?,?,?,?,?,?,?)",
        ("p-noise", 0, "x/noise.png", "def", "image", 0, now_iso()),
    )
    # education media WITH vision_json -> NOT backlog
    _seed_post(conn, "p-edu", "Always set a stop loss.", ts=TS_3)
    _seed_class(conn, "p-edu", kind="education", symbols=[])
    conn.execute(
        "INSERT INTO post_media (post_id,idx,local_path,sha256,media_type,"
        "vision_json,vision_model,vision_at,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        ("p-edu", 0, "x/edu.png", "ghi", "image", "{}", "user", now_iso(),
         0, now_iso()),
    )
    conn.commit()

    rc = main(["--db", _db_arg(tmp_path), "--skip-classify", "--skip-reconcile",
               "--skip-link", "--skip-insight", "--pacing", "0"],
              chat_fn=_never_chat, sleep=lambda _: None)
    assert rc == 0
    out = capsys.readouterr().out
    assert "vision backlog: 1" in out
    assert "design/VISION_BACKFILL_SPEC.md" in out
    conn.close()


def test_full_chain_logs_each_stage_to_pipeline_runs(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _seed_trader(conn)
    # one unclassified post -> classify stage work
    _seed_post(conn, "p-un", "Watching XYZ for a breakout.")
    # one classified standalone trade_event root with a symbol -> reconcile work
    _seed_post(conn, "p-root", "Bought XYZ at 100, stop at 95.", ts=TS_2)
    _seed_class(conn, "p-root", kind="trade_event", symbols=["XYZ"])
    # one breadth post -> insight materialises breadth_notes (SQL only, no LLM)
    _seed_post(conn, "p-breadth", "Market stays weak; staying light.", ts=TS_3)
    _seed_class(conn, "p-breadth", kind="breadth", symbols=[])
    conn.commit()

    def chat_fn(**kwargs):
        if kwargs["task"] == "classify":
            return ProviderResult(content=_class_payload(), model="test/cheap",
                                  provider="test", run_id=1)
        return ProviderResult(content=_reconcile_payload(kwargs["ref_id"]),
                              model="test/smart", provider="test", run_id=1)

    rc = main(["--db", _db_arg(tmp_path), "--pacing", "0"],
              chat_fn=chat_fn, sleep=lambda _: None)
    assert rc == 0
    stages = {row["stage"] for row in conn.execute(
        "SELECT DISTINCT stage FROM pipeline_runs")}
    assert {STAGE_CLASSIFY, STAGE_RECONCILE, STAGE_LINK, STAGE_INSIGHT} <= stages
    row = conn.execute("SELECT status, rows FROM pipeline_runs "
                       "WHERE stage='recon.classify' ORDER BY id DESC LIMIT 1"
                       ).fetchone()
    assert row["status"] == "ok" and row["rows"] == 1
    row = conn.execute("SELECT COUNT(*) FROM breadth_notes").fetchone()
    assert row[0] >= 1
    conn.close()