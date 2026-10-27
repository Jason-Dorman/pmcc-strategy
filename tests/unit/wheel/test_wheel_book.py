"""The wheel's book (W2-01): cash-secured puts, covered calls, assignment at the strike, and NAV.

WINV-05 to WINV-07 are the book's own checks, so a booking that would break one raises.
"""

from datetime import date, datetime

import pytest

from pmcc.accounting.events import Event, StockId, expected_cash
from pmcc.accounting.marks import Mark, Marks
from pmcc.domain.clock import ET
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId
from pmcc.wheel.book import WheelBook, WheelState, value

ROOT = "SYN"
EXPIRY = date(2026, 9, 4)
MON = datetime(2026, 8, 31, 10, tzinfo=ET)
FRI = datetime(2026, 9, 4, 16, tzinfo=ET)
PUT = OptionId(ROOT, EXPIRY, Right.PUT, Price.from_dollars(200))
CALL = OptionId(ROOT, EXPIRY, Right.CALL, Price.from_dollars(210))
STOCK = StockId(ROOT)
RULE = RuleId("W-P1")
CASH = Money.from_dollars(25_000)
ZERO = Money.zero()
D = Price.from_dollars


def event(side: Side, instrument: OptionId | StockId, qty: int, fill: Price | None,
          t: datetime = MON, fee: Money = ZERO) -> Event:  # fmt: skip
    cash = expected_cash(side, instrument, qty, fill, fee)
    return Event(t, side, instrument, qty, fill, fill, cash, RULE, fee=fee)


def sold_put() -> WheelBook:
    return WheelBook(CASH).apply(event(Side.SELL, PUT, 1, D("2.50")))


def assigned() -> WheelBook:
    book = sold_put().apply(event(Side.ASSIGN, PUT, 1, None, FRI))
    return book.apply(event(Side.BUY, STOCK, 100, PUT.strike, FRI))


def sold_call() -> WheelBook:
    return WheelBook(CASH, {STOCK: 100}).apply(event(Side.SELL, CALL, 1, D("1.10")))


# --- States -----------------------------------------------------------------------------------


def test_w_state_starts_in_cash() -> None:
    assert WheelBook(CASH).state is WheelState.CASH


def test_w_p4_a_sold_put_reserves_its_strike_and_adds_its_credit() -> None:
    book = sold_put()
    assert book.state is WheelState.PUT
    assert book.cash == Money.from_dollars(25_250)
    assert book.reserved == Money.from_dollars(20_000)
    assert book.short_put == (PUT, 1)


def test_w_x1_an_expired_put_frees_the_cash() -> None:
    book = sold_put().apply(event(Side.EXPIRE, PUT, 1, Price(0), FRI))
    assert book.state is WheelState.CASH
    assert (book.cash, book.reserved) == (Money.from_dollars(25_250), Money.zero())


def test_w_x2_assignment_buys_100_shares_at_the_strike() -> None:
    book = assigned()
    assert book.state is WheelState.SHARES
    assert book.shares == 100
    assert book.cash == Money.from_dollars(25_250 - 20_000)
    assert book.reserved == Money.zero()


def test_w_c1_a_call_sold_on_the_shares() -> None:
    book = sold_call()
    assert book.state is WheelState.CALL
    assert book.short_call == (CALL, 1)
    assert book.cash == Money.from_dollars(25_110)


def test_w_x3_an_expired_call_keeps_the_shares() -> None:
    book = sold_call().apply(event(Side.EXPIRE, CALL, 1, Price(0), FRI))
    assert book.state is WheelState.SHARES
    assert book.shares == 100


def test_w_x4_called_away_sells_the_shares_at_the_strike() -> None:
    book = sold_call().apply(event(Side.ASSIGN, CALL, 1, None, FRI))
    book = book.apply(event(Side.SELL, STOCK, 100, CALL.strike, FRI))
    assert book.state is WheelState.CASH
    assert book.cash == Money.from_dollars(25_110 + 21_000)
    assert book.shares == 0


# --- WINV-05 to WINV-07 -----------------------------------------------------------------------


def test_winv_05_refuses_a_put_cash_cant_secure() -> None:
    with pytest.raises(EngineError, match="cash-secured"):
        WheelBook(Money.from_dollars(19_000)).apply(event(Side.SELL, PUT, 1, D("2.50")))


def test_winv_05_counts_the_credit_toward_the_cash_securing_it() -> None:
    book = WheelBook(Money.from_dollars(19_750)).apply(event(Side.SELL, PUT, 1, D("2.50")))
    assert book.cash == book.reserved


def test_winv_06_refuses_a_call_the_shares_dont_cover() -> None:
    with pytest.raises(EngineError, match="covered"):
        WheelBook(CASH).apply(event(Side.SELL, CALL, 1, D("1.10")))
    with pytest.raises(EngineError, match="covered"):
        WheelBook(CASH, {STOCK: 100}).apply(event(Side.SELL, CALL, 2, D("1.10")))


def test_winv_06_refuses_selling_the_shares_under_a_call() -> None:
    with pytest.raises(EngineError, match="covered"):
        sold_call().apply(event(Side.SELL, STOCK, 100, D("205")))


def test_winv_07_refuses_a_put_while_shares_are_held() -> None:
    with pytest.raises(EngineError, match="shares"):
        WheelBook(CASH, {STOCK: 100}).apply(event(Side.SELL, PUT, 1, D("2.50")))


def test_winv_07_refuses_a_second_short_option() -> None:
    other = OptionId(ROOT, EXPIRY, Right.PUT, Price.from_dollars(190))
    with pytest.raises(EngineError, match="one short option"):
        sold_put().apply(event(Side.SELL, other, 1, D("1.00")))


def test_winv_07_refuses_a_long_option() -> None:
    with pytest.raises(EngineError, match="long option"):
        WheelBook(CASH).apply(event(Side.BUY, PUT, 1, D("2.50")))


def test_wheel_book_never_borrows() -> None:
    book = WheelBook(Money.from_dollars(1), {STOCK: 100})
    with pytest.raises(EngineError, match="negative"):
        book.apply(event(Side.SELL, CALL, 1, D("0.01"), fee=Money.from_dollars(5)))


def test_winv_07_refuses_short_stock() -> None:
    with pytest.raises(EngineError, match="short stock"):
        WheelBook(CASH).apply(event(Side.SELL, STOCK, 100, D("205")))


# --- Expiry and assignment rows ---------------------------------------------------------------


def test_w_x_expire_and_assign_happen_only_on_the_expiry_day() -> None:
    with pytest.raises(EngineError, match="expiry"):
        sold_put().apply(event(Side.EXPIRE, PUT, 1, Price(0), MON.replace(day=3, month=9)))


def test_w_x_expire_and_assign_need_the_short_option_held() -> None:
    with pytest.raises(EngineError, match="short option"):
        WheelBook(CASH).apply(event(Side.ASSIGN, PUT, 1, None, FRI))


def test_w_x_a_buyback_closes_a_short_without_flipping_it() -> None:
    book = sold_put().apply(event(Side.BUY, PUT, 1, D("1.00")))
    assert book.state is WheelState.CASH
    with pytest.raises(EngineError, match="flip"):
        sold_put().apply(event(Side.BUY, PUT, 2, D("1.00")))


# --- Valuation (WINV-02) ----------------------------------------------------------------------


def _marks(**prices: str) -> Marks:
    named = {"put": PUT, "call": CALL, "stock": STOCK}
    return {named[k]: Mark(D(v), MON, stale=False) for k, v in prices.items()}


def test_winv_02_nav_with_a_put_open() -> None:
    valuation = value(sold_put(), _marks(put="3.00"))
    assert valuation.put_mv == Money.from_dollars(300)
    assert valuation.nav == Money.from_dollars(25_250 - 300)
    assert valuation.free_cash == Money.from_dollars(25_250 - 20_000)


def test_winv_02_nav_with_shares_and_a_call() -> None:
    valuation = value(sold_call(), _marks(stock="205", call="0.40"))
    assert valuation.stock_mv == Money.from_dollars(20_500)
    assert valuation.nav == Money.from_dollars(25_110 + 20_500 - 40)
    assert valuation.free_cash == Money.from_dollars(25_110)


def test_winv_02_flags_a_stale_mark() -> None:
    marks: Marks = {PUT: Mark(D("3.00"), MON, stale=True)}
    assert value(sold_put(), marks).stale_flags == ("stale_put",)


def test_winv_02_flags_a_stale_call_and_stale_shares() -> None:
    marks: Marks = {CALL: Mark(D("0.40"), MON, stale=True), STOCK: Mark(D("205"), MON, stale=True)}
    assert value(sold_call(), marks).stale_flags == ("stale_call", "stale_stock")
    fresh: Marks = {CALL: Mark(D("0.40"), MON, stale=False), STOCK: Mark(D("205"), MON, stale=True)}
    assert value(sold_call(), fresh).stale_flags == ("stale_stock",)


def test_winv_02_refuses_a_held_instrument_with_no_mark() -> None:
    with pytest.raises(EngineError, match="mark"):
        value(sold_put(), {})
