"""E-2 — announcement store: knowability rule, catalyst taxonomy, parsing.

The knowability rule is the one that decides whether EP research is honest:
broadcast after the session close (15:30 IST) belongs to the NEXT session.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from unidesk.contracts.base import ContractError
from unidesk.momentum.data.calendar import from_sessions
from unidesk.research.announcements import (
    AnnouncementRecord, broadcast_from_attachment, catalyst_type_for,
    knowable_session, parse_announcements_master_csv, persist_announcements,
)

IST = timezone(timedelta(hours=5, minutes=30))


def _cal(*sessions: str):
    return from_sessions([date.fromisoformat(s) for s in sessions])


def test_broadcast_stamp_parsed_from_archive_url():
    url = "https://nsearchives.nseindia.com/corporate/x_02072026085251_Sales_Report.pdf"
    stamp = broadcast_from_attachment(url)
    assert stamp is not None
    assert stamp.astimezone(IST) == datetime(2026, 7, 2, 8, 52, 51, tzinfo=IST)


def test_pre_close_broadcast_is_knowable_same_session():
    # 08:52 IST broadcast on 02-Jul -> knowable in the 02-Jul session.
    stamp = datetime(2026, 7, 2, 3, 22, 51, tzinfo=timezone.utc)  # 08:52:51 IST
    assert knowable_session(stamp, date(2026, 7, 2), _cal("2026-07-01", "2026-07-02", "2026-07-03")) == date(2026, 7, 2)


def test_post_close_broadcast_belongs_to_the_next_session():
    # 19:05 IST broadcast on 02-Jul (after 15:30 close) -> next session, 03-Jul.
    stamp = datetime(2026, 7, 2, 13, 35, 0, tzinfo=timezone.utc)  # 19:05 IST
    assert knowable_session(stamp, date(2026, 7, 2), _cal("2026-07-02", "2026-07-03")) == date(2026, 7, 3)


def test_post_close_with_no_later_session_raises():
    stamp = datetime(2026, 7, 2, 13, 35, 0, tzinfo=timezone.utc)
    with pytest.raises(ContractError):
        knowable_session(stamp, date(2026, 7, 2), _cal("2026-07-02"))


def test_catalyst_taxonomy():
    assert catalyst_type_for("Outcome of Board Meeting", "approved financial results") == "results"
    assert catalyst_type_for("Award of Order", "bagged order worth Rs 50 cr") == "order-win"
    assert catalyst_type_for("Investor Presentation", "raises guidance for FY27") == "guidance"
    assert catalyst_type_for("Trading Window", "closure of trading window") == "other"
    assert catalyst_type_for("Analysts/Institutional Investor Meet", "") == "other"


def test_parse_dedupes_and_extracts_broadcast(tmp_path):
    master = tmp_path / "master.csv"
    master.write_text(
        "Stock Name,Date,Subject,Details,Attachments\n"
        "BAJAJ-AUTO,02/07/2026,Press Release,June sales,https://nsearchives.nseindia.com/corporate/a_02072026085251_x.pdf\n"
        "BAJAJ-AUTO,02/07/2026,Press Release,duplicate row,https://nsearchives.nseindia.com/corporate/a_02072026085251_x.pdf\n"
        "BAD ROW,not-a-date,Subject,x,\n",
        encoding="utf-8",
    )
    records = parse_announcements_master_csv(master, first_seen_at="2026-07-03T00:00:00+00:00")
    assert len(records) == 1  # duplicate and malformed rows never become data
    r = records[0]
    assert r.symbol == "BAJAJ-AUTO"
    assert r.announced_date == date(2026, 7, 2)
    assert r.broadcast_at is not None
    assert r.catalyst_type == "other"
    assert r.first_seen_at == "2026-07-03T00:00:00+00:00"


def test_store_round_trip_and_catalyst_lookup(tmp_path):
    records = [
        AnnouncementRecord("TITAN", date(2026, 7, 2), None, "results",
                           "Outcome of Board Meeting", "https://x/1.pdf", "t0", "m.csv"),
        AnnouncementRecord("TITAN", date(2026, 7, 20), None, "order-win",
                           "Award of Order", "https://x/2.pdf", "t0", "m.csv"),
    ]
    persist_announcements(records, tmp_path)
    from unidesk.research.announcements import catalyst_for_symbol, load_announcements
    rows = load_announcements(tmp_path)
    assert len(rows) == 2
    hit = catalyst_for_symbol(tmp_path, "titan", date(2026, 7, 15))
    assert hit is not None and hit["catalyst_type"] == "results"
    # absence is None — never a "none" catalyst
    assert catalyst_for_symbol(tmp_path, "UNKNOWN", date(2026, 7, 15)) is None
    # future announcements are not knowable early
    assert catalyst_for_symbol(tmp_path, "titan", date(2026, 7, 1)) is None
