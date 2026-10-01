"""E-T1: a valid quote whose spread is within the leg's share of mid, exactly at the boundary; and
the entry-timing runs' fixed-bar trigger (PO, DEC-31)."""

from datetime import UTC, date, datetime, time

import pytest

from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.strategy.ports import Leg
from pmcc.strategy.trigger import FixedBarTrigger, SpreadTrigger, as_fraction
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


# ---- DEC-31: the entry-timing runs' fixed-bar trigger ------------------------------------------

FIXED = FixedBarTrigger(bar=3, spread=TRIGGER)
HALF_DAY = date(2026, 11, 27)  # day after Thanksgiving: closes 13:00, so 4 session bars


@pytest.mark.parametrize("hour", range(10, 17))
def test_dec_31_fixed_bar_decides_the_short_only_on_its_bar(hour: int) -> None:
    view = StubView(datetime(2026, 8, 31, hour, tzinfo=ET))
    assert FIXED.can_decide(view, Leg.SHORT) is (hour == 12)  # bar 3 ends 12:00


@pytest.mark.parametrize("hour", range(10, 17))
def test_dec_31_fixed_bar_lets_the_long_decide_on_any_bar(hour: int) -> None:
    view = StubView(datetime(2026, 8, 31, hour, tzinfo=ET))
    assert FIXED.can_decide(view, Leg.LONG)


def test_dec_31_fixed_bar_past_a_half_days_close_never_decides() -> None:
    late = FixedBarTrigger(bar=5, spread=TRIGGER)
    for hour in range(10, 14):
        assert not late.can_decide(StubView(datetime.combine(HALF_DAY, time(hour), ET)), Leg.SHORT)


def test_dec_31_fixed_bar_reads_its_bar_in_new_york_time() -> None:
    utc = datetime(2026, 8, 31, 16, tzinfo=UTC)  # 12:00 ET
    assert FIXED.can_decide(StubView(utc), Leg.SHORT)


@pytest.mark.parametrize(
    ("bid", "ask", "leg", "passes"),
    [
        ("0.9500", "1.0500", Leg.SHORT, True),  # exactly 10%: E-T1's test, unchanged
        ("0.9499", "1.0501", Leg.SHORT, False),
        ("0.9850", "1.0150", Leg.LONG, True),
        ("0.9849", "1.0151", Leg.LONG, False),
    ],
)
def test_dec_31_fixed_bar_applies_e_t1s_spread_test(
    bid: str, ask: str, leg: Leg, passes: bool
) -> None:
    view = StubView(MON, chains={(EXPIRY, Right.CALL): [Row(80, bid, ask)]})
    assert FIXED.check(view, OPTION, leg).passed is passes
