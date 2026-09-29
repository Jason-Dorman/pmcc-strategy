"""Time to expiry and DTE (DEC-24): T runs to the expiry session's close, ACT/365."""

from datetime import UTC, date, datetime, time

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.domain.clock import ET
from pmcc.pricing.expiry import SECONDS_PER_YEAR, days_to_expiry, years_to_expiry

CAL = load_calendar()


def _et(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=ET)


def test_dec_24_t_is_seconds_to_the_expiry_close_over_365_days() -> None:
    expiry = CAL.session(date(2026, 9, 25))  # a Friday, closing 16:00

    t = years_to_expiry(_et(date(2026, 9, 21), 10), expiry)

    assert t == (4 * 24 + 6) * 3600 / SECONDS_PER_YEAR
    assert SECONDS_PER_YEAR == 31_536_000


def test_dec_24_t_runs_to_1300_on_a_half_day_expiry() -> None:
    expiry = CAL.session(date(2026, 11, 27))  # the day after Thanksgiving closes 13:00

    assert expiry.is_half_day
    assert years_to_expiry(_et(date(2026, 11, 27), 10), expiry) == 3 * 3600 / SECONDS_PER_YEAR


def test_dec_24_t_counts_elapsed_time_across_a_clock_change() -> None:
    # US clocks go back on Sun Nov 1 2026, so Fri 16:00 to Mon 16:00 is 73 hours, not 72.
    expiry = CAL.session(date(2026, 11, 2))

    assert years_to_expiry(_et(date(2026, 10, 30), 16), expiry) == 73 * 3600 / SECONDS_PER_YEAR


def test_dec_24_t_is_zero_at_the_expiry_close_and_negative_after() -> None:
    expiry = CAL.session(date(2026, 9, 25))

    assert years_to_expiry(_et(date(2026, 9, 25), 16), expiry) == 0.0
    assert years_to_expiry(_et(date(2026, 9, 28), 10), expiry) < 0.0


def test_dec_24_t_refuses_a_naive_time() -> None:
    with pytest.raises(ValueError, match="naive"):
        years_to_expiry(datetime(2026, 9, 21, 10), CAL.session(date(2026, 9, 25)))


def test_dec_24_dte_counts_calendar_days_from_the_decision_date() -> None:
    assert days_to_expiry(_et(date(2026, 3, 30), 15), date(2026, 9, 18)) == 172
    assert days_to_expiry(_et(date(2026, 9, 18), 10), date(2026, 9, 18)) == 0


def test_dec_24_dte_uses_the_et_date_of_the_decision() -> None:
    # 03:30 UTC on Sep 18 is 23:30 ET on Sep 17, so the decision date is Sep 17.
    assert days_to_expiry(datetime(2026, 9, 18, 3, 30, tzinfo=UTC), date(2026, 9, 18)) == 1
