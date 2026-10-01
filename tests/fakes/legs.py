"""Hand-made runs for the attribution tests (P6-03, P6-04): a ledger that follows from its blotter.

Each bar names its spot and the legs it ends with (contract, mark, Greeks); its cash is the
starting cash plus the Cash Δ of every row booked at or before it, and its NAV adds the legs at
their marks (INV-02), so a test's legs add up to its P&L as an engine run's do.
"""

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import final

from pmcc.accounting.events import Event
from pmcc.accounting.ledger import NO_GREEKS, LedgerRow, LegGreeks, LegRow, StockRow
from pmcc.domain.instruments import OPTION_MULTIPLIER, OptionId
from pmcc.domain.money import Money, Price
from tests.fakes.records import STOCK, Records


@final
@dataclass(frozen=True, slots=True)
class Held:
    """A leg at a bar's end."""

    option: OptionId
    mark: str
    greeks: LegGreeks = NO_GREEKS
    stale: bool = False
    qty: int = 1

    def row(self) -> LegRow:
        return LegRow(self.option, self.qty, Price.from_dollars(self.mark), self.stale, self.greeks)

    def value(self) -> Money:
        return Price.from_dollars(self.mark).notional(OPTION_MULTIPLIER, self.qty)


@final
@dataclass(frozen=True, slots=True)
class Tick:
    """A bar's end: its spot and what it holds. `stock` is X-S5's (shares, mark)."""

    time: datetime
    spot: str | None
    long: Held | None = None
    short: Held | None = None
    stock: tuple[int, str] | None = None


def greeks(iv: float | None, delta: float, gamma: float, theta: float,
           vega: float) -> LegGreeks:  # fmt: skip
    return LegGreeks(iv, delta, gamma, theta, vega)


def with_iv(event: Event, iv: float | None) -> Event:
    """`event` with the IV it filled at in its audit, as the engine records it (P6-04)."""
    return dataclasses.replace(event, audit={**event.audit, "fill_iv": iv})


def tape(ticks: Sequence[Tick], blotter: Sequence[Event], start: str = "10000") -> Records:
    """The run whose ledger is `ticks`, its cash and NAV following from `blotter`."""
    cash = Money.from_dollars(start)
    rows: list[LedgerRow] = []
    booked = iter(sorted(blotter, key=lambda e: e.time))
    pending = next(booked, None)
    for tick in ticks:
        while pending is not None and pending.time <= tick.time:
            cash += pending.cash_delta
            pending = next(booked, None)
        rows.append(_row(tick, cash))
    return Records(tuple(rows), tuple(blotter), starting_cash=Money.from_dollars(start))


def _row(tick: Tick, cash: Money) -> LedgerRow:
    long_mv = Money.zero() if tick.long is None else tick.long.value()
    short_mv = Money.zero() if tick.short is None else tick.short.value()
    stock = None
    stock_mv = Money.zero()
    if tick.stock is not None:
        shares, mark = tick.stock
        stock = StockRow(STOCK, shares, Price.from_dollars(mark), False)
        stock_mv = Price.from_dollars(mark).notional(1, shares)
    nav = cash + long_mv - short_mv + stock_mv
    zero = Money.zero()
    spot = None if tick.spot is None else Price.from_dollars(tick.spot)
    return LedgerRow(tick.time, spot, None if tick.long is None else tick.long.row(),
                     None if tick.short is None else tick.short.row(), stock, cash, nav, zero,
                     zero, nav, nav, ())  # fmt: skip
