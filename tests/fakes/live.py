"""Fakes for the live wheel's tests: a close snapshot priced from Black-Scholes, and a repo root
holding Sanji's price file (L2-02, L2-03).

The snapshot's quotes are Black-Scholes prices at one vol, a spread around them, rounded to the
cent, so every contract's delta is known: the live rules solve IV from the mid and should land on
the strike whose true delta is nearest the target.
"""

import json
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

import numpy as np

from pmcc.data.ric import RicForm, build_ric
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.domain.sessions import Session
from pmcc.live.snapshot import CloseSnapshot, OptionQuote, Quote
from pmcc.pricing.black_scholes import greeks, price
from pmcc.pricing.expiry import years_between

RATE = 0.042969  # LD-13's 4.32% bill yield, continuously compounded
VOL = 0.60
CLOSE = "162.83"
STRIKES = tuple(f"{145 + 2.5 * i:.2f}" for i in range(15))  # $145 to $180, as LSEG listed them


def snapshot(
    calendar: SessionCalendar,
    *,
    session: date = date(2026, 11, 13),
    close: str = CLOSE,
    strikes: Sequence[str] = STRIKES,
    spread: float = 0.02,
    vol: float = VOL,
    unquoted: Sequence[str] = (),
) -> CloseSnapshot:
    """A snapshot taken after `session`'s close for the next session's week. `spread` is the
    quote's width as a share of its price; strikes in `unquoted` are listed with no close quote."""
    last = calendar.session(session)
    upcoming = _next_session(calendar, session)
    expiry = calendar.week_final(upcoming.day).day
    options = tuple(
        _quote(calendar, last, expiry, close, strike, right, spread, vol, strike in unquoted)
        for strike in strikes
        for right in (Right.PUT, Right.CALL)
    )
    taken = last.close_bar_end.replace(hour=22)
    return CloseSnapshot(
        taken,
        last,
        upcoming,
        expiry,
        "NVDA.O",
        Price.from_dollars(close),
        options,
        10,
        Price.from_dollars("2.50"),
    )


def true_deltas(
    calendar: SessionCalendar, snap: CloseSnapshot, right: Right, vol: float = VOL
) -> dict[Price, float]:
    """Each strike's Black-Scholes delta at the snapshot's vol: what the pick should find."""
    years = _years(calendar, snap.session.close_bar_end, snap.expiry)
    out: dict[Price, float] = {}
    for q in snap.options:
        if q.option.right is right:
            g = greeks(_dollars(snap.close), _dollars(q.option.strike), years, RATE, vol,
                       right is Right.CALL)  # fmt: skip
            out[q.option.strike] = float(np.asarray(g.delta))
    return out


def sanji_root(root: Path, last_priced: date, *, extra_days: Sequence[date] = ()) -> Path:
    """A repo root whose price_history.json runs to `last_priced`, with NVDA tracked but empty,
    as the file stood on 2026-11-14."""
    days = sorted({*extra_days, last_priced})
    bars = {d.isoformat(): {"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 1.0}
            for d in days}  # fmt: skip
    data: dict[str, object] = {
        "756733": {"tracked": True, "name": "SPDR S&P 500 ETF TRUST", "price_history": bars},
        "4815747": {"tracked": True, "name": "NVIDIA CORP", "price_history": {}},
    }
    (root / "price_history.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return root


def _quote(
    calendar: SessionCalendar,
    last: Session,
    expiry: date,
    close: str,
    strike: str,
    right: Right,
    spread: float,
    vol: float,
    unquoted: bool,
) -> OptionQuote:
    option = OptionId("NVDA", expiry, right, Price.from_dollars(strike))
    ric = build_ric(option, RicForm.LIVE)
    if unquoted:
        return OptionQuote(option, ric, listed=True, close=None)
    years = _years(calendar, last.close_bar_end, expiry)
    value = float(np.asarray(price(float(close), float(strike), years, RATE, vol,
                                   right is Right.CALL)))  # fmt: skip
    bid = max(round(value * (1 - spread / 2), 2), 0.01)
    ask = max(round(value * (1 + spread / 2), 2), bid)
    return OptionQuote(option, ric, listed=True, close=Quote(
        Price.from_dollars(f"{bid:.2f}"), Price.from_dollars(f"{ask:.2f}"), None))  # fmt: skip


def _years(calendar: SessionCalendar, start: datetime, expiry: date) -> float:
    return years_between(start, calendar.session(expiry).close_bar_end)


def _next_session(calendar: SessionCalendar, day: date) -> Session:
    cursor = day
    while True:
        cursor = date.fromordinal(cursor.toordinal() + 1)
        if calendar.is_session(cursor):
            return calendar.session(cursor)


def _dollars(p: Price) -> float:
    return float(p.to_dollars())
