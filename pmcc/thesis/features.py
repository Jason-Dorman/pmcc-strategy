"""Each session's features, from data up to its close only (THESIS-SPEC §5.1, §5.2).

- **Returns:** `r_t = ln(S_t / S_(t-1))`, close to close between consecutive sessions, so a
  weekend or holiday gap falls in the next session's return. A session missing its close, or
  following one that is, has no return: nothing is forward-filled (§4.4).
- **EWMA:** `v_t = λ v_(t-1) + (1 - λ) r_t²`, starting at the 60th valid return with the mean of
  the first 60 squared returns (that one included), so no estimate exists before it. A session
  without a return has no `v_t`; the recursion resumes from the last value at the next valid
  return (TD-16).
- **RV_n:** `sqrt(252 · mean(r²))` over the last n sessions, all n with a return, else none.
- **The matched horizon:** `N_t` is the number of exchange closes after t's, through t + 30
  calendar days (that day included), from the calendar alone. Implied and forecast total variance,
  the forecast vol and the gaps are §5.2's formulas. Volatility is a decimal throughout.

The realized outcome after t is not a feature: it is in `pmcc.thesis.outcomes`, and never feeds a
signal (§5.2).
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import pairwise
from typing import final

from pmcc.domain.calendar import SessionCalendar
from pmcc.thesis.config import ThesisConfig

TRADING_DAYS_PER_YEAR = 252
CALENDAR_DAYS_PER_YEAR = 365


class TrackerInputError(ValueError):
    """A series the tracker was given can't be used: a non-session date, or a bad value."""


@final
@dataclass(frozen=True, slots=True)
class FeatureRow:
    """Session `day`'s features, as known at its close. None where an input is missing."""

    day: date
    index_close: float | None
    vix_points: float | None
    log_return: float | None
    valid_returns: int  # valid returns up to and including `day`
    ewma_variance: float | None  # daily variance, v_t
    rv_short: float | None  # RV5, annualised decimal
    rv_long: float | None  # RV20, annualised decimal
    horizon_closes: int | None  # N_t
    implied_total_variance: float | None
    forecast_total_variance: float | None
    forecast_vol: float | None  # forecast_vol_30
    forecast_gap_vol: float | None
    forecast_gap_variance: float | None
    warm: bool  # at least signal_warmup_sessions valid returns

    @property
    def vix_decimal(self) -> float | None:
        return None if self.vix_points is None else self.vix_points / 100


def horizon_sessions(calendar: SessionCalendar, day: date, days: int) -> tuple[date, ...] | None:
    """The sessions after `day` through `day + days` calendar days, or None past the calendar."""
    end = day + timedelta(days=days)
    if end > calendar.last_day:
        return None
    return tuple(s.day for s in calendar.sessions(day + timedelta(days=1), end))


def compute_features(
    index: Mapping[date, float],
    vix: Mapping[date, float],
    calendar: SessionCalendar,
    config: ThesisConfig,
) -> tuple[FeatureRow, ...]:
    """A row for every session from the first input day to the last."""
    _check(index, calendar, "index")
    _check(vix, calendar, "VIX")
    given = [*index, *vix]
    if not given:
        return ()
    days = [s.day for s in calendar.sessions(min(given), max(given))]
    returns = _returns(days, index)
    ewma = _ewma(returns, config)
    builder = _RowBuilder(calendar, config, returns, ewma)
    return tuple(builder.row(i, day, index.get(day), vix.get(day)) for i, day in enumerate(days))


def _check(series: Mapping[date, float], calendar: SessionCalendar, name: str) -> None:
    for day, value in series.items():
        if not calendar.is_session(day):
            raise TrackerInputError(f"{name} has a value on {day}, which is not a session")
        if not (math.isfinite(value) and value > 0):
            raise TrackerInputError(f"{name} on {day} is {value}: must be finite and above zero")


def _returns(days: Sequence[date], index: Mapping[date, float]) -> list[float | None]:
    closes = [index.get(day) for day in days]
    out: list[float | None] = [None]
    for prev, cur in pairwise(closes):
        out.append(math.log(cur / prev) if prev is not None and cur is not None else None)
    return out


def _ewma(returns: Sequence[float | None], config: ThesisConfig) -> list[float | None]:
    lam, init = config.forecast.ewma_lambda, config.forecast.initialization_sessions
    seen: list[float] = []
    level: float | None = None
    out: list[float | None] = []
    for r in returns:
        if r is None:
            out.append(None)
            continue
        if level is None:
            seen.append(r * r)
            level = sum(seen) / init if len(seen) == init else None
        else:
            level = lam * level + (1 - lam) * r * r
        out.append(level)
    return out


@final
class _RowBuilder:
    def __init__(
        self,
        calendar: SessionCalendar,
        config: ThesisConfig,
        returns: Sequence[float | None],
        ewma: Sequence[float | None],
    ) -> None:
        self._calendar, self._config = calendar, config
        self._returns, self._ewma = returns, ewma
        self._valid = _running_count(returns)

    def row(self, i: int, day: date, close: float | None, vix: float | None) -> FeatureRow:
        n = self._config.normalization
        horizon = horizon_sessions(self._calendar, day, self._config.forecast.horizon_calendar_days)
        count = None if horizon is None else len(horizon)
        implied = _implied(vix, self._config.forecast.horizon_calendar_days)
        forecast = _forecast(count, self._ewma[i])
        vol = _forecast_vol(forecast, self._config.forecast.horizon_calendar_days)
        return FeatureRow(
            day=day,
            index_close=close,
            vix_points=vix,
            log_return=self._returns[i],
            valid_returns=self._valid[i],
            ewma_variance=self._ewma[i],
            rv_short=realized_vol(self._returns, i, n.short_rv_sessions),
            rv_long=realized_vol(self._returns, i, n.long_rv_sessions),
            horizon_closes=count,
            implied_total_variance=implied,
            forecast_total_variance=forecast,
            forecast_vol=vol,
            forecast_gap_vol=_minus(None if vix is None else vix / 100, vol),
            forecast_gap_variance=_minus(implied, forecast),
            warm=self._valid[i] >= self._config.forecast.signal_warmup_sessions,
        )


def _running_count(returns: Sequence[float | None]) -> list[int]:
    out: list[int] = []
    total = 0
    for r in returns:
        total += r is not None
        out.append(total)
    return out


def realized_vol(returns: Sequence[float | None], i: int, n: int) -> float | None:
    """RV_n at position `i`: the last `n` returns ending there, all present, annualised."""
    if i + 1 < n:
        return None
    window = returns[i + 1 - n : i + 1]
    if any(r is None for r in window):
        return None
    return math.sqrt(TRADING_DAYS_PER_YEAR * sum(r * r for r in window if r is not None) / n)


def _implied(vix: float | None, days: int) -> float | None:
    return None if vix is None else (vix / 100) ** 2 * days / CALENDAR_DAYS_PER_YEAR


def _forecast(count: int | None, ewma: float | None) -> float | None:
    return None if count is None or ewma is None else count * ewma


def _forecast_vol(total: float | None, days: int) -> float | None:
    return None if total is None else math.sqrt(total * CALENDAR_DAYS_PER_YEAR / days)


def _minus(a: float | None, b: float | None) -> float | None:
    return None if a is None or b is None else a - b
