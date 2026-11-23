"""What followed each session: its matured 30-day realized variance (THESIS-SPEC §5.2).

`realized_total_variance_t` is the sum of r² over the closes in t's horizon (the same sessions as
`N_t`), each return close to close, so a weekend or holiday gap is in the next return. It exists
only once the horizon's last session is within the data: until then the outcome is `PENDING`,
null, never zero. A horizon missing a return is `INCOMPLETE`. These are evaluation values only:
nothing in a feature, an episode or a candidate reads them (§5.2).
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import final

from pmcc.domain.calendar import SessionCalendar
from pmcc.thesis.features import CALENDAR_DAYS_PER_YEAR, FeatureRow, horizon_sessions


class OutcomeStatus(StrEnum):
    MATURED = "MATURED"
    PENDING = "PENDING"  # the horizon ends after the data
    INCOMPLETE = "INCOMPLETE"  # a return in the horizon is missing
    UNAVAILABLE = "UNAVAILABLE"  # the horizon runs past the calendar


@final
@dataclass(frozen=True, slots=True)
class Outcome:
    day: date
    maturity_day: date | None  # the horizon's last session
    status: OutcomeStatus
    realized_total_variance: float | None
    realized_vol: float | None  # realized_vol_30
    realized_variance_premium: float | None  # implied minus realized total variance
    forecast_error_variance: float | None  # realized minus forecast total variance


def compute_outcomes(
    rows: Sequence[FeatureRow], calendar: SessionCalendar, days: int
) -> tuple[Outcome, ...]:
    """Each row's outcome, matured against the last session with an index close."""
    closes = [row.day for row in rows if row.index_close is not None]
    if not closes:
        return tuple(_empty(row.day, None, OutcomeStatus.PENDING) for row in rows)
    through = closes[-1]
    returns = {row.day: row.log_return for row in rows}
    return tuple(_outcome(row, calendar, days, through, returns) for row in rows)


def _outcome(
    row: FeatureRow,
    calendar: SessionCalendar,
    days: int,
    through: date,
    returns: dict[date, float | None],
) -> Outcome:
    horizon = horizon_sessions(calendar, row.day, days)
    if not horizon:
        return _empty(row.day, None, OutcomeStatus.UNAVAILABLE)
    if horizon[-1] > through:
        return _empty(row.day, horizon[-1], OutcomeStatus.PENDING)
    found = [returns.get(day) for day in horizon]
    if any(r is None for r in found):
        return _empty(row.day, horizon[-1], OutcomeStatus.INCOMPLETE)
    total = sum(r * r for r in found if r is not None)
    return Outcome(
        day=row.day,
        maturity_day=horizon[-1],
        status=OutcomeStatus.MATURED,
        realized_total_variance=total,
        realized_vol=math.sqrt(total * CALENDAR_DAYS_PER_YEAR / days),
        realized_variance_premium=_minus(row.implied_total_variance, total),
        forecast_error_variance=_minus(total, row.forecast_total_variance),
    )


def _empty(day: date, maturity: date | None, status: OutcomeStatus) -> Outcome:
    return Outcome(day, maturity, status, None, None, None, None)


def _minus(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b
