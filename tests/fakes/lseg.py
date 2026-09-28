"""`FakeLseg`: a stand-in for `lseg.data` that answers and fails as lseg-data 2.1.1 does (DEC-83).

Its `get_history` follows the real one:

1. LSEG's historical-pricing service answers each RIC on its own: bars, a service error code (a
   never-listed RIC, a field the RIC doesn't carry), or an HTTP status (a failing or signed-out
   Workspace).
2. A transport failure anywhere in the request fails all of it. lseg-data keeps only the
   exception's text and raises a new `LDError` with no cause and no context.
3. If no RIC answered, lseg-data raises an `LDError` listing each failure's code
   (`no_data_message`, a port of its `validate_responses`).
4. Otherwise it builds a frame: `build_one` and `build` port its `HistoricalBuilder`, quirks
   included. An hourly batch holding a failed RIC raises the `UniverseContainer` TypeError (LDG
   §4.4), a daily one answers without it, and RICs whose answers carry different fields raise or
   file values under the wrong column.

A desktop session never leaves Opened on its own, so a dead Workspace shows up only as failing
requests. `tests/unit/data/test_lseg_contract.py` feeds the same answers to lseg-data's own code,
so the port can't drift from the library. `fake_provider(fake)` wraps it in the real
`LsegProvider`: that is the FakeProvider, and only the network is fake. It records every request,
with whether the session was open when it came in.
"""

# pandas has no type stubs, so pyright strict can't see through its return types (DEC-83).
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false

from collections.abc import Callable, Collection, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import cast

import pandas as pd

from pmcc.data.lseg import LsegProvider

# Bar starts as LSEG stamps them: UTC, at the bar's start (LDG §4.8).
HOURS = (datetime(2026, 9, 14, 17), datetime(2026, 9, 14, 18), datetime(2026, 9, 14, 19))
DAYS = (datetime(2026, 9, 14), datetime(2026, 9, 15))

# Service codes. 90001 is lseg-data's own "universe is not found". The daily code and the missing-
# field code are assumptions: the P1-04 probes record the real ones (DEC-83).
NOT_FOUND = {
    "hourly": "TS.Intraday.UserRequestError.90001",
    "daily": "TS.Interday.UserRequestError.90001",
}
FIELD_NOT_CARRIED = "TS.Intraday.UserRequestError.90006"
PERMISSION_DENIED = "TS.Intraday.UserNotPermission.92000"
HTTP_REASONS = {
    401: "Unauthorized",
    403: "Forbidden",
    500: "Internal Server Error",
    503: "Service Unavailable",
}
# What lseg-data keeps of a transport failure: the text of httpx's exception.
TIMED_OUT = "timed out"
REFUSED = "All connection attempts failed"

_STAMP_HEADERS = frozenset({"DATE_TIME", "DATE"})
_NOT_SUBSCRIPTABLE = "'UniverseContainer' object is not subscriptable"

# One RIC's bars: field -> one value per bar (None is an empty cell).
Bars = Mapping[str, Sequence[float | None]]


class LDError(Exception):
    """Mimics `lseg.data.errors.LDError`. `str()` is the message alone when there is no code,
    as for everything `get_history` raises."""

    def __init__(self, code: int | None = None, message: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"Error code {self.code} | {self.message}" if self.code else f"{self.message}"


class OpenState(Enum):
    """Mimics `lseg.data.OpenState`."""

    Opened = "Opened"
    Pending = "Pending"
    Closed = "Closed"


@dataclass(frozen=True)
class Answer:
    """One RIC's answer from the service, as lseg-data holds it. `raw` is what its frame builder
    sees; `error` is the (code, message) of a failed answer."""

    ric: str
    raw: object
    error: tuple[str | int, str] | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True)
class Request:
    """One `get_history` call as the fake received it."""

    universe: tuple[str, ...]
    fields: tuple[str, ...]
    interval: str | None
    start: str | None
    end: str | None
    session_open: bool


class _Session:
    def __init__(self, fake: "FakeLseg") -> None:
        self._fake = fake

    @property
    def open_state(self) -> OpenState:
        return self._fake.state


class _Sessions:
    def __init__(self, fake: "FakeLseg") -> None:
        self._default = _Session(fake)

    def get_default(self) -> _Session:
        return self._default


@dataclass
class FakeLseg:
    """The `lseg.data` surface `pmcc.data.lseg` uses, scripted per test.

    - `listed`: the RICs the service knows, with their bars. Any other RIC is never listed.
    - `carried`: the fields every RIC carries; a RIC asked for another fails with
      `FIELD_NOT_CARRIED`. `None` means every field asked for.
    - `answers_with`: RICs whose answer carries only these of the fields asked.
    - `http_status`: RICs whose own request fails with an HTTP status.
    - `every_status`: every RIC fails with this HTTP status, as from a signed-out Workspace.
    - `denied`: RICs the account may not see (`PERMISSION_DENIED`).
    - `timeouts`: how many calls in a row time out before the proxy answers again.
    - `dies_after`: Workspace quits after this many calls are served; every later call is refused
      while the session still reports Opened.
    - `raises`: exceptions the next calls raise as they are (or factories that make them at the
      call), for errors lseg-data doesn't produce today (an unwrapped transport error, a bug).
    - `opens_to` and `open_error`: the state `open_session` leaves, and what it raises. It
      doesn't raise when the handshake fails; it leaves the session Closed or Pending (LDG §4.2).
    """

    listed: Mapping[str, Bars] = field(default_factory=dict[str, Bars])
    carried: Collection[str] | None = None
    answers_with: Mapping[str, Collection[str]] = field(default_factory=dict[str, Collection[str]])
    http_status: Mapping[str, int] = field(default_factory=dict[str, int])
    every_status: int | None = None
    denied: Collection[str] = ()
    timeouts: int = 0
    dies_after: int | None = None
    raises: list[Exception | Callable[[], Exception]] = field(
        default_factory=list[Exception | Callable[[], Exception]]
    )
    opens_to: OpenState = OpenState.Opened
    open_error: Exception | None = None
    index: Sequence[datetime] = HOURS
    state: OpenState = OpenState.Closed
    requests: list[Request] = field(default_factory=list[Request])
    opened_with: list[str | None] = field(default_factory=list[str | None])
    closes: int = 0
    served: int = 0

    def __post_init__(self) -> None:
        self.session = _Sessions(self)

    def open_session(
        self, name: str | None = None, app_key: str | None = None, config_name: str | None = None
    ) -> _Session:
        self.opened_with.append(config_name)
        if self.open_error is not None:
            raise self.open_error
        self.state = self.opens_to
        return self.session.get_default()

    def close_session(self) -> None:
        self.closes += 1
        self.state = OpenState.Closed

    def get_history(
        self,
        universe: str | Iterable[str],
        fields: str | Iterable[str] | None = None,
        interval: str | None = None,
        start: str | date | datetime | None = None,
        end: str | date | datetime | None = None,
    ) -> pd.DataFrame:
        rics, wanted = _as_tuple(universe), _as_tuple(fields or ())
        open_now = self.state is OpenState.Opened
        self.requests.append(Request(rics, wanted, interval, _text(start), _text(end), open_now))
        if self.state is OpenState.Closed:  # lseg-data's raise_if_closed
            raise ValueError("Session is not opened. Can't send any request")
        if self.raises:
            scripted = self.raises.pop(0)
            raise scripted if isinstance(scripted, Exception) else scripted()
        failure = self._transport_failure()
        if failure is not None:
            raise LDError(message=failure)
        answers = self.answers(rics, wanted, interval or "daily")
        self._serve()
        if not any(a.ok for a in answers):
            raise LDError(message=no_data_message(answers))
        axis = "Date" if interval == "daily" else "Timestamp"
        if len(rics) == 1:
            return build_one(answers[0].raw, wanted, axis)
        return build([a.raw for a in answers], wanted, axis)

    def answers(self, rics: Sequence[str], wanted: Sequence[str], interval: str) -> list[Answer]:
        """Each RIC's answer from the service, before lseg-data sees them."""
        return [self._answer(ric, wanted, interval) for ric in rics]

    def _transport_failure(self) -> str | None:
        if self.state is OpenState.Pending:  # the handshake never finished
            return TIMED_OUT
        if self.dies_after is not None and self.served >= self.dies_after:
            return REFUSED
        if self.timeouts > 0:
            self.timeouts -= 1
            return TIMED_OUT
        return None

    def _serve(self) -> None:
        self.served += 1

    def _answer(self, ric: str, wanted: Sequence[str], interval: str) -> Answer:
        status = self.every_status or self.http_status.get(ric)
        if status is not None:
            return _failed(ric, interval, status, HTTP_REASONS.get(status, "HTTP error"), http=True)
        if ric not in self.listed:
            return _failed(ric, interval, NOT_FOUND[interval], f"{ric} - The universe is not found")
        if ric in self.denied:
            return _failed(ric, interval, PERMISSION_DENIED, "The user has no permission")
        if self.carried is not None and not set(wanted) <= set(self.carried):
            message = f"Invalid field(s) {sorted(set(wanted) - set(self.carried))}"
            return _failed(ric, interval, FIELD_NOT_CARRIED, f"{message}. Requested ric: {ric}")
        keep = self.answers_with.get(ric, wanted)
        carried = [f for f in wanted if f in keep]
        return Answer(ric, self._raw(ric, carried, interval))

    def _raw(self, ric: str, carried: Sequence[str], interval: str) -> dict[str, object]:
        stamp = "DATE" if interval == "daily" else "DATE_TIME"
        headers = [{"name": stamp}] + [{"name": f} for f in carried]
        bars = self.listed[ric]
        rows: list[list[object]] = []
        for i, start in enumerate(self.index):
            values = [_cell(bars.get(f), i) for f in carried]
            if any(v is not None for v in values):
                rows.append([_stamp_text(start, interval), *values])
        rows.reverse()  # the service answers newest first
        return {"universe": {"ric": ric}, "headers": headers, "data": rows}


def fake_provider(fake: FakeLseg) -> LsegProvider:
    """The FakeProvider: the real `LsegProvider` over `fake`, with its session open."""
    fake.state = OpenState.Opened
    return LsegProvider(fake)


def no_data_message(answers: Sequence[Answer]) -> str:
    """A port of lseg-data's `validate_responses`: each distinct code once, with its message up
    to the first dot (which cuts a RIC at its ".U")."""
    text, seen = "ERROR: No successful response.\n", set[str | int]()
    for answer in answers:
        if answer.error is None or answer.error[0] in seen:
            continue
        code, message = answer.error
        seen.add(code)
        head = message.split(".", maxsplit=1)[0] if "." in message else message
        text += f"({code}, {head}), "
    return f"No data to return, please check errors: {text[:-2]}"


def no_data_error_for(ric: str, interval: str = "hourly") -> LDError:
    """The `LDError` lseg-data raises when `ric`, asked alone, was never listed."""
    answer = _failed(ric, interval, NOT_FOUND[interval], f"{ric} - The universe is not found")
    return LDError(message=no_data_message([answer]))


def lseg_timestamp(text: str) -> pd.Timestamp:
    """lseg-data's `convert_str_to_timestamp`: read as UTC, returned tz-naive."""
    return pd.to_datetime(text, utc=True, errors="coerce").tz_localize(None)


def build_one(raw: object, fields: Sequence[str], axis: str) -> pd.DataFrame:
    """A port of lseg-data's `HistoricalBuilder.build_one`: one RIC, flat field columns."""
    assert isinstance(raw, dict)
    if not raw.get("data"):
        return pd.DataFrame()
    names, stamp_at = _headers(raw)
    order = _ordered(names, fields)
    index: list[pd.Timestamp] = []
    data: list[list[object]] = []
    for row in raw["data"]:
        cells = _cells(row)
        index.append(lseg_timestamp(str(cells.pop(stamp_at))))
        data.append([cells[i] for i in order])
    columns = pd.Index([names[i] for i in order], name=raw["universe"]["ric"])
    frame = pd.DataFrame(data=data, columns=columns, index=pd.Index(index, name=axis))
    return frame.convert_dtypes().sort_index()


def build(raws: Sequence[object], fields: Sequence[str], axis: str) -> pd.DataFrame:
    """A port of lseg-data's `HistoricalBuilder.build`, quirks included.

    The first RIC to answer decides the layout: one column per RIC if its answer carries one
    field, else one per (RIC, field). The last RIC to answer decides the labels. A failed RIC's
    raw raises where lseg-data subscripts its `UniverseContainer` (`BadRaws.append`).
    """
    one_header: bool | None = None
    slots: list[list[object]] = []
    last: list[str] = []
    bad: list[tuple[int, str]] = []
    items: dict[pd.Timestamp, list[tuple[int, list[object], list[str]]]] = {}
    for at, raw in enumerate(raws):
        failed = _failed_ric(raw)
        if failed is not None:
            bad.append((at, failed))
            continue
        assert isinstance(raw, dict)
        names, stamp_at = _headers(raw)
        order = _ordered(names, fields)
        columns = [names[i] for i in order]
        for row in raw["data"]:
            cells = _cells(row)
            stamp = lseg_timestamp(str(cells.pop(stamp_at)))
            items.setdefault(stamp, []).append((at, [cells[i] for i in order], columns))
        if one_header is None:
            one_header = len(columns) == 1
        slots.append(_slot(raw["universe"]["ric"], columns, one_header))
        last = columns
    if not items:
        return pd.DataFrame()
    for at, ric in bad:
        slots.insert(at, _slot(ric, last, bool(one_header)))
    return _frame(items, slots, last, len(raws), axis)


def _frame(
    items: Mapping[pd.Timestamp, Sequence[tuple[int, list[object], list[str]]]],
    slots: Sequence[Sequence[object]],
    last: Sequence[str],
    num_raws: int,
    axis: str,
) -> pd.DataFrame:
    """lseg-data's `ItemsByDate.process_data`: each RIC's values are written from its first
    column onward, across as many columns as its answer carries."""
    offsets = {i: sum(len(s) for s in slots[:i]) for i in range(num_raws)}
    flat = [label for slot in slots for label in slot]
    data: list[list[object]] = []
    index: list[pd.Timestamp] = []
    for stamp, entries in items.items():
        previous: int | None = None
        row = _empty_row(len(flat))
        for counter, (at, values, columns) in enumerate(entries):
            if (counter != 0 and counter % num_raws == 0) or previous == at:
                index.append(stamp)
                data.append(row)
                row = _empty_row(len(flat))
                previous = at
            if previous is None:
                previous = at
            left = offsets[at]
            for value, i in zip(values, range(left, left + len(columns)), strict=False):
                row[i] = value  # past the last column this raises IndexError, as in lseg-data
        index.append(stamp)
        data.append(row)
    labels = (
        pd.Index(flat, name=last[0])
        if len(last) == 1
        else pd.MultiIndex.from_tuples(cast("list[tuple[Hashable, ...]]", flat))
    )
    frame = pd.DataFrame(data=data, columns=labels, index=pd.Index(index, name=axis))
    return frame.convert_dtypes().sort_index()


def _cells(row: Iterable[object]) -> list[object]:
    """lseg-data's `NotNoneList`: a row's values, with None as pandas' NA."""
    return [pd.NA if v is None else v for v in row]


def _empty_row(width: int) -> list[object]:
    return [pd.NA] * width


def _failed(
    ric: str, interval: str, code: str | int, message: str, *, http: bool = False
) -> Answer:
    """A failed RIC's answer. Hourly requests page, and a failed page leaves lseg-data a raw
    with no headers; a daily request keeps the service's error, or the HTTP error body."""
    if interval != "daily":
        raw: object = {"data": []}
    elif http:
        raw = {"error": {"code": code, "message": message}}
    else:
        raw = [{"universe": {"ric": ric}, "status": {"code": code, "message": message}}]
    return Answer(ric, raw, (code, message))


def _failed_ric(raw: object) -> str | None:
    """lseg-data's `BadRaws.append`: the RIC of a failed answer, `None` for a good one."""
    if not raw:
        raise TypeError(_NOT_SUBSCRIPTABLE)
    if isinstance(raw, list):
        first = raw[0]
        assert isinstance(first, dict)
        return str(first["universe"]["ric"])
    if isinstance(raw, dict) and not raw.get("headers"):
        raise TypeError(_NOT_SUBSCRIPTABLE)
    return None


def _headers(raw: dict[str, object]) -> tuple[list[str], int]:
    """lseg-data's `HPHeaders`: the field names, and where the timestamp sits in a row."""
    names: list[str] = []
    stamp_at = -1
    headers = raw["headers"]
    assert isinstance(headers, list)
    for i, header in enumerate(headers):
        assert isinstance(header, dict)
        if header["name"] in _STAMP_HEADERS:
            stamp_at = i
            continue
        names.append(str(header["name"]))
    return names, stamp_at


def _ordered(names: Sequence[str], fields: Sequence[str]) -> list[int]:
    """lseg-data's `sort_columns`: positions of `names` in the order the fields were asked,
    names nobody asked for first."""
    upper = [f.upper() for f in fields]

    def key(i: int) -> int:
        try:
            return upper.index(names[i].upper())
        except ValueError:
            return 0

    return sorted(range(len(names)), key=key)


def _slot(ric: str, columns: Sequence[str], one_header: bool) -> list[object]:
    return [ric] if one_header else [(ric, column) for column in columns]


def _cell(values: Sequence[float | None] | None, i: int) -> float | None:
    return None if values is None or i >= len(values) else values[i]


def _stamp_text(start: datetime, interval: str) -> str:
    return f"{start:%Y-%m-%d}" if interval == "daily" else f"{start:%Y-%m-%dT%H:%M:%S}.000000000Z"


def _text(value: str | date | datetime | None) -> str | None:
    return None if value is None else str(value)


def _as_tuple(value: str | Iterable[str]) -> tuple[str, ...]:
    return (value,) if isinstance(value, str) else tuple(value)
