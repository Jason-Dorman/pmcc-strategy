"""Ledger rows: one per bar (Spec › Ledger).

Each row holds the long and the short call (instrument, quantity, mark, delta, stale), the stock
position after X-S5, cash, NAV, IM, MM, available funds, excess equity, and flags:

- `stale_long`, `stale_short`, `stale_stock`: a mark carried from an earlier bar;
- `funds_negative`: available funds below zero, so the position couldn't have been held in a real
  Reg T account (Spec › NAV and Reg T);
- `entry_blocked`, `exit_pending` and the like, raised by the engine for that bar.
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
class LegRow:
    option: OptionId
    qty: int  # contracts, positive for the short too
    mark: Price
    stale: bool
    delta: float | None


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
    deltas: Mapping[OptionId, float | None],
    flags: Iterable[str] = (),
) -> LedgerRow:
    """The bar's row. The strategy holds at most one long, one short and one stock position."""
    all_flags = [*valuation.stale_flags, *flags]
    if requirements.funds_negative:
        all_flags.append("funds_negative")
    return LedgerRow(
        time=time,
        long=_leg(book.long_calls, marks, deltas),
        short=_leg(book.short_calls, marks, deltas),
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
    held: Mapping[OptionId, int], marks: Marks, deltas: Mapping[OptionId, float | None]
) -> LegRow | None:
    if len(held) > 1:
        raise EngineError(f"a strategy holds one call per side, not {sorted(held)}")
    for option, qty in held.items():
        mark = marks[option]
        return LegRow(option, qty, mark.price, mark.stale, deltas.get(option))
    return None


def _stock(book: Book, marks: Marks) -> StockRow | None:
    for stock, shares in book.stock.items():
        mark = marks[stock]
        return StockRow(stock, shares, mark.price, mark.stale)
    return None
