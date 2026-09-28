"""DEC-06: how LSEG stamps hourly bars, and which bar holds the close and the closing quote.

For each of the last 5 sessions the probe puts the daily bar beside that day's hourly bars, keyed
by their ET start, and lists which hourly bars carry the daily close print (stock TRDPRC_1) and
the daily closing quote (an option's BID and ASK). If bars are stamped at their start and quotes
are end-of-bar values, both land in the bar starting an hour before the close: 15:00, or 12:00 on
a half-day. The raw values are kept, so the report is the evidence, whatever it shows.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import final

import polars as pl

from pmcc.data.fetch import fetch_rics
from pmcc.data.probe.context import Json, Probe, over, price
from pmcc.data.provider import Interval
from pmcc.domain.sessions import Session

_ET = "America/New_York"
STOCK_FIELDS = ("TRDPRC_1",)
OPTION_FIELDS = ("BID", "ASK", "TRDPRC_1")
SESSIONS = 5

type ByHour = dict[str, dict[str, float]]


@final
@dataclass(frozen=True, slots=True)
class Compared:
    """One day of one RIC: its daily values, its hourly bars by ET start, and the bars matching."""

    daily: dict[str, float]
    hourly: ByHour
    matching_bar_starts: list[str]

    def record(self) -> Json:
        hours = list(self.hourly)
        return {
            "daily": self.daily,
            "hourly": self.hourly,
            "matching_bar_starts": self.matching_bar_starts,
            "first_bar_start": hours[0] if hours else None,
            "last_bar_start": hours[-1] if hours else None,
        }


def probe_bars(probe: Probe, stock_ric: str, option_ric: str) -> Json:
    sessions = probe.recent(SESSIONS)
    hourly, daily = Interval.HOURLY, Interval.DAILY
    stock_h, stock_d = (_rows(probe, stock_ric, STOCK_FIELDS, sessions, i) for i in (hourly, daily))
    option_h, option_d = (
        _rows(probe, option_ric, OPTION_FIELDS, sessions, i) for i in (hourly, daily)
    )
    days = [
        (
            s,
            compare(stock_h, stock_d, s.day, ("TRDPRC_1",)),
            compare(option_h, option_d, s.day, ("BID", "ASK")),
        )
        for s in sessions
    ]
    return {
        "stock_ric": stock_ric,
        "option_ric": option_ric,
        "sessions": [
            {
                "day": s.day.isoformat(),
                "close_hour_start": close_hour_start(s),
                "stock": st.record(),
                "option": op.record(),
            }
            for s, st, op in days
        ],
        "summary": summarize(days),
    }


def _rows(
    probe: Probe, ric: str, fields: Sequence[str], sessions: Sequence[Session], interval: Interval
) -> pl.DataFrame:
    request = over(sessions, fields, interval)
    return fetch_rics(probe.provider, [ric], request, retry=probe.retry).series(ric)


def close_hour_start(session: Session) -> str:
    """The ET start of the session's close bar: 15:00, or 12:00 on a half-day."""
    return f"{session.close.hour - 1:02d}:00"


def compare(
    hourly: pl.DataFrame, daily: pl.DataFrame, day: date, fields: Sequence[str]
) -> Compared:
    """`day`'s daily values beside its hourly bars. Prices compare at $0.0001 (DEC-44)."""
    by_hour = _by_hour(hourly, day)
    rows = daily.filter(pl.col("bar_start") == day).iter_rows(named=True)
    closing: dict[str, float] = {r["field"]: r["value"] for r in rows}
    wanted = {f: price(closing[f]) for f in fields if f in closing}
    matches = [
        hour
        for hour, values in by_hour.items()
        if wanted and all(f in values and price(values[f]) == p for f, p in wanted.items())
    ]
    return Compared(dict(sorted(closing.items())), by_hour, matches)


def _by_hour(hourly: pl.DataFrame, day: date) -> ByHour:
    et = hourly.with_columns(et=pl.col("bar_start").dt.convert_time_zone(_ET))
    out: ByHour = {}
    for row in et.filter(pl.col("et").dt.date() == day).sort("et").iter_rows(named=True):
        out.setdefault(f"{row['et']:%H:%M}", {})[row["field"]] = row["value"]
    return out


def summarize(days: Sequence[tuple[Session, Compared, Compared]]) -> Json:
    """How often each ET bar start held the close print and the closing quote."""
    stock, option = Counter[str](), Counter[str]()
    for _, st, op in days:
        stock.update(st.matching_bar_starts)
        option.update(op.matching_bar_starts)
    return {
        "sessions": len(days),
        "stock_close_print_in_close_hour_bar": sum(
            close_hour_start(s) in st.matching_bar_starts for s, st, _ in days
        ),
        "option_closing_quote_in_close_hour_bar": sum(
            close_hour_start(s) in op.matching_bar_starts for s, _, op in days
        ),
        "stock_close_print_by_bar_start": dict(sorted(stock.items())),
        "option_closing_quote_by_bar_start": dict(sorted(option.items())),
    }
