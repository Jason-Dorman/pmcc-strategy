"""Market values and NAV (Spec › NAV and Reg T, INV-02).

    NAV = cash + LongMV − ShortCallMV + StockMV

LongMV and ShortCallMV are mark × 100 × contracts; StockMV is shares × mark, negative when short.
Every sum is in integer $0.0001 units (DEC-44), so NAV reconciles exactly.
"""

from dataclasses import dataclass
from typing import final

from pmcc.accounting.book import Book
from pmcc.accounting.events import Instrument, multiplier
from pmcc.accounting.marks import Marks
from pmcc.domain.errors import EngineError
from pmcc.domain.money import Money


@final
@dataclass(frozen=True, slots=True)
class Valuation:
    cash: Money
    long_mv: Money
    short_mv: Money  # a positive amount: the cost to buy the short calls back
    stock_mv: Money  # signed: negative when short
    stale_long: bool
    stale_short: bool
    stale_stock: bool

    @property
    def nav(self) -> Money:
        return self.cash + self.long_mv - self.short_mv + self.stock_mv

    @property
    def stale_flags(self) -> tuple[str, ...]:
        names = ("stale_long", "stale_short", "stale_stock")
        return tuple(n for n, on in zip(names, self._stale(), strict=True) if on)

    def _stale(self) -> tuple[bool, bool, bool]:
        return self.stale_long, self.stale_short, self.stale_stock


def value(book: Book, marks: Marks) -> Valuation:
    """The book at `marks`. Raises `EngineError` if a held instrument has no mark."""
    long_mv = _mv(book.long_calls, marks)
    short_mv = _mv(book.short_calls, marks)
    stock_mv = _mv(book.stock, marks)
    return Valuation(
        cash=book.cash,
        long_mv=long_mv,
        short_mv=short_mv,
        stock_mv=stock_mv,
        stale_long=_stale(book.long_calls, marks),
        stale_short=_stale(book.short_calls, marks),
        stale_stock=_stale(book.stock, marks),
    )


def _mv[I: Instrument](held: dict[I, int], marks: Marks) -> Money:
    total = Money.zero()
    for instrument, qty in held.items():
        if instrument not in marks:
            raise EngineError(f"{instrument} is held but has never had a mark")
        total += marks[instrument].price.notional(multiplier(instrument), qty)
    return total


def _stale[I: Instrument](held: dict[I, int], marks: Marks) -> bool:
    return any(marks[i].stale for i in held if i in marks)
