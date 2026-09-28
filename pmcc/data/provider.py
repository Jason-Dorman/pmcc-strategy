"""The history port: how the data layer asks for bars without knowing LSEG (ARCHITECTURE §5.1).

`HistoryProvider` is the one call the fetch logic makes. `LsegProvider` (`pmcc.data.lseg`)
implements it; tests drive it over `FakeLseg`. A provider answers with long rows, or raises one of
four failure classes that say what the failure means (DEC-49, DEC-83):

- `NoDataError`: the service said there is no data for these RICs. Soft.
- `UnreadableAnswerError`: an answer came back that can't be read. Split the request.
- `TransientError`: anything else. Ask again.
- `ProviderOutageError`: the session is down, or a failure persists. Loud: abort and write
  nothing (LDG §4.3).

Only the service's own answer (a no-data code, or no bars) ever makes a RIC unanswered. They share
no base class, so no handler can catch an outage by accident while catching the rest.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Protocol, final

import polars as pl


class Interval(StrEnum):
    """Bar sizes, spelled as LSEG takes them. The backtest uses hourly; daily is for probes."""

    HOURLY = "hourly"
    DAILY = "daily"


def raw_schema(interval: Interval) -> pl.Schema:
    """Long rows as a provider returns them: one row per non-empty cell.

    `bar_start` is LSEG's own stamp, the bar's start (LDG §4.8): a UTC datetime for hourly bars,
    a date for daily ones. `bar_end` is added at load (P1-07), never here.
    """
    stamp = pl.Datetime("us", "UTC") if interval is Interval.HOURLY else pl.Date()
    return pl.Schema(
        {"bar_start": stamp, "ric": pl.String(), "field": pl.String(), "value": pl.Float64()}
    )


@final
@dataclass(frozen=True, slots=True)
class RawHistory:
    """Bars as asked for, in `raw_schema(interval)`. A RIC with no rows didn't answer."""

    interval: Interval
    rows: pl.DataFrame

    def __post_init__(self) -> None:
        expected = raw_schema(self.interval)
        if self.rows.schema != expected:
            raise ValueError(f"rows must be in the raw schema {expected}, got {self.rows.schema}")

    @classmethod
    def empty(cls, interval: Interval) -> "RawHistory":
        return cls(interval, pl.DataFrame(schema=raw_schema(interval)))

    def rics(self) -> frozenset[str]:
        """The RICs that answered."""
        return frozenset(self.rows["ric"].unique().to_list())


class NoDataError(Exception):
    """The service answered every RIC in the request with a no-data code (DEC-49: soft).

    A never-listed RIC, or a field a RIC doesn't carry. `codes` are the service's error codes.
    They don't say which RIC got which code, so only a single-RIC request settles a RIC.
    """

    def __init__(self, message: str, codes: tuple[str, ...]) -> None:
        super().__init__(message)
        self.message = message
        self.codes = codes


class UnreadableAnswerError(Exception):
    """An answer came back that couldn't be read into rows (DEC-83).

    lseg-data failed to build its frame (a batch holding a RIC that failed, or RICs whose answers
    carry different fields), or the frame's columns can't be attributed to RICs and fields. A
    batch is asked again one RIC at a time; a single RIC can't be split, so it counts as a failure.
    `error_class` names the original error.
    """

    def __init__(self, message: str, error_class: str) -> None:
        super().__init__(message)
        self.message = message
        self.error_class = error_class


class TransientError(Exception):
    """The request failed in a way asking again may fix (DEC-49).

    A transport failure, or a service answer that isn't a no-data code: an HTTP status from a
    failing or signed-out Workspace, a permission code, or an error with no code at all.
    """


class ProviderOutageError(Exception):
    """The provider is down: the session isn't open, or a failure persists (DEC-49: loud).

    Never recorded as "no data". The fetch aborts and writes nothing (LDG §4.3).
    """


class HistoryProvider(Protocol):
    """Bars for `rics` from `start` up to, not including, `end_exclusive` (DEC-47)."""

    def history(
        self,
        rics: Sequence[str],
        fields: Sequence[str],
        start: date,
        end_exclusive: date,
        interval: Interval,
    ) -> RawHistory: ...
