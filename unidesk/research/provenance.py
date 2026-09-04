"""Provenance stamps on every derived research row (Phase 0 spec §2.3).

A derived row that cannot name when it was effective, when it became
visible, when it was built, and from which source version is not a
research input.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from unidesk.contracts.base import ContractError, ensure_date, ensure_utc, require_str


@dataclass(frozen=True)
class Provenance:
    effective_date: date
    available_at: datetime
    built_at: datetime
    source_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "effective_date", ensure_date(self.effective_date, "effective_date"))
        object.__setattr__(self, "available_at", ensure_utc(self.available_at, "available_at"))
        object.__setattr__(self, "built_at", ensure_utc(self.built_at, "built_at"))
        object.__setattr__(self, "source_version", require_str(self.source_version, "source_version"))
        if self.available_at < datetime(
            self.effective_date.year, self.effective_date.month, self.effective_date.day,
            tzinfo=timezone.utc,
        ):
            # available_at may be the same calendar day (publication); it must
            # not precede the session date itself.
            raise ContractError("available_at cannot precede effective_date")
