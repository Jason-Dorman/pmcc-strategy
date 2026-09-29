"""Unit pulls fetched from `FakeLseg` through the real `LsegProvider`, for cache and loader tests.

One symbol (NVDA), one session (Mon Sep 14 2026) and one weekly (Fri Sep 18 2026 calls), fetched
on Sep 26, so the calls are expired and asked caret first, then live (DEC-45). `FakeLseg`'s bars
start 13:00, 14:00 and 15:00 ET, all session bars.
"""

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta

from pmcc.data.cache import UnitPull, chain_pull, stock_pull
from pmcc.data.discovery import StepMeasure, Unit
from pmcc.data.fetch import BarRequest, Retry, fetch_contracts, fetch_rics
from pmcc.data.provider import Interval
from pmcc.data.ric import RicForm, build_ric
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from tests.fakes.lseg import Bars, FakeLseg, fake_provider

SYMBOL = "NVDA"
STOCK_RIC = "NVDA.O"
FIELDS = ("BID", "ASK", "TRDPRC_1")
DAY = date(2026, 9, 14)
EXPIRY = date(2026, 9, 18)
FETCH_DATE = date(2026, 9, 26)
FETCHED_AT = datetime(2026, 9, 26, 14, 30, tzinfo=UTC)
CHAIN = Unit(f"chains/{EXPIRY:%Y-%m-%d}_C", DAY, DAY, EXPIRY, Right.CALL)
PUTS = Unit(f"chains/{EXPIRY:%Y-%m-%d}_P", DAY, DAY, EXPIRY, Right.PUT)
ALL_FIELDS = ("BID", "ASK", "TRDPRC_1", "OPEN_PRC", "HIGH_1", "LOW_1", "ACVOL_UNS", "NUM_MOVES")
STOCK = Unit("stock", DAY, DAY)

STOCK_BARS: Bars = {
    "BID": [180.01, 180.11, 180.21],
    "ASK": [180.03, 180.13, 180.23],
    "TRDPRC_1": [180.02, 180.12, 180.22],
}


def option_bars(bump: float = 0.0) -> Bars:
    """Three bars; the last has no values, so LSEG leaves it out."""
    return {
        "BID": [1.0 + bump, 1.1, None],
        "ASK": [1.2 + bump, 1.3, None],
        "TRDPRC_1": [1.1, None, None],
    }


def call(strike: int) -> OptionId:
    return OptionId(SYMBOL, EXPIRY, Right.CALL, Price.from_dollars(strike))


def put(strike: int) -> OptionId:
    return OptionId(SYMBOL, EXPIRY, Right.PUT, Price.from_dollars(strike))


def request(unit: Unit, fields: Sequence[str] = FIELDS) -> BarRequest:
    return BarRequest(tuple(fields), unit.start, unit.end + timedelta(days=1), Interval.HOURLY)


def market(
    listed: Mapping[int, Bars],
    form: RicForm = RicForm.EXPIRED,
    stock: Bars | None = STOCK_BARS,
    index: Sequence[datetime] | None = None,
    puts: Mapping[int, Bars] | None = None,
) -> FakeLseg:
    """The stock, the calls at `listed` strikes and the puts at `puts` strikes, each listed under
    `form`'s RIC."""
    rics: dict[str, Bars] = {build_ric(call(k), form): bars for k, bars in listed.items()}
    rics.update({build_ric(put(k), form): bars for k, bars in (puts or {}).items()})
    if stock is not None:
        rics[STOCK_RIC] = stock
    return FakeLseg(listed=rics) if index is None else FakeLseg(listed=rics, index=index)


def pull_chain(
    fake: FakeLseg,
    strikes: Sequence[int],
    fetched_at: datetime = FETCHED_AT,
    unit: Unit = CHAIN,
    steps: Sequence[int] = (),
    symbol: str = SYMBOL,
    fields: Sequence[str] = FIELDS,
    increments: Sequence[StepMeasure] = (),
) -> UnitPull:
    """`strikes` of the unit's expiry and right, asked as a real fetch asks them."""
    assert unit.expiry is not None
    assert unit.right is not None
    options = [OptionId(SYMBOL, unit.expiry, unit.right, Price.from_dollars(k)) for k in strikes]
    asked = request(unit, fields)
    result = fetch_contracts(
        fake_provider(fake), options, asked, FETCH_DATE, retry=Retry(sleep=_no_wait)
    )
    return chain_pull(symbol, unit, asked, steps, options, result, fetched_at, increments)


def pull_stock(
    fake: FakeLseg,
    fetched_at: datetime = FETCHED_AT,
    unit: Unit = STOCK,
    symbol: str = SYMBOL,
    fields: Sequence[str] = FIELDS,
) -> UnitPull:
    asked = request(unit, fields)
    result = fetch_rics(fake_provider(fake), [STOCK_RIC], asked, retry=Retry(sleep=_no_wait))
    return stock_pull(symbol, unit, asked, result, fetched_at)


def _no_wait(_: float) -> None:
    return None
