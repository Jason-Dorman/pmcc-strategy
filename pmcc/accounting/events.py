"""Blotter events: booked trades only, no working orders and no signals (Spec › Blotter).

An `Event` is one blotter row. Its cash is checked against its fill when it is made, so a row whose
Cash Δ doesn't follow from its price, quantity and fee can't exist (INV-01):

- `BUY`: −fill × multiplier × qty − fee.  `SELL`: +fill × multiplier × qty − fee.
- `EXPIRE` (X-S4): the short call leaves at $0, with no cash and no fee.
- `ASSIGN` (X-S5): the short call is assigned, with no cash; the stock sale at the strike is its
  own `SELL` row (DEC-34).

The multiplier is 100 shares per option contract and 1 per share (DEC-44). The fee is per option
contract (Spec › Fill model), so a stock row carries none.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import final

from pmcc.domain.instruments import OPTION_MULTIPLIER, OptionId, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId

type AuditValue = float | int | str | bool | None


@final
@dataclass(frozen=True, order=True, slots=True)
class StockId:
    """The underlying's shares (only ever held short, after X-S5)."""

    symbol: str


type Instrument = OptionId | StockId


def multiplier(instrument: Instrument) -> int:
    return OPTION_MULTIPLIER if isinstance(instrument, OptionId) else 1


@final
@dataclass(frozen=True, slots=True)
class Event:
    """One blotter row. `limit` is the mid at decision time, `fill` the simulated price; `audit`
    holds what `pmcc verify` re-derives INV-03, 06 and 08 from (quote, E-S5 terms, funds after)."""

    time: datetime
    side: Side
    instrument: Instrument
    qty: int
    limit: Price | None
    fill: Price | None
    cash_delta: Money
    rule_id: RuleId
    notes: str = ""
    fee: Money = field(default_factory=Money.zero)
    audit: Mapping[str, AuditValue] = field(default_factory=dict[str, AuditValue])

    def __post_init__(self) -> None:
        if self.time.utcoffset() is None:
            raise ValueError("an event's time must be tz-aware")
        if type(self.qty) is not int or self.qty <= 0:
            raise ValueError(f"an event's quantity must be a positive int, got {self.qty!r}")
        if self.fee.units < 0:
            raise ValueError("a fee can't be negative")
        expected = expected_cash(self.side, self.instrument, self.qty, self.fill, self.fee)
        if self.cash_delta != expected:
            raise ValueError(
                f"{self.side} {self.qty} at {self.fill}: cash Δ {self.cash_delta} isn't {expected}"
            )

    @property
    def is_option(self) -> bool:
        return isinstance(self.instrument, OptionId)


def expected_cash(
    side: Side, instrument: Instrument, qty: int, fill: Price | None, fee: Money
) -> Money:
    """The Cash Δ a row must carry. Raises `ValueError` for a row that can't exist."""
    if side in (Side.EXPIRE, Side.ASSIGN):
        if not isinstance(instrument, OptionId) or fee.units:
            raise ValueError(f"{side} is an option row with no fee")
        if side is Side.EXPIRE and fill != Price(0):
            raise ValueError("an EXPIRE row fills at $0")
        if side is Side.ASSIGN and fill is not None:
            raise ValueError("an ASSIGN row has no fill; the stock sale is its own row")
        return Money.zero()
    if fill is None or fill.units < 0:
        raise ValueError(f"a {side} row needs a fill of $0 or more")
    if isinstance(instrument, StockId) and fee.units:
        raise ValueError("the fee is per option contract; a stock row has none")
    notional = fill.notional(multiplier(instrument), qty)
    return (-notional if side is Side.BUY else notional) - fee
