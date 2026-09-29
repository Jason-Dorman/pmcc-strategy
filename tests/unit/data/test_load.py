"""`load_symbol`: FakeProvider data round-trips through the cache into `bar_end`-keyed frames with
integer prices, session bars and quote validity (ARCHITECTURE §6.5); a cache its sidecars don't
describe is refused (DEC-46)."""

import json
import math
import shutil
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import polars as pl
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pmcc.config.calendar import load_calendar
from pmcc.data.cache import CacheError, SymbolCache
from pmcc.data.calendar import CalendarMismatchError
from pmcc.data.discovery import Unit
from pmcc.data.load import SymbolData, cached_stock, load_symbol, quantize
from pmcc.data.provider import Interval
from pmcc.data.ric import RicForm, build_ric
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET, bar_end
from pmcc.domain.instruments import Right
from pmcc.domain.money import Price
from tests.fakes.lseg import Bars, FakeLseg
from tests.fakes.pulls import (
    ALL_FIELDS,
    CHAIN,
    DAY,
    EXPIRY,
    PUTS,
    STOCK,
    STOCK_BARS,
    SYMBOL,
    call,
    market,
    option_bars,
    pull_chain,
    pull_stock,
)

CALENDAR = load_calendar()


def _cached(root: Path, fake: FakeLseg | None = None, strikes: tuple[int, ...] = (100,)) -> None:
    fake = fake or market({k: option_bars() for k in strikes})
    cache = SymbolCache(root, SYMBOL)
    cache.write_unit(pull_stock(fake))
    cache.write_unit(pull_chain(fake, list(strikes)))


def _load(root: Path, calendar: SessionCalendar = CALENDAR) -> SymbolData:
    return load_symbol(root, SYMBOL, calendar)


# --- Round trip -------------------------------------------------------------------------------


def test_load_round_trips_fake_provider_stock_prices(tmp_path: Path) -> None:
    _cached(tmp_path)
    stock = _load(tmp_path).stock
    for field in ("BID", "ASK", "TRDPRC_1"):
        expected = [Price.from_dollars(v).units for v in STOCK_BARS[field] if v is not None]
        assert stock[field].to_list() == expected
    assert stock.schema["BID"] == pl.Int64


def test_load_round_trips_fake_provider_chain(tmp_path: Path) -> None:
    _cached(tmp_path)
    data = _load(tmp_path)
    assert list(data.chains) == [(EXPIRY, Right.CALL)]
    chain = data.chains[(EXPIRY, Right.CALL)]
    assert chain["ric"].unique().to_list() == [build_ric(call(100), RicForm.EXPIRED)]
    assert chain.select("expiry", "strike_cents", "right").unique().rows() == [
        (EXPIRY, 10_000, "C")
    ]
    assert chain["BID"].to_list() == [10_000, 11_000]
    assert chain["ASK"].to_list() == [12_000, 13_000]
    assert chain["TRDPRC_1"].to_list() == [11_000, None]


def test_load_adds_bar_end_in_new_york(tmp_path: Path) -> None:
    _cached(tmp_path)
    stock = _load(tmp_path).stock
    assert stock.schema["bar_end"] == pl.Datetime("us", "America/New_York")
    starts: list[datetime] = stock["bar_start_utc"].to_list()
    ends: list[datetime] = stock["bar_end"].to_list()
    assert ends == [bar_end(s) for s in starts]
    assert [e.astimezone(ET).hour for e in ends] == [14, 15, 16]


def test_load_hash_is_the_manifests(tmp_path: Path) -> None:
    _cached(tmp_path)
    manifest = json.loads(SymbolCache(tmp_path, SYMBOL).manifest_path.read_bytes())
    assert _load(tmp_path).data_manifest_hash == manifest["data_manifest_hash"]


def test_load_keeps_the_calendar(tmp_path: Path) -> None:
    _cached(tmp_path)
    assert _load(tmp_path).calendar is CALENDAR


# --- Session bars -----------------------------------------------------------------------------

# UTC bar starts on Mon Sep 14 2026 (EDT, UTC-4): 08:00, 09:00, 15:00 and 16:00 ET.
EDGES = (
    datetime(2026, 9, 14, 12),
    datetime(2026, 9, 14, 13),
    datetime(2026, 9, 14, 19),
    datetime(2026, 9, 14, 20),
)


def test_load_tags_session_bars(tmp_path: Path) -> None:
    """Pre-market and the 16:00 stub are kept, but only 10:00-16:00 bar ends are session bars."""
    bars: Bars = {"BID": [180.0] * 4, "ASK": [180.1] * 4, "TRDPRC_1": [180.05] * 4}
    fake = market({100: {"BID": [1.0] * 4, "ASK": [1.2] * 4}}, stock=bars, index=EDGES)
    _cached(tmp_path, fake)
    stock = _load(tmp_path).stock
    ends = [e.hour for e in stock["bar_end"].to_list()]
    assert list(zip(ends, stock["session_bar"].to_list(), strict=True)) == [
        (9, False),
        (10, True),
        (16, True),
        (17, False),
    ]


def test_load_tags_session_bars_on_a_half_day(tmp_path: Path) -> None:
    """Fri Nov 27 2026 closes at 13:00 (EST, UTC-5): the 13:00-14:00 bar isn't a session bar."""
    day = date(2026, 11, 27)
    index = (datetime(2026, 11, 27, 17), datetime(2026, 11, 27, 18))  # 12:00 and 13:00 ET
    stock_unit = Unit("stock", day, day)
    bars: Bars = {"BID": [180.0] * 2, "ASK": [180.1] * 2, "TRDPRC_1": [180.05] * 2}
    fake = market({}, stock=bars, index=index)
    SymbolCache(tmp_path, SYMBOL).write_unit(pull_stock(fake, unit=stock_unit))
    stock = _load(tmp_path).stock
    assert stock["session_bar"].to_list() == [True, False]


# --- Quote validity (LDG §4.7) ----------------------------------------------------------------


def test_load_marks_quote_validity(tmp_path: Path) -> None:
    index = tuple(datetime(2026, 9, 14, h) for h in (14, 15, 16, 17, 18))
    quotes: Bars = {
        "BID": [1.0, 1.0, 0.0, 1.3, None],
        "ASK": [1.2, 1.0, 1.2, 1.2, 1.2],
    }
    stock: Bars = {"BID": [180.0] * 5, "ASK": [180.1] * 5, "TRDPRC_1": [180.05] * 5}
    _cached(tmp_path, market({100: quotes}, stock=stock, index=index))
    chain = _load(tmp_path).chains[(EXPIRY, Right.CALL)]
    # valid; ASK = BID is valid; BID of 0; crossed; no BID
    assert chain["valid_quote"].to_list() == [True, True, False, False, False]


# --- A cache its sidecars don't describe ------------------------------------------------------


def test_load_refuses_a_changed_parquet(tmp_path: Path) -> None:
    _cached(tmp_path)
    path = SymbolCache(tmp_path, SYMBOL).parquet_path(CHAIN.name)
    path.write_bytes(path.read_bytes() + b"\0")
    with pytest.raises(CacheError, match="changed"):
        _load(tmp_path)


def test_load_refuses_a_missing_parquet(tmp_path: Path) -> None:
    _cached(tmp_path)
    SymbolCache(tmp_path, SYMBOL).parquet_path(CHAIN.name).unlink()
    with pytest.raises(CacheError, match="missing"):
        _load(tmp_path)


def test_load_refuses_a_parquet_with_no_sidecar(tmp_path: Path) -> None:
    _cached(tmp_path)
    SymbolCache(tmp_path, SYMBOL).sidecar_path(CHAIN.name).unlink()
    with pytest.raises(CacheError, match="no sidecar"):
        _load(tmp_path)


def test_load_needs_the_stock_unit(tmp_path: Path) -> None:
    SymbolCache(tmp_path, SYMBOL).write_unit(pull_chain(market({100: option_bars()}), [100]))
    with pytest.raises(CacheError, match="no stock unit"):
        _load(tmp_path)


def test_load_stops_when_the_tape_misses_a_session(tmp_path: Path) -> None:
    """The stock unit asked Mon-Tue, but bars came back for Monday only (DEC-33)."""
    two_days = Unit("stock", DAY, date(2026, 9, 15))
    SymbolCache(tmp_path, SYMBOL).write_unit(pull_stock(market({}), unit=two_days))
    with pytest.raises(CalendarMismatchError, match="2026-09-15"):
        _load(tmp_path)


def test_load_ignores_units_moved_aside(tmp_path: Path) -> None:
    _cached(tmp_path)
    cache = SymbolCache(tmp_path, SYMBOL)
    aside = cache.dir / "superseded"
    aside.mkdir()
    for path in (cache.parquet_path(CHAIN.name), cache.sidecar_path(CHAIN.name)):
        shutil.move(path, aside / path.name)
    data = _load(tmp_path)
    assert data.chains == {}
    assert data.stock.height == len(STOCK_BARS["BID"])


# --- Quantizing (DEC-44) ----------------------------------------------------------------------


@given(st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False))
def test_load_quantize_matches_price_for_any_float(value: float) -> None:
    assert quantize(pl.Series([value])).to_list() == [Price.from_dollars(value).units]


@given(st.integers(min_value=0, max_value=10**10))
def test_load_quantize_matches_price_on_half_units(tenth_mills: int) -> None:
    """Five decimals ending in 5 sit on a half unit, where float scaling can round the wrong way."""
    value = float(Decimal(tenth_mills * 10 + 5).scaleb(-5))
    assert quantize(pl.Series([value])).to_list() == [Price.from_dollars(value).units]


def test_load_quantize_rounds_half_even() -> None:
    assert quantize(pl.Series([1.00005, 1.00015, 2.675])).to_list() == [10_000, 10_002, 26_750]


def test_load_quantize_keeps_nulls_and_nans_as_null() -> None:
    assert quantize(pl.Series([1.5, None, math.nan])).to_list() == [15_000, None, None]


def test_load_quantize_refuses_infinity() -> None:
    with pytest.raises(ValueError, match="infinite"):
        quantize(pl.Series("BID", [math.inf]))


def test_load_quantize_empty() -> None:
    assert quantize(pl.Series("BID", [], dtype=pl.Float64)).to_list() == []


def test_load_reads_the_sidecars_not_the_manifest(tmp_path: Path) -> None:
    _cached(tmp_path)
    manifest = SymbolCache(tmp_path, SYMBOL).manifest_path
    expected = json.loads(manifest.read_bytes())["data_manifest_hash"]
    manifest.write_bytes(b"{}")
    assert _load(tmp_path).data_manifest_hash == expected


# --- Review regressions (DEC-87) --------------------------------------------------------------


def test_load_quantizes_every_price_field_and_keeps_volumes_float(tmp_path: Path) -> None:
    def bars(base: float) -> Bars:
        prices = {f: [base + 0.01 * i for i in range(3)] for f in ALL_FIELDS[:6]}
        return {**prices, "ACVOL_UNS": [100.0, 250.0, 7.0], "NUM_MOVES": [3.0, 5.0, 1.0]}

    fake = market({100: bars(1.0)}, stock=bars(180.0))
    cache = SymbolCache(tmp_path, SYMBOL)
    cache.write_unit(pull_stock(fake, fields=ALL_FIELDS))
    cache.write_unit(pull_chain(fake, [100], fields=ALL_FIELDS))
    data = _load(tmp_path)
    for frame, base in ((data.stock, 180.0), (data.chains[(EXPIRY, Right.CALL)], 1.0)):
        for field in ("BID", "ASK", "TRDPRC_1", "OPEN_PRC", "HIGH_1", "LOW_1"):
            assert frame.schema[field] == pl.Int64, field
            assert frame[field].to_list() == [
                Price.from_dollars(base + 0.01 * i).units for i in range(3)
            ]
        assert frame.schema["ACVOL_UNS"] == pl.Float64
        assert frame["ACVOL_UNS"].to_list() == [100.0, 250.0, 7.0]
        assert frame.schema["NUM_MOVES"] == pl.Float64


# Fri Oct 30 2026 (EDT, UTC-4) and Mon Nov 2 2026 (EST, UTC-5): ET starts 08, 09, 15 and 16 on each.
DST = (
    datetime(2026, 10, 30, 12),
    datetime(2026, 10, 30, 13),
    datetime(2026, 10, 30, 19),
    datetime(2026, 10, 30, 20),
    datetime(2026, 11, 2, 13),
    datetime(2026, 11, 2, 14),
    datetime(2026, 11, 2, 20),
    datetime(2026, 11, 2, 21),
)


def test_load_tags_session_bars_on_every_day_across_a_clock_change(tmp_path: Path) -> None:
    bars: Bars = {"BID": [180.0] * 8, "ASK": [180.1] * 8, "TRDPRC_1": [180.05] * 8}
    unit = Unit("stock", date(2026, 10, 30), date(2026, 11, 2))
    SymbolCache(tmp_path, SYMBOL).write_unit(
        pull_stock(market({}, stock=bars, index=DST), unit=unit)
    )
    stock = _load(tmp_path).stock
    tagged = [
        (e.day, e.hour, s) for e, s in zip(stock["bar_end"], stock["session_bar"], strict=True)
    ]
    assert tagged == [
        (30, 9, False),
        (30, 10, True),
        (30, 16, True),
        (30, 17, False),
        (2, 9, False),
        (2, 10, True),
        (2, 16, True),
        (2, 17, False),
    ]


def test_load_refuses_a_changed_stock_parquet(tmp_path: Path) -> None:
    _cached(tmp_path)
    path = SymbolCache(tmp_path, SYMBOL).parquet_path(STOCK.name)
    path.write_bytes(path.read_bytes() + b"\0")
    with pytest.raises(CacheError, match="changed"):
        _load(tmp_path)


def test_load_refuses_a_missing_stock_parquet(tmp_path: Path) -> None:
    _cached(tmp_path)
    SymbolCache(tmp_path, SYMBOL).parquet_path(STOCK.name).unlink()
    with pytest.raises(CacheError, match="missing"):
        _load(tmp_path)


def test_load_stops_when_the_tape_misses_its_first_session(tmp_path: Path) -> None:
    """The stock unit asked Mon-Tue, but bars came back for Tuesday only (DEC-33)."""
    tuesday = (datetime(2026, 9, 15, 17), datetime(2026, 9, 15, 18), datetime(2026, 9, 15, 19))
    two_days = Unit("stock", DAY, date(2026, 9, 15))
    SymbolCache(tmp_path, SYMBOL).write_unit(pull_stock(market({}, index=tuesday), unit=two_days))
    with pytest.raises(CalendarMismatchError, match="2026-09-14"):
        _load(tmp_path)


def test_load_keys_calls_and_puts_of_one_expiry_apart(tmp_path: Path) -> None:
    fake = market({100: option_bars()}, puts={95: option_bars(bump=0.5)})
    cache = SymbolCache(tmp_path, SYMBOL)
    cache.write_unit(pull_stock(fake))
    cache.write_unit(pull_chain(fake, [100]))
    cache.write_unit(pull_chain(fake, [95], unit=PUTS))
    chains = _load(tmp_path).chains
    assert sorted(chains) == [(EXPIRY, Right.CALL), (EXPIRY, Right.PUT)]
    assert chains[(EXPIRY, Right.CALL)]["right"].unique().to_list() == ["C"]
    assert chains[(EXPIRY, Right.PUT)]["right"].unique().to_list() == ["P"]
    assert chains[(EXPIRY, Right.PUT)]["BID"].to_list() == [15_000, 11_000]


@pytest.mark.parametrize("value", [2923251.30005, 1234567.89015, -2923251.30005, 99_999_999.99995])
def test_load_quantize_matches_price_on_large_values(value: float) -> None:
    """Above ~$1M plain float scaling rounds some half units wrongly; the exact path mustn't."""
    assert quantize(pl.Series([value])).to_list() == [Price.from_dollars(value).units]


@given(st.integers(min_value=-(10**13), max_value=10**13))
def test_load_quantize_matches_price_on_half_units_of_any_size(tenth_mills: int) -> None:
    value = float(Decimal(tenth_mills * 10 + 5).scaleb(-5))
    assert quantize(pl.Series([value])).to_list() == [Price.from_dollars(value).units]


# --- The cached stock tape, for a resumed fetch's plan (P1-08) ---------------------------------


def test_load_cached_stock_gives_back_the_rows_the_provider_returned(tmp_path: Path) -> None:
    pull = pull_stock(market({}), fields=ALL_FIELDS)
    cache = SymbolCache(tmp_path, SYMBOL)
    cache.write_unit(pull)

    unit, history = cached_stock(cache)

    assert unit.name == "stock"
    assert history.interval is Interval.HOURLY
    assert history.rows.equals(pull.history.rows)


def test_load_cached_stock_refuses_a_changed_parquet(tmp_path: Path) -> None:
    _cached(tmp_path)
    cache = SymbolCache(tmp_path, SYMBOL)
    path = cache.parquet_path("stock")
    path.write_bytes(path.read_bytes() + b"!")

    with pytest.raises(CacheError, match="changed"):
        cached_stock(cache)


def test_load_cached_stock_needs_a_stock_unit(tmp_path: Path) -> None:
    SymbolCache(tmp_path, SYMBOL).write_unit(pull_chain(market({100: option_bars()}), [100]))

    with pytest.raises(CacheError, match="no stock unit"):
        cached_stock(SymbolCache(tmp_path, SYMBOL))
