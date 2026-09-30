"""Events and the book (P3-04): cash follows fills exactly; an uncovered short is an EngineError."""

from datetime import date, datetime

import pytest

from pmcc.accounting.book import Book
from pmcc.accounting.events import Event, StockId, expected_cash
from pmcc.domain.clock import ET
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId

ROOT = "SYN"
FRI = datetime(2026, 9, 4, 15, tzinfo=ET)
LONG = OptionId(ROOT, date(2027, 1, 15), Right.CALL, Price.from_dollars(80))
SHORT = OptionId(ROOT, date(2026, 9, 4), Right.CALL, Price.from_dollars(102))
STOCK = StockId(ROOT)
RULE = RuleId("E-L1")
ZERO = Money.zero()


def event(side: Side, instrument: OptionId | StockId, qty: int, fill: Price | None,
          fee: Money = ZERO, t: datetime = FRI) -> Event:  # fmt: skip
    cash = expected_cash(side, instrument, qty, fill, fee)
    return Event(t, side, instrument, qty, fill, fill, cash, RULE, fee=fee)


def buy_long(qty: int = 1) -> Book:
    return Book(Money.from_dollars(10_000)).apply(event(Side.BUY, LONG, qty, Price(215_000)))


def test_inv_01_a_buy_pays_fill_times_100_times_qty_plus_fee() -> None:
    e = event(Side.BUY, LONG, 2, Price(215_001), fee=Money.from_dollars("0.65"))
    assert e.cash_delta == Money(-(215_001 * 200) - 6_500)
    book = Book(Money.from_dollars(10_000)).apply(e)
    assert book.cash == Money.from_dollars(10_000) + e.cash_delta


def test_inv_01_a_sell_receives_fill_times_100_times_qty_less_fee() -> None:
    e = event(Side.SELL, SHORT, 1, Price(8_125), fee=Money.from_dollars("0.65"))
    assert e.cash_delta == Money(8_125 * 100 - 6_500)


def test_inv_01_an_event_whose_cash_does_not_follow_its_fill_is_refused() -> None:
    with pytest.raises(ValueError, match="cash"):
        Event(FRI, Side.BUY, LONG, 1, Price(1), Price(215_000), Money(-1), RULE)


def test_expire_is_zero_cash_at_zero_fill() -> None:
    e = Event(FRI, Side.EXPIRE, SHORT, 1, None, Price(0), Money.zero(), RULE)
    assert e.cash_delta == Money.zero()
    with pytest.raises(ValueError, match=r"EXPIRE row fills at \$0"):
        Event(FRI, Side.EXPIRE, SHORT, 1, None, Price(1), Money.zero(), RULE)


def test_assign_has_no_fill_and_no_cash() -> None:
    with pytest.raises(ValueError, match="no fill"):
        Event(FRI, Side.ASSIGN, SHORT, 1, None, Price(1_020_000), Money.zero(), RULE)
    with pytest.raises(ValueError, match="option row"):
        Event(FRI, Side.ASSIGN, STOCK, 100, None, None, Money.zero(), RULE)


def test_a_stock_row_has_no_fee_and_multiplier_one() -> None:
    e = event(Side.SELL, STOCK, 100, Price.from_dollars(102))
    assert e.cash_delta == Money.from_dollars(10_200)
    with pytest.raises(ValueError, match="per option contract"):
        event(Side.SELL, STOCK, 100, Price.from_dollars(102), fee=Money(1))


@pytest.mark.parametrize("qty", [0, -1])
def test_an_event_quantity_is_positive(qty: int) -> None:
    with pytest.raises(ValueError, match="positive"):
        Event(FRI, Side.BUY, LONG, qty, Price(1), Price(1), Money.zero(), RULE)


def test_an_event_time_is_tz_aware() -> None:
    with pytest.raises(ValueError, match="tz-aware"):
        event(Side.BUY, LONG, 1, Price(1), t=FRI.replace(tzinfo=None))


def test_inv_05_a_covered_short_is_booked() -> None:
    book = buy_long().apply(event(Side.SELL, SHORT, 1, Price(8_000)))
    assert book.short_calls == {SHORT: 1}
    assert book.long_calls == {LONG: 1}


def test_inv_05_a_short_with_no_long_raises() -> None:
    with pytest.raises(EngineError, match="uncovered"):
        Book(Money.zero()).apply(event(Side.SELL, SHORT, 1, Price(8_000)))


def test_inv_05_a_short_below_the_long_strike_raises() -> None:
    below = OptionId(ROOT, SHORT.expiry, Right.CALL, Price.from_dollars(79))
    with pytest.raises(EngineError, match="uncovered"):
        buy_long().apply(event(Side.SELL, below, 1, Price(8_000)))


def test_inv_05_a_short_at_the_long_strike_is_covered() -> None:
    at = OptionId(ROOT, SHORT.expiry, Right.CALL, LONG.strike)
    assert buy_long().apply(event(Side.SELL, at, 1, Price(8_000))).short_calls == {at: 1}


def test_inv_05_a_short_expiring_after_the_long_raises() -> None:
    later = OptionId(ROOT, date(2027, 2, 19), Right.CALL, SHORT.strike)
    with pytest.raises(EngineError, match="uncovered"):
        buy_long().apply(event(Side.SELL, later, 1, Price(8_000)))


def test_inv_10_a_short_smaller_than_the_long_raises() -> None:
    with pytest.raises(EngineError, match="quantity"):
        buy_long(2).apply(event(Side.SELL, SHORT, 1, Price(8_000)))


def test_inv_05_selling_the_long_under_a_short_raises() -> None:
    book = buy_long().apply(event(Side.SELL, SHORT, 1, Price(8_000)))
    with pytest.raises(EngineError, match="uncovered"):
        book.apply(event(Side.SELL, LONG, 1, Price(215_000)))


def test_a_sale_larger_than_the_long_is_a_flip_and_raises() -> None:
    with pytest.raises(EngineError, match="flip"):
        buy_long().apply(event(Side.SELL, LONG, 2, Price(215_000)))


def test_puts_are_never_held() -> None:
    put = OptionId(ROOT, SHORT.expiry, Right.PUT, Price.from_dollars(100))
    with pytest.raises(EngineError, match="only calls"):
        Book(Money.from_dollars(1_000)).apply(event(Side.BUY, put, 1, Price(100)))


def test_expire_closes_the_short_on_its_expiry_day() -> None:
    book = buy_long().apply(event(Side.SELL, SHORT, 1, Price(8_000)))
    expired = book.apply(Event(FRI, Side.EXPIRE, SHORT, 1, None, Price(0), Money.zero(), RULE))
    assert expired.short_calls == {}
    assert expired.cash == book.cash


def test_expire_before_the_expiry_day_raises() -> None:
    book = buy_long().apply(event(Side.SELL, SHORT, 1, Price(8_000)))
    thursday = datetime(2026, 9, 3, 16, tzinfo=ET)
    with pytest.raises(EngineError, match="not its expiry"):
        book.apply(Event(thursday, Side.EXPIRE, SHORT, 1, None, Price(0), Money.zero(), RULE))


def test_expire_or_assign_without_a_short_raises() -> None:
    for side, fill in ((Side.EXPIRE, Price(0)), (Side.ASSIGN, None)):
        with pytest.raises(EngineError, match="needs a short call"):
            buy_long().apply(Event(FRI, side, SHORT, 1, None, fill, Money.zero(), RULE))


def test_assignment_then_stock_sale_leaves_short_stock_and_the_long() -> None:
    book = buy_long().apply(event(Side.SELL, SHORT, 1, Price(8_000)))
    book = book.apply(Event(FRI, Side.ASSIGN, SHORT, 1, None, None, Money.zero(), RULE))
    book = book.apply(event(Side.SELL, STOCK, 100, SHORT.strike))
    assert book.shares(STOCK) == -100
    assert book.long_calls == {LONG: 1}
    assert book.short_calls == {}
    covered = book.apply(event(Side.BUY, STOCK, 100, Price.from_dollars(103)))
    assert covered.shares(STOCK) == 0
    assert STOCK not in covered.positions
