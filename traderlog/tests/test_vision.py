from __future__ import annotations

import json
from pathlib import Path

import pytest

from traderlog.db import init_db, now_iso
from traderlog.llm.provider import ProviderResult
from traderlog.llm.vision import (
    VisionValidationError,
    apply_verified_vision,
    validate_vision,
    vision_pass,
)


GOLDEN = Path(__file__).parent / "golden"
RATEGAIN_FIXTURE = GOLDEN / "2090713569793126757_rategain_open_position_reconcile.json"
FCL_VCPSWING_FIXTURE = GOLDEN / "2085214288961237368_fcl_vcpswing_open_position_reconcile.json"


def _fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _seed_post_with_media(conn, *, post_id: str, handle: str, idx: int, is_mock: int = 0) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        (handle, 1, is_mock, now_iso()),
    )
    conn.execute(
        "INSERT INTO posts (post_id,handle,conversation_id,in_reply_to,ts_utc,ts_ist,text,url,"
        "fetched_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (post_id, handle, post_id, None, now_iso(), now_iso(), "#SYMBOL", "https://x.com/x", now_iso(), is_mock, now_iso()),
    )
    conn.execute(
        "INSERT INTO post_media (post_id, idx, local_path, sha256, media_type, is_mock, ingested_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (post_id, idx, f"{post_id}_{idx}.jpg", "deadbeef", "image", is_mock, now_iso()),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# validate_vision: the two disciplines the prompt states in prose
# ---------------------------------------------------------------------------


def test_hand_verified_readable_chart_transcription_validates():
    fixture = _fixture(RATEGAIN_FIXTURE)
    payload = fixture["vision"]["2090713569793126757"][1]["expected_vision"]
    result = validate_vision(payload)
    assert result.chart_symbol == "RATEGAIN"
    assert result.unreadable is False
    assert result.annotated_levels == ()  # no numeric label on the 'E' marker -- correctly empty
    assert "TradingView" in result.text_in_image


def test_hand_verified_unreadable_non_chart_screenshot_validates_with_empty_arrays():
    fixture = _fixture(RATEGAIN_FIXTURE)
    payload = fixture["vision"]["2090713569793126757"][0]["expected_vision"]
    result = validate_vision(payload)
    assert result.unreadable is True
    assert result.text_in_image == ()
    assert result.annotated_levels == ()
    assert "holdings-table" in result.structure_note


def test_unreadable_true_with_nonempty_text_in_image_is_rejected():
    payload = {
        "chart_symbol": None,
        "timeframe": "unknown",
        "text_in_image": ["45.75"],
        "annotated_levels": [],
        "structure_note": "not a chart",
        "confidence": 0.0,
        "unreadable": True,
    }
    with pytest.raises(VisionValidationError, match="unreadable=true"):
        validate_vision(payload)


def test_unreadable_true_with_nonempty_annotated_levels_is_rejected():
    payload = {
        "chart_symbol": "FCL",
        "timeframe": "daily",
        "text_in_image": [],
        "annotated_levels": [{"kind": "entry", "price": 39.05, "source": "buy order"}],
        "structure_note": "not a chart",
        "confidence": 0.0,
        "unreadable": True,
    }
    with pytest.raises(VisionValidationError, match="unreadable=true"):
        validate_vision(payload)


def test_annotated_level_without_source_is_rejected():
    """vision.md rule 2: every annotated_levels[] entry needs the visual justification."""
    payload = {
        "chart_symbol": "FCL",
        "timeframe": "daily",
        "text_in_image": [],
        "annotated_levels": [{"kind": "stop", "price": 39.05, "source": ""}],
        "structure_note": "a chart",
        "confidence": 0.5,
        "unreadable": False,
    }
    with pytest.raises(VisionValidationError, match="visual evidence"):
        validate_vision(payload)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda p: p.update(timeframe="1h"), "timeframe"),
        (lambda p: p.update(confidence=float("nan")), "confidence"),
        (lambda p: p.update(chart_symbol="not a ticker!"), "chart_symbol"),
        (lambda p: p.update(extra="not permitted"), "unknown"),
    ],
)
def test_vision_validation_rejects_out_of_contract_payloads(mutate, message: str):
    fixture = _fixture(RATEGAIN_FIXTURE)
    payload = dict(fixture["vision"]["2090713569793126757"][1]["expected_vision"])
    mutate(payload)
    with pytest.raises(VisionValidationError, match=message):
        validate_vision(payload)


# ---------------------------------------------------------------------------
# write path
# ---------------------------------------------------------------------------


def test_apply_verified_vision_is_the_sole_writer_and_idempotent(tmp_path: Path):
    fixture = _fixture(RATEGAIN_FIXTURE)
    payload = fixture["vision"]["2090713569793126757"][1]["expected_vision"]
    conn = init_db(tmp_path / "traderlog.db")
    _seed_post_with_media(conn, post_id="2090713569793126757", handle="iManasArora", idx=1)

    first = apply_verified_vision(conn, "2090713569793126757", 1, payload)
    second = apply_verified_vision(conn, "2090713569793126757", 1, payload)
    assert first == second

    row = conn.execute(
        "SELECT vision_json, vision_model FROM post_media WHERE post_id=? AND idx=1",
        ("2090713569793126757",),
    ).fetchone()
    stored = json.loads(row["vision_json"])
    assert stored["chart_symbol"] == "RATEGAIN"
    assert row["vision_model"] == "user"
    assert conn.execute("SELECT COUNT(*) FROM post_media").fetchone()[0] == 1
    conn.close()


def test_vision_pass_uses_vision_tier_json_provider_and_persists_provider_audit_fields(
    tmp_path: Path,
):
    fixture = _fixture(RATEGAIN_FIXTURE)
    payload = fixture["vision"]["2090713569793126757"][1]["expected_vision"]
    conn = init_db(tmp_path / "traderlog.db")
    _seed_post_with_media(conn, post_id="2090713569793126757", handle="iManasArora", idx=1)
    # vision_pass reads the local archive file -- point local_path at a real file
    # under a throwaway media root instead of hitting data/media/.
    media_root = tmp_path / "media"
    media_root.mkdir()
    (media_root / "2090713569793126757_1.jpg").write_bytes(b"\xff\xd8\xff\xe0fakejpeg")

    calls: list[dict] = []

    def chat_fn(**kwargs):
        calls.append(kwargs)
        return ProviderResult(content=payload, model="test/vision", provider="test", run_id=91)

    result = vision_pass(
        conn, "2090713569793126757", 1, chat_fn=chat_fn, media_root=media_root
    )

    assert result.chart_symbol == "RATEGAIN"
    assert calls[0]["tier"] == "vision"
    assert calls[0]["json_schema"] is True
    assert calls[0]["task"] == "vision"
    assert calls[0]["ref_id"] == "2090713569793126757"
    # multimodal content part per CONTRACTS.md #6
    assert isinstance(calls[0]["user"], list)
    assert calls[0]["user"][-1]["type"] == "image_url"
    assert calls[0]["user"][-1]["image_url"]["url"].startswith("data:image/jpeg;base64,")

    row = conn.execute(
        "SELECT vision_model FROM post_media WHERE post_id=? AND idx=1",
        ("2090713569793126757",),
    ).fetchone()
    assert row["vision_model"] == "test/vision"
    conn.close()


def test_vision_pass_raises_when_archive_missing(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _seed_post_with_media(conn, post_id="2090713569793126757", handle="iManasArora", idx=1)
    with pytest.raises(FileNotFoundError):
        vision_pass(
            conn,
            "2090713569793126757",
            1,
            chat_fn=lambda **_: (_ for _ in ()).throw(AssertionError("must not call the model")),
            media_root=tmp_path / "no_such_dir",
        )
    conn.close()
