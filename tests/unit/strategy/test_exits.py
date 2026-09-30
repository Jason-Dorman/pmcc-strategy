"""The exit rules at their boundaries (TEST-STRATEGY §4; DEC-27, DEC-28)."""

from datetime import date, datetime, time

import pytest

from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.pricing.iv import IvCode
from pmcc.strategy.exits import (
    DefensiveDelta,
    ExpiryResolver,
    FridayCheck,
    LongDeltaReset,
    LongDteRoll,
    TakeProfit,
    friday_check_bar,
)
from pmcc.strategy.ports import ExitStatus, HeldLeg, PositionState
from tests.fakes.view import CALENDAR, ROOT, Row, StubView

EXPIRY = date(2026, 9, 4)
LONG_EXPIRY = date(2026, 12, 18)
SHORT = OptionId(ROOT, EXPIRY, Right.CALL, Price.from_dollars(102))
LONG = OptionId(ROOT, LONG_EXPIRY, Right.CALL, Price.from_dollars(80))
ENTRY = datetime(2026, 8, 31, 10, tzinfo=ET)
CHECK = time(15)


def at(day: int, hour: int) -> datetime:
    """The bar ending `hour`:00 ET on September `day`, 2026."""
    return datetime(2026, 9, day, hour, tzinfo=ET)


def held_short(credit: str = "1.00", em: str | None = "2.40") -> PositionState:
    em_price = None if em is None else Price.from_dollars(em)
    short = HeldLeg(SHORT, 1, Price.from_dollars(credit), ENTRY, em_price)
    return PositionState(long=None, short=short)


def held_long() -> PositionState:
    return PositionState(HeldLeg(LONG, 1, Price.from_dollars(21), ENTRY), None)


def view(now: datetime, *rows: Row, spot: str | None = "100", expiry: date = EXPIRY) -> StubView:
    price = None if spot is None else Price.from_dollars(spot)
    return StubView(now, spot_price=price, chains={(expiry, Right.CALL): rows})


# ---- the Friday check bar ------------------------------------------------------------------


def test_x_s3_check_bar_is_the_last_bar_ending_by_15_00() -> None:
    assert friday_check_bar(CALENDAR, EXPIRY, CHECK) == at(4, 15)


def test_x_s3_check_bar_on_a_half_day_is_its_13_00_close() -> None:
    bar = friday_check_bar(CALENDAR, date(2026, 11, 27), CHECK)
    assert bar == datetime(2026, 11, 27, 13, tzinfo=ET)


def test_x_s3_check_bar_follows_a_thursday_expiry() -> None:
    thursday = datetime(2026, 7, 2, 15, tzinfo=ET)
    assert friday_check_bar(CALENDAR, date(2026, 7, 2), CHECK) == thursday


# ---- X-S1: take profit ---------------------------------------------------------------------


def x_s1(now: datetime, bid: str, ask: str) -> ExitStatus | None:
    outcome = TakeProfit(0.25, CHECK).check(view(now, Row(102, bid, ask, 0.1)), held_short())
    return None if outcome is None else outcome.status


def test_x_s1_fires_at_exactly_25pct_of_the_credit() -> None:
    assert x_s1(at(2, 12), "0.24", "0.26") is ExitStatus.FIRE  # mid 0.25


def test_x_s1_does_not_fire_one_unit_above() -> None:
    assert x_s1(at(2, 12), "0.2401", "0.2601") is ExitStatus.PASS  # mid 0.2501


def test_x_s1_is_not_checked_on_or_after_the_friday_check() -> None:
    assert x_s1(at(4, 14), "0.01", "0.03") is ExitStatus.FIRE
    assert x_s1(at(4, 15), "0.01", "0.03") is None
    assert x_s1(at(4, 16), "0.01", "0.03") is None


def test_x_s1_needs_a_fresh_quote() -> None:
    outcome = TakeProfit(0.25, CHECK).check(view(at(2, 12), Row(102, None, None)), held_short())
    assert outcome is None


def test_x_s1_needs_a_short() -> None:
    assert TakeProfit(0.25, CHECK).check(view(at(2, 12)), held_long()) is None


# ---- X-S2: defensive -----------------------------------------------------------------------


def x_s2(delta: float, code: IvCode = IvCode.OK) -> ExitStatus | None:
    rows = view(at(2, 12), Row(102, "1.50", "1.56", delta, code=code))
    outcome = DefensiveDelta(0.60).check(rows, held_short())
    return None if outcome is None else outcome.status


def test_x_s2_does_not_fire_at_exactly_0_60() -> None:
    assert x_s2(0.60) is ExitStatus.PASS


def test_x_s2_fires_just_above_0_60() -> None:
    assert x_s2(0.6000001) is ExitStatus.FIRE


def test_x_s2_fires_on_dec_27s_deep_itm_delta() -> None:
    assert x_s2(1.0, IvCode.BELOW_FLOOR) is ExitStatus.FIRE


@pytest.mark.parametrize("code", [IvCode.NO_CONVERGENCE, IvCode.NO_SPOT, IvCode.EXPIRED])
def test_x_s2_without_a_delta_is_unevaluated(code: IvCode) -> None:
    rows = view(at(2, 12), Row(102, "1.50", "1.56", float("nan"), code=code))
    outcome = DefensiveDelta(0.60).check(rows, held_short())
    assert outcome is not None
    assert outcome.status is ExitStatus.UNEVALUATED
    assert code.name in outcome.reason


def test_x_s2_needs_a_fresh_quote() -> None:
    rows = view(at(2, 12), Row(102, None, None, 0.9))
    assert DefensiveDelta(0.60).check(rows, held_short()) is None


# ---- X-S3: the Friday check ----------------------------------------------------------------


def x_s3(now: datetime, spot: str | None, em: str | None = "2.40") -> ExitStatus | None:
    outcome = FridayCheck(CHECK, 0.25).check(view(now, spot=spot), held_short(em=em))
    return None if outcome is None else outcome.status


def test_x_s3_fires_at_exactly_strike_less_a_quarter_em() -> None:
    assert x_s3(at(4, 15), "101.40") is ExitStatus.FIRE  # 102 − 0.25 × 2.40 = 101.40


def test_x_s3_does_not_fire_one_unit_below() -> None:
    assert x_s3(at(4, 15), "101.3999") is ExitStatus.PASS


def test_x_s3_is_checked_only_on_the_check_bar() -> None:
    assert x_s3(at(4, 14), "105") is None
    assert x_s3(at(4, 16), "105") is None
    assert x_s3(at(3, 15), "105") is None


def test_x_s3_fires_without_a_quote_on_the_short() -> None:
    """The trigger reads spot; only the fill needs a quote (DEC-28)."""
    assert x_s3(at(4, 15), "103") is ExitStatus.FIRE


@pytest.mark.parametrize(("spot", "em"), [(None, "2.40"), ("103", None)])
def test_x_s3_without_spot_or_em_is_unevaluated(spot: str | None, em: str | None) -> None:
    assert x_s3(at(4, 15), spot, em) is ExitStatus.UNEVALUATED


# ---- X-S4 / X-S5 ---------------------------------------------------------------------------


def test_x_s4_a_close_on_the_strike_expires() -> None:
    assert str(ExpiryResolver().resolve(Price.from_dollars(102), SHORT)) == "X-S4"


def test_x_s5_a_close_one_unit_above_is_assigned() -> None:
    assert str(ExpiryResolver().resolve(Price.from_dollars("102.0001"), SHORT)) == "X-S5"


def test_the_expiry_close_bar_is_the_sessions_close() -> None:
    assert ExpiryResolver.is_close_bar(CALENDAR, at(4, 16), EXPIRY)
    assert not ExpiryResolver.is_close_bar(CALENDAR, at(4, 15), EXPIRY)


# ---- X-L1, X-L2 ----------------------------------------------------------------------------


def x_l1(delta: float, code: IvCode = IvCode.OK) -> ExitStatus | None:
    rows = view(at(8, 10), Row(80, "21.00", "21.20", delta, code=code), expiry=LONG_EXPIRY)
    outcome = LongDeltaReset(0.50).check(rows, held_long())
    return None if outcome is None else outcome.status


def test_x_l1_does_not_fire_at_exactly_0_50() -> None:
    assert x_l1(0.50) is ExitStatus.PASS


def test_x_l1_fires_just_below_0_50() -> None:
    assert x_l1(0.4999999) is ExitStatus.FIRE


def test_x_l1_without_a_delta_is_unevaluated() -> None:
    assert x_l1(float("nan"), IvCode.NO_CONVERGENCE) is ExitStatus.UNEVALUATED


def x_l2(now: datetime, quoted: bool = True) -> ExitStatus | None:
    bid, ask = ("21.00", "21.20") if quoted else (None, None)
    rows = view(now, Row(80, bid, ask, 0.8), expiry=LONG_EXPIRY)
    outcome = LongDteRoll(90).check(rows, held_long())
    return None if outcome is None else outcome.status


def test_x_l2_does_not_fire_at_exactly_90_dte() -> None:
    assert x_l2(datetime(2026, 9, 19, 10, tzinfo=ET)) is ExitStatus.PASS  # Dec 18 − 90 days


def test_x_l2_fires_at_89_dte() -> None:
    assert x_l2(datetime(2026, 9, 20, 10, tzinfo=ET)) is ExitStatus.FIRE


def test_x_l2_needs_a_fresh_quote() -> None:
    assert x_l2(datetime(2026, 9, 20, 10, tzinfo=ET), quoted=False) is None
