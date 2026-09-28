"""The session calendar's logic, on a small synthetic table (DEC-33, ARCHITECTURE §4.2).

The shipped NYSE table and the known 2026-2027 cases are tested in
`tests/unit/config/test_calendar_file.py`.
"""

from datetime import date, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.sessions import HALF_DAY_CLOSE, REGULAR_CLOSE

# March 2026: Mon 2 ... Fri 6, Mon 9 ... Fri 13, Mon 16 ... Fri 20 (the third Friday).
MON_HOLIDAY = date(2026, 3, 9)
FRI_HOLIDAY = date(2026, 3, 20)
THU_HALF = date(2026, 3, 19)
CAL = SessionCalendar(
    date(2026, 1, 1),
    date(2026, 12, 31),
    closed={MON_HOLIDAY: "Monday holiday", FRI_HOLIDAY: "Friday holiday"},
    early_closes={THU_HALF: "Half day"},
)


def test_calendar_weekday_is_a_session_and_weekend_is_not() -> None:
    assert CAL.is_session(date(2026, 3, 2))
    assert not CAL.is_session(date(2026, 3, 7))  # Saturday
    assert not CAL.is_session(date(2026, 3, 8))  # Sunday


def test_calendar_listed_closure_is_not_a_session() -> None:
    assert not CAL.is_session(MON_HOLIDAY)
    with pytest.raises(ValueError, match="not a trading session"):
        CAL.session(MON_HOLIDAY)


def test_calendar_early_close_ends_at_13_and_other_days_at_16() -> None:
    assert CAL.session(THU_HALF).close == HALF_DAY_CLOSE
    assert CAL.session(date(2026, 3, 18)).close == REGULAR_CLOSE


def test_calendar_sessions_are_inclusive_and_skip_closures() -> None:
    days = [s.day for s in CAL.sessions(date(2026, 3, 6), date(2026, 3, 10))]
    assert days == [date(2026, 3, 6), date(2026, 3, 10)]


def test_calendar_sessions_before_counts_back_over_closures() -> None:
    days = [s.day for s in CAL.sessions_before(date(2026, 3, 11), 3)]
    assert days == [date(2026, 3, 5), date(2026, 3, 6), date(2026, 3, 10)]


def test_e_s1_week_open_is_tuesday_after_a_monday_holiday() -> None:
    assert CAL.week_open(date(2026, 3, 12)).day == date(2026, 3, 10)


def test_e_s2_week_final_is_thursday_before_a_friday_holiday() -> None:
    assert CAL.week_final(date(2026, 3, 16)).day == THU_HALF


def test_calendar_week_final_of_a_weekend_day_is_that_calendar_weeks_friday() -> None:
    assert CAL.week_final(date(2026, 3, 8)).day == date(2026, 3, 6)  # Sunday ends Mon 2 week


def test_e_s2_weekly_expiries_are_the_week_final_sessions_in_range() -> None:
    expiries = CAL.weekly_expiries(date(2026, 3, 4), date(2026, 3, 19))
    assert expiries == (date(2026, 3, 6), date(2026, 3, 13), THU_HALF)


def test_e_s2_weekly_expiries_leave_out_a_week_final_after_the_end() -> None:
    assert CAL.weekly_expiries(date(2026, 3, 2), date(2026, 3, 12)) == (date(2026, 3, 6),)


def test_e_l2_monthly_is_the_third_friday() -> None:
    assert CAL.monthly_expiry(2026, 4) == date(2026, 4, 17)


def test_e_l2_monthly_moves_to_the_session_before_a_closed_third_friday() -> None:
    assert CAL.monthly_expiry(2026, 3) == THU_HALF


def test_e_l2_monthly_expiries_in_range_are_inclusive() -> None:
    expiries = CAL.monthly_expiries(date(2026, 3, 19), date(2026, 5, 15))
    assert expiries == (THU_HALF, date(2026, 4, 17), date(2026, 5, 15))


def test_calendar_day_outside_the_table_raises() -> None:
    with pytest.raises(ValueError, match="outside the calendar"):
        CAL.is_session(date(2027, 1, 4))


def test_calendar_week_straddling_the_table_edge_raises() -> None:
    with pytest.raises(ValueError, match="outside the calendar"):
        CAL.week_open(date(2026, 1, 1))  # Thu; its Monday is Dec 29 2025


@pytest.mark.parametrize(
    ("closed", "early", "match"),
    [
        ({date(2026, 3, 7): "Saturday"}, {}, "weekend"),
        ({date(2027, 1, 4): "late"}, {}, "outside"),
        ({}, {date(2025, 12, 31): "early"}, "outside"),
        ({MON_HOLIDAY: "a"}, {MON_HOLIDAY: "b"}, "both"),
    ],
)
def test_calendar_refuses_an_impossible_table(
    closed: dict[date, str], early: dict[date, str], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        SessionCalendar(date(2026, 1, 1), date(2026, 12, 31), closed, early)


def test_calendar_refuses_a_span_that_ends_before_it_starts() -> None:
    with pytest.raises(ValueError, match="after its last"):
        SessionCalendar(date(2026, 2, 1), date(2026, 1, 1), {}, {})


@given(st.dates(date(2026, 1, 5), date(2026, 12, 25)))
def test_calendar_every_session_sits_between_its_week_open_and_week_final(day: date) -> None:
    if not CAL.is_session(day):
        return
    assert CAL.week_open(day).day <= day <= CAL.week_final(day).day
    assert CAL.week_final(day).day - CAL.week_open(day).day < timedelta(days=5)
