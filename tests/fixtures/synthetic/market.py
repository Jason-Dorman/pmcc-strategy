"""A deterministic synthetic market, written in the cache format (TEST-STRATEGY §5).

`generate(spec, root)` writes one symbol's cache under `root/{symbol}/`: a stock unit and one unit
per expiry and right, each a parquet and a sidecar written by `SymbolCache.write_unit`, as a fetch
writes them. So `load_symbol`, the pricer, MarketView and the engine read it exactly as they read
LSEG's data.

- **Sessions** come from the shipped calendar (`configs/calendar.yaml`), so a window can hold a
  Monday holiday (Labor Day), a Friday holiday (Jul 3) and a half-day (Nov 27 2026).
- **Spot** is a seeded random walk, or a scripted path of knots (`SpotPath`) that scenarios use to
  force one behaviour. The stock quotes a cent either side of it and trades at it.
- **Options** are Black-Scholes prices from an IV surface (`IvSurface`: a base, a weekly and a
  monthly level, per-expiry overrides such as an event bump), quoted as mid ± a half-spread that is
  a share of the price (`SpreadModel`), rounded out to whole cents. A bid under a cent is a zero
  bid: no valid quote, as LDG §4.7 has it.
- **Microstructure:** random holes (no BID/ASK) at `hole_rate`, trade prints on `trade_rate` of the
  option bars, and hooks that rewrite any contract-bar's quote or drop its row (scenarios).
- **Units** follow the fetch plan's shape (ARCHITECTURE §6.3), simplified: weekly calls from the
  prior week's open to the expiry, puts on the expiry's week, and monthly calls over the window.
  The stock tape starts `warmup_sessions` before the window, for RV20.

The same spec and seed write byte-identical files: nothing reads the clock or an unseeded RNG.
"""

import math
from bisect import bisect_left
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl

from pmcc.config.calendar import load_calendar
from pmcc.data.cache import SymbolCache, UnitPull
from pmcc.data.discovery import Unit
from pmcc.data.fetch import BarRequest
from pmcc.data.provider import Interval, RawHistory, raw_schema
from pmcc.data.ric import RicForm, build_ric, occ_symbol
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import BAR, ET, at_et
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.domain.sessions import Session
from pmcc.pricing.black_scholes import price
from pmcc.pricing.expiry import years_to_expiry

type FloatArray = npt.NDArray[np.float64]
type Cell = float | None
type QuoteHook = Callable[[OptionId, datetime, Cell, Cell], tuple[Cell, Cell] | None]
"""(contract, bar_end, bid, ask) → the (bid, ask) to write, or None for no row at all."""
type StockHook = Callable[[datetime, float], tuple[Cell, Cell, Cell]]
"""(bar_end, spot) → the stock's (bid, ask, trade) on that bar."""

FIELDS = ("BID", "ASK", "TRDPRC_1")
RATE = 0.0371  # the universe's r (DEC-11)
BARS_PER_YEAR = 252 * 7
FETCHED_AT = datetime(2027, 12, 1, 12, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class SpotPath:
    """Spot at chosen times, linear in bar count between knots and flat outside them. A knot sits
    on the first bar ending at or after its time."""

    knots: tuple[tuple[datetime, float], ...]

    def along(self, bar_ends: Sequence[datetime]) -> FloatArray:
        xs = [min(bisect_left(bar_ends, t), len(bar_ends) - 1) for t, _ in self.knots]
        if xs != sorted(xs):
            raise ValueError("knots must be in time order")
        return np.interp(np.arange(len(bar_ends)), xs, [s for _, s in self.knots])


def knot(day: date, hour: int, spot: float) -> tuple[datetime, float]:
    """A knot at the bar ending `hour`:00 ET on `day`."""
    return datetime.combine(day, time(hour), tzinfo=ET), spot


@dataclass(frozen=True, slots=True)
class IvSurface:
    base: float = 0.30
    weekly: float | None = None  # weeklies' level, if not the base
    monthly: float | None = None  # monthlies' level, if not the base
    by_expiry: Mapping[date, float] = field(default_factory=dict[date, float])

    def level(self, expiry: date, is_monthly: bool) -> float:
        if expiry in self.by_expiry:
            return self.by_expiry[expiry]
        kind = self.monthly if is_monthly else self.weekly
        return self.base if kind is None else kind


@dataclass(frozen=True, slots=True)
class SpreadModel:
    """Half-spread as a share of the price, with a floor in dollars."""

    weekly_half: float = 0.02  # a 4% spread: inside E-T1's 10%
    monthly_half: float = 0.005  # a 1% spread: inside E-T1's 3%
    min_half: float = 0.01


@dataclass(frozen=True, slots=True)
class SyntheticSpec:
    window_start: date
    window_end: date
    symbol: str = "SYN"
    seed: int = 7
    warmup_sessions: int = 22
    spot: float = 100.0
    drift: float = 0.0
    vol: float = 0.30
    path: SpotPath | None = None
    iv: IvSurface = IvSurface()
    spreads: SpreadModel = SpreadModel()
    hole_rate: float = 0.0
    trade_rate: float = 0.3
    weekly_step: float = 1.0
    monthly_step: float = 5.0
    monthly_dte: tuple[int, int] = (90, 280)  # nearest 180 DTE, and X-L2 below 90
    quote_hook: QuoteHook | None = None
    stock_hook: StockHook | None = None
    extended_hours: bool = False  # also write a pre-market and a post-close bar each session


@dataclass(frozen=True, slots=True)
class Market:
    """What `generate` wrote: the sessions, bar ends and spot per bar, and every unit."""

    spec: SyntheticSpec
    calendar: SessionCalendar
    bar_ends: tuple[datetime, ...]
    spots: FloatArray
    units: tuple[Unit, ...]

    def spot_at(self, t: datetime) -> float:
        return float(self.spots[self.bar_ends.index(t)])


def generate(spec: SyntheticSpec, root: Path) -> Market:
    """Write `spec`'s market to `root/{symbol}/` and describe it."""
    calendar = load_calendar()
    rng = np.random.Generator(np.random.PCG64(spec.seed))
    sessions = (
        *calendar.sessions_before(spec.window_start, spec.warmup_sessions),
        *calendar.sessions(spec.window_start, spec.window_end),
    )
    bar_ends = tuple(end for s in sessions for end in s.bar_ends())
    spots = _spots(spec, bar_ends, rng)
    tape_ends, tape_spots = _tape(spec, sessions, bar_ends, spots)
    cache = SymbolCache(root, spec.symbol)
    stock = Unit("stock", sessions[0].day, sessions[-1].day)
    cache.write_unit(_stock_pull(spec, stock, tape_ends, tape_spots))
    units = [stock]
    for unit, strikes in _option_units(spec, calendar, bar_ends, spots):
        pull = _option_pull(spec, calendar, unit, strikes, tape_ends, tape_spots, rng)
        cache.write_unit(pull)
        units.append(unit)
    return Market(spec, calendar, bar_ends, spots, tuple(units))


def _tape(
    spec: SyntheticSpec,
    sessions: Sequence[Session],
    bar_ends: Sequence[datetime],
    spots: FloatArray,
) -> tuple[tuple[datetime, ...], FloatArray]:
    """The bars written: the session bars, plus with `extended_hours` a bar ending 09:00 (pre-
    market, at the session's first spot) and one ending an hour after the close (post-close, at
    its last spot). Neither is a session bar, so nothing may read them (DEC-06)."""
    if not spec.extended_hours:
        return tuple(bar_ends), spots
    by_end = dict(zip(bar_ends, spots.tolist(), strict=True))
    tape = dict(by_end)
    for s in sessions:
        ends = s.bar_ends()
        tape[at_et(s.day, time(9))] = by_end[ends[0]]
        tape[ends[-1] + BAR] = by_end[ends[-1]]
    ordered = sorted(tape)
    return tuple(ordered), np.array([tape[t] for t in ordered])


def _spots(
    spec: SyntheticSpec, bar_ends: Sequence[datetime], rng: np.random.Generator
) -> FloatArray:
    if spec.path is not None:
        return np.round(spec.path.along(bar_ends), 2)
    dt = 1.0 / BARS_PER_YEAR
    steps = (spec.drift - 0.5 * spec.vol**2) * dt + spec.vol * math.sqrt(dt) * rng.standard_normal(
        len(bar_ends)
    )
    steps[0] = 0.0
    return np.round(spec.spot * np.exp(np.cumsum(steps)), 2)


# --- Units --------------------------------------------------------------------------------------


def _option_units(
    spec: SyntheticSpec,
    calendar: SessionCalendar,
    bar_ends: Sequence[datetime],
    spots: FloatArray,
) -> list[tuple[Unit, tuple[float, ...]]]:
    window = [(t, s) for t, s in zip(bar_ends, spots, strict=True) if t.date() >= spec.window_start]
    units: list[tuple[Unit, tuple[float, ...]]] = []
    weeklies = calendar.weekly_expiries(spec.window_start, spec.window_end + timedelta(days=7))
    for expiry in weeklies:
        first = max(calendar.week_open(expiry - timedelta(days=7)).day, spec.window_start)
        last = min(expiry, spec.window_end)
        span = [s for t, s in window if first <= t.date() <= last]
        if not span:
            continue
        low, high = min(span) - 10.0, max(span) + 15.0
        calls = _grid(low, high, spec.weekly_step)
        units.append((_unit(expiry, Right.CALL, first, last), calls))
        opens = [s for t, s in window if t.date() == calendar.week_open(expiry).day]
        if opens and calendar.week_open(expiry).day <= spec.window_end:
            atm = round(opens[0] / spec.weekly_step) * spec.weekly_step
            puts = tuple(atm + i * spec.weekly_step for i in range(-5, 6))
            week = calendar.week_open(expiry).day
            units.append((_unit(expiry, Right.PUT, week, min(expiry, spec.window_end)), puts))
    lo_dte, hi_dte = spec.monthly_dte
    monthlies = calendar.monthly_expiries(
        spec.window_start + timedelta(days=lo_dte), spec.window_end + timedelta(days=hi_dte)
    )
    all_spots = [s for _, s in window]
    for expiry in monthlies:
        if expiry in weeklies:
            continue
        strikes = _grid(0.5 * min(all_spots), 1.1 * max(all_spots), spec.monthly_step)
        last = min(expiry, spec.window_end)
        units.append((_unit(expiry, Right.CALL, spec.window_start, last), strikes))
    return units


def _unit(expiry: date, right: Right, first: date, last: date) -> Unit:
    return Unit(f"chains/{expiry:%Y-%m-%d}_{right.value}", first, last, expiry, right)


def _grid(low: float, high: float, step: float) -> tuple[float, ...]:
    start = max(math.floor(low / step), 1)
    stop = math.ceil(high / step)
    return tuple(round(i * step, 2) for i in range(start, stop + 1))


# --- Pulls --------------------------------------------------------------------------------------


def _request(unit: Unit) -> BarRequest:
    return BarRequest(FIELDS, unit.start, unit.end + timedelta(days=1), Interval.HOURLY)


def _stock_pull(
    spec: SyntheticSpec, unit: Unit, bar_ends: Sequence[datetime], spots: FloatArray
) -> UnitPull:
    ric = f"{spec.symbol}.O"
    rows: list[tuple[datetime, str, str, float]] = []
    for t, s in zip(bar_ends, spots, strict=True):
        spot = float(s)
        cells = (spec.stock_hook or _stock_cells)(t, spot)
        rows.extend(_cells(t, ric, cells))
    return _pull(spec, unit, rows, {ric: ric}, {}, {})


def _stock_cells(_: datetime, spot: float) -> tuple[Cell, Cell, Cell]:
    return round(spot - 0.01, 2), round(spot + 0.01, 2), spot


def _option_pull(
    spec: SyntheticSpec,
    calendar: SessionCalendar,
    unit: Unit,
    strikes: Sequence[float],
    bar_ends: Sequence[datetime],
    spots: FloatArray,
    rng: np.random.Generator,
) -> UnitPull:
    assert unit.expiry is not None
    assert unit.right is not None
    expiry, right = unit.expiry, unit.right
    ends = [t for t in bar_ends if unit.start <= t.date() <= unit.end]
    first = bar_ends.index(ends[0])
    s = spots[first : first + len(ends)]
    is_monthly = calendar.monthly_expiry(expiry.year, expiry.month) == expiry
    iv = spec.iv.level(expiry, is_monthly)
    session = calendar.session(expiry)
    years = np.array([years_to_expiry(t, session) for t in ends])
    half_share = spec.spreads.monthly_half if is_monthly else spec.spreads.weekly_half
    rows: list[tuple[datetime, str, str, float]] = []
    answered: dict[str, str] = {}
    unanswered: dict[str, tuple[str, ...]] = {}
    forms: dict[str, RicForm] = {}
    for k in strikes:
        option = OptionId(spec.symbol, expiry, right, Price.from_dollars(k))
        form = RicForm.EXPIRED if expiry < FETCHED_AT.date() else RicForm.LIVE
        ric = build_ric(option, form)
        values = _values(s, k, years, iv, right)
        bids, asks = _quotes(values, half_share, spec.spreads.min_half)
        holes = rng.random(len(ends)) < spec.hole_rate
        trades = rng.random(len(ends)) < spec.trade_rate
        wrote = False
        for i, t in enumerate(ends):
            quote: tuple[Cell, Cell] | None = (None, None) if holes[i] else (bids[i], asks[i])
            if spec.quote_hook is not None:
                quote = spec.quote_hook(option, t, *quote)
            if quote is None:
                continue
            trade = round(float(values[i]), 2) if trades[i] and values[i] >= 0.01 else None
            rows.extend(_cells(t, ric, (quote[0], quote[1], trade)))
            wrote = True
        if wrote:
            answered[occ_symbol(option)], forms[ric] = ric, form
        else:
            unanswered[occ_symbol(option)] = (ric,)
    return _pull(spec, unit, rows, answered, unanswered, forms)


def _values(s: FloatArray, k: float, years: FloatArray, iv: float, right: Right) -> FloatArray:
    live = years > 0
    intrinsic = np.maximum(s - k, 0.0) if right is Right.CALL else np.maximum(k - s, 0.0)
    if not live.any():
        return intrinsic
    priced = price(s[live], k, years[live], RATE, iv, right is Right.CALL)
    out = intrinsic.copy()
    out[live] = priced
    return out


def _quotes(
    values: FloatArray, half_share: float, min_half: float
) -> tuple[list[Cell], list[Cell]]:
    half = np.maximum(values * half_share, min_half)
    bids = np.floor((values - half) * 100 + 1e-9) / 100
    asks = np.ceil((values + half) * 100 - 1e-9) / 100
    bids = np.where(bids < 0.01, 0.0, bids)
    return [round(float(b), 2) for b in bids], [round(float(a), 2) for a in asks]


def _cells(
    t: datetime, ric: str, cells: tuple[Cell, Cell, Cell]
) -> list[tuple[datetime, str, str, float]]:
    start = (t - BAR).astimezone(UTC)
    return [(start, ric, f, v) for f, v in zip(FIELDS, cells, strict=True) if v is not None]


def _pull(
    spec: SyntheticSpec,
    unit: Unit,
    rows: list[tuple[datetime, str, str, float]],
    answered: Mapping[str, str],
    unanswered: Mapping[str, tuple[str, ...]],
    forms: Mapping[str, RicForm],
) -> UnitPull:
    schema = raw_schema(Interval.HOURLY)
    frame = pl.DataFrame(rows, schema=schema, orient="row")
    return UnitPull(
        symbol=spec.symbol,
        unit=unit,
        request=_request(unit),
        steps=(),
        history=RawHistory(Interval.HOURLY, frame),
        answered=answered,
        unanswered=unanswered,
        ric_form_used=forms,
        misses={},
        errors=(),
        fetched_at=FETCHED_AT,
    )
