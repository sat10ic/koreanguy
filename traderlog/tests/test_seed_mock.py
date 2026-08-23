from __future__ import annotations

import sqlite3

import pytest

from traderlog.db import init_db, now_iso
from traderlog.seed_mock import MOCK_TABLES, clear_mock, seed


EXPECTED_MOCK_TABLES = [
    "edu_links",
    "position_events",
    "post_class",
    "post_media",
    "breadth_notes",
    "watch_ideas",
    "edu_items",
    "review_queue",
    "trader_style",
    "positions",
    "posts",
    "themes",
    "regime_daily",
    "symbol_attention",
    "traders",
]


def _insert_trader(conn, handle: str, *, is_mock: int) -> None:
    conn.execute(
        "INSERT INTO traders (handle, active, is_mock, ingested_at) VALUES (?,?,?,?)",
        (handle, 1, is_mock, now_iso()),
    )


def _insert_post(conn, post_id: str, handle: str, *, is_mock: int) -> None:
    stamp = now_iso()
    conn.execute(
        "INSERT INTO posts "
        "(post_id,handle,ts_utc,ts_ist,text,url,fetched_at,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            post_id,
            handle,
            stamp,
            stamp,
            f"{post_id} source text",
            f"https://x.com/{handle}/status/{post_id}",
            stamp,
            is_mock,
            stamp,
        ),
    )


def _insert_position(conn, position_id: str, handle: str, *, is_mock: int) -> None:
    conn.execute(
        "INSERT INTO positions "
        "(position_id,handle,symbol,root_post_id,status,state_json,evidence_json,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (position_id, handle, "RATEGAIN", f"root-{position_id}", "open", "{}", "{}", is_mock, now_iso()),
    )


def _mixed_database(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")
    _insert_trader(conn, "real", is_mock=0)
    _insert_post(conn, "real-post", "real", is_mock=0)
    conn.execute(
        "INSERT INTO post_class (post_id,kind,confidence,symbols,model,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("real-post", "trade_event", 0.8, '["RATEGAIN"]', "real-model", 0, now_iso()),
    )

    _insert_trader(conn, "mock", is_mock=1)
    _insert_post(conn, "mock-post", "mock", is_mock=1)
    _insert_position(conn, "mock-position", "mock", is_mock=1)
    conn.execute(
        "INSERT INTO post_media (post_id,idx,local_path,sha256,media_type,is_mock,ingested_at) "
        "VALUES (?,?,?,?,?,?,?)",
        ("mock-post", 0, "mock/chart.png", "abc", "image", 1, now_iso()),
    )
    # Legacy seed defect: this row inherited the schema default (0), but its
    # source post proves the classification is mock provenance.
    conn.execute(
        "INSERT INTO post_class (post_id,kind,is_mock,ingested_at) VALUES (?,?,0,?)",
        ("mock-post", "trade_event", now_iso()),
    )
    conn.execute(
        "INSERT INTO position_events "
        "(position_id,post_id,kind,stated_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
        ("mock-position", "mock-post", "entry", now_iso(), 1, now_iso()),
    )
    conn.execute(
        "INSERT INTO breadth_notes "
        "(post_id,handle,trade_date,is_mock,ingested_at) VALUES (?,?,?,?,?)",
        ("mock-post", "mock", "2026-08-22", 1, now_iso()),
    )
    conn.execute(
        "INSERT INTO watch_ideas "
        "(post_id,handle,symbol,kind,stated_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?,?)",
        ("mock-post", "mock", "RATEGAIN", "watch", now_iso(), 1, now_iso()),
    )
    conn.execute(
        "INSERT INTO themes (name,is_mock,ingested_at) VALUES (?,?,?)",
        ("mock theme", 1, now_iso()),
    )
    edu_id = conn.execute(
        "INSERT INTO edu_items "
        "(post_id,handle,principle_text,stated_at,is_mock,ingested_at) VALUES (?,?,?,?,?,?)",
        ("mock-post", "mock", "mock principle", now_iso(), 1, now_iso()),
    ).lastrowid
    conn.execute(
        "INSERT INTO edu_links (edu_id,position_id,verdict,is_mock,ingested_at) VALUES (?,?,?,?,?)",
        (edu_id, "mock-position", "na", 1, now_iso()),
    )
    conn.execute(
        "INSERT INTO trader_style (handle,as_of,is_mock,ingested_at) VALUES (?,?,?,?)",
        ("mock", "2026-08-22", 1, now_iso()),
    )
    conn.execute(
        "INSERT INTO regime_daily (trade_date,is_mock,ingested_at) VALUES (?,?,?)",
        ("2026-08-22", 1, now_iso()),
    )
    conn.execute(
        "INSERT INTO symbol_attention (symbol,trade_date,is_mock,ingested_at) VALUES (?,?,?,?)",
        ("RATEGAIN", "2026-08-22", 1, now_iso()),
    )
    conn.execute(
        "INSERT INTO review_queue (kind,question,is_mock,ingested_at) VALUES (?,?,?,?)",
        ("low_conf_parse", "mock question", 1, now_iso()),
    )
    conn.commit()
    return conn


def test_clear_mock_removes_all_mock_provenance_and_preserves_real_rows(tmp_path):
    conn = _mixed_database(tmp_path)
    before = {
        "traders": tuple(conn.execute("SELECT * FROM traders WHERE handle='real'").fetchone()),
        "posts": tuple(conn.execute("SELECT * FROM posts WHERE post_id='real-post'").fetchone()),
        "post_class": tuple(
            conn.execute("SELECT * FROM post_class WHERE post_id='real-post'").fetchone()
        ),
    }

    removed = clear_mock(conn)

    assert removed == len(EXPECTED_MOCK_TABLES)
    assert MOCK_TABLES == EXPECTED_MOCK_TABLES
    assert conn.execute("SELECT COUNT(*) FROM post_class WHERE post_id='mock-post'").fetchone()[0] == 0
    for table in EXPECTED_MOCK_TABLES:
        assert conn.execute(f"SELECT COUNT(*) FROM {table} WHERE is_mock=1").fetchone()[0] == 0
    after = {
        "traders": tuple(conn.execute("SELECT * FROM traders WHERE handle='real'").fetchone()),
        "posts": tuple(conn.execute("SELECT * FROM posts WHERE post_id='real-post'").fetchone()),
        "post_class": tuple(
            conn.execute("SELECT * FROM post_class WHERE post_id='real-post'").fetchone()
        ),
    }
    assert after == before
    assert clear_mock(conn) == 0
    conn.close()


def test_clear_mock_rolls_back_every_delete_if_a_child_purge_fails(tmp_path):
    conn = _mixed_database(tmp_path)
    conn.execute(
        "CREATE TRIGGER reject_mock_theme_delete BEFORE DELETE ON themes "
        "WHEN OLD.is_mock = 1 BEGIN SELECT RAISE(ABORT, 'forced purge failure'); END"
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError, match="forced purge failure"):
        clear_mock(conn)

    assert conn.execute("SELECT COUNT(*) FROM posts WHERE post_id='mock-post'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM post_class WHERE post_id='mock-post'").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM position_events WHERE is_mock=1").fetchone()[0] == 1
    conn.close()


def test_seed_marks_every_post_class_row_as_mock(tmp_path):
    conn = init_db(tmp_path / "traderlog.db")

    seeded = seed(conn)

    assert seeded["posts"] > 0
    assert conn.execute("SELECT COUNT(*) FROM post_class WHERE is_mock=0").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM post_class").fetchone()[0] == seeded["posts"]
    conn.close()
