"""The wheel's market: one symbol's cache, with the wheel's puts in place of the PMCC's (WD-11).

The PMCC's cache gives the stock tape and the weekly calls the covered calls are sold from. Its put
units hold only each week's first session near the money, for the PMCC's expected move, so the
wheel leaves them out and reads its own: every session of each week to expiry, from
`data_cache/{SYM}/wheel/`. The data-manifest hash covers exactly the units the wheel reads.

Every week of the window must have its put unit and its call unit, and every session its stock
bars: a week whose data is missing would otherwise read as an empty chain or no spot, and be logged
as a rule's skip (no liquid put, no call at the cost basis) when it is a data gap. A gap stops the
load instead. The market also names each instrument by the RIC its cache answered with, for the
result's rows (W2-03), and keeps its chains, from which `print_pairs` reads each traded option's
trade prints against its mids for the fill evidence (W3-02).
"""

from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from fractions import Fraction
from pathlib import Path
from typing import final

import polars as pl

from pmcc.config.universe import Window
from pmcc.data.cache import STOCK_UNIT, WHEEL_PART, CacheError, SymbolCache, data_manifest_hash
from pmcc.data.load import load_chains, load_symbol, verified_units
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import to_et
from pmcc.domain.instruments import OptionId, Right
from pmcc.engine.market_view import MarketData
from pmcc.runner import Names, check_tape


@final
@dataclass(frozen=True, slots=True)
class WheelMarket:
    symbol: str
    data: MarketData
    data_manifest_hash: str
    names: Names
    chains: Mapping[tuple[date, Right], pl.DataFrame]


@final
@dataclass(frozen=True, slots=True)
class PrintPairs:
    """One right's pairs, one entry per contract-bar, in $0.0001 units: the mid rounded half-even
    as a fill at mid is, the print, the spread (ASK − BID), and whether BID ≤ print ≤ ASK."""

    mid: tuple[int, ...] = ()
    trade: tuple[int, ...] = ()
    spread: tuple[int, ...] = ()
    within: tuple[bool, ...] = ()


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
    `window`'s put or call unit or any session's stock bars."""
    pmcc = load_symbol(root, symbol, calendar)
    check_tape(pmcc, Window(start=window[0], end=window[1]))
    puts = load_chains(SymbolCache(root, symbol, part=WHEEL_PART), calendar)
    calls = {key: frame for key, frame in pmcc.chains.items() if key[1] is Right.CALL}
    chains = {**calls, **puts.chains}
    _check_weeks(chains.keys(), calendar, window, root / symbol)
    read = [u for u in verified_units(SymbolCache(root, symbol))
            if u.name == STOCK_UNIT or u.right is Right.CALL]  # fmt: skip
    entries = [e for u in (*read, *puts.units) for e in u.entries]
    data = MarketData.build(pmcc.stock, chains, calendar, rate, option_root)
    names = Names.of_frames(symbol, pmcc.stock, chains)
    return WheelMarket(symbol, data, data_manifest_hash(entries), names, chains)


def print_pairs(market: WheelMarket,
                sold: Sequence[tuple[OptionId, datetime]]) -> dict[Right, PrintPairs]:  # fmt: skip
    """Each sold option's session bars from its sale through its expiry session with a trade print
    and a valid quote, by right, in order of bar, expiry and strike."""
    rows: dict[Right, list[tuple[datetime, date, int, int, int, int]]] = {r: [] for r in Right}
    for option, at in sold:
        frame = market.chains[(option.expiry, option.right)].filter(
            (pl.col("strike_cents") == option.strike_cents) & pl.col("session_bar")
            & pl.col("valid_quote") & pl.col("TRDPRC_1").is_not_null()
        )  # fmt: skip
        for end, bid, ask, trade in frame.select("bar_end", "BID", "ASK", "TRDPRC_1").iter_rows():
            if to_et(at) <= end and end.date() <= option.expiry:
                rows[option.right].append(
                    (end, option.expiry, option.strike_cents, bid, ask, trade)
                )
    return {right: _pairs(sorted(found)) for right, found in rows.items()}


def _pairs(rows: Sequence[tuple[datetime, date, int, int, int, int]]) -> PrintPairs:
    return PrintPairs(
        mid=tuple(round(Fraction(bid + ask, 2)) for *_, bid, ask, _ in rows),
        trade=tuple(trade for *_, trade in rows),
        spread=tuple(ask - bid for *_, bid, ask, _ in rows),
        within=tuple(bid <= trade <= ask for *_, bid, ask, trade in rows),
    )


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
