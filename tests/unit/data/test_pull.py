"""P1-08's unit loop over a synthetic market behind the port (`tests/fakes/market.py`).

The window is one week, Mon Sep 14 to Fri Sep 18 2026, fetched on Sun Sep 27: 1 stock unit, 2
weekly call units (Sep 18 and the next, Sep 25), 1 put unit and 5 monthly call units. The market
lists $1 strikes within $20 of spot ($180) and $5 strikes beyond, so every weekly band asks strikes
that aren't listed, and the long bands' steps differ.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import structlog
from structlog.testing import capture_logs

from pmcc.config.calendar import load_calendar
from pmcc.data.cache import STOCK_UNIT, SymbolCache
from pmcc.data.coverage import coverage
from pmcc.data.discovery import Band, FetchPlan, Pad, Region, StepSource, Unit, UnitKind, unit_kind
from pmcc.data.fetch import Retry
from pmcc.data.load import load_symbol
from pmcc.data.provider import Interval, ProviderOutageError
from pmcc.data.pull import (
    FIELDS,
    PlanError,
    Prepared,
    Target,
    check_strikes,
    measure_step,
    prepare,
    pull_unit,
    pull_units,
)
from pmcc.data.ric import parse_ric
from pmcc.domain.clock import ET
from pmcc.domain.instruments import Right
from pmcc.domain.money import Price
from tests.fakes.market import FakeMarket

CAL = load_calendar()
NOW = datetime(2026, 9, 27, 12, tzinfo=ET)
WINDOW = (date(2026, 9, 14), date(2026, 9, 18))
TARGET = Target("NVDA", "NVDA.O", "NVDA")
NO_WAIT = Retry(sleep=lambda _: None)
FALLBACK = {Region.NEAR_MONEY: 250, Region.DEEP_ITM: 500}
_DAY = timedelta(days=1)


def _market(**kwargs: Any) -> FakeMarket:
    return FakeMarket(CAL, NOW.date(), hourly_from=date(2026, 3, 1), **kwargs)


def _clock() -> datetime:
    return NOW


def _prepare(
    market: FakeMarket, cache: SymbolCache, window: tuple[date, date] = WINDOW
) -> Prepared:
    return prepare(market, cache, CAL, TARGET, window, _clock, retry=NO_WAIT)


def _pull(market: FakeMarket, cache: SymbolCache, prepared: Prepared) -> tuple[str, ...]:
    return pull_units(market, cache, prepared, FALLBACK, _clock, retry=NO_WAIT)


def _fetch(market: FakeMarket, cache: SymbolCache) -> tuple[str, ...]:
    return _pull(market, cache, _prepare(market, cache))


def _unit_of(ric: str) -> str:
    """The unit an option RIC belongs to, or the stock unit."""
    try:
        option = parse_ric(ric).option
    except ValueError:
        return STOCK_UNIT
    return f"chains/{option.expiry:%Y-%m-%d}_{option.right.value}"


def _units_asked(market: FakeMarket, since: int = 0) -> set[str]:
    return {_unit_of(ric) for rics, *_ in market.requests[since:] for ric in rics}


def _files(cache: SymbolCache) -> dict[str, bytes]:
    return {p.relative_to(cache.dir).as_posix(): p.read_bytes() for p in cache.dir.rglob("*.*")}


@pytest.fixture
def cache(tmp_path: Path) -> SymbolCache:
    return SymbolCache(tmp_path, "NVDA")


# --- The plan: the stock tape only ------------------------------------------------------------


def test_pull_prepare_asks_for_the_stock_tape_only_and_writes_nothing(cache: SymbolCache) -> None:
    market = _market()

    prepared = _prepare(market, cache)

    assert [r[0] for r in market.requests] == [("NVDA.O",)]
    (_, fields, start, end_exclusive, interval) = market.requests[0]
    assert interval is Interval.HOURLY
    assert (start, end_exclusive) == (prepared.plan.units[0].start, WINDOW[1] + _DAY)
    assert {"HIGH_1", "LOW_1", "TRDPRC_1", "BID", "ASK"} <= set(fields)
    assert prepared.stock is not None
    assert not cache.dir.exists()


def test_pull_prepare_plans_the_window(cache: SymbolCache) -> None:
    prepared = _prepare(_market(), cache)

    kinds = [unit_kind(u.right, {b.region for b in u.bands}) for u in prepared.pending]
    assert (kinds.count(UnitKind.WEEKLY_CALLS), kinds.count(UnitKind.PUTS)) == (2, 1)
    assert kinds.count(UnitKind.MONTHLY_CALLS) == 5
    assert len(prepared.plan.units) == 1 + len(prepared.pending)
    assert prepared.cached == 0


def test_pull_prepare_refuses_a_stock_tape_that_does_not_answer(cache: SymbolCache) -> None:
    market = _market(stocks=("NVDA.N",))

    with pytest.raises(PlanError, match=r"NVDA\.O answered no hourly bars"):
        _prepare(market, cache)


def test_pull_prepare_plans_from_the_cached_tape_without_asking(cache: SymbolCache) -> None:
    first = _prepare(_market(), cache)
    _pull(_market(), cache, first)
    market = _market(spot=250.0)  # a different market: a fresh tape would plan other bands

    again = _prepare(market, cache)

    assert market.calls == 0
    assert again.plan == first.plan
    assert (again.stock, again.pending, again.cached) == (None, (), len(first.plan.units))


def test_pull_prepare_refuses_a_cached_stock_unit_of_another_window(cache: SymbolCache) -> None:
    _fetch(_market(), cache)
    market = _market()

    with pytest.raises(PlanError, match="cached stock unit covers"):
        _prepare(market, cache, (date(2026, 9, 21), date(2026, 9, 25)))
    assert market.calls == 0


def test_pull_prepare_refuses_cached_units_another_plan_wrote(cache: SymbolCache) -> None:
    _fetch(_market(), cache)
    aside = cache.dir / "superseded"
    aside.mkdir()
    for suffix in (".parquet", ".sidecar.json"):
        (cache.dir / f"stock{suffix}").rename(aside / f"stock{suffix}")
    market = _market(spot=190.0)  # a new tape, so new bands

    with pytest.raises(PlanError, match="wouldn't write") as raised:
        _prepare(market, cache)

    assert "chains/2026-09-18_C" in str(raised.value)
    assert _units_asked(market) == {STOCK_UNIT}  # no option was asked


def test_pull_prepare_refuses_a_cached_unit_outside_the_plan(cache: SymbolCache) -> None:
    _fetch(_market(), cache)
    later = SymbolCache(cache.root / "later", "NVDA")
    _pull(_market(), later, _prepare(_market(), later, (date(2026, 9, 21), date(2026, 9, 25))))
    for suffix in (".parquet", ".sidecar.json"):  # the Oct 2 weekly: not in this plan
        name = f"chains/2026-10-02_C{suffix}"
        (cache.dir / name).write_bytes((later.dir / name).read_bytes())
    market = _market()

    with pytest.raises(PlanError, match="2026-10-02_C"):
        _prepare(market, cache)
    assert market.calls == 0


# --- The unit loop ----------------------------------------------------------------------------


def test_pull_units_writes_every_planned_unit_stock_first(cache: SymbolCache) -> None:
    market = _market()
    prepared = _prepare(market, cache)

    written = _pull(market, cache, prepared)

    assert written == tuple(u.name for u in prepared.plan.units)
    assert set(cache.unit_names()) == set(written)
    data = load_symbol(cache.root, "NVDA", CAL)
    assert len(data.chains) == len(prepared.pending)


def test_pull_unit_asks_each_contract_hourly_over_its_unit_dates(cache: SymbolCache) -> None:
    market = _market()
    prepared = _prepare(market, cache)
    _pull(market, cache, prepared)

    hourly = [r for r in market.requests[1:] if r[4] is Interval.HOURLY]
    for unit in prepared.pending:
        asked = [r for r in hourly if _unit_of(r[0][0]) == unit.name]
        assert asked, unit.name
        assert {(r[2], r[3]) for r in asked} == {(unit.start, unit.end + _DAY)}


def test_pull_unit_asks_the_union_of_its_bands_ladders_on_their_steps(cache: SymbolCache) -> None:
    _fetch(_market(), cache)

    (monthly,) = [u for u in cache.units() if u.name == "chains/2027-01-15_C"]
    steps = [b.step for b in monthly.bands]
    assert steps == [500, 500, 100]  # $5 grid deep, $1 within $20 of spot
    assert [b.source for b in monthly.bands] == [StepSource.MEASURED] * 3
    strikes = {int(e.instrument[-8:]) // 10 for e in monthly.entries}  # OCC: $0.001 units
    assert {17_500, 17_900, 18_000} <= strikes  # $179 is on the $1 band only
    assert 13_900 not in strikes  # nor on a $5 band: $139 is off both grids


def test_pull_units_log_events_carry_the_symbol_and_unit(cache: SymbolCache) -> None:
    market = _market()
    prepared = _prepare(market, cache)

    with capture_logs(processors=[structlog.contextvars.merge_contextvars]) as logs:
        _pull(market, cache, prepared)

    unanswered = [e for e in logs if e["event"] == "fetch.ric.unanswered"]
    assert unanswered
    assert all(e["symbol"] == "NVDA" and e["unit"] == _unit_of(e["ric"]) for e in unanswered)
    done = [e["unit"] for e in logs if e["event"] == "fetch.unit.done"]
    assert done == [u.name for u in prepared.pending]


# --- Resume after an outage (P1-08 done-when) -------------------------------------------------


@pytest.mark.parametrize("served", [1, 2, 40, 150, 300])
def test_pull_resume_after_an_outage_refetches_only_the_missing_units(
    cache: SymbolCache, served: int
) -> None:
    dying = _market(dies_after=served)
    with pytest.raises(ProviderOutageError):
        _fetch(dying, cache)
    cached = set(cache.unit_names())
    before = _files(cache)
    fresh = _prepare(_market(), SymbolCache(cache.root / "fresh", "NVDA"))
    planned = {u.name for u in fresh.plan.units}
    assert cached < planned  # stopped part way
    assert not cache.orphans()
    assert not list(cache.root.rglob("*.partial"))  # the unit in flight left nothing

    market = _market()
    written = _fetch(market, cache)

    assert set(written) == planned - cached
    assert _units_asked(market) == planned - cached  # no request for a cached unit
    assert set(cache.unit_names()) == planned
    after = _files(cache)
    assert {k: after[k] for k in before if k != "manifest.json"} == {
        k: v for k, v in before.items() if k != "manifest.json"
    }
    load_symbol(cache.root, "NVDA", CAL)


def test_pull_outage_in_the_stock_tape_writes_nothing(cache: SymbolCache) -> None:
    with pytest.raises(ProviderOutageError):
        _fetch(_market(dies_after=0), cache)

    assert not cache.dir.exists()


# --- Strike steps (DEC-14; PO, 2026-09-28) ----------------------------------------------------

EXPIRY = date(2026, 9, 18)
NEAR = Band(Region.NEAR_MONEY, Price.from_dollars(178), Price.from_dollars(182), Pad(4), Pad(6))
WEEKLY = Unit("chains/2026-09-18_C", date(2026, 9, 8), EXPIRY, EXPIRY, Right.CALL, (NEAR,))


def _measure(market: FakeMarket, unit: Unit = WEEKLY, band: Band = NEAR) -> Any:
    return measure_step(market, "NVDA", unit, band, 250, NOW.date(), NO_WAIT)


def test_pull_step_is_measured_at_the_anchor_on_the_units_last_session() -> None:
    market = _market()

    measure = _measure(market)

    assert (measure.source, measure.step, measure.anchors) == (StepSource.MEASURED, 100, (18_000,))
    assert measure.session == EXPIRY
    assert {18_000, 18_050, 18_100, 18_250, 18_500} & set(measure.answered) == {
        18_000,
        18_100,
        18_500,
    }


def test_pull_step_asks_daily_bars_a_day_wider_each_side() -> None:
    market = _market()

    _measure(market)

    assert {(r[2], r[3], r[4]) for r in market.requests} == {
        (EXPIRY - _DAY, EXPIRY + 2 * _DAY, Interval.DAILY)
    }
    assert {r[1] for r in market.requests} == {("BID", "ASK")}


def test_pull_step_tries_the_neighbour_anchors_when_the_anchor_is_unlisted() -> None:
    market = _market(unlisted={18_000})

    measure = _measure(market)

    assert measure.source is StepSource.NEIGHBOUR
    assert measure.anchors == (18_000, 17_000, 19_000)
    assert measure.step == 100


def test_pull_step_takes_the_finer_neighbour_step_never_the_anchors() -> None:
    # $170 reads $1 ($171 is listed). Hiding $191 makes $190 read $5 ($195), and hiding $181
    # makes the unanswered $180's own offsets read $5 ($185): only the lower neighbour gives $1.
    market = _market(unlisted={18_000, 18_100, 19_100})

    measure = _measure(market)

    assert (measure.source, measure.step) == (StepSource.NEIGHBOUR, 100)
    assert {18_500, 17_000, 17_100, 19_000, 19_500} <= set(measure.answered)  # both asks kept


def test_pull_step_asks_both_neighbours_in_one_request() -> None:
    market = _market(unlisted={18_000})

    _measure(market)

    strikes = [{parse_ric(ric).option.strike_cents for ric in r[0]} for r in market.requests]
    assert any({17_000, 19_000} <= asked for asked in strikes)


def test_pull_step_falls_back_to_the_probe_report_and_says_so() -> None:
    market = _market(unlisted={17_000, 18_000, 19_000})

    with capture_logs() as logs:
        measure = _measure(market)

    assert (measure.source, measure.step, measure.measured) == (
        StepSource.PROBE_REPORT,
        250,
        False,
    )
    assert measure.anchors == (18_000, 17_000, 19_000)
    [event] = [e for e in logs if e["event"] == "fetch.increment.unmeasured"]
    assert event["anchors_cents"] == [18_000, 17_000, 19_000]
    assert event["step_cents"] == 250


def test_pull_step_ignores_a_strike_first_listed_after_the_session() -> None:
    # Jun 17 2027 lists 280 days before, on Thu Sep 10 2026; asked on Wed Sep 9, the widened
    # daily request sees its Sep 10 bar, which says nothing about Sep 9.
    expiry, day = date(2027, 6, 17), date(2026, 9, 9)
    deep = Band(Region.DEEP_ITM, Price.from_dollars(175), Price.from_dollars(185), Pad(2), Pad(2))
    unit = Unit("chains/2027-06-17_C", date(2026, 9, 8), day, expiry, Right.CALL, (deep,))
    market = _market()

    measure = _measure(market, unit, deep)

    assert market.requests  # it did ask, and the answers carried bars
    assert measure.source is StepSource.PROBE_REPORT
    assert measure.answered == ()


def test_pull_unmeasured_band_is_recorded_in_the_sidecar(cache: SymbolCache) -> None:
    market = _market(unlisted={17_000, 18_000, 19_000})

    _fetch(market, cache)

    (weekly,) = [u for u in cache.units() if u.name == "chains/2026-09-18_C"]
    assert [(b.source, b.step) for b in weekly.bands] == [(StepSource.PROBE_REPORT, 250)]


def test_pull_unmeasured_band_takes_its_own_regions_fallback() -> None:
    expiry = date(2027, 1, 15)
    deep = Band(Region.DEEP_ITM, Price.from_dollars(175), Price.from_dollars(185), Pad(2), Pad(2))
    unit = Unit("chains/2027-01-15_C", WINDOW[0], WINDOW[1], expiry, Right.CALL, (deep,))
    market = _market(unlisted={17_000, 18_000, 19_000})

    pull = pull_unit(market, TARGET, unit, FALLBACK, NOW.date(), _clock, retry=NO_WAIT)

    assert pull.steps == (FALLBACK[Region.DEEP_ITM],)
    assert pull.increments[0].source is StepSource.PROBE_REPORT
    hourly = [r for r in market.requests if r[4] is Interval.HOURLY]
    strikes = {parse_ric(ric).option.strike_cents for r in hourly for ric in r[0]}
    assert strikes
    assert all(k % 500 == 0 for k in strikes)


# --- The window, the strike field and the fields (review of P1-08) ----------------------------


@pytest.mark.parametrize(
    "window",
    [
        (date(2026, 9, 14), date(2026, 9, 19)),  # ends on a Saturday
        (date(2026, 8, 31), date(2026, 9, 7)),  # ends on Labor Day
        (date(2026, 9, 13), date(2026, 9, 18)),  # starts on a Sunday
        (date(2026, 9, 18), date(2026, 9, 14)),  # reversed
    ],
)
def test_pull_prepare_refuses_a_window_not_between_sessions_before_asking(
    cache: SymbolCache, window: tuple[date, date]
) -> None:
    market = _market()

    with pytest.raises(PlanError, match="window"):
        _prepare(market, cache, window)

    assert market.calls == 0


def test_pull_prepare_refuses_strikes_past_the_ric_field_before_any_option(
    cache: SymbolCache,
) -> None:
    market = _market(spot=990.0)

    with pytest.raises(PlanError, match=r"\$999\.99"):
        _prepare(market, cache)

    assert _units_asked(market) == {STOCK_UNIT}


def test_pull_prepare_stock_tape_events_carry_the_symbol_and_unit(cache: SymbolCache) -> None:
    market = _market(stocks=("NVDA.N",))

    merged = [structlog.contextvars.merge_contextvars]
    with capture_logs(processors=merged) as logs, pytest.raises(PlanError):
        _prepare(market, cache)

    [event] = [e for e in logs if e["event"] == "fetch.ric.unanswered"]
    assert (event["ric"], event["symbol"], event["unit"]) == ("NVDA.O", "NVDA", STOCK_UNIT)


def test_pull_asks_every_dec_13_field_on_the_stock_and_the_options(cache: SymbolCache) -> None:
    market = _market()

    _fetch(market, cache)

    assert FIELDS == (
        "BID",
        "ASK",
        "TRDPRC_1",
        "OPEN_PRC",
        "HIGH_1",
        "LOW_1",
        "ACVOL_UNS",
        "NUM_MOVES",
    )
    hourly = [r for r in market.requests if r[4] is Interval.HOURLY]
    assert {_unit_of(r[0][0]) for r in hourly} == set(cache.unit_names())
    assert {r[1] for r in hourly} == {FIELDS}
    assert all(u.fields_returned == tuple(sorted(FIELDS)) for u in cache.units())


def test_pull_asks_expired_contracts_caret_first_and_live_ones_live(cache: SymbolCache) -> None:
    _fetch(_market(), cache)  # fetched Sun Sep 27: the Sep 18 and Sep 25 weeklies have expired

    units = {u.name: u for u in cache.units()}
    for name, form in (("chains/2026-09-18_C", "expired"), ("chains/2027-01-15_C", "live")):
        answered = [e for e in units[name].entries if e.ric is not None]
        assert answered, name
        assert {e.form.value for e in answered if e.form is not None} == {form}


def test_pull_coverage_counts_only_session_bars_over_the_unit_dates(cache: SymbolCache) -> None:
    _fetch(_market(), cache)  # the fake quotes every bar, extended hours and the 16:00 stub too

    cov = coverage(cache.root, "NVDA", CAL)

    for kind, tally in cov.by_kind.items():
        assert tally.expected > 0, kind
        assert tally.valid == tally.expected, kind
    assert cov.near_money.valid == cov.near_money.expected > 0


def test_pull_prepare_refuses_a_cached_unit_with_other_dates(cache: SymbolCache) -> None:
    _fetch(_market(), cache)
    sidecar = cache.sidecar_path("chains/2026-09-25_C")
    record = json.loads(sidecar.read_bytes())
    record["request"]["start"] = "2026-09-15"  # the same bands, another start
    sidecar.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(PlanError, match="2026-09-25_C"):
        _prepare(_market(), cache)


def test_pull_strike_check_uses_the_widest_step_any_band_could_measure() -> None:
    # $985 + 2 steps fits the field on a $1 grid ($987) but not on a $10 one ($1,010).
    band = Band(Region.NEAR_MONEY, Price.from_dollars(980), Price.from_dollars(985), Pad(2), Pad(2))
    unit = Unit("chains/2026-09-18_P", WINDOW[0], WINDOW[0], EXPIRY, Right.PUT, (band,))
    plan = FetchPlan(WINDOW[0], WINDOW[1], 0.4, (unit,))

    assert band.ladder(100)[-1] <= 99_999
    with pytest.raises(PlanError, match="chains/2026-09-18_P"):
        check_strikes(plan)
