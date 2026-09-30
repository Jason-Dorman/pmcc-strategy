"""Reg T requirements, available funds and excess equity (Spec › NAV and Reg T, DEC-10).

- **Long call:** 100% of LongMV. A listed option with 9 months or less left has no loan value.
- **Covered short call:** $0. The book refuses an uncovered one.
- **Short stock, hedged by long calls (PO, DEC-10):** no initial requirement beyond the sale
  proceeds (12 CFR 220.12(c)(2)). Maintenance is 10% of the long calls' aggregate exercise price
  plus their out-of-the-money amount, capped at the greater of $5 a share and 30% of the short
  stock's market value (FINRA 4210(f)(2)(H)(v)a).
- **Short stock, unhedged:** initial 50% of its market value (150% with the proceeds);
  maintenance 30% (spec).

IM = long + short-stock initial; MM = long + short-stock maintenance. Available funds = NAV − IM;
excess equity = NAV − MM. A requirement that isn't a whole $0.0001 is rounded up, never down.
"""

from dataclasses import dataclass
from fractions import Fraction
from math import ceil
from typing import final

from pmcc.accounting.book import Book
from pmcc.accounting.events import Event, StockId
from pmcc.accounting.marks import Mark, Marks
from pmcc.accounting.valuation import Valuation, value
from pmcc.domain.instruments import OPTION_MULTIPLIER
from pmcc.domain.money import UNITS_PER_DOLLAR, Money, Price

SHORT_INITIAL = Fraction(1, 2)  # additional to the proceeds, unhedged
SHORT_MAINTENANCE = Fraction(3, 10)
HEDGED_STRIKE_SHARE = Fraction(1, 10)
PER_SHARE_FLOOR = 5 * UNITS_PER_DOLLAR  # $5.00 a share, in units


@final
@dataclass(frozen=True, slots=True)
class RegT:
    long_requirement: Money
    stock_initial: Money
    stock_maintenance: Money
    nav: Money
    hedged: bool  # short stock held against long calls (DEC-10)

    @property
    def im(self) -> Money:
        return self.long_requirement + self.stock_initial

    @property
    def mm(self) -> Money:
        return self.long_requirement + self.stock_maintenance

    @property
    def available_funds(self) -> Money:
        return self.nav - self.im

    @property
    def excess_equity(self) -> Money:
        return self.nav - self.mm

    @property
    def funds_negative(self) -> bool:
        return self.available_funds.units < 0


def regt(book: Book, valuation: Valuation, marks: Marks) -> RegT:
    initial, maintenance, hedged = _short_stock(book, marks)
    return RegT(
        long_requirement=valuation.long_mv,
        stock_initial=initial,
        stock_maintenance=maintenance,
        nav=valuation.nav,
        hedged=hedged,
    )


def funds_after(book: Book, marks: Marks, event: Event) -> Money:
    """Available funds once `event` is booked, with its instrument marked at the event's limit
    (the mid it was decided at): the E-L4 check before any entry (INV-08)."""
    after = book.apply(event)
    marked = dict(marks)
    if event.limit is not None:
        marked[event.instrument] = Mark(event.limit, event.time, stale=False)
    return regt(after, value(after, marked), marked).available_funds


def _short_stock(book: Book, marks: Marks) -> tuple[Money, Money, bool]:
    """(initial, maintenance, hedged) for the book's short stock; zeros when there is none."""
    initial, maintenance, hedged = Money.zero(), Money.zero(), True
    for stock, shares in book.stock.items():
        if shares >= 0:
            continue
        short_value = marks[stock].price.notional(1, -shares)
        covered = _hedge(book, stock, -shares, marks[stock].price)
        if covered is None:
            hedged = False
            initial += _up(short_value.units * SHORT_INITIAL)
            maintenance += _up(short_value.units * SHORT_MAINTENANCE)
        else:
            cap = max(Fraction(PER_SHARE_FLOOR * -shares), short_value.units * SHORT_MAINTENANCE)
            maintenance += _up(min(covered, cap))
    return initial, maintenance, hedged


def _hedge(book: Book, stock: StockId, shares: int, spot: Price) -> Fraction | None:
    """The hedged maintenance before its cap, from the long calls covering `shares`, lowest strike
    first; None if the long calls don't cover them all."""
    left, total = shares, Fraction(0)
    for option, qty in sorted(book.long_calls.items(), key=lambda kv: kv[0].strike):
        if option.root != stock.symbol:
            continue
        used = min(left, qty * OPTION_MULTIPLIER)
        out_of_money = max(option.strike.units - spot.units, 0)
        total += used * (option.strike.units * HEDGED_STRIKE_SHARE + out_of_money)
        left -= used
        if left == 0:
            return total
    return None


def _up(amount: Fraction) -> Money:
    """A requirement in whole $0.0001 units, rounded up."""
    return Money(ceil(amount))
