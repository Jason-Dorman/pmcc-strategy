"""Canonical JSON for results (PO, DEC-50): the same values always serialize to the same bytes.

- Keys sorted; no whitespace between tokens; UTF-8 with non-ASCII kept as is; one `\\n` at the end.
- Dollars and prices are `Decimal` and print to 4 dp (`1234.5000`), as JSON numbers.
- Any other float (IV, Greeks, ratios) is rounded to 6 dp and printed by its shortest repr;
  NaN and infinities become `null`, and −0.0 prints as `0.0`.
- Times are ISO 8601 with their offset; dates are `YYYY-MM-DD`.

INV-13 compares whole files once `manifest.run_timestamp`, the only value that changes from run to
run, is dropped (`drop_run_timestamp`). `loads` keeps every number's text, so reading a canonical
file and dumping it again gives back its bytes.
"""

import json
import math
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast, final

FLOAT_PLACES = 6  # IV, Greeks and ratios
DOLLAR_PLACES = 4  # dollars and prices: whole $0.0001 units (DEC-44)
VOLATILE = ("manifest", "run_timestamp")  # the one value INV-13 ignores


@final
class Number(str):
    """A JSON number's text as read by `loads`; dumped back verbatim."""

    __slots__ = ()


def dumps(value: object) -> str:
    """`value` as canonical JSON text, ending in a newline."""
    return _encode(value) + "\n"


def to_bytes(value: object) -> bytes:
    return dumps(value).encode("utf-8")


def loads(text: str | bytes) -> object:
    """Parse JSON, keeping each number's text (`Number`) so `dumps` reproduces it exactly."""
    return json.loads(text, parse_float=Number, parse_int=Number)


def drop_run_timestamp(raw: bytes) -> bytes:
    """A result file's bytes without `manifest.run_timestamp`: what INV-13 compares."""
    data = cast(dict[str, object], loads(raw))
    section, key = VOLATILE
    manifest = cast(dict[str, object], data[section])
    del manifest[key]
    return to_bytes(data)


def _encode(value: object) -> str:
    scalar = _scalar(value)
    if scalar is not None:
        return scalar
    if isinstance(value, Mapping):
        return _object(cast(Mapping[object, object], value))
    if isinstance(value, list | tuple):  # not any Sequence: bytes would print as numbers
        return "[" + ",".join(_encode(v) for v in cast(Sequence[object], value)) + "]"
    raise TypeError(f"no canonical JSON form for {type(value).__name__}: {value!r}")


def _scalar(value: object) -> str | None:
    """A JSON scalar's text, or `None` for a container. `bool` before `int`, `Number` before
    `str` and `datetime` before `date`: each is a subclass of the other."""
    for kind, encode in _SCALARS:
        if isinstance(value, kind):
            return encode(value)
    return None


def _object(mapping: Mapping[object, object]) -> str:
    keys = list(mapping)
    if not all(isinstance(k, str) for k in keys):
        raise TypeError(f"JSON object keys must be strings: {keys!r}")
    items = sorted(cast(list[str], keys))
    return "{" + ",".join(f"{_string(k)}:{_encode(mapping[k])}" for k in items) + "}"


def _string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _float(value: float) -> str:
    if not math.isfinite(value):
        return "null"
    return float.__repr__(round(value, FLOAT_PLACES) + 0.0)  # + 0.0: −0.0 → 0.0


def _dollars(value: Decimal) -> str:
    if not value.is_finite():
        raise ValueError(f"a dollar amount must be finite: {value!r}")
    exact = value.quantize(Decimal(1).scaleb(-DOLLAR_PLACES))
    if exact != value:
        raise ValueError(f"a dollar amount must be whole $0.0001 units: {value}")
    return "0.0000" if exact.is_zero() else f"{exact:f}"  # never "-0.0000"


def _time(value: datetime) -> str:
    if value.utcoffset() is None:
        raise ValueError(f"a time must carry its offset: {value.isoformat()}")
    return _string(value.isoformat())


def _date(value: date) -> str:
    return _string(value.isoformat())


_SCALARS: tuple[tuple[type[Any], Callable[[Any], str]], ...] = (
    (type(None), lambda _v: "null"),
    (bool, lambda v: "true" if v else "false"),
    (Number, str),
    (str, _string),
    (int, str),
    (float, _float),
    (Decimal, _dollars),
    (datetime, _time),
    (date, _date),
)
