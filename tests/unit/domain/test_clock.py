"""ET time helpers and `bar_end` (DEC-06, ARCHITECTURE §4.2, LDG §4.8)."""

from datetime import UTC, date, datetime, time, timedelta

import pytest

from pmcc.domain.clock import BAR, ET, at_et, bar_end, to_et


def test_clock_et_is_new_york() -> None:
    assert str(ET) == "America/New_York"


def test_clock_bar_is_one_hour() -> None:
    assert timedelta(hours=1) == BAR


def test_clock_bar_end_converts_naive_utc_start_to_et_end_under_edt() -> None:
    # LSEG stamps 19:00 UTC for the 15:00-16:00 ET bar under EDT.
    end = bar_end(datetime(2026, 9, 18, 19, 0))
    assert end == at_et(date(2026, 9, 18), time(16))
    assert end.tzinfo is ET
    assert end.utcoffset() == timedelta(hours=-4)


def test_clock_bar_end_converts_naive_utc_start_to_et_end_under_est() -> None:
    # Under EST the same ET bar starts at 20:00 UTC.
    end = bar_end(datetime(2026, 12, 18, 20, 0))
    assert end == at_et(date(2026, 12, 18), time(16))
    assert end.utcoffset() == timedelta(hours=-5)


def test_clock_bar_end_accepts_an_aware_start() -> None:
    start = datetime(2026, 9, 18, 19, 0, tzinfo=UTC)
    assert bar_end(start) == bar_end(datetime(2026, 9, 18, 19, 0))


def test_clock_bar_end_keeps_the_zone_of_an_aware_non_utc_start() -> None:
    # An ET start must not be relabelled as UTC.
    assert bar_end(at_et(date(2026, 9, 18), time(15))) == at_et(date(2026, 9, 18), time(16))


def test_clock_bar_end_adds_elapsed_time_across_the_dst_fall_back() -> None:
    # 05:00 UTC Nov 1 2026 is 01:00 EDT; one hour later is 01:00 EST, not 02:00.
    end = bar_end(datetime(2026, 11, 1, 5, 0))
    assert end.astimezone(UTC) == datetime(2026, 11, 1, 6, 0, tzinfo=UTC)
    assert end.hour == 1
    assert end.utcoffset() == timedelta(hours=-5)


def test_clock_at_et_builds_an_aware_et_datetime() -> None:
    t = at_et(date(2026, 7, 2), time(13))
    assert t.tzinfo is ET
    assert (t.year, t.month, t.day, t.hour) == (2026, 7, 2, 13)


def test_clock_to_et_converts_aware_times() -> None:
    t = to_et(datetime(2026, 9, 18, 20, 0, tzinfo=UTC))
    assert t == at_et(date(2026, 9, 18), time(16))
    assert t.tzinfo is ET


def test_clock_to_et_rejects_naive_times() -> None:
    with pytest.raises(ValueError, match="tz-aware"):
        to_et(datetime(2026, 9, 18, 16, 0))
