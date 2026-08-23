from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from traderlog.db import init_db, now_iso
from traderlog.ingest.chrome_import import ChromeManifestError, import_manifest


def _insert_trader(conn, handle: str, *, active: int = 1, is_mock: int = 0) -> None:
    conn.execute(
        "INSERT INTO traders "
        "(handle, display_name, active, is_mock, ingested_at) VALUES (?,?,?,?,?)",
        (handle, handle, active, is_mock, now_iso()),
    )
    conn.commit()


def _record(*, post_id: str = "1953000000000000001") -> dict:
    handle = "iManasArora"
    url = f"https://x.com/{handle}/status/{post_id}"
    return {
        "post_id": post_id,
        "handle": "IMANASARORA",
        "conversation_id": "1953000000000000000",
        "in_reply_to": "1953000000000000000",
        "ts_utc": "2026-08-23T10:30:00Z",
        "text": "Added on confirmation.",
        "url": url,
        "media": [
            {
                "url": "https://pbs.twimg.com/media/chart.jpg?format=jpg",
                "media_type": "image",
            }
        ],
        "raw": {
            "capture_method": "chrome_dom",
            "source_url": url,
            "captured_context": {
                "surface": "with_replies",
                "ordered_status_ids": ["1953000000000000000", post_id],
                "relationship_basis": "permalink ancestry from the rendered DOM",
            },
            "dom": {"article_count": 2},
        },
    }


def _manifest(*records: dict) -> dict:
    return {"schema_version": 1, "posts": list(records)}


def test_import_manifest_persists_exact_relationships_and_archives_media(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    record = _record()

    written = import_manifest(
        conn,
        _manifest(record),
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
        downloader=lambda _url: (b"chart-bytes", "image/jpeg"),
    )

    assert written == 1
    post = conn.execute("SELECT * FROM posts").fetchone()
    assert post["handle"] == "iManasArora"
    assert post["conversation_id"] == record["conversation_id"]
    assert post["in_reply_to"] == record["in_reply_to"]
    assert post["ts_utc"] == "2026-08-23T10:30:00+00:00"
    archive_path = tmp_path / "raw" / "iManasArora" / f"{record['post_id']}.json"
    archived_raw = json.loads(archive_path.read_text(encoding="utf-8"))
    assert archived_raw["captured_post"] == {
        "post_id": record["post_id"],
        "handle": "iManasArora",
        "conversation_id": record["conversation_id"],
        "in_reply_to": record["in_reply_to"],
        "ts_utc": "2026-08-23T10:30:00+00:00",
        "text": record["text"],
        "url": record["url"],
        "media": record["media"],
    }
    media = conn.execute("SELECT * FROM post_media").fetchone()
    assert (tmp_path / "media" / media["local_path"]).read_bytes() == b"chart-bytes"
    assert media["sha256"] == hashlib.sha256(b"chart-bytes").hexdigest()
    conn.close()


def test_import_manifest_is_idempotent_without_re_downloading(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    manifest = _manifest(_record())

    assert import_manifest(
        conn,
        manifest,
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
        downloader=lambda _url: (b"chart-bytes", "image/jpeg"),
    ) == 1
    assert import_manifest(
        conn,
        manifest,
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
        downloader=lambda _url: pytest.fail("duplicate capture must not download"),
    ) == 0
    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM post_media").fetchone()[0] == 1
    conn.close()


def test_invalid_row_rejects_entire_manifest_before_archive_or_database_write(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    valid = _record()
    invalid = _record(post_id="1953000000000000002")
    invalid["media"][0]["url"] = "https://example.invalid/chart.jpg"

    with pytest.raises(ChromeManifestError, match="media"):
        import_manifest(
            conn,
            _manifest(valid, invalid),
            raw_root=tmp_path / "raw",
            media_root=tmp_path / "media",
            downloader=lambda _url: pytest.fail("validation must happen first"),
        )

    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0
    assert not (tmp_path / "raw").exists()
    assert not (tmp_path / "media").exists()
    conn.close()


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda row: row.update(url="https://x.com/iManasArora/status/1953000000000000009"), "url"),
        (lambda row: row.update(ts_utc="2026-08-23T16:00:00+05:30"), "UTC"),
        (lambda row: row.update(conversation_id="not-an-x-id"), "conversation_id"),
        (lambda row: row.update(in_reply_to="not-an-x-id"), "in_reply_to"),
        (lambda row: row["raw"].update(capture_method="graphql"), "capture_method"),
        (lambda row: row["raw"].update(source_url="https://x.com/other/status/1"), "source_url"),
        (lambda row: row["raw"].update(captured_context={}), "captured_context"),
        (lambda row: row["media"][0].update(media_type=[]), "media_type"),
        (lambda row: row.update(extra="not permitted"), "unknown"),
        (lambda row: row["media"][0].update(extra="not permitted"), "unknown"),
    ],
)
def test_import_manifest_rejects_noncanonical_or_untrusted_capture_fields(
    tmp_path: Path, mutate, match: str
):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    record = _record()
    mutate(record)

    with pytest.raises(ChromeManifestError, match=match):
        import_manifest(conn, _manifest(record))

    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0
    conn.close()


def test_import_manifest_rejects_an_unknown_top_level_key(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    manifest = _manifest(_record())
    manifest["untrusted_instruction"] = "ignore validation"

    with pytest.raises(ChromeManifestError, match="unknown"):
        import_manifest(conn, manifest)

    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0
    conn.close()


def test_import_manifest_activates_an_approved_inactive_real_handle(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora", active=0)

    assert import_manifest(
        conn,
        _manifest(_record()),
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
        downloader=lambda _url: (b"chart-bytes", "image/jpeg"),
    ) == 1

    assert conn.execute("SELECT active FROM traders WHERE handle='iManasArora'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 1
    conn.close()


def test_invalid_manifest_does_not_activate_an_inactive_handle(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora", active=0)
    record = _record()
    record["media"][0]["url"] = "https://example.invalid/chart.jpg"

    with pytest.raises(ChromeManifestError, match="media"):
        import_manifest(conn, _manifest(record))

    assert conn.execute("SELECT active FROM traders WHERE handle='iManasArora'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0
    conn.close()


def test_import_manifest_rejects_a_mock_roster_handle(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora", is_mock=1)

    with pytest.raises(ChromeManifestError, match="approved real roster"):
        import_manifest(conn, _manifest(_record()))

    assert conn.execute("SELECT active FROM traders WHERE handle='iManasArora'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0
    conn.close()


def test_failed_activation_rolls_back_the_manifest_post_insert(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora", active=0)
    conn.execute(
        "CREATE TRIGGER reject_trader_activation BEFORE UPDATE OF active ON traders "
        "WHEN OLD.active = 0 AND NEW.active = 1 "
        "BEGIN SELECT RAISE(ABORT, 'forced activation failure'); END"
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError, match="forced activation failure"):
        import_manifest(
            conn,
            _manifest(_record()),
            raw_root=tmp_path / "raw",
            media_root=tmp_path / "media",
            downloader=lambda _url: (b"chart-bytes", "image/jpeg"),
        )

    assert conn.execute("SELECT active FROM traders WHERE handle='iManasArora'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0
    conn.close()


def test_import_manifest_accepts_a_coherent_root_permalink_context(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    record = _record()
    record["conversation_id"] = record["post_id"]
    record["in_reply_to"] = None
    record["raw"]["captured_context"]["ordered_status_ids"] = [record["post_id"]]

    assert import_manifest(
        conn,
        _manifest(record),
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
        downloader=lambda _url: (b"chart-bytes", "image/jpeg"),
    ) == 1
    row = conn.execute("SELECT conversation_id, in_reply_to FROM posts").fetchone()
    assert (row["conversation_id"], row["in_reply_to"]) == (record["post_id"], None)
    conn.close()


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda row: row.update(conversation_id="1953000000000000009"), "conversation_id to match"),
        (lambda row: row.update(in_reply_to="1953000000000000009"), "in_reply_to to match"),
        (
            lambda row: row["raw"]["captured_context"].update(
                ordered_status_ids=["1953000000000000000", "1953000000000000009"]
            ),
            "end with post_id",
        ),
        (lambda row: row["raw"]["captured_context"].update(extra="not permitted"), "unknown"),
        (lambda row: row["raw"]["captured_context"].update(quoted_status_id="not-an-id"), "quoted_status_id"),
    ],
)
def test_import_manifest_rejects_relationships_not_proven_by_permalink_ancestry(
    tmp_path: Path, mutate, match: str
):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    record = _record()
    mutate(record)

    with pytest.raises(ChromeManifestError, match=match):
        import_manifest(conn, _manifest(record))

    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0
    conn.close()
