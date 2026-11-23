"""The thesis calendar: 2014-2024 joined to the shipped 2025-2027 table (THESIS-SPEC §5.2; TD-15).

The history table is checked day by day against NYSE's holiday rules, computed here
independently, so a typo in the YAML can't pass. It is to be checked against the S&P 500 tape too,
once T1-01's probe pulls it.
"""

from datetime import date, timedelta
from pathlib import Path

import pytest

from pmcc.config.calendar import load_calendar, read_calendar_file
from pmcc.thesis.calendar import (
    HISTORY_PATH,
    business_days_after,
    business_days_between,
    join_tables,
    load_thesis_calendar,
)

CAL = load_thesis_calendar()
SHIPPED = load_calendar()
_DAY = timedelta(days=1)


def _easter(year: int) -> date:
    """Anonymous Gregorian algorithm (Meeus/Jones/Butcher)."""
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    el = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * el) // 451
    month = (h + el - 7 * m + 114) // 31
    day = (h + el - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _last_monday(year: int, month: int) -> date:
    day = date(year, month + 1, 1) - _DAY
    return day - timedelta(days=day.weekday())


def _observed(day: date) -> date | None:
    """NYSE's rule: Saturday to the Friday before, Sunday to the Monday after; a Saturday New
    Year's Day is not observed (it would close Dec 31)."""
    if day.weekday() == 5:
        return None if (day.month, day.day) == (1, 1) else day - _DAY
    return day + _DAY if day.weekday() == 6 else day


def _rule_closures(year: int) -> set[date]:
    fixed = [date(year, 1, 1), date(year, 7, 4), date(year, 12, 25)]
    if year >= 2022:
        fixed.append(date(year, 6, 19))
    moving = {
        _nth_weekday(year, 1, 0, 3),  # Martin Luther King, Jr. Day
        _nth_weekday(year, 2, 0, 3),  # Washington's Birthday
        _easter(year) - 2 * _DAY,  # Good Friday
        _last_monday(year, 5),  # Memorial Day
        _nth_weekday(year, 9, 0, 1),  # Labor Day
        _nth_weekday(year, 11, 3, 4),  # Thanksgiving
    }
    return moving | {d for d in map(_observed, fixed) if d is not None}


def _rule_early_closes(year: int, closed: set[date]) -> set[date]:
    out = {_nth_weekday(year, 11, 3, 4) + _DAY}  # the day after Thanksgiving
    for day in (date(year, 7, 3), date(year, 12, 24)):
        if day.weekday() < 4 and day not in closed:  # Monday to Thursday, and open
            out.add(day)
    return out


SPECIAL = {date(2018, 12, 5)}  # President George H.W. Bush


@pytest.mark.parametrize("year", range(2014, 2025))
def test_calendar_history_matches_nyse_rules(year: int) -> None:
    start, end = date(year, 1, 1), date(year, 12, 31)
    closed = set(CAL.closed_days(start, end))
    expected = _rule_closures(year) | {d for d in SPECIAL if d.year == year}
    assert closed == expected
    early = {s.day for s in CAL.sessions(start, end) if s.is_half_day}
    assert early == _rule_early_closes(year, closed)


def test_calendar_history_rules_agree_with_the_shipped_years() -> None:
    """The same rules reproduce the shipped 2025-2027 table, Carter's closure aside."""
    for year in range(2025, 2028):
        start, end = date(year, 1, 1), date(year, 12, 31)
        closed = set(SHIPPED.closed_days(start, end)) - {date(2025, 1, 9)}
        assert closed == _rule_closures(year)
        early = {s.day for s in SHIPPED.sessions(start, end) if s.is_half_day}
        assert early == _rule_early_closes(year, closed)


def test_calendar_joins_2014_to_2027_without_changing_the_shipped_table() -> None:
    assert (CAL.first_day, CAL.last_day) == (date(2014, 1, 1), date(2027, 12, 31))
    assert (SHIPPED.first_day, SHIPPED.last_day) == (date(2025, 1, 1), date(2027, 12, 31))
    day = SHIPPED.first_day
    while day <= SHIPPED.last_day:
        assert CAL.is_session(day) == SHIPPED.is_session(day)
        if CAL.is_session(day):
            assert CAL.session(day) == SHIPPED.session(day)
        day += _DAY


def test_calendar_refuses_tables_that_dont_meet(tmp_path: Path) -> None:
    history = read_calendar_file(HISTORY_PATH)
    gapped = history.model_copy(update={"last_day": date(2024, 12, 30)})
    with pytest.raises(ValueError, match="must meet"):
        join_tables(gapped, read_calendar_file())


def test_calendar_business_days_skip_weekends_and_holidays() -> None:
    assert business_days_after(CAL, date(2024, 11, 29), 2) == date(2024, 12, 3)  # Fri -> Tue
    assert business_days_after(CAL, date(2024, 7, 3), 2) == date(2024, 7, 8)  # Jul 4 closed
    assert business_days_after(CAL, date(2024, 7, 3), 0) == date(2024, 7, 3)
    assert business_days_between(CAL, date(2024, 11, 29), date(2024, 12, 3)) == 2
    assert business_days_between(CAL, date(2024, 12, 3), date(2024, 12, 3)) == 0
