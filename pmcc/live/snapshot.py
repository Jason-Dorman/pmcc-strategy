"""The close snapshot the live wheel decides from (LIVE-SPEC › Data; LD-11; L1-02).

One pull a night, after the close, through any `HistoryProvider` (the CLI hands it the headless
platform session, LD-05):

1. The last completed session, the session after it (the one its close plans for: L-S1 for the
   nightly run) and the expiry of that session's week (L-P2: the week's last session).
2. The stock's close: the last trade in the session's close bar, the hourly bar ending at the
   close (LSEG stamps bars at their start, so it starts an hour earlier: LDG §4.8, §9). If that
   bar isn't there (LSEG publishes it after the close), the snapshot stops: an earlier trade is
   not the close, and the options' quotes come from the same bar.
3. Every put and call from 10% below the close to 10% above it, in $2.50 steps, for that expiry,
   with each one's bid, ask and last trade in the close bar. A 0.30-delta weekly sits a few percent
   from the money, so the band holds it with room to spare. A strike LSEG doesn't list comes back
   unlisted (fetch's fail-soft guess-and-check, INV-12), never as an error.

An outage raises `ProviderOutageError` from the fetch and returns nothing. The snapshot holds
LSEG's prices, so the console summary (`describe`) carries counts only (LD-15); the full report
is written to a file (in Actions, a one-day artifact, as the PO approved: LD-21).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import final

import polars as pl

from pmcc.config.universe import Underlying
from pmcc.data.fetch import BarRequest, Retry, fetch_contracts, fetch_rics
from pmcc.data.provider import HistoryProvider, Interval, RawHistory
from pmcc.data.ric import RicForm, build_ric
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import BAR, to_et
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_CENT, Price
from pmcc.domain.sessions import Session

BAND_PERCENT = 10  # strikes asked: within this percent of the close, either side
STEP_CENTS = 250  # $2.50, NVDA's finest weekly strike step (the probe's, WD-11)
STEP = Price(STEP_CENTS * UNITS_PER_CENT)
QUOTE_FIELDS = ("BID", "ASK", "TRDPRC_1")
_DAY = timedelta(days=1)
_RIGHT_NAMES = {Right.PUT: "put", Right.CALL: "call"}

type Json = dict[str, object]


class SnapshotError(Exception):
    """LSEG answered, but not with what a decision needs (the stock's close). Nothing is kept."""


@final
@dataclass(frozen=True, slots=True)
class Quote:
    """A contract's bid, ask and last trade in the close bar; any may be missing."""

    bid: Price | None
    ask: Price | None
    last: Price | None

    @property
    def valid(self) -> bool:
        """A bid above zero and an ask at or above it (LDG; L-T1's first test)."""
        return (
            self.bid is not None
            and self.ask is not None
            and self.bid.units > 0
            and self.ask.units >= self.bid.units
        )


@final
@dataclass(frozen=True, slots=True)
class OptionQuote:
    """One contract asked. `listed` when LSEG answered it; `close` is None without a close bar."""

    option: OptionId
    ric: str
    listed: bool
    close: Quote | None

    @property
    def quoted_at_close(self) -> bool:
        """A valid bid and ask in the close bar (only a listed contract has one)."""
        return self.close is not None and self.close.valid


@final
@dataclass(frozen=True, slots=True)
class CloseSnapshot:
    taken_at: datetime
    session: Session
    next_session: Session
    expiry: date
    stock_ric: str
    close: Price
    options: tuple[OptionQuote, ...]


def last_completed(calendar: SessionCalendar, now: datetime) -> Session:
    """The latest session whose close is at or before `now`."""
    today = to_et(now).date()
    if calendar.is_session(today) and to_et(now) >= calendar.session(today).close_bar_end:
        return calendar.session(today)
    return calendar.sessions_before(today, 1)[0]


def next_session(calendar: SessionCalendar, now: datetime) -> Session:
    """The first session after the last completed one, so it always pairs with the close the
    snapshot reads. After the close, as the nightly run is, that is also the first session after
    the run's date (L-S1); before it, it's today's session."""
    day = last_completed(calendar, now).day + _DAY
    while not calendar.is_session(day):
        day += _DAY
    return calendar.session(day)


def strike_ladder(close: Price, band_percent: int = BAND_PERCENT) -> tuple[Price, ...]:
    """Every `STEP_CENTS` strike from `band_percent` below `close` to as far above, rounded
    outwards to whole steps."""
    cents = close.units // UNITS_PER_CENT
    step = STEP_CENTS
    low = cents * (100 - band_percent) // 100 // step * step
    high = -(-cents * (100 + band_percent) // 100 // step) * step
    return tuple(Price(c * UNITS_PER_CENT) for c in range(low, high + 1, step))


def take_snapshot(
    provider: HistoryProvider,
    underlying: Underlying,
    calendar: SessionCalendar,
    now: datetime,
    retry: Retry = Retry(),  # noqa: B008 (frozen, so a shared default is safe)
) -> CloseSnapshot:
    """Tonight's snapshot for `underlying`. Raises `SnapshotError` if the stock has no trade in
    the close bar, before any option is asked, and `ProviderOutageError` if LSEG stops answering."""
    session = last_completed(calendar, now)
    upcoming = next_session(calendar, now)
    expiry = calendar.week_final(upcoming.day).day
    request = BarRequest(QUOTE_FIELDS, session.day, session.day + _DAY, Interval.HOURLY)
    stock = fetch_rics(provider, [underlying.stock_ric], request, retry=retry)
    close = _stock_close(stock.history, underlying.stock_ric, session)
    if close is None:
        raise SnapshotError(
            f"{underlying.stock_ric} has no close for {session.day}: no last trade in its "
            f"close bar (ending {session.close_bar_end:%H:%M} ET). LSEG may not have published "
            "it yet."
        )
    options = [
        OptionId(underlying.option_root, expiry, right, strike)
        for strike in strike_ladder(close)
        for right in (Right.PUT, Right.CALL)
    ]
    fetched = fetch_contracts(provider, options, request, fetch_date=to_et(now).date(), retry=retry)
    closing = _close_bar_rows(fetched.history, session)
    quotes = tuple(_option_quote(o, fetched.answered, closing) for o in options)
    return CloseSnapshot(now, session, upcoming, expiry, underlying.stock_ric, close, quotes)


def _bar_start(bar_end: datetime) -> datetime:
    """LSEG's stamp for the bar ending at `bar_end`: its start, in UTC, as the raw rows hold it."""
    return (bar_end - BAR).astimezone(UTC)


def _close_bar_rows(history: RawHistory, session: Session) -> pl.DataFrame:
    return history.rows.filter(pl.col("bar_start") == _bar_start(session.close_bar_end))


def _stock_close(history: RawHistory, ric: str, session: Session) -> Price | None:
    """The last trade in the session's close bar, or None if it has none."""
    trades = (
        _close_bar_rows(history, session)
        .filter((pl.col("ric") == ric) & (pl.col("field") == "TRDPRC_1"))
        .get_column("value")
        .to_list()
    )
    return Price.from_dollars(trades[0]) if trades else None


def _option_quote(
    option: OptionId, answered: Mapping[OptionId, str], closing: pl.DataFrame
) -> OptionQuote:
    ric = answered.get(option)
    if ric is None:
        return OptionQuote(option, build_ric(option, RicForm.LIVE), listed=False, close=None)
    cells = {
        row["field"]: row["value"]
        for row in closing.filter(pl.col("ric") == ric).iter_rows(named=True)
    }
    if not cells:
        return OptionQuote(option, ric, listed=True, close=None)
    quote = Quote(*(_price(cells.get(name)) for name in QUOTE_FIELDS))
    return OptionQuote(option, ric, listed=True, close=quote)


def _price(value: object) -> Price | None:
    return Price.from_dollars(value) if isinstance(value, float) else None


def snapshot_report(snapshot: CloseSnapshot) -> Json:
    """The snapshot as JSON: when, what, the counts, and every contract asked."""
    return {
        "taken_at": snapshot.taken_at.isoformat(),
        "session": snapshot.session.day.isoformat(),
        "next_session": snapshot.next_session.day.isoformat(),
        "expiry": snapshot.expiry.isoformat(),
        "stock": {"ric": snapshot.stock_ric, "close": _dollars(snapshot.close)},
        "band": {"percent": BAND_PERCENT, "step": _dollars(STEP)},
        "counts": _counts(snapshot.options),
        "options": [_option_row(q) for q in snapshot.options],
    }


def describe(snapshot: CloseSnapshot) -> str:
    """One line for the console and the Actions log: counts only, no prices (LD-15)."""
    listed, quoted = _per_right(_listed(snapshot.options)), _per_right(_quoted(snapshot.options))
    return (
        f"{snapshot.stock_ric}: close of {snapshot.session.day} read; next session "
        f"{snapshot.next_session.day}, expiry {snapshot.expiry}. Asked {len(snapshot.options)} "
        f"contracts (within {BAND_PERCENT}% of the close, ${_dollars(STEP)} apart): LSEG listed "
        f"{listed['put']} puts and {listed['call']} calls; {quoted['put']} puts and "
        f"{quoted['call']} calls had a valid bid and ask at the close."
    )


def _counts(options: Sequence[OptionQuote]) -> Json:
    return {
        "asked": len(options),
        "listed": _per_right(_listed(options)),
        "quoted_at_close": _per_right(_quoted(options)),
    }


def _listed(options: Sequence[OptionQuote]) -> list[OptionQuote]:
    return [q for q in options if q.listed]


def _quoted(options: Sequence[OptionQuote]) -> list[OptionQuote]:
    return [q for q in options if q.quoted_at_close]


def _per_right(options: Sequence[OptionQuote]) -> dict[str, int]:
    return {name: sum(q.option.right is r for q in options) for r, name in _RIGHT_NAMES.items()}


def _option_row(quote: OptionQuote) -> Json:
    close = quote.close
    return {
        "ric": quote.ric,
        "right": _RIGHT_NAMES[quote.option.right],
        "strike": _dollars(quote.option.strike),
        "listed": quote.listed,
        "bid": _dollars(close.bid) if close and close.bid else None,
        "ask": _dollars(close.ask) if close and close.ask else None,
        "last": _dollars(close.last) if close and close.last else None,
        "valid": bool(close and close.valid),
    }


def _dollars(price: Price) -> str:
    return f"{price.to_dollars():.2f}"
