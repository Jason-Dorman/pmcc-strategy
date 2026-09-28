"""Chain discovery: strike increments, strike bands and the fetch plan (DEC-14, DEC-48).

Nothing here talks to LSEG. The fetch (P1-08) and the probes (P1-04) ask the questions; this module
says what to ask and reads the answers.

- **Increments (DEC-14):** ask an anchor `A` (a multiple of $10 near the region's centre) and
  `A` + $0.50, $1, $2.50, $5 on one session. The smallest offset that answers is the increment;
  if none does, it is $10.
- **Bands (ARCHITECTURE §6.3):** a band is a price range plus padding in strike steps. Its ladder
  is built in integer cents on the increment's grid (LDG §4.11) and errs wide (LDG §4.10).
- **Plan:** one unit for the stock tape, and one per expiry and right (`chains/{E}_{C|P}`), each
  with its dates and bands. Bands come from regular-session highs and lows. Fetching ranges from the
  window's highs and lows is allowed; selection only ever sees point-in-time data (Spec).
"""

import math
from collections.abc import Collection, Iterator, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from typing import final

import numpy as np
import polars as pl

from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import Right
from pmcc.domain.money import UNITS_PER_CENT, Price
from pmcc.domain.sessions import FIRST_BAR_END, Session

# --- Strike increments (DEC-14) ---------------------------------------------------------------

ANCHOR_GRID_CENTS = 1_000  # anchors are multiples of $10
INCREMENT_OFFSETS_CENTS = (50, 100, 250, 500)  # tried smallest first
NO_OFFSET_INCREMENT_CENTS = 1_000  # the increment when no offset answers


def increment_anchor(centre: Price) -> int:
    """The multiple of $10 nearest `centre` (ties go up), in cents; never below $10."""
    cents = centre.units // UNITS_PER_CENT
    anchor = (cents + ANCHOR_GRID_CENTS // 2) // ANCHOR_GRID_CENTS * ANCHOR_GRID_CENTS
    return max(anchor, ANCHOR_GRID_CENTS)


def increment_strikes(anchor: int) -> tuple[int, ...]:
    """The five strikes to ask, in cents: the anchor, then each offset above it."""
    return (anchor, *(anchor + offset for offset in INCREMENT_OFFSETS_CENTS))


def increment_from(anchor: int, answered: Collection[int]) -> int:
    """The increment in cents: the smallest offset whose strike answered, else $10."""
    for offset in INCREMENT_OFFSETS_CENTS:
        if anchor + offset in answered:
            return offset
    return NO_OFFSET_INCREMENT_CENTS


# --- Bands ------------------------------------------------------------------------------------


class Region(StrEnum):
    """Where a band sits. Increments are probed per region (DEC-14)."""

    NEAR_MONEY = "near_money"
    DEEP_ITM = "deep_itm"


_NO_PRICE = Price(0)


@final
@dataclass(frozen=True, slots=True)
class Pad:
    """Padding past a band's edge: `steps` strike steps, or `at_least` when that is wider."""

    steps: int
    at_least: Price = _NO_PRICE

    def cents(self, step: int) -> int:
        return max(self.steps * step, _ceil_cents(self.at_least))


@final
@dataclass(frozen=True, slots=True)
class Band:
    """Strikes from `below` under `low` to `above` over `high`, on whichever grid is probed."""

    region: Region
    low: Price
    high: Price
    below: Pad
    above: Pad

    def __post_init__(self) -> None:
        if not Price(0) < self.low <= self.high:
            raise ValueError(f"a band needs 0 < low <= high, got {self.low} and {self.high}")

    @property
    def centre(self) -> Price:
        """Where the increment is probed: halfway between `low` and `high`."""
        return Price((self.low.units + self.high.units) // 2)

    def ladder(self, step: int) -> tuple[int, ...]:
        """The strikes in cents, every multiple of `step` from the padded low to the padded high.

        Built in integers, so no strike drifts a cent off the grid (LDG §4.11). Never below one
        step.
        """
        if step <= 0:
            raise ValueError(f"a strike step must be positive, got {step} cents")
        bottom = (_floor_cents(self.low) - self.below.cents(step)) // step * step
        top = -(-(_ceil_cents(self.high) + self.above.cents(step)) // step) * step
        return tuple(range(max(bottom, step), top + 1, step))


def _floor_cents(price: Price) -> int:
    return price.units // UNITS_PER_CENT


def _ceil_cents(price: Price) -> int:
    return -(-price.units // UNITS_PER_CENT)


# --- The stock tape, per session --------------------------------------------------------------

_ET = "America/New_York"
_HIGHS = ("HIGH_1", "TRDPRC_1")
_LOWS = ("LOW_1", "TRDPRC_1")


@final
@dataclass(frozen=True, slots=True)
class SessionRange:
    """A session's regular-hours low and high, and its close (the close bar's TRDPRC_1)."""

    day: date
    low: Price
    high: Price
    close: Price | None


def session_ranges(rows: pl.DataFrame, sessions: Sequence[Session]) -> tuple[SessionRange, ...]:
    """Each session's range from one stock RIC's raw hourly rows (`bar_start`, `field`, `value`).

    Only session bars count (DEC-06), so extended-hours ticks stay out (LDG §4.10). A trade print
    widens the range too. A session with no session bars is left out.
    """
    bounds = pl.DataFrame(
        {"day": [s.day for s in sessions], "close_hour": [s.close.hour for s in sessions]},
        schema={"day": pl.Date(), "close_hour": pl.Int8()},
    )
    end = (pl.col("bar_start") + pl.duration(hours=1)).dt.convert_time_zone(_ET)
    bars = (
        rows.with_columns(day=end.dt.date(), hour=end.dt.hour(), on_hour=end.dt.minute() == 0)
        .join(bounds, on="day")
        .filter(pl.col("on_hour") & pl.col("hour").is_between(FIRST_BAR_END.hour, "close_hour"))
    )
    per_day = (
        bars.group_by("day")
        .agg(
            high=pl.col("value").filter(pl.col("field").is_in(_HIGHS)).max(),
            low=pl.col("value").filter(pl.col("field").is_in(_LOWS)).min(),
            close=pl.col("value")
            .filter((pl.col("field") == "TRDPRC_1") & (pl.col("hour") == pl.col("close_hour")))
            .first(),
        )
        .drop_nulls(["high", "low"])
        .sort("day")
    )
    return tuple(
        SessionRange(
            row["day"],
            Price.from_dollars(row["low"]),
            Price.from_dollars(row["high"]),
            None if row["close"] is None else Price.from_dollars(row["close"]),
        )
        for row in per_day.iter_rows(named=True)
    )


# --- Plan volatility --------------------------------------------------------------------------

RV_RETURNS = 20
TRADING_DAYS = 252
VOL_MARGIN = 1.25


def band_vol(ranges: Sequence[SessionRange], window_start: date, window_end: date) -> float:
    """sigma-hat = 1.25 x the highest RV20 in the window. It sizes bands only (DEC-48).

    RV20 here is the sample standard deviation of 20 daily log returns of session closes x √252,
    taken at every close from the last one before the window through the window's end. The
    backtest's own RV20 is pricing's (DEC-26); this one only has to err wide.
    """
    closes = sorted((r.day, r.close) for r in ranges if r.close is not None and r.day <= window_end)
    if len(closes) <= RV_RETURNS:
        raise ValueError(
            f"band volatility needs {RV_RETURNS + 1} session closes, got {len(closes)}"
        )
    days = [d for d, _ in closes]
    returns = np.diff(np.log([float(c.to_dollars()) for _, c in closes]))
    before = [i for i, d in enumerate(days) if d < window_start]
    first = max(RV_RETURNS, before[-1] if before else RV_RETURNS)
    vols = [np.std(returns[i - RV_RETURNS : i], ddof=1) for i in range(first, len(days))]
    return VOL_MARGIN * float(max(vols)) * math.sqrt(TRADING_DAYS)


# --- The fetch plan (DEC-48, ARCHITECTURE §6.3) -----------------------------------------------

WARMUP_SESSIONS = 30  # before the window, for RV20 and the plan's volatility
WEEKLY_BELOW_STEPS = 4
WEEKLY_ABOVE_STEPS = 6
WEEKLY_EM_MULTIPLE = 2.5  # the weekly call band reaches 2.5 EMest over the high
EM_WEEK_YEARS = 5 / TRADING_DAYS
PUT_PAD_STEPS = 2
LONG_MIN_DTE, LONG_TARGET_DTE, LONG_MAX_DTE = 120, 180, 270
LONG_DEEP_Z = 2.0  # K = weekLow * exp(-2.0 * sigma-hat * sqrt(T)), about delta 0.97
LONG_PAD_STEPS = 2
# The long band runs from delta ~0.97 up to the money, so its grid can change along the way
# ($5 deep, $1 near the money): it is split into this many bands, each with its own increment.
LONG_SEGMENTS = 3
# Where to look for the monthly nearest 180 DTE: wide enough to always hold one either side.
_NEAREST_FROM, _NEAREST_TO = 90, 300
_DAY = timedelta(days=1)
_WEEK = timedelta(days=7)
_YEAR_DAYS = 365


@final
@dataclass(frozen=True, slots=True)
class Unit:
    """One fetch unit: the stock tape, or one expiry's calls or puts with their strike bands.

    `start` and `end` are the first and last session dates asked for, inclusive (DEC-47).
    """

    name: str
    start: date
    end: date
    expiry: date | None = None
    right: Right | None = None
    bands: tuple[Band, ...] = ()


@final
@dataclass(frozen=True, slots=True)
class FetchPlan:
    """Every unit a symbol needs over the window, and the volatility its bands were sized with."""

    window_start: date
    window_end: date
    sigma: float
    units: tuple[Unit, ...]

    def unit(self, name: str) -> Unit:
        for unit in self.units:
            if unit.name == name:
                return unit
        raise KeyError(name)


def stock_unit(calendar: SessionCalendar, window_start: date, window_end: date) -> Unit:
    """The stock tape: 30 sessions of warm-up, then the window. The plan is built from it."""
    first = calendar.sessions_before(window_start, WARMUP_SESSIONS)[0].day
    return Unit("stock", first, window_end)


def plan_symbol(
    calendar: SessionCalendar,
    ranges: Sequence[SessionRange],
    window_start: date,
    window_end: date,
) -> FetchPlan:
    """The units for one symbol, from its stock tape's session ranges (warm-up included).

    Weekly calls for every weekly expiry in the window and the one after it (G-3's next week),
    ATM puts on each week-open session (EM), and monthly calls for every monthly that is
    120-270 DTE, or nearest 180 DTE, on some session of the window. DTE is in calendar days, and
    T for a band is calendar days ÷ 365: both only size what is fetched (DEC-24 is pricing's).
    """
    if window_start > window_end:
        raise ValueError(f"the window starts {window_start}, after it ends {window_end}")
    sigma = band_vol(ranges, window_start, window_end)
    tape = _Tape(ranges, window_start, window_end)
    parts = [
        *_weekly_calls(calendar, tape, sigma),
        *_atm_puts(calendar, tape),
        *_monthly_calls(calendar, tape, sigma),
    ]
    units = (stock_unit(calendar, window_start, window_end), *_merge(parts))
    return FetchPlan(window_start, window_end, sigma, units)


@dataclass(frozen=True, slots=True)
class _Tape:
    """The session ranges, and the window they're read over."""

    ranges: Sequence[SessionRange]
    start: date
    end: date

    def span(self, first: date, last: date) -> tuple[Price, Price]:
        """The lowest low and highest high from `first` to `last`, inclusive."""
        inside = [r for r in self.ranges if first <= r.day <= last]
        if not inside:
            raise ValueError(f"the stock tape has no session range from {first} to {last}")
        return min(r.low for r in inside), max(r.high for r in inside)


@dataclass(frozen=True, slots=True)
class _Part:
    """One reason to fetch an expiry's calls or puts: its dates and one band."""

    expiry: date
    right: Right
    start: date
    end: date
    bands: tuple[Band, ...]


def _weekly_calls(calendar: SessionCalendar, tape: _Tape, sigma: float) -> Iterator[_Part]:
    """Every week with a session in the window, even one the window ends in, then the next."""
    expiries = [
        calendar.week_final(first).day for first, _ in _weeks(calendar, tape.start, tape.end)
    ]
    expiries.append(calendar.week_final(expiries[-1] + _WEEK).day)
    for expiry in expiries:
        start = calendar.week_open(expiry - _WEEK).day
        end = min(expiry, tape.end)
        low, high = tape.span(start, end)
        em = float(high.to_dollars()) * sigma * math.sqrt(EM_WEEK_YEARS)
        above = Pad(WEEKLY_ABOVE_STEPS, Price.from_dollars(WEEKLY_EM_MULTIPLE * em))
        band = Band(Region.NEAR_MONEY, low, high, Pad(WEEKLY_BELOW_STEPS), above)
        yield _Part(expiry, Right.CALL, start, end, (band,))


def _atm_puts(calendar: SessionCalendar, tape: _Tape) -> Iterator[_Part]:
    """A put band on every week-open session in the window, the last week's included."""
    for first, _ in _weeks(calendar, tape.start, tape.end):
        week_open = calendar.week_open(first).day
        if week_open < tape.start:  # the window starts after this week's short entry
            continue
        expiry = calendar.week_final(first).day
        low, high = tape.span(week_open, week_open)
        band = Band(Region.NEAR_MONEY, low, high, Pad(PUT_PAD_STEPS), Pad(PUT_PAD_STEPS))
        yield _Part(expiry, Right.PUT, week_open, week_open, (band,))


def _monthly_calls(calendar: SessionCalendar, tape: _Tape, sigma: float) -> Iterator[_Part]:
    """A long can be entered on any session (E-L1 retries daily; X-L1/X-L2 re-enter), so a
    monthly is fetched from the first window session it is a candidate on, to its expiry or the
    window's end, whichever comes first."""
    first_candidate: dict[date, date] = {}
    for session in calendar.sessions(tape.start, tape.end):
        for expiry in _long_candidates(calendar, session.day):
            first_candidate.setdefault(expiry, session.day)
    for expiry, start in sorted(first_candidate.items()):
        end = min(expiry, tape.end)
        bands = _long_bands(calendar, tape, sigma, expiry, start, end)
        yield _Part(expiry, Right.CALL, start, end, bands)


def nearest_monthly(calendar: SessionCalendar, day: date, dte: int = LONG_TARGET_DTE) -> date:
    """The monthly expiry nearest `dte` calendar days after `day`; a tie goes to the later one.

    It sizes what is fetched and what the probes ask. E-L2's own tie-break is DEC-29's.
    """
    near = calendar.monthly_expiries(day + _NEAREST_FROM * _DAY, day + _NEAREST_TO * _DAY)
    return min(near, key=lambda m: (abs((m - day).days - dte), -(m - day).days))


def _long_candidates(calendar: SessionCalendar, day: date) -> set[date]:
    """Monthlies 120-270 DTE on `day`, plus the one nearest 180 DTE (E-L2, both variants)."""
    near = calendar.monthly_expiries(day + LONG_MIN_DTE * _DAY, day + LONG_MAX_DTE * _DAY)
    return {*near, nearest_monthly(calendar, day)}


def _long_bands(
    calendar: SessionCalendar,
    tape: _Tape,
    sigma: float,
    expiry: date,
    start: date,
    end: date,
) -> tuple[Band, ...]:
    """The union over the unit's weeks of [weekLow * exp(-2.0 sigma-hat sqrt(T)), weekHigh], with T
    from each week's first session in the unit to the expiry, split into `LONG_SEGMENTS` bands.

    The top is the week's high, at the money, so it covers delta 0.70 (quant E-L3's edge) whatever
    the volatility: a delta-based top edge moves deeper as sigma-hat grows, the wrong way to err.
    """
    lows: list[float] = []
    highs: list[Price] = []
    for week in _weeks(calendar, start, end):
        low, high = tape.span(week[0], week[-1])
        root_t = sigma * math.sqrt((expiry - week[0]).days / _YEAR_DAYS)
        lows.append(float(low.to_dollars()) * math.exp(-LONG_DEEP_Z * root_t))
        highs.append(high)
    return _segments(Price.from_dollars(min(lows)), max(highs))


def _segments(low: Price, high: Price) -> tuple[Band, ...]:
    """`low`..`high` cut into `LONG_SEGMENTS` bands of equal price ratio. The outer edges get the
    full pad; the cuts overlap by one step, so no strike falls between two grids."""
    ratio = (float(high.to_dollars()) / float(low.to_dollars())) ** (1 / LONG_SEGMENTS)
    cuts = [
        low,
        *(Price.from_dollars(float(low.to_dollars()) * ratio**i) for i in range(1, LONG_SEGMENTS)),
        high,
    ]
    last = LONG_SEGMENTS - 1
    return tuple(
        Band(
            Region.DEEP_ITM,
            cuts[i],
            cuts[i + 1],
            Pad(LONG_PAD_STEPS if i == 0 else 1),
            Pad(LONG_PAD_STEPS if i == last else 1),
        )
        for i in range(LONG_SEGMENTS)
    )


def _weeks(calendar: SessionCalendar, start: date, end: date) -> list[tuple[date, date]]:
    """The first and last session of each calendar week, clipped to `start`..`end`."""
    weeks: dict[date, list[date]] = {}
    for session in calendar.sessions(start, end):
        monday = session.day - session.day.weekday() * _DAY
        weeks.setdefault(monday, []).append(session.day)
    return [(days[0], days[-1]) for _, days in sorted(weeks.items())]


def _merge(parts: Sequence[_Part]) -> tuple[Unit, ...]:
    """One unit per expiry and right: the dates' hull and every band. A monthly Friday in the
    window can be both a weekly expiry and a long candidate."""
    grouped: dict[tuple[date, Right], list[_Part]] = {}
    for part in parts:
        grouped.setdefault((part.expiry, part.right), []).append(part)
    return tuple(
        Unit(
            f"chains/{expiry:%Y-%m-%d}_{right.value}",
            min(p.start for p in group),
            max(p.end for p in group),
            expiry,
            right,
            tuple(dict.fromkeys(b for p in group for b in p.bands)),
        )
        for (expiry, right), group in sorted(grouped.items())
    )
