"""WINV-01, 02 and 05 to 07 over random wheels (Spec › Invariants; W2-01).

A random walk through the trades the wheel books: sell a put if cash secures it (W-P4), let it
expire or be assigned (ASSIGN, then BUY 100 shares at the strike), sell a call on the shares, let it
expire or be called away (ASSIGN, then SELL the shares at the strike), and re-mark on bars with and
without quotes. Fills are any $0.0001 amount, with fees, so sub-cent fills are covered.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from hypothesis import event, given
from hypothesis import strategies as st

from pmcc.accounting.events import Event, Instrument, StockId, expected_cash, multiplier
from pmcc.accounting.marks import Mark, carry
from pmcc.domain.clock import ET
from pmcc.domain.instruments import OPTION_MULTIPLIER, OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId
from pmcc.wheel.book import WheelBook, WheelState, value

ROOT = "SYN"
STOCK = StockId(ROOT)
FIRST_EXPIRY = date(2026, 4, 3)
RULE = RuleId("W-P1")
ZERO = Money.zero()

prices = st.integers(min_value=0, max_value=300_000)  # up to $30, any $0.0001
strikes = st.integers(min_value=20, max_value=300).map(lambda d: Price.from_dollars(d))
fees = st.integers(min_value=0, max_value=20_000).map(Money)


@dataclass
class Wheel:
    """The book and its marks, with every event booked so far."""

    book: WheelBook
    marks: dict[Instrument, Mark] = field(default_factory=dict[Instrument, Mark])
    events: list[Event] = field(default_factory=list[Event])
    week: int = 0

    @property
    def expiry(self) -> date:
        return FIRST_EXPIRY + timedelta(weeks=self.week)

    def at(self, hour: int) -> datetime:
        return datetime.combine(self.expiry, datetime.min.time(), ET).replace(hour=hour)

    def book_event(self, e: Event) -> None:
        before = self.book.cash
        self.book = self.book.apply(e)
        assert self.book.cash - before == e.cash_delta  # WINV-01, per event
        self.events.append(e)
        if e.fill is not None and e.instrument in self.book.positions:
            self.marks[e.instrument] = Mark(e.fill, e.time, stale=False)


def _event(side: Side, instrument: Instrument, qty: int, t: datetime, fill: Price | None,
           fee: Money = ZERO) -> Event:  # fmt: skip
    cash = expected_cash(side, instrument, qty, fill, fee)
    return Event(t, side, instrument, qty, fill, fill, cash, RULE, fee=fee)


def _sell(wheel: Wheel, data: st.DataObject, right: Right) -> None:
    option = OptionId(ROOT, wheel.expiry, right, data.draw(strikes))
    fill, fee = Price(data.draw(prices)), data.draw(fees)
    sale = _event(Side.SELL, option, 1, wheel.at(10), fill, fee)
    secured = option.strike.notional(OPTION_MULTIPLIER, 1)
    if right is Right.PUT and wheel.book.cash + sale.cash_delta < secured:
        event("put not secured: skipped")  # W-P4
        return
    if (wheel.book.cash + sale.cash_delta).units < 0:
        event("fee over cash: skipped")  # a cash account never borrows
        return
    wheel.book_event(sale)


def _settle(wheel: Wheel, data: st.DataObject) -> None:
    """The open option's expiry: it expires, or is assigned and the shares move at its strike."""
    short = wheel.book.short_put or wheel.book.short_call
    assert short is not None
    option, qty = short
    t = wheel.at(16)
    if data.draw(st.booleans()):
        wheel.book_event(_event(Side.EXPIRE, option, qty, t, Price(0)))
    else:
        event(f"assigned {option.right}")
        wheel.book_event(_event(Side.ASSIGN, option, qty, t, None))
        side = Side.BUY if option.right is Right.PUT else Side.SELL
        wheel.book_event(_event(side, STOCK, qty * OPTION_MULTIPLIER, t, option.strike))
    wheel.week += 1


def _remark(wheel: Wheel, data: st.DataObject) -> None:
    """A new bar: each held instrument has a fresh mid, or none (its mark goes stale)."""
    fresh = {i: data.draw(st.one_of(st.none(), prices.map(Price))) for i in wheel.book.positions}
    before = wheel.book.cash
    wheel.marks = {**wheel.marks, **carry(wheel.marks, fresh, wheel.at(12))}
    assert wheel.book.cash == before  # marking never moves cash (WINV-01)


def _step(wheel: Wheel, data: st.DataObject) -> None:
    state = wheel.book.state
    moves = {
        WheelState.CASH: ["sell_put", "skip_week"],
        WheelState.PUT: ["mark", "settle"],
        WheelState.SHARES: ["sell_call", "mark", "skip_week"],
        WheelState.CALL: ["mark", "settle"],
    }[state]
    move = data.draw(st.sampled_from(moves))
    event(move)
    if move == "sell_put":
        _sell(wheel, data, Right.PUT)
    elif move == "sell_call":
        _sell(wheel, data, Right.CALL)
    elif move == "settle":
        _settle(wheel, data)
    elif move == "mark":
        _remark(wheel, data)
    else:
        wheel.week += 1


def _nav(wheel: Wheel) -> Money:
    """NAV recomputed from positions and marks, independently of `value` (WINV-02)."""
    total = wheel.book.cash
    for instrument, qty in wheel.book.positions.items():
        total += wheel.marks[instrument].price.notional(multiplier(instrument), qty)
    return total


def _check(wheel: Wheel) -> None:
    book = wheel.book
    assert value(book, wheel.marks).nav == _nav(wheel)  # WINV-02
    assert book.cash.units >= 0  # a cash account never borrows
    if book.short_put is not None:
        option, qty = book.short_put
        assert book.cash >= option.strike.notional(OPTION_MULTIPLIER, qty)  # WINV-05
        assert book.shares == 0  # WINV-07
    if book.short_call is not None:
        assert book.shares >= OPTION_MULTIPLIER * book.short_call[1]  # WINV-06
    held = [i for i in book.positions if isinstance(i, OptionId)]
    assert len(held) <= 1  # WINV-07: one short option at a time


@given(
    data=st.data(),
    cash=st.integers(0, 60_000).map(Money.from_dollars),  # up to two puts at the top strike
    steps=st.integers(1, 40),
)
def test_winv_01_02_05_06_07_hold_over_random_wheels(
    data: st.DataObject, cash: Money, steps: int
) -> None:
    wheel = Wheel(WheelBook(cash))
    for _ in range(steps):
        _step(wheel, data)
        _check(wheel)
    moved = sum((e.cash_delta for e in wheel.events), Money.zero())
    assert wheel.book.cash - cash == moved  # WINV-01, over the whole run
