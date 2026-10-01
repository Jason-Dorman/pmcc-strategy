"""Ledger rows: one per bar (Spec › Ledger).

Each row holds the bar's spot, the long and the short call (instrument, quantity, mark, stale, and
the IV and Greeks of the bar's quote), the stock position after X-S5, cash, NAV, IM, MM, available
funds, excess equity, and flags:

- `stale_long`, `stale_short`, `stale_stock`: a mark carried from an earlier bar;
- `funds_negative`: available funds below zero, so the position couldn't have been held in a real
  Reg T account (Spec › NAV and Reg T);
- `entry_blocked`, `exit_pending` and the like, raised by the engine for that bar.

The spot and the Greeks are what the engine saw on the bar, so the Greek attribution reads them
from the ledger (P6-04, DEC-63). Spot is the stock's TRDPRC_1 on the bar (DEC-23), None without a
trade. A leg's IV and Greeks are its chain row's (DEC-24 units), None without a valid quote, and
each is None where pricing left it unknown: a call under its floor has DEC-27's Greeks but no IV.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import final

from pmcc.accounting.book import Book
from pmcc.accounting.events import StockId
from pmcc.accounting.marks import Marks
from pmcc.accounting.regt import RegT
from pmcc.accounting.valuation import Valuation
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId
from pmcc.domain.money import Money, Price


@final
@dataclass(frozen=True, slots=True)
class LegGreeks:
    """A contract's IV and Greeks on a bar, each None where unknown."""

    iv: float | None
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None


NO_GREEKS = LegGreeks(None, None, None, None, None)


@final
@dataclass(frozen=True, slots=True)
class LegRow:
    option: OptionId
    qty: int  # contracts, positive for the short too
    mark: Price
    stale: bool
    greeks: LegGreeks

    @property
    def delta(self) -> float | None:
        return self.greeks.delta


@final
@dataclass(frozen=True, slots=True)
class StockRow:
    stock: StockId
    shares: int  # negative when short
    mark: Price
    stale: bool


@final
@dataclass(frozen=True, slots=True)
class LedgerRow:
    time: datetime
    spot: Price | None
    long: LegRow | None
    short: LegRow | None
    stock: StockRow | None
    cash: Money
    nav: Money
    im: Money
    mm: Money
    available_funds: Money
    excess_equity: Money
    flags: tuple[str, ...]


def ledger_row(
    time: datetime,
    book: Book,
    marks: Marks,
    valuation: Valuation,
    requirements: RegT,
    spot: Price | None,
    greeks: Mapping[OptionId, LegGreeks],
    flags: Iterable[str] = (),
) -> LedgerRow:
    """The bar's row. The strategy holds at most one long, one short and one stock position; a
    leg missing from `greeks` has none known."""
    all_flags = [*valuation.stale_flags, *flags]
    if requirements.funds_negative:
        all_flags.append("funds_negative")
    return LedgerRow(
        time=time,
        spot=spot,
        long=_leg(book.long_calls, marks, greeks),
        short=_leg(book.short_calls, marks, greeks),
        stock=_stock(book, marks),
        cash=valuation.cash,
        nav=valuation.nav,
        im=requirements.im,
        mm=requirements.mm,
        available_funds=requirements.available_funds,
        excess_equity=requirements.excess_equity,
        flags=tuple(sorted(set(all_flags))),
    )


def _leg(
    held: Mapping[OptionId, int], marks: Marks, greeks: Mapping[OptionId, LegGreeks]
) -> LegRow | None:
    if len(held) > 1:
        raise EngineError(f"a strategy holds one call per side, not {sorted(held)}")
    for option, qty in held.items():
        mark = marks[option]
        return LegRow(option, qty, mark.price, mark.stale, greeks.get(option, NO_GREEKS))
    return None


def _stock(book: Book, marks: Marks) -> StockRow | None:
    for stock, shares in book.stock.items():
        mark = marks[stock]
        return StockRow(stock, shares, mark.price, mark.stale)
    return None
