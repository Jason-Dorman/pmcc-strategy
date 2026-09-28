"""What every probe shares: the symbol, the calendar, a counted provider, and small readers.

A probe asks through the `HistoryProvider` port, never the adapter (ARCHITECTURE §3.3 rule 2), and
builds a plain JSON-ready dict. `ask` records one request as the service answered it (bars, a
no-data code, or an unreadable batch), which is what the DEC-83 checks need. A transient failure is
asked again, and one that persists is an outage: it propagates, and nothing is written (LDG §4.3).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import final

import polars as pl

from pmcc.data.fetch import BarRequest, Retry, retrying
from pmcc.data.provider import (
    HistoryProvider,
    Interval,
    NoDataError,
    RawHistory,
    UnreadableAnswerError,
)
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET, to_et
from pmcc.domain.money import Price
from pmcc.domain.sessions import Session

type Json = dict[str, object]

_DAY = timedelta(days=1)
QUOTES = ("BID", "ASK")


class CountingProvider:
    """A provider that counts the requests made through it, for the report and the estimate."""

    def __init__(self, inner: HistoryProvider) -> None:
        self._inner = inner
        self.calls = 0

    def history(
        self,
        rics: Sequence[str],
        fields: Sequence[str],
        start: date,
        end_exclusive: date,
        interval: Interval,
    ) -> RawHistory:
        self.calls += 1
        return self._inner.history(rics, fields, start, end_exclusive, interval)


@final
@dataclass(frozen=True, slots=True)
class Probe:
    """One symbol's probe run. `now` is ET; the fetch date for the RIC form policy is its date."""

    symbol: str
    root: str
    calendar: SessionCalendar
    provider: HistoryProvider
    now: datetime
    retry: Retry

    @property
    def today(self) -> date:
        return to_et(self.now).date()

    @property
    def last_session(self) -> Session:
        """The latest session whose close is at or before `now`."""
        day = self.today
        while not (
            self.calendar.is_session(day) and self.calendar.session(day).close_bar_end <= self.now
        ):
            day -= _DAY
        return self.calendar.session(day)

    def recent(self, count: int) -> tuple[Session, ...]:
        """The last `count` completed sessions, oldest first."""
        last = self.last_session
        return (*self.calendar.sessions_before(last.day, count - 1), last)


def over(sessions: Sequence[Session], fields: Sequence[str], interval: Interval) -> BarRequest:
    """A request for `fields` from the first session to the last, inclusive (DEC-47)."""
    return BarRequest(tuple(fields), sessions[0].day, sessions[-1].day + _DAY, interval)


@final
@dataclass(frozen=True, slots=True)
class Asked:
    """One request: how the service answered, its codes, the report's record, and any rows.

    `outcome` is `answered`, `no_data`, or `unreadable` (a batch whose answer can't be read).
    """

    outcome: str
    codes: tuple[str, ...]
    record: Json
    history: RawHistory | None


def ask(probe: Probe, rics: Sequence[str], request: BarRequest) -> Asked:
    """One request, recorded as the service answered it: bars, a no-data code, or (for a batch) an
    answer that can't be read.

    Anything else is asked again, like any fetch (DEC-49): a transient failure, or a single RIC's
    unreadable answer. A dead or signed-out Workspace shows up only as transient failures (DEC-83),
    so one that persists becomes a `ProviderOutageError`, never a recorded outcome.
    """

    def attempt() -> RawHistory | NoDataError | UnreadableAnswerError:
        try:
            return probe.provider.history(
                rics, request.fields, request.start, request.end_exclusive, request.interval
            )
        except NoDataError as exc:
            return exc
        except UnreadableAnswerError as exc:
            if len(rics) > 1:
                return exc
            raise

    base: Json = {"rics": list(rics), "fields": list(request.fields), "interval": request.interval}
    answer = retrying(attempt, probe.retry, len(rics))
    if isinstance(answer, NoDataError):
        detail: Json = {"codes": list(answer.codes), "message": answer.message}
        return Asked("no_data", answer.codes, {**base, "outcome": "no_data", **detail}, None)
    if isinstance(answer, UnreadableAnswerError):
        detail = {"error_class": answer.error_class, "message": answer.message}
        return Asked("unreadable", (), {**base, "outcome": "unreadable", **detail}, None)
    detail = {
        "answered": sorted(answer.rics()),
        "rows": answer.rows.height,
        "fields_with_values": sorted(set(answer.rows["field"].to_list())),
    }
    return Asked("answered", (), {**base, "outcome": "answered", **detail}, answer)


def wide(rows: pl.DataFrame) -> pl.DataFrame:
    """Raw hourly rows as one row per RIC and bar, a column per field, plus `end` in ET."""
    if rows.is_empty():
        return pl.DataFrame(
            schema={"ric": pl.String(), "end": pl.Datetime("us", "America/New_York")}
        )
    return rows.pivot(on="field", index=["bar_start", "ric"], values="value").with_columns(
        end=(pl.col("bar_start") + pl.duration(hours=1)).dt.convert_time_zone("America/New_York")
    )


def session_bar_ends(sessions: Sequence[Session]) -> pl.Series:
    """Every session bar's end (DEC-06), to pick session bars out of a tape."""
    ends = [end for s in sessions for end in s.bar_ends()]
    return pl.Series("end", ends, dtype=pl.Datetime("us", "America/New_York"))


def valid_mid(frame: pl.DataFrame) -> pl.Expr:
    """BID > 0, ASK > 0 and ASK >= BID (ARCHITECTURE §6.5). Missing columns mean no quote."""
    if not {"BID", "ASK"} <= set(frame.columns):
        return pl.lit(False)
    return (pl.col("BID") > 0) & (pl.col("ASK") > 0) & (pl.col("ASK") >= pl.col("BID"))


def price(value: float) -> Price:
    return Price.from_dollars(value)


def dollars(value: Price) -> float:
    return float(value.to_dollars())


def et_hour(stamp: datetime) -> str:
    """A UTC bar start as its ET wall-clock start, e.g. "15:00"."""
    return f"{stamp.astimezone(ET):%H:%M}"
