"""The thesis's exchange calendar, 2014-2027, and its business-day counts (THESIS-SPEC §4.4, §5.2).

`configs/calendar_history.yaml` (2014-2024) joined to the shipped `configs/calendar.yaml`
(2025-2027), which the backtests and the live wheel read alone and which stays unchanged (TD-15).
The two tables must meet with no gap and no overlap.

A US business day, for credit's publication lag and age (§4.4), is an NYSE session: the same
table, so one calendar answers both (TD-15).
"""

from datetime import date, datetime, time, timedelta
from pathlib import Path

from pmcc.config.calendar import CALENDAR_PATH, CalendarFile, read_calendar_file
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import at_et, to_et

HISTORY_PATH = Path(__file__).resolve().parents[2] / "configs" / "calendar_history.yaml"
_DAY = timedelta(days=1)


def load_thesis_calendar(
    history: Path = HISTORY_PATH, shipped: Path = CALENDAR_PATH
) -> SessionCalendar:
    """One calendar over both tables. Raises `ValueError` if they don't meet day to day."""
    return join_tables(read_calendar_file(history), read_calendar_file(shipped))


def join_tables(earlier: CalendarFile, later: CalendarFile) -> SessionCalendar:
    if earlier.last_day + _DAY != later.first_day:
        raise ValueError(
            f"the calendar tables must meet: one ends {earlier.last_day}, the next starts "
            f"{later.first_day}"
        )
    first, second = earlier.to_calendar(), later.to_calendar()
    return SessionCalendar(
        earlier.first_day,
        later.last_day,
        closed=first.closed_days(earlier.first_day, earlier.last_day)
        | second.closed_days(later.first_day, later.last_day),
        early_closes={e.day: e.name for e in (*earlier.early_closes, *later.early_closes)},
    )


def sessions_after(calendar: SessionCalendar, day: date, count: int) -> tuple[date, ...]:
    """The first `count` sessions after `day` (any day, a session or not), in order."""
    found: list[date] = []
    cursor = day
    while len(found) < count:
        cursor += _DAY
        if calendar.is_session(cursor):
            found.append(cursor)
    return tuple(found)


def sessions_within(calendar: SessionCalendar, day: date, count: int) -> tuple[date, ...]:
    """Up to `count` sessions after `day`, stopping at the calendar's last day: fewer when the
    calendar ends first (a search window cut short, which its caller must say)."""
    found: list[date] = []
    cursor = day
    while len(found) < count and cursor < calendar.last_day:
        cursor += _DAY
        if calendar.is_session(cursor):
            found.append(cursor)
    return tuple(found)


def business_days_after(calendar: SessionCalendar, day: date, count: int) -> date:
    """The `count`th business day after `day`; `day` itself when `count` is 0."""
    return sessions_after(calendar, day, count)[-1] if count else day


def business_days_between(calendar: SessionCalendar, start: date, end: date) -> int:
    """The business days after `start`, up to and including `end`: 0 when `end` <= `start`."""
    if end <= start:
        return 0
    return len(calendar.sessions(start + _DAY, end))


def last_decided(calendar: SessionCalendar, now: datetime, clock: time) -> date:
    """The latest session whose decision (`clock`, New York) is at or before `now`: the last one a
    run may publish (§7.1: a session's signal is never generated before its decision)."""
    today = to_et(now).date()
    if calendar.is_session(today) and now >= decision_at(today, clock):
        return today
    return calendar.sessions_before(today, 1)[0].day


def decision_at(day: date, clock: time) -> datetime:
    """When session `day`'s signal is decided: `clock` New York time on that day (§7.1)."""
    return at_et(day, clock)
