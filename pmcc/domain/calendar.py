"""The exchange calendar: trading sessions, calendar weeks and expiries (DEC-33, ARCHITECTURE §4.2).

Every weekday in the table's span is a session unless the table closes it; an early close ends at
13:00. The calendar is reference data, published in advance, so it answers for future days too
(DEC-33): MarketView exposes it without the as-of gate. A day outside the table's span raises
rather than guess.

- A week is a calendar week, Monday to Sunday. Its first session is the week-open session (what
  the rules call "Monday"), and its last is the week-final session: the weekly expiry (E-S2).
- A monthly expires on the third Friday, or on the session before it when that Friday is closed.
"""

from collections.abc import Mapping
from datetime import date, timedelta
from typing import final

from pmcc.domain.sessions import HALF_DAY_CLOSE, REGULAR_CLOSE, Session

_DAY = timedelta(days=1)
_WEEK = timedelta(days=7)
_FRIDAY = 4
_WEEKDAYS = 5


@final
class SessionCalendar:
    """Sessions from a holiday table: `closed` days and `early_closes`, each with its name."""

    def __init__(
        self,
        first_day: date,
        last_day: date,
        closed: Mapping[date, str],
        early_closes: Mapping[date, str],
    ) -> None:
        if first_day > last_day:
            raise ValueError(f"the calendar's first day {first_day} is after its last {last_day}")
        self._first, self._last = first_day, last_day
        for kind, days in (("closed", closed), ("early close", early_closes)):
            for day in days:
                self._check_listed(kind, day)
        both = sorted(set(closed) & set(early_closes))
        if both:
            raise ValueError(f"a day can't be both closed and an early close: {both}")
        self._closed = dict(closed)
        self._early = dict(early_closes)

    @property
    def first_day(self) -> date:
        return self._first

    @property
    def last_day(self) -> date:
        return self._last

    def closed_days(self, start: date, end: date) -> dict[date, str]:
        """The table's closures from `start` to `end`, inclusive, with their names."""
        return {d: name for d, name in sorted(self._closed.items()) if start <= d <= end}

    def is_session(self, day: date) -> bool:
        self._check_covered(day)
        return day.weekday() < _WEEKDAYS and day not in self._closed

    def session(self, day: date) -> Session:
        if not self.is_session(day):
            raise ValueError(f"{day} is not a trading session")
        return Session(day, HALF_DAY_CLOSE if day in self._early else REGULAR_CLOSE)

    def sessions(self, start: date, end: date) -> tuple[Session, ...]:
        """The sessions from `start` to `end`, inclusive, in order."""
        days = (start + i * _DAY for i in range((end - start).days + 1))
        return tuple(self.session(d) for d in days if self.is_session(d))

    def sessions_before(self, day: date, count: int) -> tuple[Session, ...]:
        """The `count` sessions before `day` (not including it), in order."""
        found: list[Session] = []
        cursor = day - _DAY
        while len(found) < count:
            if self.is_session(cursor):
                found.append(self.session(cursor))
            cursor -= _DAY
        return tuple(reversed(found))

    def week_sessions(self, day: date) -> tuple[Session, ...]:
        """The sessions of `day`'s calendar week."""
        monday = day - day.weekday() * _DAY
        return self.sessions(monday, monday + (_WEEKDAYS - 1) * _DAY)

    def week_open(self, day: date) -> Session:
        """The first session of `day`'s week: Tuesday after a Monday holiday."""
        return self._week(day)[0]

    def week_final(self, day: date) -> Session:
        """The last session of `day`'s week: the weekly expiry (Thursday if Friday is closed)."""
        return self._week(day)[-1]

    def weekly_expiries(self, start: date, end: date) -> tuple[date, ...]:
        """The week-final sessions from `start` to `end`, inclusive."""
        monday = start - start.weekday() * _DAY
        found: list[date] = []
        while monday <= end:
            sessions = self.week_sessions(monday)
            if sessions and start <= sessions[-1].day <= end:
                found.append(sessions[-1].day)
            monday += _WEEK
        return tuple(found)

    def monthly_expiry(self, year: int, month: int) -> date:
        """The third Friday of the month, or the session before it when that Friday is closed."""
        first = date(year, month, 1)
        day = first + ((_FRIDAY - first.weekday()) % 7 + 14) * _DAY
        while not self.is_session(day):
            day -= _DAY
        return day

    def monthly_expiries(self, start: date, end: date) -> tuple[date, ...]:
        """The monthly expiries from `start` to `end`, inclusive."""
        found: list[date] = []
        year, month = start.year, start.month
        while date(year, month, 1) <= end:
            expiry = self.monthly_expiry(year, month)
            if start <= expiry <= end:
                found.append(expiry)
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        return tuple(found)

    def _week(self, day: date) -> tuple[Session, ...]:
        sessions = self.week_sessions(day)
        if not sessions:
            raise ValueError(f"the week of {day} has no trading session")
        return sessions

    def _check_covered(self, day: date) -> None:
        if not self._first <= day <= self._last:
            raise ValueError(f"{day} is outside the calendar ({self._first} to {self._last})")

    def _check_listed(self, kind: str, day: date) -> None:
        self._check_covered(day)
        if day.weekday() >= _WEEKDAYS:
            raise ValueError(f"{kind} day {day} is a weekend day, never a session anyway")
