"""DEC-47: how LSEG reads a request's start and end dates, for daily and hourly bars.

DEC-47 takes `pmcc fetch` dates as inclusive and passes `end + 1 day`, since LSEG's end is
effectively exclusive (LDG §2). NVDA's first probe found a 5-session daily request answering
without its first day, while one-day daily requests answered. So, on the stock, the probe asks three
windows of the latest complete week (its final session done, so nothing asked is in the future):
its first session alone, the whole week, and its last session alone, each as [first day, last day
+ 1), daily and hourly, and records the days that come back.
"""

from collections.abc import Sequence
from datetime import timedelta

import polars as pl

from pmcc.data.probe.context import Json, Probe, ask, over
from pmcc.data.provider import Interval, RawHistory
from pmcc.domain.sessions import Session

_ET = "America/New_York"
_WEEK = timedelta(days=7)


def probe_edges(probe: Probe, stock_ric: str) -> Json:
    week = last_complete_week(probe)
    windows = {"first_session": week[:1], "week": week, "last_session": week[-1:]}
    return {
        f"{name}_{interval.value}": _edge(probe, stock_ric, sessions, interval)
        for name, sessions in windows.items()
        for interval in (Interval.DAILY, Interval.HOURLY)
    }


def last_complete_week(probe: Probe) -> tuple[Session, ...]:
    """The sessions of the latest week whose final session is done, so no window asks for a
    session that hasn't happened: its empty answer would read as LSEG leaving an edge day out."""
    last = probe.last_session.day
    week = probe.calendar.week_sessions(last)
    return week if week[-1].day == last else probe.calendar.week_sessions(last - _WEEK)


def _edge(probe: Probe, ric: str, sessions: Sequence[Session], interval: Interval) -> Json:
    request = over(sessions, ("TRDPRC_1",), interval)
    asked = ask(probe, [ric], request)
    return {
        "start": request.start.isoformat(),
        "end_exclusive": request.end_exclusive.isoformat(),
        "outcome": asked.outcome,
        "days": _days(asked.history, interval),
    }


def _days(history: RawHistory | None, interval: Interval) -> list[str]:
    """The days that came back: bar dates, or the ET dates of hourly bar starts."""
    if history is None or history.rows.is_empty():
        return []
    stamps = history.rows["bar_start"]
    if interval is Interval.HOURLY:
        stamps = stamps.dt.convert_time_zone(_ET).dt.date()
    return sorted({d.isoformat() for d in stamps.cast(pl.Date).to_list()})
