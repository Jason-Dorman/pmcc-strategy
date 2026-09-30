"""The book: cash and positions. `Book.apply(event)` is its only mutator (ARCHITECTURE §5.4, §9).

Cash moves only when an event is applied, by exactly the event's Cash Δ (INV-01). Positions are
signed quantities: contracts for calls (+ long, − short) and shares for the stock.

After every event the book must still be a covered diagonal, or it raises `EngineError` (Spec ›
NAV and Reg T: "an uncovered short is an engine error, not a margin case"):

- only calls are held;
- every short call is covered by long calls with a strike at or below its strike and an expiry at
  or after its expiry, in at least its quantity (INV-05);
- whenever a short call is open, the short and long quantities are equal (INV-10);
- an event never turns a long into a short or a short into a long in one step;
- `EXPIRE` and `ASSIGN` close a short call, on its expiry day.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import final

from pmcc.accounting.events import Event, Instrument, StockId
from pmcc.domain.clock import to_et
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money

_SIGN = {Side.BUY: 1, Side.SELL: -1, Side.EXPIRE: 1, Side.ASSIGN: 1}


@final
@dataclass(frozen=True, slots=True)
class Book:
    cash: Money
    positions: Mapping[Instrument, int] = field(default_factory=dict[Instrument, int])

    def apply(self, event: Event) -> "Book":
        """The book after `event`. Raises `EngineError` if the event can't be booked, or if it
        would leave a short call uncovered or unequal to the long."""
        held = self.positions.get(event.instrument, 0)
        _check_closing(event, held)
        after = held + _SIGN[event.side] * event.qty
        if held and after and (held > 0) != (after > 0):
            raise EngineError(f"{event.side} {event.qty} would flip {event.instrument} ({held})")
        positions = {k: v for k, v in self.positions.items() if k != event.instrument}
        if after:
            positions[event.instrument] = after
        book = Book(self.cash + event.cash_delta, positions)
        book.check_covered()
        return book

    @property
    def long_calls(self) -> dict[OptionId, int]:
        return {k: q for k, q in self._options().items() if q > 0}

    @property
    def short_calls(self) -> dict[OptionId, int]:
        """Short calls and their quantities, as positive numbers."""
        return {k: -q for k, q in self._options().items() if q < 0}

    def shares(self, stock: StockId) -> int:
        return self.positions.get(stock, 0)

    @property
    def stock(self) -> dict[StockId, int]:
        return {k: q for k, q in self.positions.items() if isinstance(k, StockId)}

    def check_covered(self) -> None:
        """INV-05 and INV-10 on this book. Raises `EngineError`."""
        options = self._options()
        puts = [o for o in options if o.right is not Right.CALL]
        if puts:
            raise EngineError(f"only calls are traded; the book holds {puts}")
        longs, shorts = self.long_calls, self.short_calls
        for short, qty in shorts.items():
            cover = sum(q for o, q in longs.items() if _covers(o, short))
            if cover < qty:
                raise EngineError(f"short {short} x{qty} is uncovered (covering longs: {cover})")
        if shorts and sum(shorts.values()) != sum(longs.values()):
            raise EngineError(
                f"short quantity {sum(shorts.values())} != long quantity {sum(longs.values())}"
            )

    def _options(self) -> dict[OptionId, int]:
        return {k: q for k, q in self.positions.items() if isinstance(k, OptionId)}


def _covers(long: OptionId, short: OptionId) -> bool:
    return long.strike <= short.strike and long.expiry >= short.expiry


def _check_closing(event: Event, held: int) -> None:
    if event.side not in (Side.EXPIRE, Side.ASSIGN):
        return
    option = event.instrument
    if not isinstance(option, OptionId) or held > -event.qty:
        raise EngineError(f"{event.side} needs a short call of {event.qty}; holding {held}")
    if to_et(event.time).date() != option.expiry:
        raise EngineError(f"{event.side} of {option} on {event.time.date()}, not its expiry")
