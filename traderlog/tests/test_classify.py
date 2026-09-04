from __future__ import annotations

import json
from pathlib import Path

import pytest

from traderlog.db import init_db, now_iso
from traderlog.llm.classify import (
    ClassificationValidationError,
    apply_verified_classification,
    classify_post,
    validate_classification,
)
from traderlog.llm.provider import ProviderResult


FIXTURE = (
    Path(__file__).parent / "golden" / "2090713569793126757_rategain_new_position.json"
)
FASTZONE_FIXTURE = (
    Path(__file__).parent / "golden" / "2089923284565700807_fcl_partial_exit.json"
)


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _insert_source_post(conn, post: dict, *, is_mock: int = 0) -> None:
    conn.execute(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        (post["handle"], 1, is_mock, now_iso()),
    )
    conn.execute(
        "INSERT INTO posts "
        "(post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,text,url,"
        "fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (
            post["post_id"],
            post["handle"],
            post["conversation_id"],
            post["in_reply_to"],
            post["ts_utc"],
            post["ts_utc"],
            post["text"],
            post["url"],
            now_iso(),
            is_mock,
            now_iso(),
        ),
    )
    conn.commit()


def test_rategain_fixture_has_exact_new_position_text_and_classification_schema():
    fixture = _fixture()
    post = fixture["post"]
    expected = fixture["expected_classifier"]

    assert set(fixture) == {
        "fixture_version",
        "post",
        "expected_classifier",
        "human_event_label",
    }
    assert fixture["fixture_version"] == 1
    assert set(post) == {
        "post_id",
        "handle",
        "conversation_id",
        "in_reply_to",
        "ts_utc",
        "url",
        "text",
    }
    assert set(expected) == {
        "kind",
        "confidence",
        "symbols",
        "play_type",
        "conviction_words",
        "reason",
    }
    assert post["text"] == (
        "#NewPosition - LONG in #RATEGAIN at 955 \n\nstop 2%\n\n"
        "Target: https://t.ly/_XCrz\n\nDisc: Not a buy recommendation. Do NOT copy "
        "and lose your capital because you are very likely to."
    )
    normalized = validate_classification(expected, post["text"])
    assert normalized.kind == "trade_event"
    assert normalized.symbols == ("RATEGAIN",)
    assert normalized.confidence == 1.0
    assert fixture["human_event_label"] == {
        "post_id": post["post_id"],
        "event_taxonomy": "entry",
        "source": "user",
        "scope": "classification_metadata_only",
    }


def test_fcl_partial_exit_fixture_has_source_grounded_classification_schema():
    fixture = json.loads(FASTZONE_FIXTURE.read_text(encoding="utf-8"))
    post = fixture["post"]
    expected = fixture["expected_classifier"]

    assert set(fixture) == {
        "fixture_version",
        "post",
        "expected_classifier",
        "human_event_label",
    }
    assert fixture["fixture_version"] == 1
    assert set(post) == {
        "post_id",
        "handle",
        "conversation_id",
        "in_reply_to",
        "ts_utc",
        "url",
        "text",
    }
    assert set(expected) == {
        "kind",
        "confidence",
        "symbols",
        "play_type",
        "conviction_words",
        "reason",
    }
    assert post["text"] == (
        "Sold 1/3rd around 3r on day one of move trailing rest risk free #fcl\n"
        "Everything risk free now with 2/3rd size holding all 👇"
    )
    normalized = validate_classification(expected, post["text"])
    assert normalized.kind == "trade_event"
    assert normalized.symbols == ("FCL",)
    assert normalized.confidence == 1.0
    assert normalized.play_type == "unclear"
    assert normalized.conviction_words == ()
    assert fixture["human_event_label"] == {
        "post_id": post["post_id"],
        "event_taxonomy": "partial_exit",
        "source": "user",
        "scope": "classification_metadata_only",
    }


def test_verified_classification_upsert_is_idempotent_and_does_not_create_event(tmp_path: Path):
    fixture = _fixture()
    conn = init_db(tmp_path / "traderlog.db")
    _insert_source_post(conn, fixture["post"])

    first = apply_verified_classification(
        conn,
        fixture["post"]["post_id"],
        fixture["expected_classifier"],
    )
    second = apply_verified_classification(
        conn,
        fixture["post"]["post_id"],
        fixture["expected_classifier"],
    )

    assert first == second
    row = conn.execute("SELECT * FROM post_class").fetchone()
    assert row["kind"] == "trade_event"
    assert json.loads(row["symbols"]) == ["RATEGAIN"]
    assert row["model"] == "user"
    assert row["run_id"] is None
    assert row["is_mock"] == 0
    assert conn.execute("SELECT COUNT(*) FROM post_class").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM position_events").fetchone()[0] == 0
    conn.close()


def test_classify_post_uses_cheap_json_provider_and_persists_provider_audit_fields(
    tmp_path: Path,
):
    fixture = _fixture()
    conn = init_db(tmp_path / "traderlog.db")
    _insert_source_post(conn, fixture["post"])
    calls: list[dict] = []

    def chat_fn(**kwargs):
        calls.append(kwargs)
        return ProviderResult(
            content=fixture["expected_classifier"],
            model="test/cheap",
            provider="test",
            run_id=73,
        )

    result = classify_post(conn, fixture["post"]["post_id"], chat_fn=chat_fn)

    assert result.kind == "trade_event"
    assert calls[0]["tier"] == "cheap"
    assert calls[0]["json_schema"] is True
    assert calls[0]["task"] == "classify"
    assert calls[0]["ref_id"] == fixture["post"]["post_id"]
    assert "KIND definitions" in calls[0]["system"]
    assert "CONVICTION_WORDS" in calls[0]["system"]
    row = conn.execute("SELECT * FROM post_class").fetchone()
    assert (row["model"], row["run_id"], row["is_mock"]) == ("test/cheap", 73, 0)
    assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0
    conn.close()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload.update(kind="entry"), "kind"),
        (lambda payload: payload.update(confidence=float("nan")), "confidence"),
        (lambda payload: payload.update(symbols=["UNKNOWN"]), "source text"),
        (lambda payload: payload.update(play_type="breakout", kind="breadth"), "play_type"),
        (lambda payload: payload.update(conviction_words=["starter"]), "conviction_words"),
        (lambda payload: payload.update(reason=""), "reason"),
        (lambda payload: payload.update(extra="not permitted"), "unknown"),
    ],
)
def test_classifier_validation_rejects_non_contract_or_non_source_grounded_fields(
    mutate, message: str
):
    fixture = _fixture()
    payload = dict(fixture["expected_classifier"])
    mutate(payload)

    with pytest.raises(ClassificationValidationError, match=message):
        validate_classification(payload, fixture["post"]["text"])
