"""N-21 — SEBI-derived IPO lock-in dates, verified against the rule source.

Derived, never observed: the desk has the listing date, and the lock-in ends
are formulaic from it under the cited SEBI ICDR amendment versions. The
allotment-date approximation is documented in the module.
"""
from __future__ import annotations

from datetime import date

from unidesk.momentum.data.lockin import RULE_VERSION, derive_lockins

RULE_VERSION = RULE_VERSION


def test_lockin_dates_derive_from_listing():
    listing = date(2026, 7, 3)
    rows = derive_lockins(listing)
    by = {r.holder_class: r for r in rows}
    assert by["anchor_50pct"].unlock_date == "2026-08-02"      # +30 days
    assert by["anchor_50pct_2"].unlock_date == "2026-10-01"    # +90 days
    assert by["non_promoter_pre_ipo"].unlock_date == "2027-01-02"  # +183 days
    assert by["promoter_18m"].unlock_date == "2028-01-02"      # +548 days
    assert all(r.derived_from_rule for r in rows)
    assert all(r.rule_version.startswith("SEBI-ICDR") for r in rows)


def test_every_row_carries_rule_version_and_citation():
    rows = derive_lockins(date(2026, 1, 15))
    assert len(rows) == 4
    for r in rows:
        assert r.derived_from_rule is True
        assert "ICDR" in r.citation
        assert r.rule_version == "SEBI-ICDR-2018-AM3-2021-AM4-ANCHOR"
