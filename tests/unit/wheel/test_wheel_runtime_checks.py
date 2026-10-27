"""The wheel's runtime invariants fire (W2-02): WINV-01, 02, 05 to 08 on a bar, and the engine's
per-event and per-run guards, WINV-03 and 09 and the market's r."""

from dataclasses import replace
from datetime import date, datetime

import pytest

from pmcc.accounting.events import Event, Instrument, StockId, expected_cash
from pmcc.accounting.marks import Mark
from pmcc.config.calendar import load_calendar
from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId
from pmcc.engine.invariants import InvariantViolation
from pmcc.wheel.book import WheelBook, value
from pmcc.wheel.invariants import check_bar

CAL = load_calendar()
EXPIRY = date(2026, 9, 4)
MON = datetime(2026, 8, 31, 10, tzinfo=ET)
PUT = OptionId("SYN", EXPIRY, Right.PUT, Price.from_dollars(98))
CASH = Money.from_dollars(25_000)


def _sale() -> Event:
    fill = Price.from_dollars("1.20")
    cash = expected_cash(Side.SELL, PUT, 1, fill, Money.zero())
    return Event(MON, Side.SELL, PUT, 1, fill, fill, cash, RuleId("W-P1"))


def _after_sale() -> tuple[WheelBook, dict[Instrument, Mark], Event]:
    sale = _sale()
    book = WheelBook(CASH).apply(sale)
    return book, {PUT: Mark(Price.from_dollars("1.20"), MON, stale=False)}, sale


def test_winv_a_consistent_bar_passes() -> None:
    book, marks, sale = _after_sale()
    check_bar(MON, book, marks, CASH, [sale], value(book, marks), CAL)


def test_winv_01_fires_when_cash_moves_without_a_row() -> None:
    book, marks, sale = _after_sale()
    with pytest.raises(InvariantViolation, match="WINV-01"):
        check_bar(MON, book, marks, CASH, [], value(book, marks), CAL)
    with pytest.raises(InvariantViolation, match="WINV-01"):
        check_bar(MON, book, marks, CASH - Money(1), [sale], value(book, marks), CAL)


def test_winv_02_fires_when_nav_doesnt_reconcile() -> None:
    book, marks, sale = _after_sale()
    wrong = replace(value(book, marks), put_mv=Money.zero())
    with pytest.raises(InvariantViolation, match="WINV-02"):
        check_bar(MON, book, marks, CASH, [sale], wrong, CAL)


@pytest.mark.parametrize(
    "positions",
    [
        {PUT: -1},  # cash $0 can't secure it (WINV-05)
        {PUT: -1, StockId("SYN"): 100},  # shares beside a put (WINV-07)
        {OptionId("SYN", EXPIRY, Right.CALL, Price.from_dollars(102)): -1},  # uncovered (WINV-06)
    ],
)
def test_winv_05_06_07_fire_on_a_book_outside_the_rules(positions: dict[Instrument, int]) -> None:
    book = WheelBook(Money.zero(), positions)  # built directly: `apply` would refuse it
    marks = {i: Mark(Price.from_dollars(1), MON, stale=False) for i in positions}
    with pytest.raises(InvariantViolation, match="WINV-05/06/07"):
        check_bar(MON, book, marks, Money.zero(), [], value(book, marks), CAL)


def test_winv_08_fires_on_an_option_open_after_its_expiry_session() -> None:
    book, marks, _ = _after_sale()
    close = CAL.session(EXPIRY).close_bar_end
    check_bar(close, book, marks, book.cash, [], value(book, marks), CAL)  # its last bar: fine
    later = datetime(2026, 9, 8, 10, tzinfo=ET)
    with pytest.raises(InvariantViolation, match="WINV-08"):
        check_bar(later, book, marks, book.cash, [], value(book, marks), CAL)
