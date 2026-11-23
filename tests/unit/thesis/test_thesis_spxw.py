"""SPXW's RICs, expiry, strikes and rough condor (T1-01; spec §6.2, §6.3, §7.2; TD-07)."""

import math
from datetime import date

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.domain.instruments import Right
from pmcc.pricing.black_scholes import price
from pmcc.thesis import spxw
from pmcc.thesis.config import load_thesis_config
from pmcc.thesis.spxw import Leg, Spelling

CAL = load_calendar()
RULES = load_thesis_config().cost_sample
SPXW_LOWER = Spelling("SPXW", lowercase=True)


@pytest.mark.parametrize(
    ("spelling", "right", "strike", "ric"),
    [
        (SPXW_LOWER, Right.CALL, 6600, "SPXWl182666000.U"),
        (SPXW_LOWER, Right.PUT, 6125, "SPXWx182661250.U"),
        (Spelling("SPXW", lowercase=False), Right.PUT, 6125, "SPXWX182661250.U"),
        (Spelling("SPX", lowercase=True), Right.CALL, 6600, "SPXl182666000.U"),
        (SPXW_LOWER, Right.CALL, 950, "SPXWL182695000.U"),  # below 1,000: cents, upper case
    ],
)
def test_t1_01_ric_spells_index_strikes_in_tenths(
    spelling: Spelling, right: Right, strike: int, ric: str
) -> None:
    assert spxw.option_ric(spelling, date(2026, 12, 18), right, strike) == ric


def test_t1_01_ric_refuses_a_strike_too_wide_for_five_digits() -> None:
    with pytest.raises(ValueError, match="five-digit"):
        spxw.option_ric(SPXW_LOWER, date(2026, 12, 18), Right.CALL, 10_000)


def test_td_19_expiries_are_the_window_sessions_nearest_30_days_first() -> None:
    # From Mon Nov 23 2026, 28-35 days is Dec 21-28: Dec 23 is 30 days out; Dec 22 and 24 tie at
    # one day off, the earlier first; Christmas and the weekend are closed.
    assert spxw.candidate_expiries(CAL, date(2026, 11, 23), RULES) == (
        date(2026, 12, 23),
        date(2026, 12, 22),
        date(2026, 12, 24),
        date(2026, 12, 21),
        date(2026, 12, 28),
    )


def test_t1_01_expiry_tie_goes_earlier_and_skips_closed_days() -> None:
    # From Thu Nov 26 2026 (Thanksgiving; the arithmetic still holds): 30 days is Sat Dec 26, so
    # Fri Dec 25 (closed) and Sun Dec 27 are out; Thu Dec 24 (28) and Mon Dec 28 (32) tie at 2
    # days off, and the earlier wins.
    assert spxw.candidate_expiries(CAL, date(2026, 11, 26), RULES)[0] == date(2026, 12, 24)


def test_t1_01_no_expiries_past_the_calendar() -> None:
    assert spxw.candidate_expiries(CAL, CAL.last_day, RULES) == ()


def test_t1_01_ladder_rounds_outwards_to_whole_steps() -> None:
    assert spxw.ladder(6101.0, 6119.0, RULES) == (6100, 6105, 6110, 6115, 6120)


def test_t1_01_estimated_strikes_bracket_the_spot_at_0_20_delta() -> None:
    years = 30 / 365
    put_k, call_k = spxw.estimated_strikes(6600.0, 20.0, years, RULES)
    # Black-Scholes deltas at those strikes, VIX as every strike's vol and no rate.
    for strike, target in ((put_k, -0.20), (call_k, 0.20)):
        d1 = (math.log(6600 / strike) + 0.02 * years) / (0.2 * math.sqrt(years))
        delta = 0.5 * (1 + math.erf(d1 / math.sqrt(2))) - (1 if target < 0 else 0)
        assert delta == pytest.approx(target, abs=1e-9)


def test_t1_01_parity_spot_recovers_the_discounted_forward() -> None:
    years, spot, strike = 0.08, 6600.0, 6600
    call = float(price(spot, strike, years, RULES.rate_decimal, 0.18, True))
    put = float(price(spot, strike, years, RULES.rate_decimal, 0.18, False))
    legs = (Leg("c", Right.CALL, strike, call, call), Leg("p", Right.PUT, strike, put, put))

    assert spxw.parity_spot(*legs, years, RULES) == pytest.approx(spot, rel=1e-9)


def test_t1_01_parity_spot_needs_both_mids_at_one_strike() -> None:
    call = Leg("c", Right.CALL, 6600, 10.0, 11.0)
    assert spxw.parity_spot(call, Leg("p", Right.PUT, 6605, 9.0, 10.0), 0.08, RULES) is None
    assert spxw.parity_spot(call, Leg("p", Right.PUT, 6600, None, 10.0), 0.08, RULES) is None


@pytest.mark.parametrize(
    ("bid", "ask", "tight"),
    [
        (2.0, 3.0, True),  # 1.0 wide: the floor
        (2.0, 3.01, False),
        (20.0, 24.4, True),  # 4.4 = 0.20 × the 22.2 mid
        (20.0, 24.6, False),
        (0.0, 0.5, True),  # a zero bid is a quote (a long wing's)
        (None, 3.0, False),
        (3.0, 2.0, False),  # crossed
    ],
)
def test_t1_01_spread_test_is_spec_6_3s(bid: float | None, ask: float, tight: bool) -> None:
    assert Leg("x", Right.PUT, 6000, bid, ask).tight(RULES) is tight


def _chain(spot: float, vol: float, years: float, width: float = 0.04) -> list[Leg]:
    legs: list[Leg] = []
    for strike in range(5600, 7400, 5):
        for right in (Right.PUT, Right.CALL):
            value = float(price(spot, strike, years, RULES.rate_decimal, vol, right is Right.CALL))
            half = max(0.05, value * width) / 2
            legs.append(
                Leg(f"{right.name}{strike}", right, strike, max(0.0, value - half), value + half)
            )
    return legs


def test_t1_01_condor_picks_0_20_delta_shorts_and_the_smallest_common_wing() -> None:
    years = 30 / 365
    legs = spxw.priced(_chain(6600.0, 0.18, years), 6600.0, years, RULES)
    found = spxw.condor(legs, 6600.0, RULES)

    assert found is not None
    assert found.short_put.delta == pytest.approx(-0.20, abs=0.01)
    assert found.short_call.delta == pytest.approx(0.20, abs=0.01)
    assert found.width == 35  # 0.5% of 6,600 is 33: the next 5-point strike width
    assert found.long_put.strike == found.short_put.strike - 35
    assert found.long_call.strike == found.short_call.strike + 35
    assert 0 < found.natural_credit < found.mid_credit < found.width


def test_t1_01_condor_costs_add_up() -> None:
    years = 30 / 365
    found = spxw.condor(
        spxw.priced(_chain(6600.0, 0.18, years), 6600.0, years, RULES), 6600.0, RULES
    )

    assert found is not None
    spreads = sum(
        leg.ask - leg.bid for leg in found.legs if leg.ask is not None and leg.bid is not None
    )
    assert found.round_trip_spread == pytest.approx(spreads)
    assert found.mid_credit - found.natural_credit == pytest.approx(spreads / 2)
    assert found.fees == pytest.approx(0.16)  # $2 × 8 transactions ÷ $100


def test_t1_01_condor_is_none_without_a_short_within_tolerance() -> None:
    years = 30 / 365
    calls_only = [leg for leg in _chain(6600.0, 0.18, years) if leg.right is Right.CALL]
    assert spxw.condor(spxw.priced(calls_only, 6600.0, years, RULES), 6600.0, RULES) is None


def test_t1_01_condor_is_none_without_wings_in_range() -> None:
    years = 30 / 365
    sparse = [leg for leg in _chain(6600.0, 0.18, years) if leg.strike % 100 == 0]
    # 100 points apart: no width from 33 to 49.5 exists.
    assert spxw.condor(spxw.priced(sparse, 6600.0, years, RULES), 6600.0, RULES) is None


def test_t1_01_priced_leaves_an_unsolvable_leg_unpriced() -> None:
    legs = spxw.priced([Leg("x", Right.CALL, 6600, None, None)], 6600.0, 0.08, RULES)
    assert legs[0].iv is None
    assert legs[0].delta is None
