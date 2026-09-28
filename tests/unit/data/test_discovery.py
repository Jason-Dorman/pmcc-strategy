"""Chain discovery: increments (DEC-14), integer-cent ladders, band formulas and the fetch plan
(DEC-48, ARCHITECTURE §6.3)."""

import math
from datetime import UTC, date, datetime, time, timedelta
from itertools import pairwise
from statistics import NormalDist

import polars as pl
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pmcc.config.calendar import load_calendar
from pmcc.data.discovery import (
    EM_WEEK_YEARS,
    LONG_SEGMENTS,
    Band,
    Pad,
    Region,
    SessionRange,
    band_vol,
    increment_anchor,
    increment_from,
    increment_strikes,
    plan_symbol,
    session_ranges,
    stock_unit,
)
from pmcc.data.provider import Interval, raw_schema
from pmcc.domain.clock import ET
from pmcc.domain.instruments import Right
from pmcc.domain.money import Price

CAL = load_calendar()
P = Price.from_dollars

# --- Increments (DEC-14) ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("centre", "anchor"),
    [
        ("183.20", 18_000),
        ("185.00", 19_000),
        ("184.99", 18_000),
        ("4.99", 1_000),
        ("999.99", 100_000),
    ],
)
def test_dec_14_anchor_is_the_nearest_multiple_of_ten_dollars(centre: str, anchor: int) -> None:
    assert increment_anchor(P(centre)) == anchor


def test_dec_14_asks_the_anchor_and_four_offsets() -> None:
    assert increment_strikes(18_000) == (18_000, 18_050, 18_100, 18_250, 18_500)


@pytest.mark.parametrize(
    ("answered", "step"),
    [
        ({18_000, 18_050, 18_100, 18_250, 18_500}, 50),
        ({18_000, 18_100, 18_250, 18_500}, 100),
        ({18_000, 18_250, 18_500}, 250),
        ({18_000, 18_500}, 500),
        ({18_000}, 1_000),
        (set[int](), 1_000),
    ],
)
def test_dec_14_increment_is_the_smallest_offset_that_answers(
    answered: set[int], step: int
) -> None:
    assert increment_from(18_000, answered) == step


# --- Ladders ----------------------------------------------------------------------------------


def test_band_ladder_pads_in_steps_and_lands_on_the_grid() -> None:
    band = Band(Region.NEAR_MONEY, P("180.37"), P("190.12"), Pad(4), Pad(6))
    ladder = band.ladder(100)
    assert (ladder[0], ladder[-1]) == (17_600, 19_700)  # 180.37-4 → 176; 190.12+6 → 197
    assert ladder == tuple(range(17_600, 19_701, 100))


def test_band_ladder_on_a_2_50_grid_holds_only_multiples_of_250() -> None:
    ladder = Band(Region.DEEP_ITM, P("141.10"), P("163.90"), Pad(2), Pad(2)).ladder(250)
    assert (ladder[0], ladder[-1]) == (13_500, 17_000)
    assert all(k % 250 == 0 for k in ladder)


def test_band_pad_at_least_wins_when_wider_than_its_steps() -> None:
    band = Band(Region.NEAR_MONEY, P("100"), P("100"), Pad(4), Pad(6, P("30.004")))
    assert band.ladder(100)[-1] == 13_100  # 100 + 30.01 (the pad rounds up to whole cents)
    assert band.ladder(1_000)[-1] == 16_000  # 6 steps of $10 beat $30


def test_band_ladder_never_goes_below_one_step() -> None:
    assert Band(Region.DEEP_ITM, P("3"), P("4"), Pad(4), Pad(2)).ladder(100)[0] == 100


def test_band_centre_is_halfway() -> None:
    assert Band(Region.DEEP_ITM, P("100"), P("151"), Pad(2), Pad(2)).centre == P("125.50")


@pytest.mark.parametrize(("low", "high"), [("0", "10"), ("11", "10"), ("-1", "10")])
def test_band_refuses_an_empty_or_nonpositive_range(low: str, high: str) -> None:
    with pytest.raises(ValueError, match="0 < low <= high"):
        Band(Region.NEAR_MONEY, P(low), P(high), Pad(1), Pad(1))


def test_band_ladder_refuses_a_nonpositive_step() -> None:
    with pytest.raises(ValueError, match="positive"):
        Band(Region.NEAR_MONEY, P("10"), P("11"), Pad(1), Pad(1)).ladder(0)


@given(
    low=st.integers(100, 150_000),
    width=st.integers(0, 50_000),
    step=st.sampled_from([50, 100, 250, 500, 1_000]),
    below=st.integers(0, 8),
    above=st.integers(0, 8),
    at_least=st.integers(0, 5_000),
)
def test_band_ladder_is_an_integer_cent_grid_covering_the_padded_range(
    low: int, width: int, step: int, below: int, above: int, at_least: int
) -> None:
    band = Band(
        Region.NEAR_MONEY,
        Price(low * 100),
        Price((low + width) * 100),
        Pad(below),
        Pad(above, Price(at_least * 100)),
    )
    ladder = band.ladder(step)
    want_bottom = low - below * step
    want_top = low + width + max(above * step, at_least)
    assert all(isinstance(k, int) and k % step == 0 for k in ladder)
    assert ladder == tuple(range(ladder[0], ladder[-1] + 1, step))
    assert ladder[0] <= max(want_bottom, step) < ladder[0] + step
    assert ladder[-1] - step < want_top <= ladder[-1]


# --- Session ranges from the tape -------------------------------------------------------------


def _row(day: date, start_hour: int, field: str, value: float) -> dict[str, object]:
    start = datetime.combine(day, time(start_hour), tzinfo=ET).astimezone(UTC)
    return {"bar_start": start, "ric": "NVDA.O", "field": field, "value": value}


def _rows(*rows: dict[str, object]) -> pl.DataFrame:
    return pl.DataFrame(list(rows), schema=raw_schema(Interval.HOURLY))


def test_session_ranges_use_session_bars_only_and_the_close_bars_print() -> None:
    day = date(2026, 9, 18)
    rows = _rows(
        _row(day, 7, "LOW_1", 50.0),  # a bogus pre-market tick (LDG §4.10)
        _row(day, 9, "LOW_1", 99.0),
        _row(day, 9, "HIGH_1", 104.0),
        _row(day, 12, "HIGH_1", 106.0),
        _row(day, 14, "TRDPRC_1", 103.0),
        _row(day, 15, "TRDPRC_1", 105.5),  # the close bar: 15:00-16:00
        _row(day, 16, "TRDPRC_1", 120.0),  # the post-close stub
        _row(day, 17, "HIGH_1", 130.0),
    )
    [got] = session_ranges(rows, CAL.sessions(day, day))
    assert got == SessionRange(day, P("99"), P("106"), P("105.5"))


def test_session_ranges_close_on_a_half_day_is_the_1200_bar() -> None:
    day = date(2026, 11, 27)
    rows = _rows(_row(day, 12, "TRDPRC_1", 101.0), _row(day, 13, "TRDPRC_1", 99.0))
    [got] = session_ranges(rows, CAL.sessions(day, day))
    assert got.close == P("101")
    assert (got.low, got.high) == (P("101"), P("101"))  # prints widen the range


def test_session_ranges_leave_out_a_session_with_no_session_bars() -> None:
    day = date(2026, 9, 18)
    assert session_ranges(_rows(_row(day, 18, "HIGH_1", 1.0)), CAL.sessions(day, day)) == ()


# --- Plan volatility --------------------------------------------------------------------------

WINDOW = (date(2026, 7, 6), date(2026, 9, 18))  # the spec's example window
MOVE = 0.01


def _ranges(start: date, end: date, low: str = "100", high: str = "110") -> list[SessionRange]:
    """Flat highs and lows; closes alternate up and down by 1% in log terms."""
    sessions = CAL.sessions(start, end)
    closes = [105 * math.exp(MOVE * (i % 2)) for i in range(len(sessions))]
    return [
        SessionRange(s.day, P(low), P(high), P(c)) for s, c in zip(sessions, closes, strict=True)
    ]


RANGES = _ranges(date(2026, 5, 1), date(2026, 9, 18))
SIGMA = 1.25 * MOVE * math.sqrt(20 / 19) * math.sqrt(252)


def test_band_vol_is_one_and_a_quarter_times_the_highest_rv20() -> None:
    assert band_vol(RANGES, *WINDOW) == pytest.approx(SIGMA, rel=1e-4)  # closes are Prices


def test_band_vol_reads_the_highest_rv20_in_the_window_not_before_it() -> None:
    calm = [
        SessionRange(r.day, r.low, r.high, P("105")) if r.day < date(2026, 6, 1) else r
        for r in RANGES
    ]
    spike = [*calm[:5], SessionRange(calm[5].day, P("1"), P("999"), P("400")), *calm[6:]]
    assert band_vol(spike, *WINDOW) == pytest.approx(SIGMA, rel=1e-4)


def _with_close(day: date, close: str) -> list[SessionRange]:
    return [SessionRange(r.day, r.low, r.high, P(close)) if r.day == day else r for r in RANGES]


@pytest.mark.parametrize(
    "day",
    [
        date(2026, 7, 2),  # the last close before the window: RV20 on the first session
        date(2026, 8, 10),  # inside
        date(2026, 9, 18),  # the window's last close
    ],
)
def test_band_vol_sees_a_jump_at_every_close_it_should(day: date) -> None:
    assert band_vol(_with_close(day, "140"), *WINDOW) > 2 * SIGMA


def test_band_vol_ignores_a_jump_no_rv20_it_reads_can_see() -> None:
    # The first RV20 read is at Jul 2 (the last close before the window) and spans Jun 3 - Jul 2,
    # so a spike on May 29 is outside every one; so is a close after the window's end.
    after = SessionRange(date(2026, 9, 21), P("100"), P("110"), P("400"))
    ranges = [*_with_close(date(2026, 5, 29), "140"), after]
    assert band_vol(ranges, *WINDOW) == pytest.approx(SIGMA, rel=1e-4)


def test_band_vol_uses_20_returns_with_the_sample_deviation() -> None:
    # 21 closes: 20 returns alternating +/-1%, so the RV20 is exact.
    ranges = RANGES[-21:]
    got = band_vol(ranges, ranges[-1].day, ranges[-1].day)
    assert got == pytest.approx(SIGMA, rel=1e-4)


def test_band_vol_needs_21_closes() -> None:
    with pytest.raises(ValueError, match="21 session closes"):
        band_vol(RANGES[-20:], RANGES[-5].day, RANGES[-1].day)


# --- The plan ---------------------------------------------------------------------------------

PLAN = plan_symbol(CAL, RANGES, *WINDOW)


def test_dec_48_stock_unit_starts_30_sessions_before_the_window() -> None:
    unit = PLAN.unit("stock")
    assert len(CAL.sessions(unit.start, WINDOW[0] - timedelta(days=1))) == 30
    assert unit.end == WINDOW[1]
    assert stock_unit(CAL, *WINDOW) == unit


def test_dec_48_spec_window_needs_the_nov_2026_to_may_2027_monthlies() -> None:
    monthlies = [
        u.expiry
        for u in PLAN.units
        if u.right is Right.CALL and u.bands[0].region is Region.DEEP_ITM
    ]
    assert monthlies == [
        date(2026, 11, 20),
        date(2026, 12, 18),
        date(2027, 1, 15),
        date(2027, 2, 19),
        date(2027, 3, 19),
        date(2027, 4, 16),
        date(2027, 5, 21),
    ]


def test_dec_48_weekly_calls_cover_every_weekly_in_the_window_and_the_next_one() -> None:
    weekly = [
        u for u in PLAN.units if u.right is Right.CALL and u.bands[0].region is Region.NEAR_MONEY
    ]
    expiries = [u.expiry for u in weekly]
    assert expiries[0] == date(2026, 7, 10)
    assert date(2026, 7, 2) not in expiries  # its week ends before the window
    assert expiries[-2:] == [date(2026, 9, 18), date(2026, 9, 25)]
    assert len(expiries) == 12


def test_dec_48_weekly_call_unit_runs_from_the_prior_week_open_to_its_expiry() -> None:
    unit = PLAN.unit("chains/2026-07-10_C")
    assert (unit.start, unit.end) == (date(2026, 6, 29), date(2026, 7, 10))
    assert PLAN.unit("chains/2026-09-11_C").start == date(2026, 8, 31)  # Labor Day week


def test_dec_48_next_weekly_after_the_window_ends_at_the_window_end() -> None:
    unit = PLAN.unit("chains/2026-09-25_C")
    assert (unit.start, unit.end) == (date(2026, 9, 14), WINDOW[1])


def test_dec_48_weekly_call_band_is_low_minus_4_steps_to_high_plus_max_of_em_and_6_steps() -> None:
    [band] = PLAN.unit("chains/2026-07-10_C").bands
    em = 110 * PLAN.sigma * math.sqrt(EM_WEEK_YEARS)
    assert (band.low, band.high) == (P("100"), P("110"))
    assert band.below == Pad(4)
    assert band.above == Pad(6, P(2.5 * em))
    assert band.ladder(100)[0] == 9_600
    pad = max(600, -(-band.above.at_least.units // 100))
    assert band.ladder(100)[-1] == -(-(11_000 + pad) // 100) * 100


def test_dec_48_atm_put_unit_is_the_week_open_session_only() -> None:
    labor_day_week = PLAN.unit("chains/2026-09-11_P")
    assert (labor_day_week.start, labor_day_week.end) == (date(2026, 9, 8), date(2026, 9, 8))
    [band] = labor_day_week.bands
    assert (band.below, band.above) == (Pad(2), Pad(2))


def test_dec_48_monthly_band_runs_from_delta_97_to_the_money_in_three_segments() -> None:
    unit = PLAN.unit("chains/2027-01-15_C")
    bands = unit.bands
    first_t = (date(2027, 1, 15) - date(2026, 7, 6)).days / 365
    assert len(bands) == LONG_SEGMENTS
    assert bands[0].low == P(100 * math.exp(-2.0 * PLAN.sigma * math.sqrt(first_t)))
    assert bands[-1].high == P("110")  # the weeks' high: at the money
    assert all(a.high == b.low for a, b in pairwise(bands))
    assert [(b.below, b.above) for b in bands] == [
        (Pad(2), Pad(1)),
        (Pad(1), Pad(1)),
        (Pad(1), Pad(2)),
    ]
    assert (unit.start, unit.end) == WINDOW


@given(vol=st.floats(0.05, 1.5), dte=st.integers(120, 270))
def test_dec_48_monthly_band_covers_delta_70_whatever_the_volatility(vol: float, dte: int) -> None:
    # Quant E-L3 takes delta 0.70-0.90. A strike at delta 0.70 sits below spot for any sigma and T
    # (r >= 0), so a band whose top is the week's high always holds it; a delta-based top didn't.
    spot, years = 110.0, dte / 365
    k70 = spot * math.exp(-NormalDist().inv_cdf(0.70) * vol * math.sqrt(years) + vol**2 * years / 2)
    top = PLAN.unit("chains/2027-01-15_C").bands[-1]
    assert k70 <= float(top.high.to_dollars()) or k70 > spot


def test_dec_14_long_segments_are_probed_at_their_own_centres() -> None:
    # A $1 grid near the money and a $5 grid deep: the top segment's anchor sits near the money.
    centres = [b.centre for b in PLAN.unit("chains/2027-01-15_C").bands]
    assert centres == sorted(centres)
    assert increment_anchor(centres[-1]) >= 9_000


def test_dec_48_window_ending_mid_week_keeps_its_last_weeks_put_and_next_weekly() -> None:
    tape = _ranges(date(2026, 5, 1), date(2026, 9, 23))
    plan = plan_symbol(CAL, tape, date(2026, 8, 3), date(2026, 9, 23))  # ends Wednesday
    names = {u.name for u in plan.units}
    assert {"chains/2026-09-25_P", "chains/2026-09-25_C", "chains/2026-10-02_C"} <= names
    assert plan.unit("chains/2026-09-25_C").end == date(2026, 9, 23)
    assert plan.unit("chains/2026-10-02_C").end == date(2026, 9, 23)


def test_dec_48_first_week_open_of_the_window_gets_its_put() -> None:
    unit = PLAN.unit("chains/2026-07-10_P")
    assert (unit.start, unit.end) == (WINDOW[0], WINDOW[0])


def test_dec_48_window_starting_mid_week_skips_that_weeks_put() -> None:
    plan = plan_symbol(CAL, RANGES, date(2026, 7, 8), WINDOW[1])
    names = {u.name for u in plan.units}
    assert "chains/2026-07-10_P" not in names
    assert "chains/2026-07-10_C" in names


LONG_WINDOW = (date(2026, 1, 5), date(2026, 9, 18))
LONG_PLAN = plan_symbol(CAL, _ranges(date(2025, 11, 1), date(2026, 9, 18)), *LONG_WINDOW)


def test_dec_48_monthly_is_fetched_from_its_first_candidate_session() -> None:
    unit = PLAN.unit("chains/2027-05-21_C")  # 270 DTE on Mon Aug 24 2026
    assert (unit.start, unit.end) == (date(2026, 8, 24), WINDOW[1])


def test_dec_48_monthly_expiring_inside_the_window_stops_at_its_expiry() -> None:
    unit = LONG_PLAN.unit("chains/2026-05-15_C")
    assert unit.end == date(2026, 5, 15)
    assert unit.start == LONG_WINDOW[0]


def test_dec_48_expiry_that_is_both_weekly_and_long_candidate_is_one_unit_with_two_bands() -> None:
    plan = LONG_PLAN
    unit = plan.unit("chains/2026-07-17_C")
    assert {b.region for b in unit.bands} == {Region.NEAR_MONEY, Region.DEEP_ITM}
    assert (unit.start, unit.end) == (LONG_WINDOW[0], date(2026, 7, 17))
    assert len({u.name for u in plan.units}) == len(plan.units)


def test_dec_48_plan_refuses_a_window_that_ends_before_it_starts() -> None:
    with pytest.raises(ValueError, match="after it ends"):
        plan_symbol(CAL, RANGES, WINDOW[1], WINDOW[0])


def test_band_vol_reads_the_rv20_at_the_last_close_before_the_window() -> None:
    # Only the RV20 at Jul 2 (used on the window's first session) reaches back to this close.
    oldest = CAL.sessions_before(date(2026, 7, 2), 20)[0].day
    assert band_vol(_with_close(oldest, "140"), *WINDOW) > 1.5 * SIGMA
