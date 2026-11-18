"""Fakes for the volatility chart's tests (L4-02): option quotes priced from Black-Scholes at known
vols, and a `HistoryProvider` that answers NVDA.O's close and any option RIC from them.

Every quote is the Black-Scholes price at one vol, 1% either side, rounded to the cent, so the IV
solved from its mid lands on that vol to within the rounding.
"""

from collections.abc import Mapping, Sequence
from datetime import UTC, date, timedelta

import numpy as np
import polars as pl

from pmcc.data.provider import Interval, ProviderOutageError, RawHistory, raw_schema
from pmcc.data.ric import RicForm, build_ric, parse_ric
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import BAR
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_DOLLAR, Price
from pmcc.domain.sessions import Session
from pmcc.live.snapshot import OptionQuote, Quote
from pmcc.pricing.black_scholes import price
from pmcc.pricing.expiry import years_between

RATE = 0.042969  # LD-13's, continuously compounded
STOCK = "NVDA.O"
HALF_SPREAD = 0.01


def quoted_price(
    calendar: SessionCalendar, session: Session, expiry: date, close: float, strike: float,
    right: Right, vol: float,
) -> tuple[float, float]:  # fmt: skip
    """The bid and ask, in dollars, of a contract at `vol` at `session`'s close."""
    years = years_between(session.close_bar_end, calendar.session(expiry).close_bar_end)
    value = float(np.asarray(price(close, strike, years, RATE, vol, right is Right.CALL)))
    return round(value * (1 - HALF_SPREAD), 2), round(value * (1 + HALF_SPREAD), 2)


def option_quotes(
    calendar: SessionCalendar,
    session: Session,
    expiry: date,
    close: float,
    strikes: Sequence[float],
    *,
    call_vol: float = 0.5,
    put_vol: float = 0.5,
    unquoted: Sequence[tuple[Right, float]] = (),
) -> tuple[OptionQuote, ...]:
    """Each strike's put and call, quoted in the close bar at their vols; those in `unquoted`
    listed with no close quote."""
    quotes: list[OptionQuote] = []
    for strike in strikes:
        for right, vol in ((Right.PUT, put_vol), (Right.CALL, call_vol)):
            option = OptionId("NVDA", expiry, right, Price.from_dollars(f"{strike:.2f}"))
            ric = build_ric(option, RicForm.LIVE)
            if (right, strike) in unquoted:
                quotes.append(OptionQuote(option, ric, listed=True, close=None))
                continue
            bid, ask = quoted_price(calendar, session, expiry, close, strike, right, vol)
            close_quote = Quote(Price.from_dollars(f"{bid:.2f}"), Price.from_dollars(f"{ask:.2f}"),
                                None)  # fmt: skip
            quotes.append(OptionQuote(option, ric, listed=True, close=close_quote))
    return tuple(quotes)


class VolProvider:
    """A `HistoryProvider`: NVDA.O's last trade in each session's close bar from `closes`, and
    every option RIC asked, in any form, quoted at `vol` in each session's close bar from the
    close that day. Strikes in `unlisted` (dollars) answer nothing; `down` raises an outage."""

    def __init__(
        self,
        calendar: SessionCalendar,
        closes: Mapping[date, float],
        *,
        vol: float = 0.5,
        unlisted: Sequence[float] = (),
        down: bool = False,
    ) -> None:
        self._calendar = calendar
        self._closes = closes
        self._vol = vol
        self._unlisted = {Price.from_dollars(f"{s:.2f}") for s in unlisted}
        self._down = down
        self.asked: list[tuple[str, ...]] = []

    def history(
        self,
        rics: Sequence[str],
        fields: Sequence[str],
        start: date,
        end_exclusive: date,
        interval: Interval,
    ) -> RawHistory:
        self.asked.append(tuple(rics))
        if self._down:
            raise ProviderOutageError("the LSEG platform session did not open")
        sessions = self._calendar.sessions(start, end_exclusive - timedelta(days=1))
        rows = [row for ric in rics for s in sessions for row in self._rows(ric, fields, s)]
        frame = pl.DataFrame(rows, schema=raw_schema(interval), orient="row")
        return RawHistory(interval, frame)

    def _rows(self, ric: str, fields: Sequence[str], session: Session) -> list[tuple[object, ...]]:
        close = self._closes.get(session.day)
        if close is None:
            return []
        stamp = (session.close_bar_end - BAR).astimezone(UTC)
        if ric == STOCK:
            return [(stamp, ric, "TRDPRC_1", close)] if "TRDPRC_1" in fields else []
        option = parse_ric(ric).option
        if option.strike in self._unlisted or option.expiry < session.day:
            return []
        strike = option.strike.units / UNITS_PER_DOLLAR
        bid, ask = quoted_price(
            self._calendar, session, option.expiry, close, strike, option.right, self._vol
        )
        cells = {"BID": bid, "ASK": ask}
        return [(stamp, ric, f, v) for f, v in cells.items() if f in fields]
