"""E-T1: a valid quote whose spread is within the leg's share of mid, exactly at the boundary."""

from datetime import date, datetime

import pytest

from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.strategy.ports import Leg
from pmcc.strategy.trigger import SpreadTrigger, as_fraction
from tests.fakes.view import ROOT, Row, StubView

MON = datetime(2026, 8, 31, 10, tzinfo=ET)
EXPIRY = date(2027, 2, 19)
OPTION = OptionId(ROOT, EXPIRY, Right.CALL, Price.from_dollars(80))
TRIGGER = SpreadTrigger(long_max_spread=0.03, short_max_spread=0.10)


def check(bid: str | None, ask: str | None, leg: Leg) -> bool:
    view = StubView(MON, chains={(EXPIRY, Right.CALL): [Row(80, bid, ask)]})
    return TRIGGER.check(view, OPTION, leg).passed


@pytest.mark.parametrize(
    ("bid", "ask", "leg", "passes"),
    [
        ("0.9850", "1.0150", Leg.LONG, True),  # exactly 3% of mid
        ("0.9849", "1.0151", Leg.LONG, False),  # just over
        ("0.9500", "1.0500", Leg.SHORT, True),  # exactly 10%
        ("0.9499", "1.0501", Leg.SHORT, False),
        ("0.9500", "1.0500", Leg.LONG, False),  # a short's spread fails the long's limit
    ],
)
def test_e_t1_spread_limit_is_inclusive_and_exact(
    bid: str, ask: str, leg: Leg, passes: bool
) -> None:
    assert check(bid, ask, leg) is passes


def test_e_t1_no_quote_fails() -> None:
    view = StubView(MON, chains={(EXPIRY, Right.CALL): [Row(80, None, None)]})
    result = TRIGGER.check(view, OPTION, Leg.LONG)
    assert not result.passed
    assert result.quote is None


def test_e_t1_reports_the_quote_and_spread() -> None:
    view = StubView(MON, chains={(EXPIRY, Right.CALL): [Row(80, "0.9850", "1.0150")]})
    result = TRIGGER.check(view, OPTION, Leg.LONG)
    assert result.quote is not None
    assert result.spread_pct == pytest.approx(0.03)


def test_thresholds_are_read_as_their_decimals() -> None:
    assert as_fraction(0.03) == pytest.approx(0.03)
    assert as_fraction(0.1).numerator == 1
    assert as_fraction(0.1).denominator == 10
