from __future__ import annotations

import json
from pathlib import Path

import pytest

from traderlog.db import init_db, now_iso
from traderlog.ingest.archive import archive_post
from traderlog.ingest.provisional_import import (
    APPROVED_HANDLES,
    ProvisionalImportError,
    import_provisional,
    load_provisional_posts,
)


def _insert_trader(conn, handle: str) -> None:
    conn.execute(
        "INSERT INTO traders (handle, display_name, active, is_mock, ingested_at) VALUES (?,?,?,?,?)",
        (handle, handle, 1, 0, now_iso()),
    )
    conn.commit()


def _record(
    *,
    handle: str = "iManasArora",
    post_id: str = "2090333404718059564",
    text: str = "Moving stop to break-even #SUVEN",
    media_urls: list[str] | None = None,
    is_pinned: bool | None = False,
) -> dict:
    record = {
        "post_id": post_id,
        "handle": handle,
        "posted_at": "2026-08-20T07:01:34.000Z",
        "text": text,
        "url": f"https://x.com/{handle}/status/{post_id}",
        "media_urls": media_urls or [],
        "article_excerpt": "Untrusted display excerpt that must never become post text.",
        "surfaces": ["profile_replies"],
    }
    if is_pinned is not None:
        record["is_pinned"] = is_pinned
    return record


def _source(*records: dict) -> dict:
    output: dict[str, dict] = {}
    for record in records:
        output.setdefault(record["handle"], {})[record["post_id"]] = record
    return output


def _import(conn, source, tmp_path: Path, **kwargs):
    return import_provisional(
        conn,
        source,
        handles=kwargs.pop("handles", ["iManasArora"]),
        raw_root=tmp_path / "raw",
        media_root=tmp_path / "media",
        downloader=kwargs.pop("downloader", lambda _url: (b"media", "image/jpeg")),
        **kwargs,
    )


def test_approved_handles_lock_the_owner_authorized_roster():
    # Owner-authorized roster, 17 handles as of the 2026-08-24 expansion (HANDOFF.md).
    assert len(APPROVED_HANDLES) == 17
    assert len(set(APPROVED_HANDLES)) == 17
    assert APPROVED_HANDLES == (
        "iManasArora",
        "Fastzonetrader",
        "tradinghustlr",
        "VCPSwing",
        "StocksNerd",
        "ChartistEdge",
        "iArpanK",
        "mystocks_in",
        "rpmrpm4",
        "thechartist26",
        "SakatasHomma",
        "Trading4Bucks",
        "wealthexpress21",
        "Setups_Swing",
        "investor_sr33",
        "multibaggerwala",
        "AdeptMarket",
    )


def test_selects_approved_handles_and_rejects_unapproved_ones(tmp_path: Path):
    records = [
        _record(handle=handle, post_id=f"2090333404718059{index:03d}")
        for index, handle in enumerate(APPROVED_HANDLES)
    ]
    source = _source(*records)

    selected = load_provisional_posts(source, list(APPROVED_HANDLES))

    assert {post.handle for post, _pinned in selected} == set(APPROVED_HANDLES)
    with pytest.raises(ProvisionalImportError, match="unapproved"):
        load_provisional_posts(source, ["SomeOtherTrader"])


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda record: record.update(post_id="2090333404718059565"), "key"),
        (lambda record: record.update(url="https://x.com/iManasArora/status/1"), "url"),
        (lambda record: record.update(posted_at="2026-08-20T12:31:34+05:30"), "UTC"),
        (lambda record: record.update(handle="imanasaRora"), "handle"),
    ],
)
def test_rejects_strict_source_identity(mutate, match: str):
    record = _record()
    source = _source(record)
    mutate(source["iManasArora"][record["post_id"]])
    with pytest.raises(ProvisionalImportError, match=match):
        load_provisional_posts(source, ["iManasArora"])


def test_dry_run_excludes_pinned_and_empty_without_archiving_or_db_writes(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    good = _record(media_urls=["https://pbs.twimg.com/media/chart.jpg?format=jpg"])
    pinned = _record(post_id="2090333404718059565", is_pinned=True)
    empty = _record(post_id="2090333404718059566", text="   ")

    report = _import(conn, _source(good, pinned, empty), tmp_path, dry_run=True)

    assert report.selected == 3
    assert (report.eligible, report.excluded, report.excluded_pinned, report.excluded_empty) == (1, 2, 1, 1)
    assert (report.existing, report.new, report.media_items, report.new_media_items, report.failed) == (0, 1, 1, 1, {})
    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM traders").fetchone()[0] == 0
    assert not (tmp_path / "raw").exists()
    assert not (tmp_path / "media").exists()
    conn.close()


def test_unproven_ancestry_is_stored_as_null_with_raw_provenance(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    report = _import(conn, _source(_record()), tmp_path)

    assert report.new == 1
    row = conn.execute("SELECT conversation_id, in_reply_to, text, raw_path FROM posts").fetchone()
    assert (row["conversation_id"], row["in_reply_to"]) == (None, None)
    assert row["text"] == "Moving stop to break-even #SUVEN"
    raw = json.loads((tmp_path / "raw" / "iManasArora" / "2090333404718059564.json").read_text())
    assert raw["provisional_record"]["article_excerpt"].startswith("Untrusted")
    assert raw["provenance"]["relationship_status"] == "unresolved"
    conn.close()


def test_proven_permalink_ancestry_is_preserved(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    record = _record(is_pinned=None)
    record.update(
        conversation_id="2090305661993377912",
        in_reply_to="2090329044181225792",
        ordered_status_ids=["2090305661993377912", "2090329044181225792", record["post_id"]],
        relationship_basis="permalink_visible_ancestry",
    )

    assert _import(conn, _source(record), tmp_path).new == 1
    row = conn.execute("SELECT conversation_id, in_reply_to FROM posts").fetchone()
    assert tuple(row) == ("2090305661993377912", "2090329044181225792")
    raw = json.loads((tmp_path / "raw" / "iManasArora" / f"{record['post_id']}.json").read_text())
    assert raw["provenance"]["relationship_status"] == "proven"
    conn.close()


def test_rejects_non_x_media_host_before_any_writes(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    record = _record(media_urls=["https://example.invalid/chart.jpg"])

    with pytest.raises(ProvisionalImportError, match="media URL"):
        _import(conn, _source(record), tmp_path)

    assert conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0] == 0
    assert not (tmp_path / "raw").exists()
    conn.close()


def test_archives_before_indexing_each_post(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    observed = []

    def checking_archiver(post, **kwargs):
        observed.append(conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0])
        return archive_post(post, **kwargs)

    assert _import(conn, _source(_record()), tmp_path, archiver=checking_archiver).new == 1
    assert observed == [0]
    conn.close()


def test_media_failure_isolated_and_never_inserts_that_post(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    good = _record(post_id="2090333404718059564", media_urls=["https://pbs.twimg.com/media/good.jpg"])
    bad = _record(post_id="2090333404718059565", media_urls=["https://pbs.twimg.com/media/bad.jpg"])

    def downloader(url: str):
        if "bad" in url:
            raise OSError("simulated media outage")
        return b"good", "image/jpeg"

    report = _import(conn, _source(good, bad), tmp_path, downloader=downloader)

    assert report.new == 1
    assert set(report.failed) == {bad["post_id"]}
    assert conn.execute("SELECT post_id FROM posts").fetchall()[0][0] == good["post_id"]
    assert conn.execute("SELECT COUNT(*) FROM post_media WHERE post_id=?", (bad["post_id"],)).fetchone()[0] == 0
    conn.close()


def test_idempotence_preserves_first_sight_archive_and_existing_post(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "iManasArora")
    first = _record(text="first capture")
    assert _import(conn, _source(first), tmp_path).new == 1
    second = _record(text="richer later capture")

    report = _import(conn, _source(second), tmp_path, downloader=lambda _url: pytest.fail("must not re-download"))

    assert (report.existing, report.new) == (1, 0)
    assert conn.execute("SELECT text FROM posts").fetchone()[0] == "first capture"
    raw = json.loads((tmp_path / "raw" / "iManasArora" / f"{first['post_id']}.json").read_text())
    assert raw["provisional_record"]["text"] == "first capture"
    conn.close()


def test_first_capture_creates_inactive_watch_roster_row_then_activates_it(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    seen_in_archiver = []

    def roster_checking_archiver(post, **kwargs):
        seen_in_archiver.append(
            tuple(
                conn.execute(
                    "SELECT active, is_mock FROM traders WHERE handle=?", ("StocksNerd",)
                ).fetchone()
            )
        )
        return archive_post(post, **kwargs)

    record = _record(handle="StocksNerd", post_id="2090333404718059570")
    report = _import(
        conn, _source(record), tmp_path, handles=["StocksNerd"],
        archiver=roster_checking_archiver,
    )

    assert report.new == 1
    # roster row must already exist, inactive + real, before store_posts activates it
    assert seen_in_archiver == [(0, 0)]
    row = conn.execute(
        "SELECT tier, tags, active, notes, is_mock FROM traders WHERE handle=?",
        ("StocksNerd",),
    ).fetchone()
    assert tuple(row) == (
        "WATCH",
        '["india","nse"]',
        1,
        "Owner-authorized 2026-08-23; activated on first capture.",
        0,
    )
    assert report.activated_handles == ("StocksNerd",)
    conn.close()


def test_reimport_same_post_is_noop_and_never_duplicates_roster_row(tmp_path: Path):
    conn = init_db(tmp_path / "traderlog.db")
    record = _record(handle="StocksNerd", post_id="2090333404718059570")

    first = _import(conn, _source(record), tmp_path, handles=["StocksNerd"])
    assert first.new == 1
    assert first.activated_handles == ("StocksNerd",)
    assert conn.execute(
        "SELECT COUNT(*) FROM traders WHERE handle=?", ("StocksNerd",)
    ).fetchone()[0] == 1

    second = _import(
        conn,
        _source(record),
        tmp_path,
        handles=["StocksNerd"],
        downloader=lambda _url: pytest.fail("must not re-download"),
    )

    assert (second.existing, second.new, second.activated_handles) == (1, 0, ())
    assert conn.execute(
        "SELECT COUNT(*) FROM traders WHERE handle=?", ("StocksNerd",)
    ).fetchone()[0] == 1
    assert conn.execute(
        "SELECT active FROM traders WHERE handle=?", ("StocksNerd",)
    ).fetchone()[0] == 1
    conn.close()
