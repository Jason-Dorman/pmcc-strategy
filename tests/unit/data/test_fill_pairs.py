"""The fill-assumption check's sample (P6-07; PO, DEC-64): which bars pair a print with a mid, and
which group each joins.

Sep 18 2026 is a monthly expiry and a weekly one. Labor Day closes Mon Sep 7, so its weekly's
dates begin on Tue Sep 8, the prior week's first session (DEC-16): from then on its bars are
shorts, and before then longs.
"""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from pathlib import Path

import polars as pl
import pytest

from pmcc.config.calendar import load_calendar
from pmcc.data.cache import CachedBand, CachedUnit, SymbolCache
from pmcc.data.discovery import Region
from pmcc.data.fillcheck import LONGS, SHORTS, FillSample, fill_pairs
from pmcc.data.load import SymbolData, load_symbol
from pmcc.domain.clock import ET
from pmcc.domain.instruments import Right
from pmcc.domain.money import Price
from pmcc.domain.quotes import Quote
from tests.fixtures.synthetic.market import generate
from tests.fixtures.synthetic.scenarios import random_walk

CAL = load_calendar()
WINDOW = (date(2026, 3, 30), date(2026, 9, 25))
MONTHLY = date(2026, 9, 18)
NEXT = date(2026, 9, 25)
LONG_DAY, WEEKLY_DAY = date(2026, 9, 4), date(2026, 9, 14)

# bar end, strike ($), BID, ASK, TRDPRC_1, session bar, valid quote
type Row = tuple[datetime, int, float, float, float | None, bool, bool]


def at(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=ET)


def row(end: datetime, strike: int = 100, bid: float = 1.00, ask: float = 1.10,
        trade: float | None = 1.06, session: bool = True, valid: bool = True) -> Row:  # fmt: skip
    return (end, strike, bid, ask, trade, session, valid)


def chain(rows: Sequence[Row]) -> pl.DataFrame:
    """A loaded chain's columns, prices in $0.0001 units."""
    columns = list(zip(*rows, strict=True)) if rows else [()] * 7
    units = [[None if v is None else round(v * 10_000) for v in c] for c in columns[2:5]]
    return pl.DataFrame(
        {
            "bar_end": pl.Series(columns[0], dtype=pl.Datetime("us", "America/New_York")),
            "strike_cents": pl.Series([s * 100 for s in columns[1]], dtype=pl.Int64),
            **{f: pl.Series(u, dtype=pl.Int64) for f, u in zip(("BID", "ASK", "TRDPRC_1"), units,
                                                               strict=True)},
            "session_bar": pl.Series(columns[5], dtype=pl.Boolean),
            "valid_quote": pl.Series(columns[6], dtype=pl.Boolean),
        }
    )  # fmt: skip


def unit(expiry: date, right: Right = Right.CALL, bands: Sequence[CachedBand] = ()) -> CachedUnit:
    name = f"chains/{expiry}_{right.value}"
    return CachedUnit(name, f"{name}.parquet", "", expiry, right, WINDOW[0], expiry, (),
                      tuple(bands))  # fmt: skip


def pairs(chains: dict[CachedUnit, Sequence[Row]]) -> dict[str, FillSample]:
    frames = {_key(u): chain(rows) for u, rows in chains.items()}
    return fill_pairs(SymbolData("NVDA", pl.DataFrame(), frames, CAL, ""), list(chains), WINDOW)


def _key(u: CachedUnit) -> tuple[date, Right]:
    assert u.expiry is not None
    assert u.right is not None
    return u.expiry, u.right


def units(dollars: Sequence[float]) -> tuple[int, ...]:
    return tuple(round(d * 10_000) for d in dollars)


def test_p6_07_a_pair_is_a_session_bar_in_the_window_with_a_print_and_a_valid_quote() -> None:
    found = pairs({unit(MONTHLY): [
        row(at(WEEKLY_DAY, 11)),
        row(at(WEEKLY_DAY, 12), trade=None),  # no trade in the bar
        row(at(WEEKLY_DAY, 13), valid=False),
        row(at(WEEKLY_DAY, 17), session=False),  # after the close
        row(at(date(2026, 9, 8), 10), trade=1.04),  # the weekly's first date
        row(at(LONG_DAY, 11), trade=1.08),
        row(at(date(2026, 3, 27), 11)),  # before the window
    ]})  # fmt: skip

    assert found[SHORTS] == FillSample(units([1.05, 1.05]), units([1.04, 1.06]), units([0.1, 0.1]))
    assert found[LONGS] == FillSample(units([1.05]), units([1.08]), units([0.1]))


@pytest.mark.parametrize(("bid", "ask"), [(10_000, 10_001), (10_001, 10_002), (10_000, 10_500)])
def test_p6_07_mid_rounds_half_even_as_a_fill_at_mid_does(bid: int, ask: int) -> None:
    found = pairs({unit(MONTHLY): [row(at(WEEKLY_DAY, 11), bid=bid / 1e4, ask=ask / 1e4)]})

    assert found[SHORTS].mid == (Quote(Price(bid), Price(ask)).mid.units,)
    assert found[SHORTS].spread == (ask - bid,)


def test_p6_07_a_merged_unit_splits_its_strikes_by_band() -> None:
    """As fetched, deep bands come three to a unit (LONG_SEGMENTS), so the limits are the lowest
    near-money floor and the highest deep top. Near-money $95 to $105 on $2.50 floors at 4 steps
    under, $85 ($100 to $110 would floor at $90). Deep $40 to $60, $60 to $80 and $80 to $100 on $5
    top out at 2 steps over: $70, $90 and $110. So a $80 call two weeks from expiry isn't a short,
    and a $115 one is no long."""
    near = (_band(Region.NEAR_MONEY, 95, 105, 250), _band(Region.NEAR_MONEY, 100, 110, 250))
    deep = tuple(_band(Region.DEEP_ITM, low, low + 20, 500) for low in (40, 60, 80))
    strikes = {WEEKLY_DAY: (80, 85, 120), LONG_DAY: (80, 110, 115)}
    # Each row trades at its strike in cents, so a pair's trade names its strike.
    rows = [row(at(d, 11), strike=k, trade=k / 100) for d, ks in strikes.items() for k in ks]

    merged = pairs({unit(MONTHLY, bands=(*near, *deep)): rows})
    alone = pairs({unit(MONTHLY, bands=near): rows})

    assert (merged[SHORTS].trade, merged[LONGS].trade) == (units([0.85, 1.20]), units([0.80, 1.10]))
    assert alone[SHORTS].trade == units([0.80, 0.85, 1.20])  # one region: every strike
    assert alone[LONGS].trade == units([0.80, 1.10, 1.15])


def _band(region: Region, low: int, high: int, step: int) -> CachedBand:
    return CachedBand(region, Price.from_dollars(low), Price.from_dollars(high), step, None)


def test_p6_07_puts_are_left_out() -> None:
    found = pairs({unit(MONTHLY, Right.PUT): [row(at(WEEKLY_DAY, 11))]})

    assert found[SHORTS] == found[LONGS] == FillSample((), (), ())


def test_p6_07_pairs_are_ordered_by_bar_then_expiry_then_strike() -> None:
    found = pairs({
        unit(NEXT): [row(at(WEEKLY_DAY, 11), strike=90, trade=1.01)],
        unit(MONTHLY): [row(at(WEEKLY_DAY, 12), trade=1.02), row(at(WEEKLY_DAY, 11), strike=95,
                        trade=1.03), row(at(WEEKLY_DAY, 11), strike=90, trade=1.04)],
    })  # fmt: skip

    assert found[SHORTS].trade == units([1.04, 1.03, 1.01, 1.02])


def test_p6_07_pairs_match_a_plain_reading_of_a_synthetic_cache(tmp_path: Path) -> None:
    """An oracle over every row of the cache: weekly calls (prior week's open to expiry) are
    shorts, the monthlies (never weekly expiries here) longs."""
    spec = random_walk()
    generate(spec, tmp_path)
    data = load_symbol(tmp_path, spec.symbol, CAL)
    cached = SymbolCache(tmp_path, spec.symbol).units()
    window = (spec.window_start, spec.window_end)

    found = fill_pairs(data, cached, window)

    # Each pair keyed by its bar, expiry and strike: (key, (mid, trade, spread)).
    expected: dict[str, list[tuple[tuple[datetime, date, int], tuple[int, int, int]]]] = {
        SHORTS: [], LONGS: []}  # fmt: skip
    for u in cached:
        if u.expiry is None or u.right is not Right.CALL:
            continue
        weekly_from = CAL.week_open(u.expiry - timedelta(days=7)).day
        for r in data.chains[(u.expiry, u.right)].iter_rows(named=True):
            end: datetime = r["bar_end"]
            if not (r["session_bar"] and r["valid_quote"] and r["TRDPRC_1"] is not None
                    and window[0] <= end.date() <= window[1]):  # fmt: skip
                continue
            mid = Quote(Price(r["BID"]), Price(r["ASK"])).mid.units
            group = SHORTS if end.date() >= weekly_from else LONGS
            expected[group].append(((end, u.expiry, r["strike_cents"]),
                                    (mid, r["TRDPRC_1"], r["ASK"] - r["BID"])))  # fmt: skip
    for group, rows in expected.items():
        rows.sort(key=lambda e: e[0])
        assert rows, group
        mid, trade, spread = (tuple(e[1][i] for e in rows) for i in range(3))
        assert found[group] == FillSample(mid, trade, spread)
