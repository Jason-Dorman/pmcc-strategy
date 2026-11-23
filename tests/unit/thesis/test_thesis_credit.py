"""The credit condition (THESIS-SPEC §4.4, §5.5), and §14's publication-lag test (2)."""

from datetime import date, datetime, time

import pytest

from pmcc.domain.clock import at_et
from pmcc.thesis.calendar import decision_at
from pmcc.thesis.credit import (
    CreditObservation,
    CreditSeries,
    CreditStatus,
    assumed_available_at,
    credit_series,
    credit_state,
    percent_to_bps,
)
from tests.fakes.thesis_tracker import CAL, CONFIG, credit, weekdays

DAYS = weekdays(date(2024, 9, 2), date(2024, 11, 29))  # the source's own days, holidays too
DECIDE = date(2024, 12, 3)  # a Tuesday: Friday Nov 29's observation is usable from 20:30


def _state(series: CreditSeries, day: date = DECIDE, at: datetime | None = None):
    moment = decision_at(day, time(20, 30)) if at is None else at
    return credit_state(series, day, moment, CAL, CONFIG.credit)


def _series(level: float, short_rise: float = 0.0, long_rise: float = 0.0) -> CreditSeries:
    """Observations ending at `level`: `short_rise` above the one 5 back, `long_rise` above the
    one 20 back."""
    n = len(DAYS)

    def bps(i: int) -> float:
        if i == n - 1:
            return level
        if i >= n - 1 - 5:
            return level - short_rise
        return level - long_rise

    return credit(DAYS, bps)


def test_f55_fred_percent_converts_to_bps() -> None:
    assert percent_to_bps(3.52) == 352
    assert percent_to_bps(0.05) == 5


def test_f44_assumed_availability_is_two_business_days_later_at_2030() -> None:
    got = assumed_available_at(date(2024, 11, 29), CAL, CONFIG.credit)
    assert got == at_et(date(2024, 12, 3), time(20, 30))
    assert assumed_available_at(date(2024, 11, 27), CAL, CONFIG.credit) == at_et(
        date(2024, 12, 2),
        time(20, 30),  # Thanksgiving is no business day
    )


def test_f44_credit_available_a_day_late_cant_affect_todays_signal() -> None:
    series = _series(300.0)
    late = CreditSeries(
        [
            *series.observations,
            CreditObservation(DECIDE, 900.0, at_et(date(2024, 12, 4), time(20, 30))),
        ]
    )
    assert _state(late) == _state(series)
    assert _state(late).observation_date == date(2024, 11, 29)
    tomorrow = _state(late, date(2024, 12, 4))
    assert (tomorrow.observation_date, tomorrow.status) == (DECIDE, CreditStatus.UNSTABLE)


def test_f44_an_observation_is_usable_only_once_its_time_has_passed() -> None:
    series = _series(300.0)
    early = _state(series, at=at_et(DECIDE, time(20, 29)))
    assert early.observation_date == date(2024, 11, 28)


@pytest.mark.parametrize(
    ("level", "short_rise", "long_rise", "stable"),
    [
        (450.0, 0.0, 0.0, True),  # the level on the line
        (451.0, 0.0, 0.0, False),
        (300.0, 15.0, 15.0, True),  # +15 on the line
        (300.0, 16.0, 16.0, False),
        (300.0, 0.0, 40.0, True),  # +40 on the line
        (300.0, 0.0, 41.0, False),
        (300.0, -50.0, -120.0, True),  # falls pass
    ],
)
def test_f55_stable_needs_the_level_and_both_changes(
    level: float, short_rise: float, long_rise: float, stable: bool
) -> None:
    state = _state(_series(level, short_rise, long_rise))
    assert state.status is (CreditStatus.STABLE if stable else CreditStatus.UNSTABLE)
    assert (state.level_bps, state.change_short_bps, state.change_long_bps) == (
        level,
        short_rise,
        long_rise,
    )


def test_f55_comparators_count_the_sources_observations_not_sessions() -> None:
    # Thanksgiving (Nov 28) is in the source's days but is no session: still one observation back.
    state = _state(_series(300.0, short_rise=10.0))
    assert DAYS[-6] == date(2024, 11, 22)
    assert state.change_short_bps == 10.0


def test_f44_stale_credit_is_unavailable_not_unstable() -> None:
    state = _state(_series(300.0), date(2024, 12, 9))  # Nov 29's is 6 business days old by then
    assert (state.status, state.age_business_days) == (CreditStatus.UNAVAILABLE, 6)
    assert "old" in state.note
    assert state.level_ok is None


def test_f55_too_few_observations_is_unavailable() -> None:
    few = credit(DAYS[-20:], lambda i: 300.0)
    state = _state(few)
    assert state.status is CreditStatus.UNAVAILABLE
    assert "21 are needed" in state.note


def test_f44_series_refuses_duplicates_and_out_of_order_availability() -> None:
    day = date(2024, 11, 29)
    at = at_et(DECIDE, time(20, 30))
    with pytest.raises(ValueError, match="two observations"):
        CreditSeries([CreditObservation(day, 1.0, at), CreditObservation(day, 2.0, at)])
    with pytest.raises(ValueError, match="available before"):
        CreditSeries(
            [
                CreditObservation(date(2024, 11, 27), 1.0, at),
                CreditObservation(day, 2.0, at_et(date(2024, 12, 2), time(20, 30))),
            ]
        )
    with pytest.raises(ValueError, match="tz-aware"):
        CreditObservation(day, 1.0, datetime(2024, 12, 3, 20, 30))


def test_f44_credit_series_keeps_only_points_inside_the_calendar() -> None:
    points = [(date(2013, 12, 30), 400.0), (date(2014, 1, 2), 401.0), (date(2028, 1, 3), 402.0)]
    series = credit_series(points, CAL, CONFIG.credit)
    assert [o.observation_date for o in series.observations] == [date(2014, 1, 2)]
