"""Fakes for the thesis probe's tests (T1-01): an in-memory history provider, a finder, FRED text.

`ChainProvider` serves daily closes for the RICs it's given, and an SPXW chain priced by
Black-Scholes at one vol, in one RIC spelling only (`SPXW`, a lower-case month letter, a strike of
1,000 or more in tenths) and at `expiry` only, so the probe's listing check and its 0.20-delta
picks have known answers; on hourly bars (the close bar) unless `option_intervals` says
otherwise. A RIC it doesn't
know gets the service's no-data code, as LSEG answers one.
"""

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta

import numpy as np
import polars as pl

from pmcc.data.provider import (
    DailyTable,
    Interval,
    NoDataError,
    RawHistory,
    TransientError,
    raw_schema,
)
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.sessions import Session
from pmcc.pricing.black_scholes import price
from pmcc.thesis import spxw
from pmcc.thesis.config import load_thesis_config
from pmcc.thesis.fred import FredKey

RULES = load_thesis_config().cost_sample
NO_DATA = ("TS.Intraday.UserRequestError.90001",)
_RIC = re.compile(r"SPXW(?P<letter>[a-x])(?P<day>\d{2})(?P<year>\d{2})(?P<strike>\d{5})\.U")
_CALL_LETTERS = "abcdefghijkl"
_PUT_LETTERS = "mnopqrstuvwx"


@dataclass
class ChainProvider:
    """Daily closes per RIC; an SPXW chain at `vol` for `session`'s close bar, quoted
    `spread` wide (as a share of each price, at least 0.05)."""

    calendar: SessionCalendar
    closes: Mapping[str, Mapping[date, float]]
    session: date
    expiry: date
    spot: float = 6600.0
    vol: float = 0.18
    spread: float = 0.04
    option_intervals: frozenset[Interval] = frozenset({Interval.HOURLY})  # where SPXW answers
    asked: list[tuple[str, ...]] = field(default_factory=list[tuple[str, ...]])

    def history(
        self,
        rics: Sequence[str],
        fields: Sequence[str],
        start: date,
        end_exclusive: date,
        interval: Interval,
    ) -> RawHistory:
        self.asked.append(tuple(rics))
        rows = [r for ric in rics for r in self._rows(ric, fields, start, end_exclusive, interval)]
        if not rows:
            raise NoDataError("No data to return", NO_DATA)
        return RawHistory(interval, pl.DataFrame(rows, schema=raw_schema(interval), orient="row"))

    def _rows(
        self, ric: str, fields: Sequence[str], start: date, end: date, interval: Interval
    ) -> list[tuple[object, str, str, float]]:
        if interval is Interval.DAILY and ric in self.closes:
            days = self.closes[ric]
            return [(d, ric, "TRDPRC_1", v) for d, v in days.items() if start <= d < end]
        quote = self._quote(ric) if interval in self.option_intervals else None
        if quote is None:
            return []
        session = self.calendar.session(self.session)
        stamp = self.session if interval is Interval.DAILY else _bar_start(session)
        bid, ask = quote
        return [(stamp, ric, f, v) for f, v in (("BID", bid), ("ASK", ask)) if f in fields]

    def _quote(self, ric: str) -> tuple[float, float] | None:
        match = _RIC.fullmatch(ric)
        if match is None:
            return None
        is_call = match["letter"] not in _PUT_LETTERS
        month = (_CALL_LETTERS if is_call else _PUT_LETTERS).index(match["letter"]) + 1
        listed = (self.expiry.month, self.expiry.day, self.expiry.year % 100)
        if (month, int(match["day"]), int(match["year"])) != listed:
            return None  # only the one expiry is listed
        strike = int(match["strike"]) / 10
        years = spxw.years_from_close(
            self.calendar.session(self.session), self.calendar, self.expiry
        )
        value = float(price(self.spot, strike, years, RULES.rate_decimal, self.vol, is_call))
        half = max(0.05, value * self.spread) / 2
        return round(max(0.0, value - half), 2), round(value + half, 2)


def _bar_start(session: Session) -> datetime:
    return (session.close_bar_end - timedelta(hours=1)).astimezone(UTC)


def daily(start: date, values: Sequence[float], calendar: SessionCalendar) -> dict[date, float]:
    """`values` on the calendar's sessions from `start`."""
    sessions = calendar.sessions(start, start + timedelta(days=len(values) * 2 + 10))
    return {s.day: v for s, v in zip(sessions, values, strict=False)}


@dataclass
class FakeFinder:
    """LSEG's search and table, scripted: `hits` per query, `tables` per RIC. `fails` makes every
    call raise a `TransientError`."""

    hits: Mapping[str, list[dict[str, str | None]]] = field(
        default_factory=dict[str, list[dict[str, str | None]]]
    )
    tables: Mapping[str, DailyTable] = field(default_factory=dict[str, DailyTable])
    fails: bool = False

    def search(self, query: str, select: str, top: int) -> list[dict[str, str | None]]:
        if self.fails:
            raise TransientError("LDError: search is down")
        return self.hits.get(query, [])[:top]

    def table(self, ric: str, start: date, end_exclusive: date) -> DailyTable:
        if self.fails or ric not in self.tables:
            raise TransientError(f"LDError: no table for {ric}")
        return self.tables[ric]


FRED_KEY = FredKey("0123456789abcdef0123456789abcdef")
FRED_TEXT = json.dumps(
    {
        "observations": [
            {"date": "2023-11-20", "value": "4.01"},
            {"date": "2023-11-21", "value": "."},
            {"date": "2023-11-22", "value": "3.98"},
        ]
    }
)


def oas_table(ric: str, days: Sequence[date]) -> DailyTable:
    values = np.linspace(3.0, 3.5, len(days))
    return DailyTable(
        ric, ("VALUE",), tuple((d, (float(v),)) for d, v in zip(days, values, strict=True))
    )
