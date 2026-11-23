"""LSEG's search, and a daily history read with whatever columns LSEG returns (T1-01; TD-04, TD-05).

The thesis's probe looks for a series it doesn't know the RIC or fields of (ICE BofA US High Yield
OAS), so `LsegProvider`'s history, which keeps only the fields asked for, can't read it. Here:

- `search`: lseg-data's `discovery.search`, its rows as plain dicts of strings.
- `table`: `get_history` with no fields, on a daily interval, every column kept as LSEG named it.

Both ask through lseg-data's default session, which `platform_session` opens and checks first;
each checks it is still Opened before asking (else `ProviderOutageError`). An error lseg-data
raises comes back as a `TransientError` with its class and text, and an answer that isn't a table
as an `UnreadableAnswerError`, for the probe to report beside the other answers. The table is the
port's `DailyTable`. pandas stops at this module's edge.
"""

# pandas has no type stubs, so pyright strict can't see through its return types (DEC-83).
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false

import math
from collections.abc import Iterable
from datetime import date, datetime
from typing import Protocol

import pandas as pd

from pmcc.data.lseg.api import LsegSessions
from pmcc.data.lseg.provider import is_open
from pmcc.data.provider import (
    DailyTable,
    ProviderOutageError,
    TransientError,
    UnreadableAnswerError,
)

DAILY = "daily"


class LsegSearch(Protocol):
    def search(
        self, *, query: str | None = None, select: str | None = None, top: int = 10
    ) -> object: ...


class DiscoveryApi(Protocol):
    """The slice of `lseg.data` this module calls."""

    @property
    def session(self) -> LsegSessions: ...

    @property
    def discovery(self) -> LsegSearch: ...

    def get_history(
        self,
        universe: str | Iterable[str],
        fields: str | Iterable[str] | None = None,
        interval: str | None = None,
        start: str | date | datetime | None = None,
        end: str | date | datetime | None = None,
    ) -> object: ...


class LsegDiscovery:
    """Search and column-agnostic daily history over lseg-data's open default session."""

    def __init__(self, api: DiscoveryApi) -> None:
        self._api = api

    def search(self, query: str, select: str, top: int) -> list[dict[str, str | None]]:
        """Up to `top` documents matching `query`, with the `select` properties LSEG returns."""
        self._check_open()
        try:
            frame = self._api.discovery.search(query=query, select=select, top=top)
        except Exception as exc:
            raise TransientError(f"{type(exc).__name__}: {exc}") from exc
        records = _frame(frame).to_dict("records")
        return [{str(k): _text(v) for k, v in row.items()} for row in records]

    def table(self, ric: str, start: date, end_exclusive: date) -> DailyTable:
        """`ric`'s daily rows from `start` up to `end_exclusive`, every column LSEG sends."""
        self._check_open()
        try:
            frame = self._api.get_history(
                universe=ric, interval=DAILY, start=start.isoformat(), end=end_exclusive.isoformat()
            )
        except Exception as exc:
            raise TransientError(f"{type(exc).__name__}: {exc}") from exc
        return _table(ric, _frame(frame))

    def _check_open(self) -> None:
        if not is_open(self._api.session.get_default().open_state):
            raise ProviderOutageError("the LSEG session is not open; nothing was requested")


def _frame(frame: object) -> pd.DataFrame:
    # None isn't an empty answer: lseg-data returns a DataFrame, empty when there are no rows, so
    # None is unreadable, never "no data".
    if not isinstance(frame, pd.DataFrame):
        detail = f"expected a DataFrame, got {type(frame).__name__}"
        raise UnreadableAnswerError(detail, "NotATable")
    return frame


def _table(ric: str, frame: pd.DataFrame) -> DailyTable:
    if frame.empty:
        return DailyTable(ric, tuple(str(c) for c in frame.columns), ())
    if not isinstance(frame.index, pd.DatetimeIndex):
        raise UnreadableAnswerError(
            f"expected a DatetimeIndex, got {type(frame.index).__name__}", "NotATable"
        )
    columns = tuple(str(c) for c in frame.columns)
    numeric = frame.apply(pd.to_numeric, errors="coerce")
    days = [stamp.date() for stamp in frame.index]
    rows = tuple(
        (day, tuple(_number(v) for v in values))
        for day, values in zip(days, numeric.itertuples(index=False, name=None), strict=True)
    )
    return DailyTable(ric, columns, rows)


def _number(value: object) -> float | None:
    if isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value):
        return float(value)
    return None


def _text(value: object) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return str(value)


def lseg_discovery() -> LsegDiscovery:
    """Over lseg-data's default session: open it with `platform_session` first."""
    import lseg.data as ld

    return LsegDiscovery(ld)
