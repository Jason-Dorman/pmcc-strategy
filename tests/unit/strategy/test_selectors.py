"""E-L2, E-L3, E-S2 and E-S3 baseline at their boundaries, with DEC-29's tie-breaks."""

from datetime import date, datetime

from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.pricing.iv import IvCode
from pmcc.strategy.ports import ExpiryKind, HeldLeg
from pmcc.strategy.selectors import (
    LongSelector,
    NearestDeltaLong,
    NearestDeltaShort,
    NearestDteExpiry,
    ShortSelector,
    WeekFinalExpiry,
)
from tests.fakes.view import ROOT, Row, StubView

MON = datetime(2026, 8, 31, 10, tzinfo=ET)
WEEKLY = date(2026, 9, 4)
M170, M190 = date(2027, 2, 17), date(2027, 3, 9)  # 170 and 190 days from Aug 31
M180 = date(2027, 2, 27)
LONG = HeldLeg(OptionId(ROOT, M180, Right.CALL, Price.from_dollars(80)), 1,
               Price.from_dollars(22), MON)  # fmt: skip


def monthlies(*expiries: date) -> dict[ExpiryKind, tuple[date, ...]]:
    return {ExpiryKind.MONTHLY: expiries}


# ---- E-L2 baseline: the monthly nearest 180 DTE ---------------------------------------------


def test_e_l2_picks_the_monthly_nearest_the_target_dte() -> None:
    view = StubView(MON, listed=monthlies(date(2026, 12, 18), M180, date(2027, 6, 17)))
    assert NearestDteExpiry(180).candidates(view) == (M180,)


def test_e_l2_a_tie_goes_to_the_later_expiry() -> None:
    view = StubView(MON, listed=monthlies(M170, M190))
    assert NearestDteExpiry(180).candidates(view) == (M190,)


def test_e_l2_one_day_nearer_wins_the_tie() -> None:
    view = StubView(MON, listed=monthlies(date(2027, 2, 18), M190))  # 171 vs 190 days
    assert NearestDteExpiry(180).candidates(view) == (date(2027, 2, 18),)


def test_e_l2_no_listed_monthly_selects_nothing() -> None:
    view = StubView(MON)
    assert NearestDteExpiry(180).candidates(view) == ()
    assert LongSelector(NearestDteExpiry(180), NearestDeltaLong(0.80)).select(view) is None


# ---- E-L3 baseline: delta nearest 0.80 -------------------------------------------------------


def long_view(*rows: Row) -> StubView:
    return StubView(MON, chains={(M180, Right.CALL): rows}, listed=monthlies(M180))


def pick_long(view: StubView) -> OptionId | None:
    selected = LongSelector(NearestDteExpiry(180), NearestDeltaLong(0.80)).select(view)
    return None if selected is None else selected.option


def strike(option: OptionId | None) -> float | None:
    return None if option is None else float(option.strike.to_dollars())


def test_e_l3_picks_the_delta_nearest_the_target() -> None:
    view = long_view(Row(75, "26.00", "26.40", 0.86), Row(80, "22.00", "22.40", 0.81),
                     Row(85, "18.00", "18.40", 0.74))  # fmt: skip
    assert strike(pick_long(view)) == 80


def test_e_l3_a_delta_tie_goes_to_the_lower_spread() -> None:
    view = long_view(Row(75, "26.00", "26.60", 0.85), Row(85, "18.00", "18.20", 0.75))
    assert strike(pick_long(view)) == 85


def test_e_l3_a_delta_and_spread_tie_goes_to_the_lower_strike() -> None:
    view = long_view(Row(75, "20.00", "20.40", 0.85), Row(85, "20.00", "20.40", 0.75))
    assert strike(pick_long(view)) == 75


def test_e_l3_skips_ineligible_and_unquoted_contracts() -> None:
    view = long_view(Row(80, "22.00", "22.40", 0.80, code=IvCode.NO_CONVERGENCE),
                     Row(81, None, None, 0.80), Row(90, "15.00", "15.40", 0.65))  # fmt: skip
    assert strike(pick_long(view)) == 90


def test_e_l3_no_eligible_contract_selects_nothing() -> None:
    assert pick_long(long_view(Row(80, None, None, 0.80))) is None


def test_e_l3_selection_values_explain_the_pick() -> None:
    view = long_view(Row(80, "22.00", "22.40", 0.81))
    selected = LongSelector(NearestDteExpiry(180), NearestDeltaLong(0.80)).select(view)
    assert selected is not None
    assert selected.values["delta"] == 0.81
    assert selected.values["target_delta"] == 0.80
    assert selected.values["dte"] == 180
    assert selected.values["strike"] == "80.0000"


# ---- E-S2: the week's final session ----------------------------------------------------------


def test_e_s2_is_the_weeks_final_session() -> None:
    assert WeekFinalExpiry().expiry(StubView(MON)) == WEEKLY


def test_e_s2_is_thursday_when_friday_is_closed() -> None:
    view = StubView(datetime(2026, 6, 29, 10, tzinfo=ET))
    assert WeekFinalExpiry().expiry(view) == date(2026, 7, 2)


def test_e_s2_after_a_monday_holiday_is_still_friday() -> None:
    view = StubView(datetime(2026, 9, 8, 10, tzinfo=ET))
    assert WeekFinalExpiry().expiry(view) == date(2026, 9, 11)


# ---- E-S3 baseline: OTM delta nearest 0.30 ---------------------------------------------------


def short_view(spot: str | None, *rows: Row) -> StubView:
    price = None if spot is None else Price.from_dollars(spot)
    return StubView(MON, spot_price=price, chains={(WEEKLY, Right.CALL): rows})


def pick_short(view: StubView) -> OptionId | None:
    selected = ShortSelector(WeekFinalExpiry(), NearestDeltaShort(0.30)).select(view, LONG)
    return None if selected is None else selected.option


def test_e_s3_picks_the_otm_delta_nearest_the_target() -> None:
    view = short_view("100", Row(101, "1.20", "1.26", 0.40), Row(102, "0.80", "0.84", 0.31),
                      Row(103, "0.50", "0.53", 0.22))  # fmt: skip
    assert strike(pick_short(view)) == 102


def test_e_s3_a_strike_at_spot_is_not_out_of_the_money() -> None:
    view = short_view("100", Row(100, "1.60", "1.66", 0.30), Row(101, "1.20", "1.26", 0.45))
    assert strike(pick_short(view)) == 101


def test_e_s3_a_delta_tie_goes_to_the_lower_spread() -> None:
    view = short_view("100", Row(101, "1.20", "1.30", 0.35), Row(103, "0.50", "0.52", 0.25))
    assert strike(pick_short(view)) == 103


def test_e_s3_a_delta_and_spread_tie_goes_to_the_higher_strike() -> None:
    view = short_view("100", Row(101, "1.00", "1.04", 0.35), Row(103, "1.00", "1.04", 0.25))
    assert strike(pick_short(view)) == 103


def test_e_s3_no_spot_selects_nothing() -> None:
    assert pick_short(short_view(None, Row(102, "0.80", "0.84", 0.30))) is None


def test_e_s3_no_eligible_otm_call_selects_nothing() -> None:
    view = short_view("100", Row(99, "1.80", "1.84", 0.60),
                      Row(102, "0.80", "0.84", 0.30, code=IvCode.BELOW_FLOOR))  # fmt: skip
    assert pick_short(view) is None
