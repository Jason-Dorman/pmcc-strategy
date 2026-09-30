"""MarketView: the look-ahead guard (Spec › Look-ahead guard, ARCHITECTURE §5.2, INV-04).

`MarketData` holds one symbol's loaded frames, priced once, and indexed for reads by time; every
run over the symbol shares it. `MarketData.view(now)` gives the strategy a `HistoricalView`, whose
every accessor passes through one gate, `_as_of`, that raises `LookAheadError` for a time after
`now`. Strategies never get a frame, so this gate is the structural guarantee the Methodology page
cites.

- **Session bars only.** Every read is of a session bar (DEC-06): extended-hours bars never reach a
  rule. A time that isn't a session bar's end has no quote, no spot and an empty chain.
- **Listing is point-in-time (PO, DEC-32).** A contract is listed at t once it has had a valid
  BID/ASK on a session bar at or before t, and it stays listed. A chain shows only listed contracts,
  and an expiry is listed once one of its calls is.
- **The calendar** is reference data published in advance, so it answers for any day (DEC-33).
"""

from bisect import bisect_right
from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import UTC, date, datetime, timedelta
from typing import final

import numpy as np
import numpy.typing as npt
import polars as pl

from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import to_et
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_CENT, Price
from pmcc.domain.quotes import Quote
from pmcc.pricing.chain import PricedQuotes, PricedSymbol, UnitKey, price_symbol
from pmcc.pricing.iv import IvCode
from pmcc.strategy.ports import ChainSnapshot, ExpiryKind, LookAheadError

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MICROSECOND = timedelta(microseconds=1)
_NEVER = np.iinfo(np.int64).max  # a strike that is never listed

type IntArray = npt.NDArray[np.int64]


def micros(t: datetime) -> int:
    """A tz-aware time as whole µs since the epoch: an exact key, whatever its zone."""
    return (to_et(t).astimezone(UTC) - _EPOCH) // _MICROSECOND


@final
@dataclass(frozen=True, slots=True)
class _StockBar:
    trade: Price | None
    quote: Quote | None


@final
@dataclass(frozen=True, slots=True)
class _Expiry:
    expiry: date
    first_listed: int  # µs: the first session bar any of its calls had a valid quote
    kinds: frozenset[ExpiryKind]


@final
class MarketData:
    """One symbol's session bars, priced and indexed by time. Build with `MarketData.build`."""

    def __init__(
        self,
        root: str,
        calendar: SessionCalendar,
        rate: float,
        stock: Mapping[int, _StockBar],
        priced: PricedSymbol,
        listing: Mapping[UnitKey, Mapping[int, int]],
    ) -> None:
        self.root = root
        self.calendar = calendar
        self.rate = rate  # the r its chains are priced at; every run on it must use the same
        self._stock = dict(stock)
        self._priced = priced
        self._listing = {key: dict(strikes) for key, strikes in listing.items()}
        self._closes = _close_trades(calendar, self._stock)
        self._close_keys = [m for m, _, _ in self._closes]
        self._expiries = _expiries(calendar, self._listing)
        self._chains: dict[tuple[int, date, Right], ChainSnapshot] = {}

    @classmethod
    def build(
        cls,
        stock: pl.DataFrame,
        chains: Mapping[UnitKey, pl.DataFrame],
        calendar: SessionCalendar,
        rate: float,
        root: str,
    ) -> "MarketData":
        """From the loader's frames (ARCHITECTURE §6.5): prices every chain once (`price_symbol`)
        and indexes the stock tape and each contract's first listing."""
        return cls(
            root=root,
            calendar=calendar,
            rate=rate,
            stock=_stock_bars(stock),
            priced=price_symbol(stock, chains, calendar, rate),
            listing={key: _first_listed(frame) for key, frame in chains.items()},
        )

    def view(self, now: datetime) -> "HistoricalView":
        return HistoricalView(self, now)

    # Reads by exact time; HistoricalView gates them.

    def stock_bar(self, t: int) -> _StockBar | None:
        return self._stock.get(t)

    def chain(self, t: datetime, expiry: date, right: Right) -> ChainSnapshot:
        key = (micros(t), expiry, right)
        if key not in self._chains:
            self._chains[key] = self._listed_chain(t, *key)
        return self._chains[key]

    def expiries(self, kind: ExpiryKind, t: datetime) -> tuple[date, ...]:
        at, today = micros(t), to_et(t).date()
        return tuple(
            e.expiry
            for e in self._expiries
            if kind in e.kinds and e.first_listed <= at and e.expiry >= today
        )

    def close_trades(self, t: datetime) -> dict[datetime, Price]:
        stop = bisect_right(self._close_keys, micros(t))
        return {end: price for _, end, price in self._closes[:stop]}

    def _listed_chain(self, t: datetime, at: int, expiry: date, right: Right) -> ChainSnapshot:
        """The bar's listed rows. A listed contract stays listed (DEC-32): one with no row on
        this bar is still in the chain, with no quote, so it is never mistaken for unlisted."""
        if not self._is_session_bar(t):
            return ChainSnapshot(expiry, right, to_et(t), _no_rows())
        listing = self._listing.get((expiry, right), {})
        snapshot = self._priced.snapshot(t, expiry, right) or _no_rows()
        firsts = np.array([listing.get(int(k), _NEVER) for k in snapshot.strike], dtype=np.int64)
        rows = snapshot.take(firsts <= at)
        present = set(rows.strike.tolist())
        missing = sorted(k for k, first in listing.items() if first <= at and k not in present)
        if missing:
            rows = _in_strike_order(rows, _unquoted(missing))
        return ChainSnapshot(expiry, right, to_et(t), rows)

    def _is_session_bar(self, t: datetime) -> bool:
        day = to_et(t).date()
        if not self.calendar.first_day <= day <= self.calendar.last_day:
            return False
        return self.calendar.is_session(day) and self.calendar.session(day).contains(t)


@final
class HistoricalView:
    """The `MarketView` a strategy gets on one bar. Every accessor goes through `_as_of`."""

    def __init__(self, data: MarketData, now: datetime) -> None:
        self._data = data
        self._now = to_et(now)

    @property
    def now(self) -> datetime:
        return self._now

    @property
    def root(self) -> str:
        return self._data.root

    def spot(self, at: datetime | None = None) -> Price | None:
        bar = self._data.stock_bar(micros(self._as_of(at)))
        return None if bar is None else bar.trade

    def stock_quote(self, at: datetime | None = None) -> Quote | None:
        bar = self._data.stock_bar(micros(self._as_of(at)))
        return None if bar is None else bar.quote

    def quote(self, option: OptionId, at: datetime | None = None) -> Quote | None:
        if option.root != self._data.root:
            raise ValueError(f"{option.root} isn't this market's option root {self._data.root}")
        chain = self.chain(option.expiry, option.right, at)
        row = chain.row(option.strike)
        return None if row is None else chain.quotes.quote(row)

    def chain(self, expiry: date, right: Right, at: datetime | None = None) -> ChainSnapshot:
        return self._data.chain(self._as_of(at), expiry, right)

    def expiries(self, kind: ExpiryKind, at: datetime | None = None) -> tuple[date, ...]:
        return self._data.expiries(kind, self._as_of(at))

    def close_trades(self, at: datetime | None = None) -> Mapping[datetime, Price]:
        return self._data.close_trades(self._as_of(at))

    def calendar(self) -> SessionCalendar:
        return self._data.calendar

    def _as_of(self, at: datetime | None) -> datetime:
        """The time a read is for: `now`, or an earlier `at`. A later one is look-ahead."""
        t = self._now if at is None else to_et(at)
        if t > self._now:
            raise LookAheadError(
                f"read at {t.isoformat()} from a decision at {self._now.isoformat()} (INV-04)"
            )
        return t


def _stock_bars(stock: pl.DataFrame) -> dict[int, _StockBar]:
    rows = stock.filter(pl.col("session_bar")).select(
        "bar_end", "TRDPRC_1", "BID", "ASK", "valid_quote"
    )
    bars: dict[int, _StockBar] = {}
    for end, trade, bid, ask, valid in rows.iter_rows():
        quote = Quote(Price(bid), Price(ask)) if valid else None
        bars[micros(end)] = _StockBar(None if trade is None else Price(trade), quote)
    return bars


def _first_listed(frame: pl.DataFrame) -> dict[int, int]:
    """Each strike's first session bar with a valid quote, in µs, keyed by $0.0001 units."""
    firsts = (
        frame.filter(pl.col("session_bar") & pl.col("valid_quote"))
        .group_by("strike_cents")
        .agg(pl.col("bar_end").min())
    )
    return {
        int(cents) * UNITS_PER_CENT: micros(first)
        for cents, first in firsts.select("strike_cents", "bar_end").iter_rows()
    }


def _close_trades(
    calendar: SessionCalendar, stock: Mapping[int, _StockBar]
) -> list[tuple[int, datetime, Price]]:
    """Every session's close-bar TRDPRC_1, in time order (DEC-23)."""
    if not stock:
        return []
    first = datetime.fromtimestamp(min(stock) / 1e6, UTC)
    last = datetime.fromtimestamp(max(stock) / 1e6, UTC)
    closes: list[tuple[int, datetime, Price]] = []
    for session in calendar.sessions(to_et(first).date(), to_et(last).date()):
        end = session.close_bar_end
        bar = stock.get(micros(end))
        if bar is not None and bar.trade is not None:
            closes.append((micros(end), end, bar.trade))
    return closes


def _expiries(
    calendar: SessionCalendar, listing: Mapping[UnitKey, Mapping[int, int]]
) -> tuple[_Expiry, ...]:
    """Each call expiry that is ever listed, with when and what kind (DEC-33)."""
    found: list[_Expiry] = []
    for (expiry, right), strikes in sorted(listing.items()):
        if right is not Right.CALL or not strikes:
            continue
        kinds: set[ExpiryKind] = set()
        if calendar.week_final(expiry).day == expiry:
            kinds.add(ExpiryKind.WEEKLY)
        if calendar.monthly_expiry(expiry.year, expiry.month) == expiry:
            kinds.add(ExpiryKind.MONTHLY)
        found.append(_Expiry(expiry, min(strikes.values()), frozenset(kinds)))
    return tuple(found)


def _unquoted(strikes: list[int]) -> PricedQuotes:
    """Listed strikes with no row on the bar: no quote, so no IV, Greeks or mid."""
    n = len(strikes)
    zeros, nans = np.zeros(n, dtype=np.int64), np.full(n, np.nan)
    code = np.full(n, IvCode.NO_QUOTE, dtype=np.int8)
    return PricedQuotes(np.array(strikes, dtype=np.int64), zeros, zeros,
                        np.zeros(n, dtype=np.bool_), nans, nans, nans, code, nans, nans, nans,
                        nans, nans)  # fmt: skip


def _in_strike_order(a: PricedQuotes, b: PricedQuotes) -> PricedQuotes:
    columns = [np.concatenate((getattr(a, f.name), getattr(b, f.name))) for f in fields(a)]
    joined = PricedQuotes(*columns)
    return joined.take(np.argsort(joined.strike, kind="stable"))


def _no_rows() -> PricedQuotes:
    ints, floats = np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float64)
    return PricedQuotes(ints, ints, ints, np.zeros(0, dtype=np.bool_), floats, floats, floats,
                        np.zeros(0, dtype=np.int8), floats, floats, floats, floats,
                        floats)  # fmt: skip
