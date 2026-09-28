"""Any `get_history` answer, as long polars rows (LDG §4.5, DEC-83).

The column shape changes with the request. lseg-data 2.1.1 builds it this way (pinned by
`tests/unit/data/test_lseg_contract.py`):

- one RIC: flat field columns
- several RICs: a `(RIC, field)` MultiIndex when the first RIC to answer carries two or more
  fields, and flat RIC columns named after the last RIC's field when it carries one. In that
  flat layout each RIC gets one column, and a RIC whose answer carries more fields spills into the
  next RIC's column. So flat RIC columns are trusted only when a single field was asked.

LDG also saw `(field, RIC)` columns, so either order is read. Columns are attributed by matching
the RICs and fields that were asked for, never by position. An answer that can't be attributed is
rejected rather than guessed: asked again one RIC at a time, it comes back as flat field columns,
which always can be. pandas stops at this module's edge.
"""

# pandas has no type stubs, so pyright strict can't see through its return types (DEC-83).
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false
# pyright: reportUnknownArgumentType=false, reportMissingTypeStubs=false

from collections.abc import Sequence

import pandas as pd
import polars as pl

from pmcc.data.provider import Interval, UnreadableAnswerError, raw_schema

Label = tuple[str, str]  # (ric, field)


def to_long(
    frame: object, rics: Sequence[str], fields: Sequence[str], interval: Interval
) -> pl.DataFrame:
    """`frame` as `raw_schema(interval)` rows: asked-for RICs and fields, empty cells dropped."""
    schema = raw_schema(interval)
    if frame is None:
        return pl.DataFrame(schema=schema)
    if not isinstance(frame, pd.DataFrame):
        raise _unreadable(f"expected a DataFrame, got {type(frame).__name__}")
    if frame.empty:
        return pl.DataFrame(schema=schema)
    labels = attribute(list(frame.columns), frame.columns.name, rics, fields)
    kept = {f"c{i}": label for i, label in enumerate(labels) if label is not None}
    if not kept:
        return pl.DataFrame(schema=schema)
    names = pl.DataFrame(
        {
            "column": list(kept),
            "ric": [ric for ric, _ in kept.values()],
            "field": [name for _, name in kept.values()],
        }
    )
    return (
        _wide(frame, interval)
        .unpivot(on=list(kept), index="bar_start", variable_name="column", value_name="value")
        .join(names, on="column")
        .filter(pl.col("value").is_not_null() & pl.col("value").is_not_nan())
        .select(schema.names())
        .cast(schema)
        .sort("ric", "field", "bar_start")
    )


def attribute(
    labels: Sequence[object], name: object, rics: Sequence[str], fields: Sequence[str]
) -> list[Label | None]:
    """Each column's `(ric, field)`, or `None` for a column nobody asked for.

    `name` is the columns' name, which lseg-data sets to a field when the columns are RICs.
    """
    if labels and all(isinstance(label, tuple) for label in labels):
        return _from_pairs(labels, set(rics), set(fields))
    flat = [str(label) for label in labels]
    if set(fields) & set(flat):
        return _from_field_columns(flat, rics, set(fields))
    if set(rics) & set(flat):
        return _from_ric_columns(flat, name, set(rics), fields)
    raise _unreadable(f"columns {flat[:5]} match none of the RICs or fields asked for")


def _from_pairs(labels: Sequence[object], rics: set[str], fields: set[str]) -> list[Label | None]:
    pairs = [_pair(label) for label in labels]
    if {first for first, _ in pairs} & rics:
        ordered = pairs
    elif {second for _, second in pairs} & rics:
        ordered = [(second, first) for first, second in pairs]
    else:
        raise _unreadable(f"no level of the columns {pairs[:3]} holds the RICs asked for")
    return [(r, f) if r in rics and f in fields else None for r, f in ordered]


def _pair(label: object) -> Label:
    if not isinstance(label, tuple) or len(label) != 2:
        raise _unreadable(f"expected two column levels, got {label!r}")
    first, second = label
    return str(first), str(second)


def _from_field_columns(
    flat: Sequence[str], rics: Sequence[str], fields: set[str]
) -> list[Label | None]:
    if len(set(rics)) != 1:
        raise _unreadable(f"field columns {flat[:5]} for {len(set(rics))} RICs")
    ric = rics[0]
    return [(ric, column) if column in fields else None for column in flat]


def _from_ric_columns(
    flat: Sequence[str], name: object, rics: set[str], fields: Sequence[str]
) -> list[Label | None]:
    # With several fields asked, flat RIC columns mean the RICs' answers carried different fields,
    # and lseg-data may have filed some values under the wrong column: never trust them.
    if len(set(fields)) != 1:
        raise _unreadable(f"RIC columns for {len(set(fields))} fields asked, {list(fields)}")
    field = fields[0]
    if name is not None and str(name) != field:
        raise _unreadable(f"RIC columns named {name!r}, but only {field!r} was asked")
    return [(column, field) if column in rics else None for column in flat]


def _wide(frame: pd.DataFrame, interval: Interval) -> pl.DataFrame:
    """`bar_start` plus one Float64 column per frame column, named `c0`, `c1`, … by position."""
    positional = frame.set_axis([f"c{i}" for i in range(frame.shape[1])], axis=1)
    numeric = positional.apply(pd.to_numeric, errors="coerce").reset_index(drop=True)
    columns = list(numeric.columns)
    return (
        pl.DataFrame(numeric)
        .select(pl.col(columns).cast(pl.Float64, strict=False))
        .with_columns(_stamps(frame.index, interval))
    )


def _stamps(index: object, interval: Interval) -> pl.Series:
    """LSEG's stamps: intraday ones are tz-naive UTC bar starts (LDG §4.8); daily ones are dates."""
    if not isinstance(index, pd.DatetimeIndex):
        raise _unreadable(f"expected a DatetimeIndex, got {type(index).__name__}")
    if interval is Interval.DAILY:  # a date is a date: no zone to convert
        days = index if index.tz is None else index.tz_localize(None)
        return pl.Series("bar_start", days.to_numpy()).cast(pl.Date)
    utc = index if index.tz is None else index.tz_convert("UTC").tz_localize(None)
    return (
        pl.Series("bar_start", utc.to_numpy()).cast(pl.Datetime("us")).dt.replace_time_zone("UTC")
    )


def _unreadable(detail: str) -> UnreadableAnswerError:
    return UnreadableAnswerError(
        f"can't attribute the answer to RICs and fields: {detail}", "Unattributable"
    )
