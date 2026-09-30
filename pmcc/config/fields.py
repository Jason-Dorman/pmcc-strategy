"""Pydantic field types for config values the domain types hold: dollars as integer units (DEC-44),
an ET clock time, and a rule ID. Each serializes to plain JSON, so the config hash can cover it."""

import re
from datetime import time
from decimal import Decimal
from typing import Annotated

from pydantic import PlainSerializer, PlainValidator, WithJsonSchema

from pmcc.domain import Money, Price, RuleId

_HH_MM = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")
_DOLLAR_TEXT = re.compile(r"[0-9]+\.[0-9]{4}")  # how a dollar field serializes
_UNIT = Decimal("0.0001")


def _dollars(value: object) -> Decimal:
    """A non-negative dollar amount, exact to $0.0001 (DEC-44): a YAML number, or the "0.1000"
    string it serializes to. Never a bool or any other string, and never rounded."""
    if isinstance(value, str) and _DOLLAR_TEXT.fullmatch(value):
        amount = Decimal(value)
    elif isinstance(value, int | float) and not isinstance(value, bool):
        amount = Decimal(float.__repr__(value) if isinstance(value, float) else value)
    else:
        raise ValueError(f"not a dollar amount: {value!r}")
    if not amount.is_finite() or amount < 0:
        raise ValueError(f"a dollar amount must be finite and not negative: {value!r}")
    try:
        exact = amount == amount.quantize(_UNIT)
    except ArithmeticError:  # too many digits to quantize
        exact = False
    if not exact:
        raise ValueError(f"a dollar amount must be exact to $0.0001: {value!r}")
    return amount


def _price(value: object) -> Price:
    return value if isinstance(value, Price) else Price.from_dollars(_dollars(value))


def _money(value: object) -> Money:
    return value if isinstance(value, Money) else Money.from_dollars(_dollars(value))


def _clock(value: object) -> time:
    """A quoted "HH:MM" only: unquoted, YAML 1.1 reads 15:00 as the integer 900."""
    if isinstance(value, time):
        return value
    if not isinstance(value, str) or not _HH_MM.fullmatch(value):
        raise ValueError(f'a clock time is a quoted "HH:MM", got {value!r}')
    return time.fromisoformat(value)


def _rule_id(value: object) -> RuleId:
    if not isinstance(value, str):
        raise ValueError(f"not a rule ID: {value!r}")
    return RuleId(value)


_DOLLARS_SCHEMA = WithJsonSchema({"type": "string", "pattern": f"^{_DOLLAR_TEXT.pattern}$"})

DollarPrice = Annotated[
    Price,
    PlainValidator(_price),
    PlainSerializer(lambda p: str(p.to_dollars()), return_type=str),
    _DOLLARS_SCHEMA,
]
"""A per-share threshold in dollars, held as a `Price`; serialized as "0.1000"."""

DollarMoney = Annotated[
    Money,
    PlainValidator(_money),
    PlainSerializer(lambda m: str(m.to_dollars()), return_type=str),
    _DOLLARS_SCHEMA,
]
"""A cash amount in dollars, held as `Money`; serialized as "0.0000"."""

ClockTime = Annotated[
    time,
    PlainValidator(_clock),
    PlainSerializer(lambda t: t.strftime("%H:%M"), return_type=str),
    WithJsonSchema({"type": "string", "pattern": _HH_MM.pattern}),
]
"""A wall-clock time in ET, written "HH:MM"."""

RuleIdField = Annotated[
    RuleId,
    PlainValidator(_rule_id),
    PlainSerializer(str, return_type=str),
    WithJsonSchema({"type": "string"}),
]
"""A well-formed rule ID (`E-T1`, `G-3`, …)."""
