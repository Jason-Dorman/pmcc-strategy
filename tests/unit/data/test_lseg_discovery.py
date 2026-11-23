"""LSEG's search and column-agnostic daily history (T1-01): frames in, plain rows out, every failure
one of the port's classes."""

# pandas has no type stubs (DEC-83).
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd
import pytest

from pmcc.data.lseg.discovery import LsegDiscovery
from pmcc.data.provider import ProviderOutageError, TransientError, UnreadableAnswerError
from tests.fakes.lseg import OpenState


@dataclass
class _State:
    open_state: OpenState = OpenState.Opened


@dataclass
class _Sessions:
    state: _State = field(default_factory=_State)

    def get_default(self) -> _State:
        return self.state


@dataclass
class _Search:
    answer: object = None
    error: Exception | None = None
    asked: list[dict[str, object]] = field(default_factory=list[dict[str, object]])

    def search(
        self, *, query: str | None = None, select: str | None = None, top: int = 10
    ) -> object:
        self.asked.append({"query": query, "select": select, "top": top})
        if self.error is not None:
            raise self.error
        return self.answer


@dataclass
class _Api:
    discovery: _Search = field(default_factory=_Search)
    session: _Sessions = field(default_factory=_Sessions)
    history: object = None
    history_error: Exception | None = None
    asked: list[dict[str, object]] = field(default_factory=list[dict[str, object]])

    def get_history(
        self,
        universe: str | Iterable[str],
        fields: str | Iterable[str] | None = None,
        interval: str | None = None,
        start: str | date | datetime | None = None,
        end: str | date | datetime | None = None,
    ) -> object:
        self.asked.append({"universe": universe, "fields": fields, "interval": interval})
        if self.history_error is not None:
            raise self.history_error
        return self.history


class LDError(Exception):
    pass


def test_t1_01_search_returns_rows_as_strings_with_none_for_empty() -> None:
    api = _Api(
        _Search(pd.DataFrame({"RIC": ["A=X", None], "DocumentTitle": ["HY OAS", float("nan")]}))
    )
    rows = LsegDiscovery(api).search("high yield", "RIC,DocumentTitle", 5)

    assert rows == [{"RIC": "A=X", "DocumentTitle": "HY OAS"}, {"RIC": None, "DocumentTitle": None}]
    assert api.discovery.asked == [{"query": "high yield", "select": "RIC,DocumentTitle", "top": 5}]


def test_t1_01_table_keeps_every_column_lseg_sends() -> None:
    frame = pd.DataFrame(
        {"VALUE": [3.52, None], "MID_YLD_1": [7.1, 7.2]},
        index=pd.DatetimeIndex(["2024-01-02", "2024-01-03"]),
    )
    api = _Api(history=frame)
    table = LsegDiscovery(api).table("A=X", date(2014, 1, 1), date(2024, 1, 4))

    assert table.columns == ("VALUE", "MID_YLD_1")
    assert table.rows == ((date(2024, 1, 2), (3.52, 7.1)), (date(2024, 1, 3), (None, 7.2)))
    assert table.column("VALUE") == ((date(2024, 1, 2), 3.52),)
    assert api.asked == [{"universe": "A=X", "fields": None, "interval": "daily"}]


def test_t1_01_none_is_unreadable_not_an_empty_table() -> None:
    with pytest.raises(UnreadableAnswerError):
        LsegDiscovery(_Api(history=None)).table("A=X", date(2024, 1, 1), date(2024, 1, 2))


def test_t1_01_an_empty_answer_is_an_empty_table() -> None:
    assert (
        LsegDiscovery(_Api(history=pd.DataFrame()))
        .table("A=X", date(2024, 1, 1), date(2024, 1, 2))
        .rows
        == ()
    )


def test_t1_01_a_closed_session_asks_nothing() -> None:
    api = _Api()
    api.session.state.open_state = OpenState.Closed
    with pytest.raises(ProviderOutageError):
        LsegDiscovery(api).search("x", "RIC", 1)
    assert api.discovery.asked == []


def test_t1_01_an_lseg_error_is_transient() -> None:
    api = _Api(_Search(error=LDError("Error code 400 | bad query")))
    with pytest.raises(TransientError, match="LDError: Error code 400"):
        LsegDiscovery(api).search("x", "RIC", 1)


def test_t1_01_an_answer_that_isnt_a_frame_is_unreadable() -> None:
    with pytest.raises(UnreadableAnswerError):
        LsegDiscovery(_Api(history=[1, 2])).table("A=X", date(2024, 1, 1), date(2024, 1, 2))
