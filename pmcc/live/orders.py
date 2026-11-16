"""Orders in the course's order language (Sanji's) and `open_orders.json` (LIVE-SPEC › Orders).

The order page (https://jakevestal.github.io/server-logic-533/order.html) defines the language. An
order is `rejected` there for an unknown field, an unknown token, a missing required field, or a
quantity below 1; this module checks each of those before anything is written (LINV-01), along with
the page's per-field rules:

- `for` is a date, `YYYY-MM-DD` (never "next"); whether it is a session is the run's check
  (LINV-05). `qty` and `underlying` (an IBKR conid, not a ticker) are whole numbers of at least 1;
  `order_type`, `action`, `contract` and `ref` take the page's values only.
- A limit order needs `lmt_prc`; a market order mustn't have one. A put or call needs `expiry` and
  `strike`; shares (`contract: underlying`) carry neither. A field is given or left out: `null` is
  never a value. A date expiry is on or after `for`.
- Tokens are strings, in the page's forms: expiry `NDTE+`, `NDTE-`, `NDTE`, a date, `W+`, `M+`;
  strike a number, `atm`, `otm:N`, `itm:N`, `pct:±X`, `delta:X` (no sign, below 100), `premium:X`
  (`vega:` is reserved and rejected); limit a number, `mid`, `bid`, `ask`, or one of those three
  plus or minus a dollar amount.
- An id is used once in the file (LD-19). The page's "Unique in the repo" also means not in
  Sanji's `fills.json`; the run checks that, since it needs Sanji's book (L2-02, L2-03).

Book-dependent rules (a `SEL` with no long, a `BTC` with no short) aren't the language's; the
live rules check them (L2-03). The file is the page's shape: a JSON list, `[]` for an empty book.
It's written whole, LF, two-space indent, the page's field order, absent fields left out.
"""

import json
import re
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_core import ErrorDetails

from pmcc.data.files import replace_file
from pmcc.domain.instruments import Right
from pmcc.domain.money import Price

FIELD_ORDER = (
    "id",
    "for",
    "order_type",
    "action",
    "qty",
    "underlying",
    "contract",
    "expiry",
    "strike",
    "ref",
    "lmt_prc",
)

_NUMBER = r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?"
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_EXPIRY = re.compile(r"(?:0|[1-9][0-9]*)DTE[+-]?|W\+|M\+")
_STRIKE_NUMBER = re.compile(_NUMBER)
_STRIKE_STEPS = re.compile(r"(?:otm|itm):[1-9][0-9]*")
# Whole percents only: the page shows `pct:-5` and no decimal, and an unknown token is rejected
_STRIKE_PCT = re.compile(r"pct:[+-]?(?:0|[1-9][0-9]*)")
_STRIKE_POSITIVE = re.compile(rf"(?P<kind>delta|premium):(?P<value>{_NUMBER})")
_LIMIT = re.compile(rf"{_NUMBER}|(?:mid|bid|ask)(?:[+-]{_NUMBER})?")
_MAX_DELTA = 100


class OrderError(ValueError):
    """An order the language rejects, or an order file that can't be read. Nothing is written."""


class Order(BaseModel):
    """One order, as the page defines it. `for` is `for_` here, since `for` is a keyword."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, populate_by_name=True)

    id: str = Field(min_length=1)
    for_: date = Field(alias="for")
    order_type: Literal["mkt", "lmt"]
    action: Literal["BUY", "SEL", "SHT", "BTC"]
    qty: int = Field(ge=1)
    underlying: int = Field(ge=1)
    contract: Literal["put", "call", "underlying"]
    expiry: str | None = None
    strike: str | None = None
    ref: Literal["open", "prev_close"] | None = None
    lmt_prc: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _no_nulls(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        fields = cast(dict[str, object], data)
        nulls = [name for name, value in fields.items() if value is None]
        if nulls:
            raise ValueError(f"{nulls[0]} is null: leave the field out instead")
        return fields

    @field_validator("for_", mode="before")
    @classmethod
    def _session_date(cls, value: object) -> object:
        if isinstance(value, str):
            return _calendar_date(value, "a date, YYYY-MM-DD (the session the order is for)")
        return value

    @field_validator("expiry")
    @classmethod
    def _expiry_token(cls, value: str | None) -> str | None:
        if value is None or _EXPIRY.fullmatch(value):
            return value
        _calendar_date(value, "an expiry token: NDTE+, NDTE-, NDTE, a date, W+ or M+")
        return value

    @field_validator("strike")
    @classmethod
    def _strike_token(cls, value: str | None) -> str | None:
        if value is None or _is_strike(value):
            return value
        if value.startswith("vega:"):
            raise ValueError("vega is reserved: rejected until it is turned on")
        raise ValueError(
            "not a strike token: a number, atm, otm:N, itm:N, pct:±X, delta:X or premium:X"
        )

    @field_validator("lmt_prc")
    @classmethod
    def _limit_token(cls, value: str | None) -> str | None:
        if value is None or (_LIMIT.fullmatch(value) and not _is_zero(value)):
            return value
        raise ValueError("not a limit token: a number, mid, bid, ask, or one of those ± dollars")

    @model_validator(mode="after")
    def _fields_for_its_kind(self) -> Self:
        if self.order_type == "lmt" and self.lmt_prc is None:
            raise ValueError("lmt_prc is required for a limit order")
        if self.order_type == "mkt" and self.lmt_prc is not None:
            raise ValueError("lmt_prc is forbidden on a market order")
        for name in ("expiry", "strike"):
            given = getattr(self, name) is not None
            if self.contract == "underlying" and given:
                raise ValueError(f"{name} is forbidden on shares (contract: underlying)")
            if self.contract != "underlying" and not given:
                raise ValueError(f"{name} is required on a {self.contract}")
        return self

    @model_validator(mode="after")
    def _expiry_not_before_session(self) -> Self:
        expiry = self.expiry
        if expiry and _DATE.fullmatch(expiry) and date.fromisoformat(expiry) < self.for_:
            raise ValueError(
                f"expiry {expiry} is before the session the order is for ({self.for_})"
            )
        return self


def parse_orders(data: object) -> tuple[Order, ...]:
    """The orders in `data`, a parsed `open_orders.json`. Raises `OrderError` naming the first
    order the language rejects, and on an id used twice."""
    if not isinstance(data, list):
        raise OrderError("the order book must be a JSON list of orders ([] when empty)")
    orders: list[Order] = []
    seen: set[str] = set()
    for i, raw in enumerate(cast(list[object], data)):
        try:
            order = Order.model_validate(raw)
        except ValidationError as exc:
            raise OrderError(f"order {i}{_named(raw)}: {_reason(exc)}") from None
        if order.id in seen:
            raise OrderError(f"order {i} ({order.id}): the id is used twice; ids are unique")
        seen.add(order.id)
        orders.append(order)
    return tuple(orders)


def render_orders(orders: Sequence[Order]) -> str:
    """The file's text: a JSON list in the page's field order, absent fields left out."""
    rows = [_row(o.model_dump(mode="json", by_alias=True, exclude_none=True)) for o in orders]
    return json.dumps(rows, indent=2, ensure_ascii=False) + "\n"


def _row(fields: dict[str, object]) -> dict[str, object]:
    """One order's fields in the page's order, FIELD_ORDER, whatever order the model holds."""
    return {name: fields[name] for name in FIELD_ORDER if name in fields}


def write_orders(path: Path, orders: Sequence[Order]) -> None:
    """Check every order, then write the file whole. Raises `OrderError` and writes nothing if
    any order is invalid (LINV-01)."""
    text = render_orders(orders)
    parse_orders(json.loads(text))
    replace_file(path, text.encode("utf-8"))


def read_orders(path: Path) -> tuple[Order, ...]:
    """The orders in `path`; none when it doesn't exist. Raises `OrderError` when it can't be read
    as the order language."""
    if not path.exists():
        return ()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise OrderError(f"{path.name} can't be read as UTF-8 text: {exc}") from None
    try:
        return parse_orders(json.loads(text))
    except json.JSONDecodeError as exc:
        raise OrderError(f"{path.name} is not valid JSON: {exc}") from None
    except OrderError as exc:
        raise OrderError(f"{path.name}: {exc}") from None


def strike_token(strike: Price) -> str:
    """A strike as the plain number the page takes: `155`, `152.5`."""
    return format(strike.to_dollars().normalize(), "f")


def pct_token(strike: Price, reference: Price, step: int = 1) -> str:
    """A strike as its distance from `reference` in whole percents, rounded to a multiple of
    `step` (PO, LD-29): `pct:-5` for $155 against a $162.83 close. Sanji applies it to the order's
    `ref` print, the open, then takes the nearest listed strike (a tie further out of the money),
    so the strike moves with a gap. A whole percent moves the target at most half a percent, which
    lands on the same strike while strikes are over 1% of the price apart."""
    pct = (Decimal(strike.units) / Decimal(reference.units) - 1) * 100
    whole = int((pct / step).to_integral_value()) * step
    return f"pct:{whole}"


def order_id(session: date, right: Right, strike: str) -> str:
    """A wheel order's id (LD-19): its session, right and strike token, so a re-run makes the same
    one: `wheel-2026-11-16-P-pct-5`, `wheel-2026-11-16-C-170`."""
    return f"wheel-{session.isoformat()}-{right.value}-{strike.replace(':', '')}"


def _calendar_date(text: str, what: str) -> date:
    if _DATE.fullmatch(text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            pass
    raise ValueError(f"{text!r} is not {what}")


def _is_strike(token: str) -> bool:
    if _STRIKE_NUMBER.fullmatch(token):
        return not _is_zero(token)
    if token == "atm" or _STRIKE_STEPS.fullmatch(token) or _STRIKE_PCT.fullmatch(token):
        return True
    match = _STRIKE_POSITIVE.fullmatch(token)
    if match is None:
        return False
    value = Decimal(match["value"])
    return value > 0 and (match["kind"] == "premium" or value < _MAX_DELTA)


def _is_zero(token: str) -> bool:
    return _STRIKE_NUMBER.fullmatch(token) is not None and Decimal(token) == 0


def _named(raw: object) -> str:
    name = cast(dict[str, object], raw).get("id") if isinstance(raw, dict) else None
    return f" ({name})" if isinstance(name, str) and name else ""


def _reason(exc: ValidationError) -> str:
    error = exc.errors()[0]
    field = ".".join(str(part) for part in error["loc"])
    return _describe(error, field)


def _describe(error: ErrorDetails, field: str) -> str:
    if error["type"] == "extra_forbidden":
        return f"unknown field {field!r}"
    if error["type"] == "missing":
        return f"missing required field {field!r}"
    message = error["msg"].removeprefix("Value error, ")
    return f"{field}: {message}" if field else message
