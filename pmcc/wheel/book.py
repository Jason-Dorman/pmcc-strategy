"""The wheel's book: cash, at most one short option, and shares (Spec › Trade rules, Accounting).

`WheelBook.apply(event)` is its only mutator, and cash moves only by the event's Cash Δ (WINV-01).
It is the PMCC's book's sibling, not a variant of it: the PMCC's covered-diagonal rules stay where
they are, and the wheel's are checked after every event, so a booking that breaks one raises
`EngineError` (WD-24):

- a cash account: cash never goes negative, and no option or share is ever held long on margin;
- the wheel only sells options: no long option, and at most one short option at a time (WINV-07);
- a short put is cash-secured: cash ≥ strike × 100 × contracts, its credit counted (WINV-05), and
  no shares are held beside it (WINV-07);
- a short call is covered: shares ≥ 100 × contracts (WINV-06); no short stock, ever;
- an event never turns a long into a short or a short into a long in one step;
- `EXPIRE` and `ASSIGN` close a short option, on its expiry day. An assignment's share purchase
  (put) or sale (call) at the strike is its own `BUY` or `SELL` row.

The state follows from what is held: Cash, Put, Shares or Call.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import final

from pmcc.accounting.events import Event, Instrument, StockId, multiplier
from pmcc.accounting.marks import Marks
from pmcc.domain.clock import to_et
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OPTION_MULTIPLIER, OptionId, Right, Side
from pmcc.domain.money import Money

_SIGN = {Side.BUY: 1, Side.SELL: -1, Side.EXPIRE: 1, Side.ASSIGN: 1}


class WheelState(StrEnum):
    CASH = "cash"
    PUT = "put"
    SHARES = "shares"
    CALL = "call"


type Short = tuple[OptionId, int]  # the option and its contracts, as a positive number


@final
@dataclass(frozen=True, slots=True)
class WheelBook:
    cash: Money
    positions: Mapping[Instrument, int] = field(default_factory=dict[Instrument, int])

    def apply(self, event: Event) -> "WheelBook":
        """The book after `event`. Raises `EngineError` if it can't be booked or would leave the
        book outside the wheel's rules."""
        held = self.positions.get(event.instrument, 0)
        _check_closing(event, held)
        after = held + _SIGN[event.side] * event.qty
        if held and after and (held > 0) != (after > 0):
            raise EngineError(f"{event.side} {event.qty} would flip {event.instrument} ({held})")
        positions = {k: v for k, v in self.positions.items() if k != event.instrument}
        if after:
            positions[event.instrument] = after
        book = WheelBook(self.cash + event.cash_delta, positions)
        book.check()
        return book

    @property
    def short_put(self) -> Short | None:
        return self._short(Right.PUT)

    @property
    def short_call(self) -> Short | None:
        return self._short(Right.CALL)

    @property
    def shares(self) -> int:
        return sum(q for i, q in self.positions.items() if isinstance(i, StockId))

    @property
    def reserved(self) -> Money:
        """The cash securing the short put: its strike × 100 × contracts."""
        put = self.short_put
        return Money.zero() if put is None else put[0].strike.notional(OPTION_MULTIPLIER, put[1])

    @property
    def state(self) -> WheelState:
        if self.short_put is not None:
            return WheelState.PUT
        if self.short_call is not None:
            return WheelState.CALL
        return WheelState.SHARES if self.shares else WheelState.CASH

    def check(self) -> None:
        """WINV-05 to WINV-07 and the cash account on this book. Raises `EngineError`."""
        if self.cash.units < 0:
            raise EngineError(f"cash would go negative ({self.cash}): a cash account never borrows")
        options = self._options()
        if any(q > 0 for q in options.values()):
            raise EngineError(f"the wheel never holds a long option: {options}")
        if len(options) > 1:
            raise EngineError(f"the wheel holds one short option at a time, not {sorted(options)}")
        if any(q < 0 for i, q in self.positions.items() if isinstance(i, StockId)):
            raise EngineError("the wheel never holds short stock")
        self._check_put()
        self._check_call()

    def _check_put(self) -> None:
        if self.short_put is None:
            return
        if self.shares:
            raise EngineError(f"a put can't be open while {self.shares} shares are held")
        if self.cash < self.reserved:
            raise EngineError(
                f"the put isn't cash-secured: cash {self.cash} < strike x 100 {self.reserved}"
            )

    def _check_call(self) -> None:
        call = self.short_call
        if call is not None and self.shares < OPTION_MULTIPLIER * call[1]:
            raise EngineError(f"call {call[0]} x{call[1]} isn't covered by {self.shares} shares")

    def _options(self) -> dict[OptionId, int]:
        return {k: q for k, q in self.positions.items() if isinstance(k, OptionId)}

    def _short(self, right: Right) -> Short | None:
        for option, qty in self._options().items():
            if option.right is right and qty < 0:
                return option, -qty
        return None


def _check_closing(event: Event, held: int) -> None:
    if event.side not in (Side.EXPIRE, Side.ASSIGN):
        return
    option = event.instrument
    if not isinstance(option, OptionId) or held > -event.qty:
        raise EngineError(f"{event.side} needs a short option of {event.qty}; holding {held}")
    if to_et(event.time).date() != option.expiry:
        raise EngineError(f"{event.side} of {option} on {event.time.date()}, not its expiry")


# --- Valuation (WINV-02) ----------------------------------------------------------------------


@final
@dataclass(frozen=True, slots=True)
class WheelValuation:
    """NAV = cash + shares × stock mark − short put MV − short call MV, in integer $0.0001.

    `reserved` is the cash securing the put; `free_cash` is the rest."""

    cash: Money
    reserved: Money
    stock_mv: Money
    put_mv: Money  # positive: the cost to buy the put back
    call_mv: Money  # positive: the cost to buy the call back
    stale_flags: tuple[str, ...]

    @property
    def nav(self) -> Money:
        return self.cash + self.stock_mv - self.put_mv - self.call_mv

    @property
    def free_cash(self) -> Money:
        return self.cash - self.reserved


def value(book: WheelBook, marks: Marks) -> WheelValuation:
    """The book at `marks`. Raises `EngineError` if a held instrument has no mark."""
    for instrument in book.positions:
        if instrument not in marks:
            raise EngineError(f"{instrument} is held but has never had a mark")
    put, call = book.short_put, book.short_call
    stock: dict[Instrument, int] = {
        i: q for i, q in book.positions.items() if isinstance(i, StockId)
    }
    legs = (("stale_put", put), ("stale_call", call))
    stale = [name for name, short in legs if short is not None and marks[short[0]].stale]
    if any(marks[i].stale for i in stock):
        stale.append("stale_stock")
    return WheelValuation(
        cash=book.cash,
        reserved=book.reserved,
        stock_mv=_mv(stock, marks),
        put_mv=_mv({put[0]: put[1]} if put else {}, marks),
        call_mv=_mv({call[0]: call[1]} if call else {}, marks),
        stale_flags=tuple(sorted(stale)),
    )


def _mv(held: Mapping[Instrument, int], marks: Marks) -> Money:
    total = Money.zero()
    for instrument, qty in held.items():
        total += marks[instrument].price.notional(multiplier(instrument), qty)
    return total
