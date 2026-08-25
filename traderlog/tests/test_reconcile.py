from __future__ import annotations

import json
from pathlib import Path

import pytest

from traderlog.db import init_db, now_iso
from traderlog.llm.provider import ProviderResult
from traderlog.llm.reconcile import (
    ReconcileValidationError,
    _load_thread,
    apply_verified_reconciliation,
    reconcile_thread,
    thread_hash,
    validate_reconciliation,
)


GOLDEN = Path(__file__).parent / "golden"
FIXTURES = [
    GOLDEN / "2090713569793126757_rategain_open_position_reconcile.json",
    GOLDEN / "2089923284565700807_fcl_fastzone_partial_exit_reconcile.json",
    GOLDEN / "2085214288961237368_fcl_vcpswing_open_position_reconcile.json",
]


def _fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _seed_thread(conn, fixture: dict, *, is_mock: int = 0) -> None:
    handle = fixture["handle"]
    conn.execute(
        "INSERT OR IGNORE INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        (handle, 1, is_mock, now_iso()),
    )
    for post in fixture["thread"]:
        conn.execute(
            "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,text,url,"
            "fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                post["post_id"], post["handle"], post["conversation_id"], post["in_reply_to"],
                post["ts_utc"], post["ts_ist"], post["text"], post["url"], now_iso(), is_mock, now_iso(),
            ),
        )
        for media in fixture.get("vision", {}).get(post["post_id"], []):
            conn.execute(
                "INSERT INTO post_media (post_id, idx, local_path, sha256, media_type, "
                "vision_json, vision_model, vision_at, is_mock, ingested_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    post["post_id"], media["media_idx"], media["local_path"], "deadbeef", "image",
                    json.dumps(media["expected_vision"], ensure_ascii=False), "user", now_iso(),
                    is_mock, now_iso(),
                ),
            )
    conn.commit()


# ---------------------------------------------------------------------------
# each real, hand-verified thread: validation + full write path
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_golden_thread_validates_and_matches_hand_verified_state(path: Path, tmp_path: Path):
    fixture = _fixture(path)
    conn = init_db(tmp_path / "traderlog.db")
    _seed_thread(conn, fixture)
    posts = conn.execute(
        "SELECT * FROM posts WHERE conversation_id=? AND handle=? ORDER BY ts_utc ASC",
        (fixture["root_post_id"], fixture["handle"]),
    ).fetchall()

    result = validate_reconciliation(fixture["expected_reconciliation"], posts)

    expected = fixture["expected_reconciliation"]
    assert result.symbol == expected["symbol"]
    assert result.status == expected["status"]
    assert result.confidence == pytest.approx(expected["confidence"])
    assert list(result.unresolved) == expected["unresolved"]
    assert result.to_state_dict() == expected
    conn.close()


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_reconcile_thread_writes_positions_and_events_with_full_citation(
    path: Path, tmp_path: Path
):
    fixture = _fixture(path)
    conn = init_db(tmp_path / "traderlog.db")
    _seed_thread(conn, fixture)
    valid_post_ids = {p["post_id"] for p in fixture["thread"]}

    calls: list[dict] = []

    def chat_fn(**kwargs):
        calls.append(kwargs)
        return ProviderResult(
            content=fixture["expected_reconciliation"], model="test/smart", provider="test", run_id=42
        )

    result = reconcile_thread(conn, fixture["root_post_id"], chat_fn=chat_fn)

    assert len(calls) == 1
    assert calls[0]["tier"] == "smart"
    assert calls[0]["task"] == "reconcile"
    assert calls[0]["json_schema"] is True
    assert calls[0]["ref_id"] == fixture["root_post_id"]

    pos_row = conn.execute(
        "SELECT * FROM positions WHERE root_post_id=?", (fixture["root_post_id"],)
    ).fetchone()
    assert pos_row is not None
    assert pos_row["symbol"] == result.symbol
    assert pos_row["status"] == result.status
    assert pos_row["is_mock"] == 0

    # The parse check's core invariant: confidence implies a non-empty evidence map.
    evidence = json.loads(pos_row["evidence_json"])
    assert evidence  # non-empty -- check_parse would fail this position otherwise
    for field_path, post_id in evidence.items():
        assert post_id in valid_post_ids, f"evidence[{field_path!r}] cites a post outside the thread"

    # position_events invariant: every event cites a post_id that really exists.
    events = conn.execute(
        "SELECT * FROM position_events WHERE position_id=? ORDER BY seq", (pos_row["position_id"],)
    ).fetchall()
    for event in events:
        assert event["post_id"] in valid_post_ids
        assert event["is_mock"] == 0
    conn.close()


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_unchanged_thread_costs_zero_llm_calls_and_is_byte_identical(path: Path, tmp_path: Path):
    """CONTRACTS.md #3: cache on thread_hash; idempotence is tested."""
    fixture = _fixture(path)
    conn = init_db(tmp_path / "traderlog.db")
    _seed_thread(conn, fixture)

    calls: list[dict] = []

    def chat_fn(**kwargs):
        calls.append(kwargs)
        return ProviderResult(
            content=fixture["expected_reconciliation"], model="test/smart", provider="test", run_id=1
        )

    first = reconcile_thread(conn, fixture["root_post_id"], chat_fn=chat_fn)
    assert len(calls) == 1

    def failing_chat_fn(**kwargs):
        raise AssertionError("an unchanged thread must cost zero LLM calls")

    second = reconcile_thread(conn, fixture["root_post_id"], chat_fn=failing_chat_fn)

    assert first.to_json() == second.to_json()
    conn.close()


def test_thread_hash_changes_when_vision_output_is_added():
    posts = [{"post_id": "1", "text": "hello"}]
    before = thread_hash(posts, {})
    after = thread_hash(posts, {"1": [{"unreadable": True}]})
    assert before != after


def test_thread_hash_stable_for_identical_input():
    posts = [{"post_id": "1", "text": "hello"}, {"post_id": "2", "text": "world"}]
    vision = {"2": [{"chart_symbol": "FCL"}]}
    assert thread_hash(posts, vision) == thread_hash(posts, vision)


def test_apply_verified_reconciliation_matches_llm_path_and_makes_no_calls(tmp_path: Path):
    fixture = _fixture(FIXTURES[0])
    conn = init_db(tmp_path / "traderlog.db")
    _seed_thread(conn, fixture)

    audited = apply_verified_reconciliation(
        conn, fixture["root_post_id"], fixture["expected_reconciliation"]
    )
    row = conn.execute(
        "SELECT reconcile_model FROM positions WHERE root_post_id=?", (fixture["root_post_id"],)
    ).fetchone()
    assert row["reconcile_model"] == "user"
    assert audited.symbol == fixture["expected_reconciliation"]["symbol"]
    conn.close()


# ---------------------------------------------------------------------------
# _load_thread: orphan posts (conversation_id IS NULL) must still see their
# own root. Regression coverage for the bug where the fallback query bound
# root_post_id but the root's own conversation_id (NULL) never matched it,
# so the "thread" came back empty and reconcile_thread could never see a
# single-post trade.
# ---------------------------------------------------------------------------


def _insert_bare_post(conn, *, post_id: str, handle: str, conversation_id, text: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        (handle, 1, 1, now_iso()),
    )
    conn.execute(
        "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,text,url,"
        "fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            post_id, handle, conversation_id, None,
            "2026-01-01T00:00:00+00:00", "2026-01-01T05:30:00+05:30",
            text, f"https://x.com/{handle}/status/{post_id}",
            now_iso(), 1, now_iso(),
        ),
    )
    conn.commit()


def test_load_thread_includes_root_for_orphan_post_with_no_conversation_id(tmp_path: Path):
    """The dominant real-corpus shape: a complete trade in one post with no
    thread at all. conversation_id is NULL, so the root must be appended
    explicitly -- this is the exact case that used to return an empty list."""
    conn = init_db(tmp_path / "traderlog.db")
    _insert_bare_post(
        conn,
        post_id="2090677732745335261",
        handle="Fastzonetrader",
        conversation_id=None,
        text="Booked all around 4r impact 1.2% #aeroflex",
    )

    rows = _load_thread(conn, "2090677732745335261")

    assert [r["post_id"] for r in rows] == ["2090677732745335261"]
    conn.close()


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_load_thread_is_a_noop_for_posts_with_a_real_conversation_id(path: Path, tmp_path: Path):
    """For posts that DO have a conversation_id, the root's own conversation_id
    already equals itself, so the raw SQL query already returns the root row
    -- the fix's root-append branch must never fire here. Prove it by
    comparing _load_thread's output directly against the same raw query the
    function runs internally: identical rows, identical order."""
    fixture = _fixture(path)
    conn = init_db(tmp_path / "traderlog.db")
    _seed_thread(conn, fixture)

    raw_rows = conn.execute(
        "SELECT * FROM posts WHERE conversation_id = ? AND handle = ? "
        "ORDER BY ts_utc ASC, post_id ASC",
        (fixture["root_post_id"], fixture["handle"]),
    ).fetchall()
    thread_rows = _load_thread(conn, fixture["root_post_id"])

    assert [r["post_id"] for r in thread_rows] == [r["post_id"] for r in raw_rows]
    assert fixture["root_post_id"] in {r["post_id"] for r in raw_rows}, (
        "fixture sanity check: the raw query must already include the root "
        "for this test to actually exercise the no-op path"
    )
    conn.close()


@pytest.mark.parametrize("path", FIXTURES, ids=lambda p: p.stem)
def test_load_thread_never_duplicates_root_when_it_already_matches(path: Path, tmp_path: Path):
    fixture = _fixture(path)
    conn = init_db(tmp_path / "traderlog.db")
    _seed_thread(conn, fixture)

    rows = _load_thread(conn, fixture["root_post_id"])

    post_ids = [r["post_id"] for r in rows]
    assert post_ids.count(fixture["root_post_id"]) == 1
    conn.close()


# ---------------------------------------------------------------------------
# rejection tests -- the evidence/unresolved invariants themselves
# ---------------------------------------------------------------------------


def _valid_payload_and_posts() -> tuple[dict, list[dict]]:
    fixture = _fixture(FIXTURES[0])
    return dict(fixture["expected_reconciliation"]), fixture["thread"]


def test_populated_field_without_citation_is_rejected():
    payload, posts = _valid_payload_and_posts()
    del payload["evidence"]["entries[0].price"]
    with pytest.raises(ReconcileValidationError, match="no evidence"):
        validate_reconciliation(payload, posts)


def test_evidence_citing_a_post_outside_the_thread_is_rejected():
    payload, posts = _valid_payload_and_posts()
    payload["evidence"]["entries[0].price"] = "9999999999999999999"
    with pytest.raises(ReconcileValidationError, match="not present in the input thread"):
        validate_reconciliation(payload, posts)


def test_evidence_citing_a_nonexistent_field_is_rejected():
    payload, posts = _valid_payload_and_posts()
    payload["evidence"]["stop.price"] = posts[0]["post_id"]  # stop is null in this fixture
    with pytest.raises(ReconcileValidationError, match="not populated"):
        validate_reconciliation(payload, posts)


def test_symbol_not_present_in_thread_text_is_rejected():
    payload, posts = _valid_payload_and_posts()
    payload["symbol"] = "TOTALLYUNRELATED"
    with pytest.raises(ReconcileValidationError, match="does not appear"):
        validate_reconciliation(payload, posts)


def test_entry_post_id_not_in_thread_is_rejected():
    payload, posts = _valid_payload_and_posts()
    payload["entries"][0]["post_id"] = "not-in-this-thread"
    with pytest.raises(ReconcileValidationError, match="not in the input thread"):
        validate_reconciliation(payload, posts)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p.update(status="entered"), "status"),
        (lambda p: p.update(confidence=1.5), "confidence"),
        (lambda p: p.update(extra_field="nope"), "unknown"),
        (lambda p: p["unresolved"].append(""), "unresolved"),
    ],
)
def test_reconciliation_validation_rejects_out_of_contract_payloads(mutate, message: str):
    payload, posts = _valid_payload_and_posts()
    mutate(payload)
    with pytest.raises(ReconcileValidationError, match=message):
        validate_reconciliation(payload, posts)


# ---------------------------------------------------------------------------
# synthetic (NOT a real trader post) full-field coverage: adds / stop-move /
# target-hit / full exit / net_result_pct / holding_days / event-kind mapping.
# The three golden fixtures are thin by design (see their "notes"); this
# exercises code paths the honest real corpus does not happen to reach.
# ---------------------------------------------------------------------------


def _synthetic_full_lifecycle_thread() -> list[dict]:
    return [
        {
            "post_id": "s1", "handle": "synthetic", "conversation_id": "s1", "in_reply_to": None,
            "ts_utc": "2026-01-01T00:00:00+00:00", "ts_ist": "2026-01-01T05:30:00+05:30",
            "url": "https://x.com/synthetic/status/s1", "text": "LONG TESTCO at 100, sl 90",
        },
        {
            "post_id": "s2", "handle": "synthetic", "conversation_id": "s1", "in_reply_to": "s1",
            "ts_utc": "2026-01-02T00:00:00+00:00", "ts_ist": "2026-01-02T05:30:00+05:30",
            "url": "https://x.com/synthetic/status/s2", "text": "added 25% more at 110, sl to cost 100, tgt 130",
        },
        {
            "post_id": "s3", "handle": "synthetic", "conversation_id": "s1", "in_reply_to": "s2",
            "ts_utc": "2026-01-05T00:00:00+00:00", "ts_ist": "2026-01-05T05:30:00+05:30",
            "url": "https://x.com/synthetic/status/s3", "text": "tgt hit, booked full at 130, +18%",
        },
    ]


def _synthetic_full_lifecycle_payload() -> dict:
    return {
        "symbol": "TESTCO",
        "status": "closed",
        "entries": [{"price": 100, "date": "2026-01-01", "post_id": "s1"}],
        "adds": [{"price": 110, "date": "2026-01-02", "qty_pct": 25, "post_id": "s2"}],
        "stop": {"price": 100, "post_id": "s2", "moved_from": 90},
        "targets": [{"price": 130, "hit": True, "post_id": "s3"}],
        "exits": [{"price": 130, "date": "2026-01-05", "qty_pct": 100, "post_id": "s3"}],
        "net_result_pct": 18.0,
        "holding_days": 4,
        "confidence": 0.95,
        "unresolved": [],
        "evidence": {
            "symbol": "s1",
            "entries[0].price": "s1",
            "entries[0].date": "s1",
            "adds[0].price": "s2",
            "adds[0].date": "s2",
            "adds[0].qty_pct": "s2",
            "stop.price": "s2",
            "stop.moved_from": "s2",
            "targets[0].price": "s3",
            "targets[0].hit": "s3",
            "exits[0].price": "s3",
            "exits[0].date": "s3",
            "exits[0].qty_pct": "s3",
            "net_result_pct": "s3",
            "holding_days": "s3",
        },
    }


def test_synthetic_full_lifecycle_validates_and_round_trips():
    posts = _synthetic_full_lifecycle_thread()
    payload = _synthetic_full_lifecycle_payload()
    result = validate_reconciliation(payload, posts)
    assert result.status == "closed"
    assert result.net_result_pct == 18.0
    assert result.holding_days == 4
    assert result.to_state_dict() == payload


def test_synthetic_full_lifecycle_writes_correctly_kinded_events(tmp_path: Path):
    posts = _synthetic_full_lifecycle_thread()
    payload = _synthetic_full_lifecycle_payload()
    conn = init_db(tmp_path / "traderlog.db")
    conn.execute(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        ("synthetic", 1, 1, now_iso()),
    )
    for post in posts:
        conn.execute(
            "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,text,url,"
            "fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                post["post_id"], post["handle"], post["conversation_id"], post["in_reply_to"],
                post["ts_utc"], post["ts_ist"], post["text"], post["url"], now_iso(), 1, now_iso(),
            ),
        )
    conn.commit()

    def chat_fn(**kwargs):
        return ProviderResult(content=payload, model="test/smart", provider="test", run_id=1)

    reconcile_thread(conn, "s1", chat_fn=chat_fn)
    pos = conn.execute("SELECT * FROM positions WHERE root_post_id='s1'").fetchone()
    events = conn.execute(
        "SELECT kind, price, qty_pct, note, post_id FROM position_events "
        "WHERE position_id=? ORDER BY seq", (pos["position_id"],),
    ).fetchall()
    kinds = [e["kind"] for e in events]
    assert kinds == ["entry", "add", "sl_move", "target_hit", "exit"]
    assert events[2]["note"] == "moved from 90"
    assert events[4]["qty_pct"] == 100
    assert pos["is_mock"] == 1
    conn.close()
