"""IPO lock-in dates derived from SEBI ICDR rules (ROTATION/event-track N-21).

RULE SOURCE (verified 2026-09-05 against SEBI's own notification): SEBI (Issue
of Capital and Disclosure Requirements) Regulations, 2018, as amended:

* Third Amendment Regulations, 2021 (notified Aug 2021), Reg 115: pre-issue
  promoter holding (MPC and excess) locked **18 months** from allotment
  (reduced from 3 years).
* Third Amendment 2021, Reg 116: pre-issue non-promoter holding locked
  **6 months** from allotment in an IPO (reduced from 1 year).
* Fourth Amendment 2021: anchor investor allocation split — 50% released
  **30 days**, 50% **90 days** from allotment.

All dates here are DERIVED (``derived_from_rule = True`` with the rule version
stored alongside): they approximate the allotment date with the listing date
(the desk's only observed anchor) and are descriptive context — never a risk
input, never a ranking input. If SEBI amends the periods again, bump
RULE_VERSION and the derived dates recompute; history stored under the old
version keeps its own stamp.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, timedelta

RULE_VERSION = "SEBI-ICDR-2018-AM3-2021-AM4-ANCHOR"

# (holder_class, months_or_days, is_days, citation)
_RULE_TABLE = [
    ("anchor_50pct", 30, True, "ICDR AM4 2021: 50% of anchor allocation, 30 days"),
    ("anchor_50pct_2", 90, True, "ICDR AM4 2021: remaining 50% of anchor, 90 days"),
    ("non_promoter_pre_ipo", 183, True, "ICDR AM3 2021 Reg 116: 6 months ≈ 183 days"),
    ("promoter_18m", 548, True, "ICDR AM3 2021 Reg 115: 18 months ≈ 548 days"),
]


@dataclass(frozen=True)
class LockInEntry:
    holder_class: str
    unlock_date: str
    days_from_listing: int
    derived_from_rule: bool
    rule_version: str
    citation: str


def derive_lockins(listing_date: date) -> list[LockInEntry]:
    out: list[LockInEntry] = []
    for holder, amount, is_days, citation in _RULE_TABLE:
        unlock = listing_date + (timedelta(days=amount) if is_days
                                 else timedelta(days=round(amount * 30.4375)))
        out.append(LockInEntry(
            holder_class=holder,
            unlock_date=unlock.isoformat(),
            days_from_listing=amount if is_days else round(amount * 30.4375),
            derived_from_rule=True,
            rule_version=RULE_VERSION,
            citation=citation,
        ))
    return out
