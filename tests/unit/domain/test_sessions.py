"""Session and session-bar model (DEC-06, ARCHITECTURE §4.2)."""

from datetime import UTC, date, datetime, time

import pytest

from pmcc.domain.clock import at_et, bar_end
from pmcc.domain.sessions import HALF_DAY_CLOSE, REGULAR_CLOSE, Session, session_of

FRI = date(2026, 9, 18)
HALF = date(2026, 11, 27)  # day after Thanksgiving: 13:00 close
SESSIONS = {FRI: Session(FRI), HALF: Session(HALF, close=HALF_DAY_CLOSE)}


def _end(day: date, hour: int) -> datetime:
    return at_et(day, time(hour))


def test_session_regular_close_is_16_and_half_day_close_is_13() -> None:
    assert time(16) == REGULAR_CLOSE
    assert time(13) == HALF_DAY_CLOSE
    assert not Session(FRI).is_half_day
    assert Session(HALF, close=HALF_DAY_CLOSE).is_half_day


def test_session_regular_day_has_seven_bars_ending_10_to_16() -> None:
    ends = Session(FRI).bar_ends()
    assert ends == tuple(_end(FRI, h) for h in range(10, 17))


def test_session_half_day_has_four_bars_ending_10_to_13() -> None:
    ends = Session(HALF, close=HALF_DAY_CLOSE).bar_ends()
    assert ends == tuple(_end(HALF, h) for h in range(10, 14))


def test_session_close_bar_end_is_the_close_instant() -> None:
    assert Session(FRI).close_bar_end == _end(FRI, 16)
    assert Session(HALF, close=HALF_DAY_CLOSE).close_bar_end == _end(HALF, 13)


@pytest.mark.parametrize("close", [time(9), time(17), time(15, 30), time(12, 0, 1)])
def test_session_rejects_a_close_off_the_session_hours(close: time) -> None:
    with pytest.raises(ValueError, match="close"):
        Session(FRI, close=close)


@pytest.mark.parametrize(
    ("hour", "expected"),
    [
        (8, False),  # pre-market bar 08:00-09:00
        (9, False),  # ends 09:00
        (10, True),  # 09:00-10:00 bar: the first session bar
        (15, True),
        (16, True),  # 15:00-16:00 bar: the close bar
        (17, False),  # 16:00-17:00 post-close stub
        (20, False),  # extended hours
    ],
)
def test_session_contains_only_bars_ending_10_to_16(hour: int, expected: bool) -> None:
    assert Session(FRI).contains(_end(FRI, hour)) is expected


@pytest.mark.parametrize(("hour", "expected"), [(10, True), (13, True), (14, False), (16, False)])
def test_session_half_day_contains_only_bars_ending_10_to_13(hour: int, expected: bool) -> None:
    assert Session(HALF, close=HALF_DAY_CLOSE).contains(_end(HALF, hour)) is expected


def test_session_contains_nothing_from_another_day() -> None:
    assert not Session(FRI).contains(_end(date(2026, 9, 17), 12))


def test_session_contains_nothing_off_the_hour() -> None:
    assert not Session(FRI).contains(at_et(FRI, time(12, 30)))


def test_session_contains_matches_the_same_instant_in_utc() -> None:
    assert Session(FRI).contains(datetime(2026, 9, 18, 20, 0, tzinfo=UTC))


def test_session_contains_rejects_naive_times() -> None:
    with pytest.raises(ValueError, match="tz-aware"):
        Session(FRI).contains(datetime(2026, 9, 18, 16, 0))


@pytest.mark.parametrize(
    ("day", "hour", "expected"),
    [(FRI, 16, True), (FRI, 15, False), (HALF, 13, True), (HALF, 16, False)],
)
def test_session_is_close_bar_only_at_the_session_close(
    day: date, hour: int, expected: bool
) -> None:
    assert SESSIONS[day].is_close_bar(_end(day, hour)) is expected


def test_session_of_classifies_lseg_stamps_into_sessions() -> None:
    # 19:00 UTC start (EDT) -> ends 16:00 ET: the Friday close bar.
    assert session_of(bar_end(datetime(2026, 9, 18, 19, 0)), SESSIONS) == Session(FRI)
    # 20:00 UTC start -> ends 17:00 ET: the post-close stub, not a session bar.
    assert session_of(bar_end(datetime(2026, 9, 18, 20, 0)), SESSIONS) is None
    # Half-day, EST: 17:00 UTC start -> ends 13:00 ET, the close bar.
    assert session_of(bar_end(datetime(2026, 11, 27, 17, 0)), SESSIONS) == SESSIONS[HALF]
    # Half-day, EST: 18:00 UTC start -> ends 14:00 ET, after the early close.
    assert session_of(bar_end(datetime(2026, 11, 27, 18, 0)), SESSIONS) is None


def test_session_of_is_none_on_a_day_without_a_session() -> None:
    assert session_of(_end(date(2026, 9, 19), 12), SESSIONS) is None
