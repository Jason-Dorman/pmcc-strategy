"""Marks, valuation, Reg T and the ledger row (P3-04; Spec › NAV and Reg T; PO, DEC-10)."""

from datetime import date, datetime

import pytest

from pmcc.accounting.book import Book
from pmcc.accounting.events import Event, Instrument, StockId, expected_cash
from pmcc.accounting.ledger import ledger_row
from pmcc.accounting.marks import Mark, carry
from pmcc.accounting.regt import funds_after, regt
from pmcc.accounting.valuation import value
from pmcc.domain.clock import ET
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId

ROOT = "META"
T = datetime(2026, 9, 4, 16, tzinfo=ET)
LONG = OptionId(ROOT, date(2027, 1, 15), Right.CALL, Price.from_dollars(600))
SHORT = OptionId(ROOT, date(2026, 9, 4), Right.CALL, Price.from_dollars(740))
STOCK = StockId(ROOT)
RULE = RuleId("X-S5")


def mark(dollars: str | int, stale: bool = False) -> Mark:
    return Mark(Price.from_dollars(dollars), T, stale)


def test_nav_is_cash_plus_long_less_short_plus_stock() -> None:
    book = Book(Money.from_dollars(1_000), {LONG: 1, SHORT: -1})
    marks: dict[Instrument, Mark] = {LONG: mark(160), SHORT: mark("2.50")}
    v = value(book, marks)
    assert v.long_mv == Money.from_dollars(16_000)
    assert v.short_mv == Money.from_dollars(250)
    assert v.nav == Money.from_dollars(1_000 + 16_000 - 250)


def test_a_held_instrument_without_a_mark_is_an_engine_error() -> None:
    with pytest.raises(EngineError, match="never had a mark"):
        value(Book(Money.zero(), {LONG: 1}), {})


def test_diagonal_only_available_funds_are_cash_less_short_mv() -> None:
    """Spec: with only the diagonal open, available funds reduce to cash − short call MV."""
    book = Book(Money.from_dollars(1_000), {LONG: 1, SHORT: -1})
    marks: dict[Instrument, Mark] = {LONG: mark(160), SHORT: mark("2.50")}
    r = regt(book, value(book, marks), marks)
    assert r.im == Money.from_dollars(16_000)  # the long, paid in full
    assert r.mm == r.im
    assert r.available_funds == Money.from_dollars(1_000 - 250)
    assert r.excess_equity == r.available_funds


def test_dec_10_hedged_short_stock_needs_no_initial_beyond_the_proceeds() -> None:
    book = Book(Money.from_dollars(80_000), {LONG: 1, STOCK: -100})
    marks: dict[Instrument, Mark] = {LONG: mark(150), STOCK: mark(750)}
    r = regt(book, value(book, marks), marks)
    assert r.hedged
    assert r.stock_initial == Money.zero()
    assert r.im == Money.from_dollars(15_000)


def test_dec_10_hedged_maintenance_is_10pct_of_the_long_strike() -> None:
    """DEC-10's worked example: META at $750 against a $600 long needs $6,000, not $22,500."""
    book = Book(Money.from_dollars(80_000), {LONG: 1, STOCK: -100})
    marks: dict[Instrument, Mark] = {LONG: mark(150), STOCK: mark(750)}
    r = regt(book, value(book, marks), marks)
    assert r.stock_maintenance == Money.from_dollars(6_000)
    assert r.mm == Money.from_dollars(15_000 + 6_000)


def test_dec_10_hedged_maintenance_adds_the_long_calls_out_of_the_money_amount() -> None:
    book = Book(Money.from_dollars(80_000), {LONG: 1, STOCK: -100})
    # the $600 long is $10 out of the money
    marks: dict[Instrument, Mark] = {LONG: mark(10), STOCK: mark(590)}
    r = regt(book, value(book, marks), marks)
    assert r.stock_maintenance == Money.from_dollars(6_000 + 1_000)


def test_dec_10_hedged_maintenance_is_capped_at_30pct_of_the_short() -> None:
    deep = OptionId(ROOT, LONG.expiry, Right.CALL, Price.from_dollars(700))
    book = Book(Money.from_dollars(80_000), {deep: 1, STOCK: -100})
    # 10% of $70,000 + $60,000 OTM, cap $3,000
    marks: dict[Instrument, Mark] = {deep: mark(1), STOCK: mark(100)}
    r = regt(book, value(book, marks), marks)
    assert r.stock_maintenance == Money.from_dollars(3_000)


def test_dec_10_hedged_cap_has_a_5_dollar_a_share_floor() -> None:
    low = OptionId(ROOT, LONG.expiry, Right.CALL, Price.from_dollars(10))
    book = Book(Money.from_dollars(80_000), {low: 1, STOCK: -100})
    # 10% of $1,000 = $100 < cap max($500, $360)
    marks: dict[Instrument, Mark] = {low: mark(1), STOCK: mark(12)}
    r = regt(book, value(book, marks), marks)
    assert r.stock_maintenance == Money.from_dollars(100)
    # OTM $800 + $100 = $900 > cap max($500, $60)
    marks: dict[Instrument, Mark] = {low: mark(1), STOCK: mark(2)}
    r = regt(book, value(book, marks), marks)
    assert r.stock_maintenance == Money.from_dollars(500)


def test_unhedged_short_stock_is_150pct_initial_and_30pct_maintenance() -> None:
    book = Book(Money.from_dollars(80_000), {STOCK: -100})
    marks: dict[Instrument, Mark] = {STOCK: mark(750)}
    r = regt(book, value(book, marks), marks)
    assert not r.hedged
    assert r.stock_initial == Money.from_dollars(37_500)
    assert r.stock_maintenance == Money.from_dollars(22_500)


def test_a_requirement_is_rounded_up_to_the_next_unit() -> None:
    book = Book(Money.zero(), {STOCK: -1})
    # 50% and 30% of 3 units
    marks: dict[Instrument, Mark] = {STOCK: Mark(Price(3), T, stale=False)}
    r = regt(book, value(book, marks), marks)
    assert r.stock_initial == Money(2)
    assert r.stock_maintenance == Money(1)


def test_funds_negative_flags_the_ledger_row() -> None:
    book = Book(Money.from_dollars(100), {LONG: 1, STOCK: -100})
    marks: dict[Instrument, Mark] = {LONG: mark(150), STOCK: mark(750)}
    v = value(book, marks)
    r = regt(book, v, marks)
    assert r.funds_negative
    row = ledger_row(T, book, marks, v, r, {LONG: 0.95}, flags=["exit_pending"])
    assert row.flags == ("exit_pending", "funds_negative")
    assert row.stock is not None
    assert row.stock.shares == -100
    assert row.long is not None
    assert row.long.delta == 0.95
    assert row.short is None


def test_ledger_row_carries_stale_flags_and_marks() -> None:
    book = Book(Money.from_dollars(1_000), {LONG: 1, SHORT: -1})
    marks = carry({LONG: mark(160), SHORT: mark(3)}, {LONG: None, SHORT: Price(20_000)}, T)
    v = value(book, marks)
    row = ledger_row(T, book, marks, v, regt(book, v, marks), {})
    assert row.flags == ("stale_long",)
    assert row.long is not None
    assert row.long.stale
    assert row.short is not None
    assert row.short.mark == Price(20_000)
    assert row.nav == v.nav


def test_carry_leaves_out_an_instrument_never_marked() -> None:
    assert carry({}, {LONG: None}, T) == {}


def test_inv_08_funds_after_marks_the_new_leg_at_its_limit() -> None:
    book = Book(Money.from_dollars(16_000))
    fill = Price.from_dollars(160)
    buy = Event(T, Side.BUY, LONG, 1, Price.from_dollars(159), fill,
                expected_cash(Side.BUY, LONG, 1, fill, Money.zero()), RuleId("E-L1"))  # fmt: skip
    assert funds_after(book, {}, buy) == Money.zero()
    rich = Event(T, Side.BUY, LONG, 1, Price.from_dollars(159), Price.from_dollars(161),
                 Money.from_dollars(-16_100), RuleId("E-L1"))  # fmt: skip
    assert funds_after(book, {}, rich) == Money.from_dollars(-100)
