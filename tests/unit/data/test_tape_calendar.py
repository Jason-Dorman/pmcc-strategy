"""Tape holidays must match the table (DEC-33; PO 2026-09-27: a mismatch stops with an error)."""

from datetime import UTC, date, datetime, time, timedelta

import polars as pl
import pytest

from pmcc.config.calendar import load_calendar
from pmcc.data.calendar import (
    CalendarMismatchError,
    check_trading_days,
    sessions_from_tape,
    tape_days,
)
from pmcc.domain.clock import ET

CAL = load_calendar()
# Jun 29 - Jul 10 2026: Fri Jul 3 is closed (Independence Day observed).
START, END = date(2026, 6, 29), date(2026, 7, 10)
SESSIONS = [s.day for s in CAL.sessions(START, END)]


def _starts(days: list[date], hours: range = range(4, 20)) -> pl.Series:
    """LSEG-style hourly bar starts (UTC) for each day, the stock's 04:00-20:00 ET tape."""
    stamps = [datetime.combine(d, time(h), tzinfo=ET).astimezone(UTC) for d in days for h in hours]
    return pl.Series("bar_start", stamps, dtype=pl.Datetime("us", "UTC"))


def test_calendar_tape_matching_the_table_gives_its_sessions() -> None:
    sessions = sessions_from_tape(CAL, _starts(SESSIONS), START, END)
    assert [s.day for s in sessions] == SESSIONS
    assert date(2026, 7, 3) not in SESSIONS


def test_calendar_tape_trading_on_a_table_holiday_raises_naming_it() -> None:
    with pytest.raises(CalendarMismatchError, match=r"2026-07-03 \(Independence Day"):
        sessions_from_tape(CAL, _starts([*SESSIONS, date(2026, 7, 3)]), START, END)


def test_calendar_table_session_with_no_bars_raises_naming_it() -> None:
    missing = date(2026, 7, 7)
    with pytest.raises(CalendarMismatchError, match="no bars: 2026-07-07"):
        sessions_from_tape(CAL, _starts([d for d in SESSIONS if d != missing]), START, END)


def test_calendar_extended_hours_bars_alone_do_not_make_a_trading_day() -> None:
    pre_and_post = _starts([date(2026, 7, 3)], hours=range(4, 9))
    assert tape_days(pre_and_post) == frozenset()


def test_calendar_the_0900_and_1500_et_bars_mark_a_trading_day() -> None:
    assert tape_days(_starts([date(2026, 7, 2)], hours=range(9, 10))) == {date(2026, 7, 2)}
    assert tape_days(_starts([date(2026, 7, 2)], hours=range(15, 16))) == {date(2026, 7, 2)}


def test_calendar_tape_days_use_et_dates_not_utc_dates() -> None:
    # 20:00 ET on Jul 2 is 00:00 UTC on Jul 3; it is still an extended-hours bar on Jul 2.
    late = pl.Series(
        [datetime(2026, 7, 3, 0, tzinfo=UTC), datetime(2026, 7, 2, 19, tzinfo=UTC)],
        dtype=pl.Datetime("us", "UTC"),
    )
    assert tape_days(late) == {date(2026, 7, 2)}


def test_calendar_check_reports_both_directions_and_ignores_days_outside() -> None:
    traded = {*SESSIONS, date(2026, 7, 3), date(2026, 6, 26)} - {date(2026, 7, 7)}
    mismatch = check_trading_days(CAL, traded, START, END)
    assert mismatch.traded_but_closed == (date(2026, 7, 3),)
    assert mismatch.session_without_bars == (date(2026, 7, 7),)
    assert not mismatch.ok
    assert check_trading_days(CAL, SESSIONS, START, END).ok


def test_calendar_weekend_bars_are_a_mismatch() -> None:
    saturday = date(2026, 7, 4)
    mismatch = check_trading_days(CAL, [*SESSIONS, saturday], START, END)
    assert mismatch.traded_but_closed == (saturday,)
    assert mismatch.start + timedelta(days=11) == mismatch.end
