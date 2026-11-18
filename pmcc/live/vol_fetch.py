"""Asking LSEG for the volatility points (L4-02; PO, LD-33; LD-34).

Through the backtests' fetch (batched, retried, a strike LSEG doesn't list fail-soft), in two
steps:

1. **The plan:** the stock's close each session, the last trade in its close bar, from 20
   sessions before the first point to the last, in one request. It says how much the points will
   ask for, so a backfill's size is shown before it's pulled (CLAUDE.md › LSEG access).
2. **The points:** expiry by expiry (the tenor's, which several sessions share), every put and
   call within $7.50 of each of its sessions' closes, over those sessions' close bars.

An outage raises `ProviderOutageError`; a session with no close raises `VolError`. Either way
nothing is returned, so nothing is written.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import final

from pmcc.data.fetch import BATCH_SIZE, BarRequest, Retry, fetch_contracts, fetch_rics
from pmcc.data.provider import HistoryProvider, Interval
from pmcc.data.ric import forms_to_ask
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.domain.sessions import Session
from pmcc.live.snapshot import QUOTE_FIELDS, close_bar_rows, option_quote, stock_close
from pmcc.live.vol import (
    RV_RETURNS,
    VolError,
    VolPoint,
    atm_ladder,
    atm_point,
    rv20_through,
    tenor_expiry,
)

_DAY = timedelta(days=1)


@final
@dataclass(frozen=True, slots=True)
class Plan:
    """What the points will ask LSEG for: each expiry's sessions and strikes, from the closes."""

    sessions: tuple[Session, ...]
    closes: Mapping[date, Price]
    groups: Mapping[date, tuple[Session, ...]]  # the tenor's expiry: its sessions, in order
    strikes: Mapping[date, tuple[Price, ...]]  # the expiry: every strike its sessions ask
    fetch_date: date

    @property
    def contracts(self) -> int:
        return 2 * sum(len(s) for s in self.strikes.values())

    @property
    def requests(self) -> int:
        """The closes' request, and each expiry's batches in each RIC form it's asked in. More
        when a contract doesn't answer: it's asked again alone."""
        rounds = (
            len(forms_to_ask(e, self.fetch_date)) * math.ceil(2 * len(k) / BATCH_SIZE)
            for e, k in self.strikes.items()
        )
        return 1 + sum(rounds)

    def describe(self) -> str:
        first, last = self.sessions[0].day, self.sessions[-1].day
        return (
            f"{len(self.sessions)} sessions ({first} to {last}) over {len(self.groups)} expiries: "
            f"{self.contracts} contracts, about {self.requests} requests (more if some aren't "
            "listed: each is asked again alone)."
        )


def plan_points(
    provider: HistoryProvider,
    stock_ric: str,
    calendar: SessionCalendar,
    sessions: Sequence[Session],
    fetch_date: date,
    retry: Retry,
) -> Plan:
    """The closes, and from them each session's expiry and strikes. Raises `VolError` if a
    session has no close."""
    first = calendar.sessions_before(sessions[0].day, RV_RETURNS)[0].day
    closes = _closes(provider, stock_ric, calendar, first, sessions[-1], retry)
    missing = [s.day.isoformat() for s in sessions if s.day not in closes]
    if missing:
        raise VolError(
            f"{stock_ric} has no close for {', '.join(missing)}: no last trade in the close bar. "
            "LSEG may not have published it yet."
        )
    groups: dict[date, list[Session]] = {}
    for session in sessions:
        groups.setdefault(tenor_expiry(calendar, session.day), []).append(session)
    strikes = {
        expiry: tuple(sorted({k for s in group for k in atm_ladder(closes[s.day])}))
        for expiry, group in groups.items()
    }
    return Plan(
        tuple(sessions),
        closes,
        {e: tuple(g) for e, g in groups.items()},
        strikes,
        fetch_date,
    )


def fetch_points(
    provider: HistoryProvider,
    plan: Plan,
    option_root: str,
    calendar: SessionCalendar,
    rate: float,
    retry: Retry,
) -> tuple[VolPoint, ...]:
    """Each planned session's point, in session order."""
    points: list[VolPoint] = []
    for expiry, group in plan.groups.items():
        options = [
            OptionId(option_root, expiry, right, strike)
            for strike in plan.strikes[expiry]
            for right in (Right.PUT, Right.CALL)
        ]
        request = BarRequest(QUOTE_FIELDS, group[0].day, group[-1].day + _DAY, Interval.HOURLY)
        fetched = fetch_contracts(
            provider, options, request, fetch_date=plan.fetch_date, retry=retry
        )
        for session in group:
            close = plan.closes[session.day]
            near = {k.units for k in atm_ladder(close)}
            closing = close_bar_rows(fetched.history, session)
            quotes = [
                option_quote(o, fetched.answered, closing)
                for o in options
                if o.strike.units in near
            ]
            rv20 = rv20_through(calendar, session.day, plan.closes)
            points.append(atm_point(session, close, calendar.session(expiry), quotes, rate, rv20))
    return tuple(sorted(points, key=lambda p: p.session))


def _closes(
    provider: HistoryProvider,
    ric: str,
    calendar: SessionCalendar,
    first: date,
    last: Session,
    retry: Retry,
) -> dict[date, Price]:
    request = BarRequest(("TRDPRC_1",), first, last.day + _DAY, Interval.HOURLY)
    result = fetch_rics(provider, [ric], request, retry=retry)
    return {
        s.day: close
        for s in calendar.sessions(first, last.day)
        if (close := stock_close(result.history, ric, s)) is not None
    }
