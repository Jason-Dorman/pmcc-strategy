"""The credit condition, as known at a decision (THESIS-SPEC §4.4, §5.5).

- **Units:** basis points. FRED's percent (3.52) is 352 bps (`percent_to_bps`).
- **Availability:** an observation is usable at a decision only once its `available_at` has
  passed. Without a recorded time, it is assumed to be the observation date plus two business
  days at 20:30 New York (`assumed_available_at`); a business day is an NYSE session (TD-15).
- **Stable credit:** the latest usable OAS at or below 450 bps, its change from the observation
  five source observations earlier at or below +15 bps, and from twenty earlier at or below +40
  (falls always pass). The comparators are the series' own observations, counted back from the
  latest usable one, not sessions.
- **Unavailable, not unstable:** fewer than 21 usable observations, or a latest one more than
  three business days old at the decision, is `UNAVAILABLE`: a data-quality outcome that blocks
  an entry without calling credit unstable (§4.4).
"""

import math
from bisect import bisect_right
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from itertools import pairwise
from typing import final

from pmcc.domain.calendar import SessionCalendar
from pmcc.thesis.calendar import business_days_after, business_days_between, decision_at
from pmcc.thesis.config import CreditConfig

SHORT_COMPARATOR = 5  # maximum_change_5_observations_bps compares 5 observations back
LONG_COMPARATOR = 20  # maximum_change_20_observations_bps compares 20 back


class CreditStatus(StrEnum):
    STABLE = "STABLE"
    UNSTABLE = "UNSTABLE"
    UNAVAILABLE = "UNAVAILABLE"


def percent_to_bps(percent: float) -> float:
    """A spread in percent (FRED's unit) as basis points: 3.52 -> 352."""
    return round(percent * 100, 6)


@final
@dataclass(frozen=True, slots=True)
class CreditObservation:
    observation_date: date
    spread_bps: float
    available_at: datetime  # tz-aware

    def __post_init__(self) -> None:
        if not math.isfinite(self.spread_bps):
            raise ValueError(f"credit on {self.observation_date} is {self.spread_bps}")
        if self.available_at.utcoffset() is None:
            raise ValueError(f"credit on {self.observation_date}: available_at must be tz-aware")


def assumed_available_at(
    observation_date: date, calendar: SessionCalendar, config: CreditConfig
) -> datetime:
    """The disclosed assumption when no publication time is recorded (§4.4)."""
    lag = config.assumed_publication_lag_business_days
    return decision_at(
        business_days_after(calendar, observation_date, lag), config.publication_time
    )


@final
class CreditSeries:
    """Observations in date order, one per date, available no earlier than an older one."""

    def __init__(self, observations: Sequence[CreditObservation]) -> None:
        ordered = sorted(observations, key=lambda o: o.observation_date)
        for prev, cur in pairwise(ordered):
            if prev.observation_date == cur.observation_date:
                raise ValueError(f"credit has two observations on {cur.observation_date}")
            if cur.available_at < prev.available_at:
                raise ValueError(
                    f"credit for {cur.observation_date} is available before "
                    f"{prev.observation_date}'s"
                )
        self._obs = tuple(ordered)
        self._available = [o.available_at for o in ordered]

    @property
    def observations(self) -> tuple[CreditObservation, ...]:
        return self._obs

    def usable_at(self, moment: datetime) -> tuple[CreditObservation, ...]:
        """The observations available at `moment`, oldest first."""
        return self._obs[: bisect_right(self._available, moment)]


def credit_series(
    points: Iterable[tuple[date, float]], calendar: SessionCalendar, config: CreditConfig
) -> CreditSeries:
    """A source's (date, bps) points as a series on the assumed publication lag (§4.4), kept only
    inside the calendar's span: its business days can't be counted outside it. A point before
    2014 can't be a comparator for a warm session anyway (§5.1's 252 sessions come first)."""
    return CreditSeries(
        [
            CreditObservation(day, bps, assumed_available_at(day, calendar, config))
            for day, bps in points
            if calendar.first_day <= day <= calendar.last_day
        ]
    )


@final
@dataclass(frozen=True, slots=True)
class CreditState:
    """The credit condition at session `day`'s decision."""

    day: date
    decided_at: datetime
    status: CreditStatus
    observation_date: date | None
    level_bps: float | None
    change_short_bps: float | None  # vs 5 observations earlier
    change_long_bps: float | None  # vs 20 observations earlier
    level_ok: bool | None
    change_short_ok: bool | None
    change_long_ok: bool | None
    age_business_days: int | None
    note: str  # why it is unavailable; empty otherwise


def credit_state(
    series: CreditSeries,
    day: date,
    decided_at: datetime,
    calendar: SessionCalendar,
    config: CreditConfig,
) -> CreditState:
    usable = series.usable_at(decided_at)
    if len(usable) <= LONG_COMPARATOR:
        note = f"{len(usable)} observations usable; {LONG_COMPARATOR + 1} are needed"
        return _unavailable(day, decided_at, usable[-1] if usable else None, None, note, calendar)
    latest = usable[-1]
    age = business_days_between(calendar, latest.observation_date, day)
    if age > config.maximum_age_business_days:
        note = f"the latest is {age} business days old; at most {config.maximum_age_business_days}"
        return _unavailable(day, decided_at, latest, age, note, calendar)
    short = latest.spread_bps - usable[-1 - SHORT_COMPARATOR].spread_bps
    long_ = latest.spread_bps - usable[-1 - LONG_COMPARATOR].spread_bps
    checks = (
        latest.spread_bps <= config.maximum_level_bps,
        short <= config.maximum_change_5_observations_bps,
        long_ <= config.maximum_change_20_observations_bps,
    )
    status = CreditStatus.STABLE if all(checks) else CreditStatus.UNSTABLE
    return CreditState(
        day, decided_at, status, latest.observation_date, latest.spread_bps, short, long_,
        *checks, age, "",
    )  # fmt: skip


def _unavailable(
    day: date,
    decided_at: datetime,
    latest: CreditObservation | None,
    age: int | None,
    note: str,
    calendar: SessionCalendar,
) -> CreditState:
    if latest is not None and age is None:
        age = business_days_between(calendar, latest.observation_date, day)
    return CreditState(
        day, decided_at, CreditStatus.UNAVAILABLE,
        None if latest is None else latest.observation_date,
        None if latest is None else latest.spread_bps,
        None, None, None, None, None, age, note,
    )  # fmt: skip
