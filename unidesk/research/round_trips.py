"""N-41 — round-trip matching over the broker tradebook (FIFO, long-only).

CONVENTION (stated, per the node): **FIFO per symbol, long-only** — the
tradebook is DELIVERY product, so BUY fills open/add and SELL fills consume
the oldest open lots first. A round trip closes when the position returns to
zero; partial exits are recorded as realised-exit events that reduce the
open position and carry their own matched P&L.

REALISED P&L, NOT R: fills carry no stop records, so an R-multiple cannot be
computed without inventing a risk anchor (house rule 1). Every exit reports
rupee P&L and percent return; the missing-stop gap is named at the
aggregation site, not papered over.

Unmatched fills are REPORTED, never dropped: leftover BUYs are still-open
positions; SELLs with no open lots are reported as orphans (they would have
been silently dropped by every previous pass).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class Fill:
    trade_date: date
    symbol: str
    side: str            # BUY | SELL
    quantity: float
    price: float
    net_value: float     # fees already netted by the broker export

    @property
    def per_share_net(self) -> float:
        return self.net_value / self.quantity if self.quantity else 0.0


def _parse_date(raw) -> date:
    if isinstance(raw, date):
        return raw
    return date.fromisoformat(str(raw)[:10])


def to_fills(rows: Iterable[dict]) -> list[Fill]:
    out: list[Fill] = []
    for r in rows:
        out.append(Fill(
            trade_date=_parse_date(r["trade_date"]),
            symbol=str(r["symbol"]).upper(),
            side=str(r["side"]).upper(),
            quantity=float(r["quantity"]),
            price=float(r["price"]),
            net_value=float(r["net_value"]),
        ))
    out.sort(key=lambda f: (f.trade_date, f.symbol))
    return out


@dataclass(frozen=True)
class RealizedExit:
    symbol: str
    close_date: date
    quantity: float
    cost_basis: float        # FIFO buy net value of the consumed lots
    sell_net: float          # pro-rata share of the sell fill's net value
    pnl: float               # sell_net - cost_basis
    return_pct: float        # pnl / cost_basis * 100
    holding_days: int        # first consumed lot's date -> close date
    fully_closes: bool       # position is flat after this exit
    same_day: bool           # every consumed lot printed on the close date


@dataclass
class MatchResult:
    realized_exits: list[RealizedExit] = field(default_factory=list)
    round_trips: list[RealizedExit] = field(default_factory=list)   # subset: fully_closes
    unmatched_buys: list[Fill] = field(default_factory=list)        # still-open lots
    unmatched_sells: list[Fill] = field(default_factory=list)       # sells with no open lots
    skipped_zero_quantity: int = 0
    matched_buy_fills: int = 0
    matched_sell_fills: int = 0
    split_sell_fills: int = 0          # partially matched, partially orphaned


def match_round_trips(fills: Iterable[Fill]) -> MatchResult:
    result = MatchResult()
    by_symbol: dict[str, list[Fill]] = {}
    for f in fills:
        if f.quantity <= 0:
            result.skipped_zero_quantity += 1
            continue
        by_symbol.setdefault(f.symbol, []).append(f)

    for symbol in sorted(by_symbol):
        lots: list[list] = []   # mutable [date, remaining_qty, remaining_net]
        for f in by_symbol[symbol]:
            if f.side == "BUY":
                lots.append([f.trade_date, f.quantity, f.net_value])
                result.matched_buy_fills += 1
                continue
            # SELL: consume FIFO
            if not lots:
                result.unmatched_sells.append(f)
                continue
            result.matched_sell_fills += 1
            remaining = f.quantity
            cost_basis = 0.0
            matched_qty = 0.0
            first_lot_date = lots[0][0]
            while remaining > 1e-9 and lots:
                lot = lots[0]
                take = min(remaining, lot[1])
                per_share_cost = lot[2] / lot[1] if lot[1] else 0.0
                cost_basis += per_share_cost * take
                matched_qty += take
                first_lot_date = min(first_lot_date, lot[0])
                lot[1] -= take
                lot[2] -= per_share_cost * take
                remaining -= take
                if lot[1] <= 1e-9:
                    lots.pop(0)
            if remaining > 1e-9:
                # the sell exceeded the open position — the excess is an
                # orphan, reported (never dropped) with its pro-rata value
                if matched_qty > 0:
                    result.split_sell_fills += 1
                result.unmatched_sells.append(Fill(
                    f.trade_date, symbol, "SELL", remaining, f.price,
                    f.net_value * (remaining / f.quantity if f.quantity else 0.0),
                ))
            pro_rata = matched_qty / f.quantity if f.quantity else 0.0
            sell_net = f.net_value * pro_rata
            pnl = sell_net - cost_basis
            ret = pnl / cost_basis * 100 if cost_basis else 0.0
            fully = not lots
            same_day = first_lot_date == f.trade_date
            exit_rec = RealizedExit(
                symbol=symbol, close_date=f.trade_date, quantity=matched_qty,
                cost_basis=cost_basis, sell_net=sell_net, pnl=pnl, return_pct=ret,
                holding_days=(f.trade_date - first_lot_date).days, fully_closes=fully,
                same_day=same_day,
            )
            result.realized_exits.append(exit_rec)
            if fully:
                result.round_trips.append(exit_rec)

        # leftover lots = still-open positions, reported
        for lot_date, qty, net in lots:
            result.unmatched_buys.append(Fill(lot_date, symbol, "BUY", qty, 0.0, net))

    result.realized_exits.sort(key=lambda e: (e.close_date, e.symbol))
    result.round_trips = [e for e in result.realized_exits if e.fully_closes]
    return result
