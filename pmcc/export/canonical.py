"""Canonical JSON for results (PO, DEC-50): the same values always serialize to the same bytes.

- Keys sorted; no whitespace between tokens; UTF-8 with non-ASCII kept as is; one `\\n` at the end.
- Dollars and prices are `Decimal` and print to 4 dp (`1234.5000`), as JSON numbers.
- Any other float (IV, Greeks, ratios) is rounded to 6 dp and printed by its shortest repr;
  NaN and infinities become `null`, and −0.0 prints as `0.0`.
- Times are ISO 8601 with their offset; dates are `YYYY-MM-DD`.
- A `Number` prints verbatim: `verbatim_floats` wraps a dump's floats so they print exactly as
  `json.dumps` does, unrounded, for the config section its hash covers (DEC-92).

INV-13 compares whole files once `manifest.run_timestamp` and `manifest.git_sha` are dropped
(`drop_volatile`): the run time, and the commit, which moves on once results are committed (PO,
DEC-50). `loads` keeps every number's text, so reading a canonical file and dumping it again gives
back its bytes.
"""

import json
import math
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast, final

FLOAT_PLACES = 6  # IV, Greeks and ratios
DOLLAR_PLACES = 4  # dollars and prices: whole $0.0001 units (DEC-44)
VOLATILE = ("run_timestamp", "git_sha")  # the manifest values INV-13 ignores (PO, DEC-50)


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


def drop_volatile(raw: bytes) -> bytes:
    """A result file's bytes without the manifest's `VOLATILE` values: what INV-13 compares.
    Raises `KeyError` if one is missing."""
    data = cast(dict[str, object], loads(raw))
    manifest = cast(dict[str, object], data["manifest"])
    for key in VOLATILE:
        del manifest[key]
    return to_bytes(data)


def verbatim_floats(value: object) -> object:
    """`value` with each float replaced by a `Number` holding `json.dumps`'s text for it, so it
    prints unrounded. Only for finite floats: a JSON dump has no others."""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"not a JSON number: {value!r}")
        return Number(json.dumps(value))
    if isinstance(value, Mapping):
        return {k: verbatim_floats(v) for k, v in cast(Mapping[str, object], value).items()}
    if isinstance(value, list | tuple):
        return [verbatim_floats(v) for v in cast(Sequence[object], value)]
    return value


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
