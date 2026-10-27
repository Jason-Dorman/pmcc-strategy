"""The wheel's market: one symbol's cache, with the wheel's puts in place of the PMCC's (WD-11).

The PMCC's cache gives the stock tape and the weekly calls the covered calls are sold from. Its put
units hold only each week's first session near the money, for the PMCC's expected move, so the
wheel leaves them out and reads its own: every session of each week to expiry, from
`data_cache/{SYM}/wheel/`. The data-manifest hash covers exactly the units the wheel reads.

Every week of the window must have its put unit and its call unit: a week whose data is missing
would otherwise read as an empty chain, and be logged as a rule's skip (no liquid put, no call at
the cost basis) when it is a data gap. A gap stops the load instead.
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import final

from pmcc.data.cache import STOCK_UNIT, WHEEL_PART, CacheError, SymbolCache, data_manifest_hash
from pmcc.data.load import load_chains, load_symbol, verified_units
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import Right
from pmcc.engine.market_view import MarketData


@final
@dataclass(frozen=True, slots=True)
class WheelMarket:
    data: MarketData
    data_manifest_hash: str


def load_wheel_market(
    root: Path,
    symbol: str,
    option_root: str,
    calendar: SessionCalendar,
    rate: float,
    window: tuple[date, date],
) -> WheelMarket:
    """`root/{symbol}/`'s stock and calls with `root/{symbol}/wheel/`'s puts, priced at `rate`.
    Raises `CacheError` for a cache its sidecars don't describe, or one missing any week of
    `window`'s put or call unit."""
    pmcc = load_symbol(root, symbol, calendar)
    puts = load_chains(SymbolCache(root, symbol, part=WHEEL_PART), calendar)
    calls = {key: frame for key, frame in pmcc.chains.items() if key[1] is Right.CALL}
    chains = {**calls, **puts.chains}
    _check_weeks(chains.keys(), calendar, window, root / symbol)
    read = [u for u in verified_units(SymbolCache(root, symbol))
            if u.name == STOCK_UNIT or u.right is Right.CALL]  # fmt: skip
    entries = [e for u in (*read, *puts.units) for e in u.entries]
    data = MarketData.build(pmcc.stock, chains, calendar, rate, option_root)
    return WheelMarket(data, data_manifest_hash(entries))


def _check_weeks(
    held: Collection[tuple[date, Right]],
    calendar: SessionCalendar,
    window: tuple[date, date],
    where: Path,
) -> None:
    missing = [
        f"{expiry} {right.name.lower()}s"
        for s in calendar.sessions(*window)
        if calendar.week_open(s.day).day == s.day
        for expiry in (calendar.week_final(s.day).day,)
        for right in (Right.PUT, Right.CALL)
        if (expiry, right) not in held
    ]
    if missing:
        raise CacheError(
            f"{where} has no weekly unit for {', '.join(missing)}: the wheel needs every week's "
            "puts (`pmcc fetch --wheel`) and calls (`pmcc fetch`)"
        )
