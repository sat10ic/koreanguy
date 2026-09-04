"""ROTATION N-24 — group daily state: aggregate per-symbol universe state
into SECTOR / INDUSTRY groups, with honest coverage on every percentage.

Source of per-symbol data: the report's ``universe_states`` block (R-1
schema v2: symbol, close, above_ema21 (tri-state), above_ema50 (tri-state),
rs_rank) + the sector/industry mapping (Chartsmaze + Nexus fill).

Coverage rule (spec §46): a percentage is suppressed when fewer than 80% of
the group's members carry measurable data — the row renders
``INSUFFICIENT COVERAGE``, never a partial number, never 0.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from unidesk.momentum.universe.symbol_master import normalize_symbol

COVERAGE_FLOOR = 0.80


@dataclass(frozen=True)
class GroupDailyState:
    session: str
    group_kind: str            # SECTOR | INDUSTRY
    group_name: str
    members_total: int
    members_with_ema21: int
    members_with_ema50: int
    above_ema21_n: int
    above_ema50_n: int
    rs_rank_values: tuple[float, ...]
    candidates_n: int
    build_version: str = "group-state-v1"
    available_at: str = ""     # caller stamps; the ingest knows when this was computable

    @property
    def coverage(self) -> float:
        return self.members_with_ema21 / self.members_total if self.members_total else 0.0

    @property
    def breadth_ema21_pct(self) -> Optional[float]:
        """Suppressed when coverage is below the floor — the caller renders
        INSUFFICIENT COVERAGE, never the number (spec §46)."""
        if self.coverage < COVERAGE_FLOOR or not self.members_with_ema21:
            return None
        return round(100.0 * self.above_ema21_n / self.members_with_ema21, 1)

    @property
    def breadth_ema50_pct(self) -> Optional[float]:
        if self.coverage < COVERAGE_FLOOR or not self.members_with_ema50:
            return None
        return round(100.0 * self.above_ema50_n / self.members_with_ema50, 1)

    @property
    def coverage_sufficient(self) -> bool:
        return self.coverage >= COVERAGE_FLOOR

    @property
    def rs_rank_mean(self) -> Optional[float]:
        if not self.rs_rank_values:
            return None
        return round(sum(self.rs_rank_values) / len(self.rs_rank_values), 1)

    def to_dict(self) -> dict:
        return {
            "session": self.session, "group_kind": self.group_kind,
            "group_name": self.group_name,
            "members_total": self.members_total,
            "members_with_ema21": self.members_with_ema21,
            "members_with_ema50": self.members_with_ema50,
            "above_ema21_n": self.above_ema21_n, "above_ema50_n": self.above_ema50_n,
            "breadth_ema21_pct": self.breadth_ema21_pct,
            "breadth_ema50_pct": self.breadth_ema50_pct,
            "rs_rank_mean": self.rs_rank_mean,
            "candidates_n": self.candidates_n,
            "coverage": round(self.coverage, 3),
            "coverage_sufficient": self.coverage >= COVERAGE_FLOOR,
            "build_version": self.build_version, "available_at": self.available_at,
        }


def aggregate_groups(
    *,
    session: str,
    universe_states: list[dict],
    symbol_group: dict[str, dict],       # symbol -> {sector, industry}
    candidates_by_symbol: dict[str, int]  # symbol -> candidate count for the session
) -> list[GroupDailyState]:
    """Aggregate per-symbol universe state into SECTOR and INDUSTRY groups.

    ``universe_states``: the report's own per-symbol rows (tri-state EMA
    flags). ``symbol_group``: the merged Chartsmaze+Nexus mapping. A symbol
    absent from the mapping has no group and is counted in the disclosed
    ``unmapped`` total — never assigned to an invented group."""
    out: list[GroupDailyState] = []
    for kind, key in (("SECTOR", "sector"), ("INDUSTRY", "industry")):
        groups: dict[str, list[dict]] = {}
        unmapped = 0
        for st in universe_states:
            sym = st.get("symbol", "")
            info = symbol_group.get(sym)
            gname = (info or {}).get(key) if info else None
            if not gname:
                unmapped += 1
                continue
            groups.setdefault(gname, []).append(st)

        for gname, members in sorted(groups.items()):
            e21_total = sum(1 for m in members if m.get("above_ema21") is not None)
            e50_total = sum(1 for m in members if m.get("above_ema50") is not None)
            e21_n = sum(1 for m in members if m.get("above_ema21") is True)
            e50_n = sum(1 for m in members if m.get("above_ema50") is True)
            rs = [float(m["rs_rank"]) for m in members if m.get("rs_rank") is not None]
            cand = sum(candidates_by_symbol.get(m.get("symbol", ""), 0) for m in members)
            out.append(GroupDailyState(
                session=session, group_kind=kind, group_name=gname,
                members_total=len(members),
                members_with_ema21=e21_total, members_with_ema50=e50_total,
                above_ema21_n=e21_n, above_ema50_n=e50_n,
                rs_rank_values=tuple(sorted(rs)),
                candidates_n=cand,
            ))
        if unmapped:
            print(f"[group-state] {kind}: {unmapped} symbols without a {key.lower()} mapping "
                  f"(counted as unmapped, never assigned)")
    return out
