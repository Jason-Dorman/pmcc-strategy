"""Sessions from the stock tape, checked against the holiday table (Spec › Chain discovery, DEC-33).

The spec takes weekly expiries from the stock tape, so a holiday week never gets an invented Friday
expiry. The tape and the table must agree over the tape's span (PO, 2026-09-27). A day with
regular-hours bars that the table closes, or a table session with no bars, raises
`CalendarMismatchError` naming the days; nothing is patched quietly. Once they agree, the table's
sessions are the tape's, with the table's early closes: a tape can't show a 13:00 close, because
post-market trading carries on after it.
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from typing import final

import polars as pl

from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.sessions import Session

_ET = "America/New_York"
# Bars starting 09:00-15:00 ET hold the regular session (DEC-06). Any of them marks a trading day;
# extended-hours bars alone never do.
_REGULAR_START_HOURS = (9, 15)


class CalendarMismatchError(Exception):
    """The stock tape and the holiday table disagree about which days traded."""


@final
@dataclass(frozen=True, slots=True)
class DayMismatch:
    """Days the tape and the table disagree on, from `start` to `end`."""

    start: date
    end: date
    traded_but_closed: tuple[date, ...]
    session_without_bars: tuple[date, ...]

    @property
    def ok(self) -> bool:
        return not (self.traded_but_closed or self.session_without_bars)


def check_trading_days(
    calendar: SessionCalendar, traded: Collection[date], start: date, end: date
) -> DayMismatch:
    """Compare the days a tape traded with the table's sessions, from `start` to `end`."""
    sessions = {s.day for s in calendar.sessions(start, end)}
    seen = {d for d in traded if start <= d <= end}
    return DayMismatch(
        start,
        end,
        traded_but_closed=tuple(sorted(seen - sessions)),
        session_without_bars=tuple(sorted(sessions - seen)),
    )


def tape_days(bar_starts: pl.Series) -> frozenset[date]:
    """The ET days with at least one regular-hours bar. `bar_starts` are LSEG's UTC bar starts."""
    first, last = _REGULAR_START_HOURS
    et = bar_starts.dt.convert_time_zone(_ET)
    return frozenset(et.filter(et.dt.hour().is_between(first, last)).dt.date().to_list())


def sessions_from_tape(
    calendar: SessionCalendar, bar_starts: pl.Series, start: date, end: date
) -> tuple[Session, ...]:
    """The sessions from `start` to `end`, once the tape's trading days match the table's.

    Raises `CalendarMismatchError` naming every day they disagree on.
    """
    mismatch = check_trading_days(calendar, tape_days(bar_starts), start, end)
    if not mismatch.ok:
        raise CalendarMismatchError(describe(calendar, mismatch))
    return calendar.sessions(start, end)


def describe(calendar: SessionCalendar, mismatch: DayMismatch) -> str:
    """What disagrees, for an error or a probe report. Fix the table (with a source) or the data."""
    closed = calendar.closed_days(mismatch.start, mismatch.end)
    parts = [
        f"the stock tape and configs/calendar.yaml disagree ({mismatch.start} to {mismatch.end})"
    ]
    if mismatch.traded_but_closed:
        named = ", ".join(f"{d} ({closed.get(d, 'weekend')})" for d in mismatch.traded_but_closed)
        parts.append(f"bars on days the table closes: {named}")
    if mismatch.session_without_bars:
        parts.append(
            f"table sessions with no bars: {', '.join(map(str, mismatch.session_without_bars))}"
        )
    return "; ".join(parts)
