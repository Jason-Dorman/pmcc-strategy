"""`pmcc fetch` for one symbol: plan from the stock tape, then the unit loop (ARCHITECTURE §6.1).

It sits above `fetch` and `cache`, since `cache` builds on `fetch`'s results (DEC-87).

1. `prepare` checks that the window runs from one session to a later or equal one, then reads
   the stock tape, from the cache if its unit is there, or else with one request. It checks the
   tape's trading days against the calendar (DEC-33) and plans the units (§6.3). Nothing else is
   asked, so the estimate prints before any option request. Every cached unit must be one the
   plan would write, with the same dates and bands; if one isn't, nothing is asked and the user
   moves it into `superseded/` (DEC-46). A band whose ladder could pass $999.99 stops the plan
   there too (DEC-12).
2. `pull_units` writes the stock unit if `prepare` fetched it, then each unit that has no sidecar
   yet. For each one it measures each band's strike step (DEC-14), asks the band's ladder for
   hourly bars (`fetch_contracts`), and writes the parquet, then the sidecar. An outage raises
   `ProviderOutageError` and loses only the unit in flight. Re-running skips cached units, so it
   resumes where the outage stopped it.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import final

import polars as pl
import structlog

from pmcc.data.cache import STOCK_UNIT, CachedUnit, SymbolCache, UnitPull, chain_pull, stock_pull
from pmcc.data.calendar import sessions_from_tape
from pmcc.data.discovery import (
    NO_OFFSET_INCREMENT_CENTS,
    Band,
    FetchPlan,
    Region,
    StepMeasure,
    StepSource,
    Unit,
    increment_anchor,
    increment_from,
    increment_strikes,
    neighbour_anchors,
    plan_symbol,
    session_ranges,
    stock_unit,
)
from pmcc.data.fetch import BarRequest, Retry, fetch_contracts, fetch_rics
from pmcc.data.load import cached_stock
from pmcc.data.provider import HistoryProvider, Interval, RawHistory
from pmcc.data.ric import MAX_STRIKE
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import to_et
from pmcc.domain.instruments import OptionId
from pmcc.domain.money import UNITS_PER_CENT, Price

# Every field the spec asks for, on the stock and the options (DEC-13).
FIELDS = ("BID", "ASK", "TRDPRC_1", "OPEN_PRC", "HIGH_1", "LOW_1", "ACVOL_UNS", "NUM_MOVES")
STEP_FIELDS = ("BID", "ASK")  # the strike-step asks only need to know a strike is listed
MAX_STRIKE_CENTS = MAX_STRIKE.units // UNITS_PER_CENT
_DAY = timedelta(days=1)

log = structlog.get_logger()

type Clock = Callable[[], datetime]


class PlanError(Exception):
    """No plan can be made (the stock tape didn't answer), or the cache holds units the plan
    wouldn't write."""


@final
@dataclass(frozen=True, slots=True)
class Target:
    """One symbol and the identifiers LSEG knows it by (`configs/universe.yaml`, DEC-12)."""

    symbol: str
    stock_ric: str
    root: str


@final
@dataclass(frozen=True, slots=True)
class Prepared:
    """A symbol's plan, and what is left to fetch.

    `stock` is the stock unit `prepare` fetched, to be written first; `None` when it was cached.
    `pending` holds the chain units with no sidecar yet, in plan order.
    """

    target: Target
    plan: FetchPlan
    stock: UnitPull | None
    pending: tuple[Unit, ...]

    @property
    def cached(self) -> int:
        """Plan units already cached."""
        return len(self.plan.units) - len(self.pending) - (self.stock is not None)


# --- 1. The plan ------------------------------------------------------------------------------


def prepare(
    provider: HistoryProvider,
    cache: SymbolCache,
    calendar: SessionCalendar,
    target: Target,
    window: tuple[date, date],
    clock: Clock,
    *,
    fields: Sequence[str] = FIELDS,
    retry: Retry = Retry(),  # noqa: B008 (frozen, so a shared default is safe)
) -> Prepared:
    """The plan for `window` (first and last session, inclusive, DEC-47), asking for the stock
    tape only, and only when it isn't cached.

    Raises `PlanError`, before asking anything, for a window that doesn't run from a session to
    a later or equal session; and after the stock tape, when the tape doesn't answer, the cache
    holds units from another plan, or a band could reach past $999.99. Raises
    `CalendarMismatchError` when the tape's trading days aren't the calendar's, and
    `ProviderOutageError` when LSEG stops answering.
    """
    start, end = window
    _check_window(calendar, start, end)
    unit = stock_unit(calendar, start, end)
    if cache.has_unit(STOCK_UNIT):
        cached, history = cached_stock(cache)
        _check_same(cached, unit)
        pull = None
    else:
        with structlog.contextvars.bound_contextvars(symbol=target.symbol, unit=STOCK_UNIT):
            pull = _fetch_stock(provider, target, unit, clock(), fields, retry)
        history = pull.history
    sessions = sessions_from_tape(calendar, history.rows["bar_start"], unit.start, unit.end)
    plan = plan_symbol(calendar, session_ranges(history.rows, sessions), start, end)
    _check_cached(cache, plan)
    check_strikes(plan)
    pending = tuple(u for u in plan.units if u.name != STOCK_UNIT and not cache.has_unit(u.name))
    log.info(
        "fetch.plan",
        symbol=target.symbol,
        units=len(plan.units),
        pending=len(pending),
        stock="fetched" if pull is not None else "cached",
        sigma=round(plan.sigma, 4),
    )
    return Prepared(target, plan, pull, pending)


def _check_window(calendar: SessionCalendar, start: date, end: date) -> None:
    """Each unit's strike steps are measured on its last session, often the window's end, so
    both ends must be sessions (DEC-47, DEC-88)."""
    if start > end:
        raise PlanError(f"the window starts {start}, after it ends {end}")
    not_sessions = [d for d in (start, end) if not calendar.is_session(d)]
    if not_sessions:
        raise PlanError(
            f"the window must start and end on sessions; {', '.join(map(str, not_sessions))} "
            "isn't one (a weekend or a holiday in configs/calendar.yaml)"
        )


def _fetch_stock(
    provider: HistoryProvider,
    target: Target,
    unit: Unit,
    fetched_at: datetime,
    fields: Sequence[str],
    retry: Retry,
) -> UnitPull:
    request = BarRequest(tuple(fields), unit.start, unit.end + _DAY, Interval.HOURLY)
    result = fetch_rics(provider, [target.stock_ric], request, retry=retry)
    if target.stock_ric not in result.answered:
        miss = result.misses[target.stock_ric]
        raise PlanError(
            f"{target.stock_ric} answered no hourly bars from {unit.start} to {unit.end} "
            f"({miss.reason.value}: {miss.message}), so there is nothing to plan from"
        )
    return stock_pull(target.symbol, unit, request, result, fetched_at)


def _check_same(cached: CachedUnit, unit: Unit) -> None:
    if (cached.start, cached.end_exclusive) != (unit.start, unit.end + _DAY):
        raise PlanError(
            f"the cached stock unit covers {cached.start} to {cached.end_exclusive - _DAY}, but "
            f"this window's plan needs {unit.start} to {unit.end}. Move the symbol's cached units "
            "into superseded/ to fetch another window (DEC-46)."
        )


def _check_cached(cache: SymbolCache, plan: FetchPlan) -> None:
    """Every cached chain unit must be one the plan would write, with its dates and bands."""
    planned = {u.name: u for u in plan.units}
    stray = [
        c.name
        for c in cache.units()
        if c.name != STOCK_UNIT
        and (c.name not in planned or _shape(c) != _plan_shape(planned[c.name]))
    ]
    if stray:
        raise PlanError(
            f"cached units this plan wouldn't write, or would write with other dates or bands: "
            f"{stray}. Move each one's parquet and sidecar into {cache.dir / 'superseded'} and "
            "fetch again (DEC-46)."
        )


def check_strikes(plan: FetchPlan) -> None:
    """No ladder may pass the RIC's $999.99 strike field (DEC-12). A band's widest ladder is on
    the widest step DEC-14 can find, so this holds whatever the step asks measure."""
    widest = NO_OFFSET_INCREMENT_CENTS
    over = [u.name for u in plan.units for b in u.bands if b.ladder(widest)[-1] > MAX_STRIKE_CENTS]
    if over:
        raise PlanError(
            f"units whose strikes could pass the RIC's $999.99 field: {over}. That is a question "
            "for the PO (DEC-12)."
        )


type _Shape = tuple[date, date, tuple[tuple[Region, Price, Price], ...]]


def _shape(unit: CachedUnit) -> _Shape:
    return unit.start, unit.end_exclusive, tuple((b.region, b.low, b.high) for b in unit.bands)


def _plan_shape(unit: Unit) -> _Shape:
    return unit.start, unit.end + _DAY, tuple((b.region, b.low, b.high) for b in unit.bands)


# --- 2. The unit loop -------------------------------------------------------------------------


def pull_units(
    provider: HistoryProvider,
    cache: SymbolCache,
    prepared: Prepared,
    fallback: Mapping[Region, int],
    clock: Clock,
    *,
    fields: Sequence[str] = FIELDS,
    retry: Retry = Retry(),  # noqa: B008 (frozen, so a shared default is safe)
) -> tuple[str, ...]:
    """Write the stock unit if it was just fetched, then every pending unit; the names written.

    `fallback` is the step, per region, for a band no anchor answers in (the probe report's,
    PO, DEC-14). Raises `ProviderOutageError` when LSEG stops answering: the units already
    written stay, and the one in flight leaves no file.
    """
    written: list[str] = []
    if prepared.stock is not None:
        cache.write_unit(prepared.stock)
        written.append(STOCK_UNIT)
    fetch_date = to_et(clock()).date()
    target = prepared.target
    for unit in prepared.pending:
        with structlog.contextvars.bound_contextvars(symbol=target.symbol, unit=unit.name):
            log.info("fetch.unit.start", start=str(unit.start), end=str(unit.end))
            pull = pull_unit(
                provider, target, unit, fallback, fetch_date, clock, fields=fields, retry=retry
            )
            cache.write_unit(pull)
            log.info(
                "fetch.unit.done",
                requested=len(pull.answered) + len(pull.unanswered),
                answered=len(pull.answered),
                unanswered=len(pull.unanswered),
            )
        written.append(unit.name)
    return tuple(written)


def pull_unit(
    provider: HistoryProvider,
    target: Target,
    unit: Unit,
    fallback: Mapping[Region, int],
    fetch_date: date,
    clock: Clock,
    *,
    fields: Sequence[str] = FIELDS,
    retry: Retry = Retry(),  # noqa: B008 (frozen, so a shared default is safe)
) -> UnitPull:
    """One chain unit: each band's step, then the union of the bands' ladders, hourly."""
    measures = tuple(
        measure_step(provider, target.root, unit, band, fallback[band.region], fetch_date, retry)
        for band in unit.bands
    )
    ladders = (b.ladder(m.step) for b, m in zip(unit.bands, measures, strict=True))
    strikes = sorted({k for ladder in ladders for k in ladder})
    options = [_option(target.root, unit, k) for k in strikes]
    request = BarRequest(tuple(fields), unit.start, unit.end + _DAY, Interval.HOURLY)
    result = fetch_contracts(provider, options, request, fetch_date, retry=retry)
    steps = [m.step for m in measures]
    return chain_pull(target.symbol, unit, request, steps, options, result, clock(), measures)


# --- Strike steps (DEC-14) --------------------------------------------------------------------


def measure_step(
    provider: HistoryProvider,
    root: str,
    unit: Unit,
    band: Band,
    fallback: int,
    fetch_date: date,
    retry: Retry,
) -> StepMeasure:
    """`band`'s strike step, asked on the unit's last session, by which every strike it lists is
    listed.

    The anchor nearest the band's centre and its offsets are asked. If the anchor didn't answer,
    it measured nothing: the anchors $10 either side are asked, and the finest step they show is
    taken. If none answers, the step is `fallback`, flagged unmeasured (PO, DEC-14).
    """
    day = unit.end
    anchor = increment_anchor(band.centre)
    answered = _answering(provider, root, unit, day, (anchor,), fetch_date, retry)
    if anchor in answered:
        step = increment_from(anchor, answered)
        return StepMeasure(day, (anchor,), answered, step, StepSource.MEASURED)
    neighbours = neighbour_anchors(anchor)
    answered = tuple(
        sorted({*answered, *_answering(provider, root, unit, day, neighbours, fetch_date, retry)})
    )
    anchors = (anchor, *neighbours)
    steps = [increment_from(a, answered) for a in neighbours if a in answered]
    if steps:
        return StepMeasure(day, anchors, answered, min(steps), StepSource.NEIGHBOUR)
    log.warning(
        "fetch.increment.unmeasured",
        region=band.region.value,
        session=str(day),
        anchors_cents=list(anchors),
        step_cents=fallback,
    )
    return StepMeasure(day, anchors, answered, fallback, StepSource.PROBE_REPORT)


def _answering(
    provider: HistoryProvider,
    root: str,
    unit: Unit,
    day: date,
    anchors: Sequence[int],
    fetch_date: date,
    retry: Retry,
) -> tuple[int, ...]:
    """The strikes, of each anchor and its offsets, that have a daily bar on `day`.

    Daily requests are a day wider on each side and filtered by date, since LSEG's daily edges
    depend on the request (DEC-47).
    """
    options = [_option(root, unit, k) for a in anchors for k in increment_strikes(a)]
    request = BarRequest(STEP_FIELDS, day - _DAY, day + 2 * _DAY, Interval.DAILY)
    result = fetch_contracts(provider, options, request, fetch_date, retry=retry)
    on_day = _rics_on(result.history, day)
    return tuple(sorted(o.strike_cents for o, ric in result.answered.items() if ric in on_day))


def _rics_on(history: RawHistory, day: date) -> frozenset[str]:
    return frozenset(history.rows.filter(pl.col("bar_start") == day)["ric"].to_list())


def _option(root: str, unit: Unit, strike_cents: int) -> OptionId:
    if unit.expiry is None or unit.right is None:
        raise ValueError(f"unit {unit.name} isn't a chain unit")
    return OptionId(root, unit.expiry, unit.right, Price(strike_cents * UNITS_PER_CENT))
