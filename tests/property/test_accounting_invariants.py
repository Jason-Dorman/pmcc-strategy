"""INV-01, 02, 08 and 10 over random sequences of fills, expiries, assignments and marks (Spec ›
Invariant tests; TEST-STRATEGY §3).

A random walk through the trades a PMCC books: buy the long, sell a covered short, buy it back,
let it expire or be assigned (ASSIGN, then the short-stock SELL at the strike, then a cover), sell
the long, and re-mark on bars with and without quotes (stale marks). Fills are any $0.0001 amount,
so sub-cent `spread_capture` fills are covered (DEC-44). Entries are gated as the engine gates them,
on available funds after the trade (E-L4).
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from hypothesis import event, given
from hypothesis import strategies as st

from pmcc.accounting.book import Book
from pmcc.accounting.events import Event, Instrument, StockId, multiplier
from pmcc.accounting.marks import Mark, Marks, carry
from pmcc.accounting.regt import funds_after, regt
from pmcc.accounting.valuation import value
from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId

ROOT = "SYN"
STOCK = StockId(ROOT)
SHORT_EXPIRY = date(2026, 9, 4)
LONG_EXPIRY = date(2027, 1, 15)
START = datetime(2026, 9, 4, 10, tzinfo=ET)
RULE = RuleId("E-L1")
ZERO = Money.zero()

prices = st.integers(min_value=1, max_value=3_000_000)  # up to $300, any $0.0001
strikes = st.integers(min_value=20, max_value=300).map(lambda d: Price.from_dollars(d))
fees = st.integers(min_value=0, max_value=20_000).map(Money)


@dataclass
class Account:
    """The book and its marks, with every event booked so far."""

    book: Book
    marks: dict[Instrument, Mark] = field(default_factory=dict[Instrument, Mark])
    events: list[Event] = field(default_factory=list[Event])
    clock: datetime = START

    def tick(self) -> datetime:
        self.clock += timedelta(minutes=1)
        return self.clock

    def book_event(self, event: Event) -> None:
        before = self.book.cash
        self.book = self.book.apply(event)
        assert self.book.cash - before == event.cash_delta  # INV-01, per event
        self.events.append(event)
        if event.limit is not None and event.instrument in self.book.positions:
            self.marks[event.instrument] = Mark(event.limit, event.time, stale=False)


def _event(side: Side, instrument: Instrument, qty: int, t: datetime, *, limit: Price | None,
           fill: Price | None, fee: Money = ZERO) -> Event:  # fmt: skip
    if side in (Side.EXPIRE, Side.ASSIGN):
        cash = Money.zero()
    else:
        assert fill is not None
        notional = fill.notional(multiplier(instrument), qty)
        cash = (-notional if side is Side.BUY else notional) - fee
    return Event(t, side, instrument, qty, limit, fill, cash, RULE, fee=fee)


def _nav(account: Account) -> Money:
    """NAV recomputed from positions and marks, independently of `value` (INV-02)."""
    total = account.book.cash
    for instrument, qty in account.book.positions.items():
        total += account.marks[instrument].price.notional(multiplier(instrument), qty)
    return total


def _long(account: Account) -> tuple[OptionId, int] | None:
    return next(iter(account.book.long_calls.items()), None)


def _short(account: Account) -> tuple[OptionId, int] | None:
    return next(iter(account.book.short_calls.items()), None)


def _entry(account: Account, event: Event) -> None:
    """Book an entry only if available funds stay ≥ 0 (E-L4), and check they do (INV-08)."""
    if funds_after(account.book, account.marks, event).units < 0:
        return
    account.book_event(event)
    after = regt(account.book, value(account.book, account.marks), account.marks)
    assert after.available_funds.units >= 0


def _buy_long(account: Account, data: st.DataObject) -> None:
    option = OptionId(ROOT, LONG_EXPIRY, Right.CALL, data.draw(strikes))
    mid = Price(data.draw(prices))
    fill = mid + Price(data.draw(st.integers(0, 5_000)))
    qty, fee = data.draw(st.integers(1, 3)), data.draw(fees)
    _entry(account, _event(Side.BUY, option, qty, account.tick(), limit=mid, fill=fill, fee=fee))


def _sell_short(account: Account, data: st.DataObject, long: tuple[OptionId, int]) -> None:
    option, qty = long
    strike = option.strike + Price.from_dollars(data.draw(st.integers(0, 50)))
    short = OptionId(ROOT, SHORT_EXPIRY, Right.CALL, strike)
    mid = Price(data.draw(prices))
    fill = Price(max(mid.units - data.draw(st.integers(0, 5_000)), 0))
    fee = data.draw(fees)
    _entry(account, _event(Side.SELL, short, qty, account.tick(), limit=mid, fill=fill, fee=fee))


def _close_short(account: Account, data: st.DataObject, short: tuple[OptionId, int]) -> None:
    option, qty = short
    how = data.draw(st.sampled_from(["buy", "expire", "assign"]))
    t = account.tick()
    if how == "buy":
        fill = Price(data.draw(prices))
        account.book_event(_event(Side.BUY, option, qty, t, limit=fill, fill=fill))
    elif how == "expire":
        account.book_event(_event(Side.EXPIRE, option, qty, t, limit=None, fill=Price(0)))
    else:
        event("assigned")
        account.book_event(_event(Side.ASSIGN, option, qty, t, limit=None, fill=None))
        shares = qty * 100
        account.marks[STOCK] = Mark(Price(data.draw(prices)), t, stale=False)
        sale = _event(Side.SELL, STOCK, shares, t, limit=None, fill=option.strike)
        account.book_event(sale)


def _cover(account: Account, data: st.DataObject) -> None:
    fill = Price(data.draw(prices))
    shares = -account.book.shares(STOCK)
    account.book_event(_event(Side.BUY, STOCK, shares, account.tick(), limit=fill, fill=fill))


def _sell_long(account: Account, data: st.DataObject, long: tuple[OptionId, int]) -> None:
    option, qty = long
    fill = Price(data.draw(prices))
    account.book_event(_event(Side.SELL, option, qty, account.tick(), limit=fill, fill=fill))


def _remark(account: Account, data: st.DataObject) -> None:
    """A new bar: each held instrument has a fresh mid, or none (its mark goes stale)."""
    fresh = {i: data.draw(st.one_of(st.none(), prices.map(Price))) for i in account.book.positions}
    before = account.book.cash
    account.marks = {**account.marks, **carry(account.marks, fresh, account.tick())}
    assert account.book.cash == before  # marking never moves cash (INV-01)


def _step(account: Account, data: st.DataObject) -> None:
    long, short = _long(account), _short(account)
    moves = ["mark"]
    if long is None and short is None:
        moves.append("buy_long")
    if long is not None and short is None:
        moves += ["sell_short", "sell_long"]
    if short is not None:
        moves.append("close_short")
    if account.book.shares(STOCK) < 0:
        moves.append("cover")
    move = data.draw(st.sampled_from(moves))
    event(move)
    if move == "mark":
        _remark(account, data)
    elif move == "buy_long":
        _buy_long(account, data)
    elif move == "sell_short":
        assert long is not None
        _sell_short(account, data, long)
    elif move == "sell_long":
        assert long is not None
        _sell_long(account, data, long)
    elif move == "close_short":
        assert short is not None
        _close_short(account, data, short)
    else:
        _cover(account, data)


@given(
    data=st.data(),
    cash=st.integers(0, 10_000_000_000).map(Money),
    steps=st.integers(1, 40),
)
def test_inv_01_02_08_10_hold_over_random_trading(
    data: st.DataObject, cash: Money, steps: int
) -> None:
    account = Account(Book(cash))
    for _ in range(steps):
        _step(account, data)
        valuation = value(account.book, account.marks)
        assert valuation.nav == _nav(account)  # INV-02
        shorts, longs = account.book.short_calls, account.book.long_calls
        if shorts:
            assert sum(shorts.values()) == sum(longs.values())  # INV-10
    moved = sum((e.cash_delta for e in account.events), Money.zero())
    assert account.book.cash - cash == moved  # INV-01, over the whole run


@given(data=st.data())
def test_inv_02_stale_marks_carry_the_last_mid(data: st.DataObject) -> None:
    option = OptionId(ROOT, LONG_EXPIRY, Right.CALL, Price.from_dollars(80))
    first = Price(data.draw(prices))
    marks: Marks = carry({}, {option: first}, START)
    for i in range(data.draw(st.integers(1, 10))):
        marks = carry(marks, {option: None}, START + timedelta(hours=i + 1))
        assert marks[option] == Mark(first, START, stale=True)
    book = Book(Money(1_000_000_000), {option: 1})
    assert value(book, marks).nav == Money(1_000_000_000) + first.notional(100, 1)
    assert value(book, marks).stale_flags == ("stale_long",)
