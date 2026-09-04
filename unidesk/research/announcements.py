"""Corporate-announcement store (E-2) — the realised-event source for the EP
track and the Phase 0 availability ledger (gate item #26).

Source: the Chartsmaze extractor's ``corporate-announcements`` master CSV
(``Stock Name, Date, Subject, Details, Attachments``; dedup keys
``Stock Name, Date, Subject``). NSE is the source of record; the archive URL
embeds the exchange dissemination timestamp (``_DDMMYYYYHHMMSS_``), which is
what the knowability rule consumes — never the ``Date`` column alone.

THE KNOWABILITY RULE (event-track §3.2): an announcement is knowable from its
broadcast moment, not its date. A filing broadcast after the session close
(15:30 IST) belongs to the NEXT trading session. ``knowable_session`` encodes
exactly that; nothing else may derive session membership.

Absence is not evidence: a symbol with no announcement row has
``catalyst_type = None`` upstream — never ``"none"``.
"""
from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta, timezone

_IST = timezone(timedelta(hours=5, minutes=30))
from pathlib import Path
from typing import Optional

from unidesk.contracts.base import ContractError, ensure_date
from unidesk.momentum.universe.symbol_master import normalize_symbol

# Broadcast timestamps live in the NSE archive attachment URLs:
#   ..._02072026085251_Sales_Report.pdf  -> 02-Jul-2026 08:52:51 IST
_BROADCAST_RE = re.compile(r"_(\d{2})(\d{2})(\d{4})(\d{2})(\d{2})(\d{2})_")

# Session close (IST). A broadcast after this belongs to the next session.
SESSION_CLOSE_HHMM = (15, 30)

# Catalyst taxonomy (event-track §3.2): results / order-win / guidance / other.
_CATALYST_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("results", ("financial result", "outcome of board meeting", "results")),
    ("order-win", ("order win", "bagged", "letter of award", "award of order", "contract")),
    ("guidance", ("guidance", "outlook", "forecast")),
)


def catalyst_type_for(subject: str, details: str = "") -> str:
    """Keyword classification over subject + details. Default is ``other`` —
    a real announcement with no recognisable catalyst is still an announcement."""
    text = f"{subject}\n{details}".lower()
    for catalyst, needles in _CATALYST_RULES:
        if any(needle in text for needle in needles):
            return catalyst
    return "other"


def _parse_bslash_date(value: str) -> Optional[date]:
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def broadcast_from_attachment(attachment_url: str) -> Optional[datetime]:
    """Exchange dissemination timestamp from the archive URL, IST-normalised
    to UTC (NSE archive stamps are IST). ``None`` when the URL carries no
    embedded stamp — the caller then falls back to the announced date."""
    m = _BROADCAST_RE.search(attachment_url or "")
    if not m:
        return None
    dd, mm, yyyy, hh, mi, ss = (int(g) for g in m.groups())
    return datetime(yyyy, mm, dd, hh, mi, ss, tzinfo=_IST).astimezone(timezone.utc)


def knowable_session(broadcast_at: datetime, announced_date: date, trading_calendar) -> date:
    """First trading session in which the announcement was KNOWABLE.

    Broadcast on/before the session close (15:30 IST) -> the same date, if it
    is an observed session; broadcast after the close -> the next observed
    session. Dates absent from the calendar raise: the caller's calendar is
    the authority, and guessing a session is how leakage starts."""
    local = broadcast_at.astimezone(_IST)
    after_close = (local.hour, local.minute) >= SESSION_CLOSE_HHMM
    sessions = [d.trade_date for d in trading_calendar.days]
    if not sessions:
        raise ContractError("trading calendar has no sessions")
    if after_close:
        later = [s for s in sessions if s > announced_date]
        if not later:
            raise ContractError(f"no session after {announced_date} for a post-close filing")
        return later[0]
    if announced_date in sessions:
        return announced_date
    later = [s for s in sessions if s > announced_date]
    if not later:
        raise ContractError(f"announced date {announced_date} is not in the calendar and has no later session")
    return later[0]


@dataclass(frozen=True)
class AnnouncementRecord:
    symbol: str
    announced_date: date
    broadcast_at: Optional[datetime]           # exchange dissemination stamp (UTC)
    catalyst_type: str                          # results / order-win / guidance / other
    subject: str
    source_url: str
    first_seen_at: str                          # ingest time — the availability-ledger field
    source_file: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["announced_date"] = self.announced_date.isoformat()
        d["broadcast_at"] = self.broadcast_at.isoformat() if self.broadcast_at else None
        return d


def parse_announcements_master_csv(path: Path, *, source_file: Optional[str] = None,
                                   first_seen_at: Optional[str] = None) -> list[AnnouncementRecord]:
    """Parse the extractor's master CSV into records. Rows without a
    parseable date or symbol are skipped and counted, never invented."""
    seen: set[tuple[str, str, str]] = set()
    out: list[AnnouncementRecord] = []
    skipped = 0
    stamp = first_seen_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    src = source_file or Path(path).name
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for raw in csv.DictReader(fh):
            row = {(k or "").strip(): (v or "").strip() for k, v in raw.items()}
            announced = _parse_bslash_date(row.get("Date") or "")
            subject = row.get("Subject") or ""
            try:
                symbol = normalize_symbol(row.get("Stock Name") or "")
            except ContractError:
                skipped += 1
                continue
            if not symbol or announced is None or not subject:
                skipped += 1
                continue
            key = (symbol, announced.isoformat(), subject)
            if key in seen:
                continue
            seen.add(key)
            attachment = row.get("Attachments") or ""
            out.append(AnnouncementRecord(
                symbol=symbol,
                announced_date=announced,
                broadcast_at=broadcast_from_attachment(attachment),
                catalyst_type=catalyst_type_for(subject, row.get("Details") or ""),
                subject=subject,
                source_url=attachment,
                first_seen_at=stamp,
                source_file=src,
            ))
    if skipped:
        print(f"[announcements] skipped {skipped} malformed rows")
    return out


def persist_announcements(records: list[AnnouncementRecord], root: Path) -> Path:
    """Partitioned by announced date under ``root/date=YYYY-MM-DD/``. The
    index JSON keeps the store self-describing without a reader pass."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    root = Path(root)
    by_date: dict[str, list[AnnouncementRecord]] = {}
    for r in records:
        by_date.setdefault(r.announced_date.isoformat(), []).append(r)
    for day, rows in by_date.items():
        part = root / f"date={day}"
        part.mkdir(parents=True, exist_ok=True)
        schema = pa.schema([
            ("symbol", pa.string()), ("announced_date", pa.string()),
            ("broadcast_at", pa.string()), ("catalyst_type", pa.string()),
            ("subject", pa.string()), ("source_url", pa.string()),
            ("first_seen_at", pa.string()), ("source_file", pa.string()),
        ])
        table = pa.Table.from_pylist([r.to_dict() for r in rows], schema=schema)
        pq.write_table(table, part / "announcements.parquet")
    index = root / "index.json"
    index.write_text(json.dumps({
        "rows": len(records),
        "dates": {d: len(v) for d, v in sorted(by_date.items())},
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=1), encoding="utf-8")
    return index


def load_announcements(root: Path) -> list[dict]:
    """Every persisted announcement, oldest first."""
    import pyarrow.parquet as pq

    out: list[dict] = []
    for part in sorted(Path(root).glob("date=*/announcements.parquet")):
        t = pq.read_table(part)
        for i in range(t.num_rows):
            out.append({c: t.column(c)[i].as_py() for c in t.column_names})
    return out


def catalyst_for_symbol(root: Path, symbol: str, as_of: date) -> Optional[dict]:
    """The most recent announcement for ``symbol`` knowable at ``as_of`` —
    ``None`` when none exists (absence is not evidence; the caller renders a
    named null, never ``"none"``)."""
    normalized = normalize_symbol(symbol)
    best: Optional[dict] = None
    for row in load_announcements(root):
        if normalize_symbol(row["symbol"]) != normalized:
            continue
        if row["announced_date"] > as_of.isoformat():
            continue
        if best is None or row["announced_date"] > best["announced_date"]:
            best = row
    return best
