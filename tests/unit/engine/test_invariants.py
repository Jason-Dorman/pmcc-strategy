"""Runtime invariants catch what they guard (ARCHITECTURE §8.4), and the loop's closing spot."""

from datetime import date, datetime

import pytest

from pmcc.accounting.book import Book
from pmcc.accounting.events import AuditValue, Event, Instrument, StockId, expected_cash
from pmcc.accounting.marks import Mark
from pmcc.accounting.valuation import value
from pmcc.config.calendar import load_calendar
from pmcc.domain.clock import ET
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId
from pmcc.domain.sessions import Session
from pmcc.engine.invariants import InvariantViolation, check_bar, check_event
from pmcc.engine.loop import closing_spot
from tests.fakes.view import StubView

T = datetime(2026, 8, 31, 10, tzinfo=ET)
LONG = OptionId("SYN", date(2027, 2, 19), Right.CALL, Price.from_dollars(90))
SHORT = OptionId("SYN", date(2026, 9, 4), Right.CALL, Price.from_dollars(102))
RULES = frozenset(RuleId(r) for r in ("E-L1", "E-S1", "X-S1"))
CALENDAR = load_calendar()


def event(rule: str, side: Side, option: OptionId, fill: int, audit: dict[str, AuditValue],
          limit: int | None = None) -> Event:  # fmt: skip
    price = Price(fill)
    cash = expected_cash(side, option, 1, price, Money.zero())
    lim = Price(limit if limit is not None else fill)
    return Event(T, side, option, 1, lim, price, cash, RuleId(rule), audit=audit)


def good_long(**audit: AuditValue) -> Event:
    return event("E-L1", Side.BUY, LONG, 128_700,
                 {"bid": 128_000, "ask": 129_400, "funds_after": 1, **audit})  # fmt: skip


def test_a_good_entry_passes() -> None:
    check_event(good_long(), RULES, 0.0)


def test_inv_09_a_rule_the_config_lacks_fails() -> None:
    with pytest.raises(InvariantViolation, match="INV-09"):
        check_event(event("X-S2", Side.BUY, SHORT, 100, {"bid": 90, "ask": 110}), RULES, 0.0)


def test_inv_03_a_fill_without_a_quote_fails() -> None:
    with pytest.raises(InvariantViolation, match="INV-03"):
        check_event(event("X-S1", Side.BUY, SHORT, 100, {}), RULES, 0.0)


def test_inv_03_a_fill_off_the_fill_model_fails() -> None:
    off = event("X-S1", Side.BUY, SHORT, 101, {"bid": 90, "ask": 110}, limit=100)
    with pytest.raises(InvariantViolation, match="INV-03"):
        check_event(off, RULES, 0.0)
    check_event(event("X-S1", Side.BUY, SHORT, 105, {"bid": 90, "ask": 110}, limit=100),
                RULES, 0.5)  # fmt: skip


def test_inv_08_an_entry_leaving_negative_funds_fails() -> None:
    with pytest.raises(InvariantViolation, match="INV-08"):
        check_event(good_long(funds_after=-1), RULES, 0.0)


def test_inv_06_a_short_entry_failing_e_s5_fails() -> None:
    audit: dict[str, AuditValue] = {"bid": 9_100, "ask": 9_600, "funds_after": 5,
                                    "e_s5_satisfied": False}  # fmt: skip
    with pytest.raises(InvariantViolation, match="INV-06"):
        check_event(event("E-S1", Side.SELL, SHORT, 9_350, audit), RULES, 0.0)


def test_an_assignment_sale_is_not_a_quote_fill() -> None:
    sale = event("X-S1", Side.SELL, SHORT, 1_020_000, {"assignment": True})
    check_event(sale, RULES, 0.0)


def _bar(book: Book, cash_before: Money, events: list[Event], marks: dict[OptionId, Mark],
         now: datetime = T) -> None:  # fmt: skip
    marked: dict[Instrument, Mark] = {**marks}
    check_bar(now, book, cash_before, events, value(book, marked), marked, CALENDAR)


def test_inv_01_cash_moving_without_a_row_fails() -> None:
    book = Book(Money(100))
    with pytest.raises(InvariantViolation, match="INV-01"):
        _bar(book, Money(0), [], {})


def test_inv_02_a_nav_that_does_not_reconcile_fails() -> None:
    book = Book(Money(0), {LONG: 1})
    marks: dict[Instrument, Mark] = {LONG: Mark(Price(100), T, stale=False)}
    good = value(book, marks)
    moved: dict[Instrument, Mark] = {LONG: Mark(Price(101), T, stale=False)}
    with pytest.raises(InvariantViolation, match="INV-02"):
        check_bar(T, book, Money(0), [], good, moved, CALENDAR)


def test_inv_05_an_uncovered_short_fails() -> None:
    book = Book(Money(0), {SHORT: -1})  # built directly: apply() would refuse it
    with pytest.raises(InvariantViolation, match="INV-05"):
        _bar(book, Money(0), [], {SHORT: Mark(Price(100), T, stale=False)})


def test_inv_07_a_short_open_after_its_expiry_session_fails() -> None:
    book = Book(Money(0), {LONG: 1, SHORT: -1})
    marks = {LONG: Mark(Price(100), T, stale=False), SHORT: Mark(Price(1), T, stale=False)}
    _bar(book, Money(0), [], marks, datetime(2026, 9, 4, 16, tzinfo=ET))
    with pytest.raises(InvariantViolation, match="INV-07"):
        _bar(book, Money(0), [], marks, datetime(2026, 9, 8, 10, tzinfo=ET))


def test_an_invariant_violation_is_an_engine_error() -> None:
    assert issubclass(InvariantViolation, EngineError)


# ---- the closing spot (PO, DEC-23) -----------------------------------------------------------

FRI = CALENDAR.session(date(2026, 9, 4))


class _Tape(StubView):
    trades: dict[datetime, Price]

    def spot(self, at: datetime | None = None) -> Price | None:
        return self.trades.get(self._gate(at))


def _tape(trades: dict[int, str]) -> _Tape:
    view = _Tape(FRI.close_bar_end)
    view.trades = {
        datetime(2026, 9, 4, h, tzinfo=ET): Price.from_dollars(p) for h, p in trades.items()
    }
    return view


def test_closing_spot_is_the_close_bars_trade() -> None:
    assert closing_spot(_tape({15: "101", 16: "102"}), FRI) == Price.from_dollars(102)


def test_closing_spot_falls_back_to_the_last_trade_in_the_session() -> None:
    assert closing_spot(_tape({12: "99", 14: "101"}), FRI) == Price.from_dollars(101)


def test_no_trade_all_session_is_an_engine_error() -> None:
    with pytest.raises(EngineError, match="no closing spot"):
        closing_spot(_tape({}), FRI)


def test_closing_spot_never_reads_another_session() -> None:
    assert isinstance(FRI, Session)
    view = _tape({})
    view.trades[datetime(2026, 9, 3, 16, tzinfo=ET)] = Price.from_dollars(100)
    with pytest.raises(EngineError):
        closing_spot(view, FRI)


def test_inv_03_a_stock_cover_off_the_fill_model_fails() -> None:
    stock = StockId("SYN")
    price = Price(1_040_100)
    cover = Event(T, Side.BUY, stock, 100, Price(1_040_000), price,
                  expected_cash(Side.BUY, stock, 100, price, Money.zero()), RuleId("X-S1"),
                  audit={"bid": 1_039_900, "ask": 1_040_100})  # fmt: skip
    with pytest.raises(InvariantViolation, match="INV-03"):
        check_event(cover, RULES, 0.0)


def test_inv_03_a_zero_bid_is_no_quote() -> None:
    with pytest.raises(InvariantViolation, match="INV-03"):
        check_event(event("X-S1", Side.BUY, SHORT, 5, {"bid": 0, "ask": 10}, limit=5), RULES, 0.0)


def test_inv_03_a_limit_that_is_not_the_mid_fails() -> None:
    wrong_limit = event("X-S1", Side.BUY, SHORT, 100, {"bid": 90, "ask": 110}, limit=99)
    with pytest.raises(InvariantViolation, match="INV-03"):
        check_event(wrong_limit, RULES, 0.0)
