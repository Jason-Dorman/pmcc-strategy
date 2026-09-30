"""What a strategy sees and what it hands back (ARCHITECTURE §5.2, §5.3).

Rules see the market only through `MarketView`: no rule touches a dataframe (Spec › Look-ahead
guard). Every accessor reads as of a time, `now` by default, and a time after `now` raises
`LookAheadError`. The engine implements the view (`pmcc.engine.market_view`); strategies only name
this protocol, so `pmcc.strategy` never imports the engine (ARCHITECTURE §3.3 rule 3).

The rest are the values rules return: a `Selection` with the numbers that justified it, a trigger
result, a gate result, an exit outcome. Their `values` become blotter notes and gate-log values.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Protocol, final

from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.domain.quotes import Quote
from pmcc.domain.rules import RuleId
from pmcc.pricing.chain import PricedQuotes

type Value = float | int | str | bool | None
type Values = Mapping[str, Value]


class LookAheadError(EngineError):
    """A read of data stamped after the decision time (INV-04)."""


class ExpiryKind(StrEnum):
    WEEKLY = "weekly"  # a week-final session (E-S2)
    MONTHLY = "monthly"  # a third Friday, or the session before it (E-L2, DEC-33)


class Leg(StrEnum):
    LONG = "long"
    SHORT = "short"


@final
@dataclass(frozen=True, slots=True)
class ChainSnapshot:
    """One expiry's calls or puts on one session bar: listed contracts only (DEC-32), in strike
    order, priced (`PricedQuotes`). Empty when the chain has no listed row on the bar."""

    expiry: date
    right: Right
    bar_end: datetime
    quotes: PricedQuotes

    @property
    def size(self) -> int:
        return int(self.quotes.strike.size)

    def strike(self, row: int) -> Price:
        return Price(int(self.quotes.strike[row]))

    def strikes(self) -> tuple[Price, ...]:
        return tuple(self.strike(i) for i in range(self.size))

    def row(self, strike: Price) -> int | None:
        return self.quotes.at(strike)


class MarketView(Protocol):
    """The market as of `now`, the decision bar's end (DEC-06). `at` defaults to `now`; a later
    `at` raises `LookAheadError`."""

    @property
    def now(self) -> datetime: ...

    @property
    def root(self) -> str:
        """The option root, to name contracts."""
        ...

    def spot(self, at: datetime | None = None) -> Price | None:
        """The underlying's TRDPRC_1 in the bar ending `at`; None if it didn't trade (DEC-23)."""
        ...

    def stock_quote(self, at: datetime | None = None) -> Quote | None:
        """The underlying's BID/ASK on the bar ending `at`, if valid."""
        ...

    def quote(self, option: OptionId, at: datetime | None = None) -> Quote | None:
        """The contract's BID/ASK on the bar ending `at`, if valid (fresh quotes only, DEC-27)."""
        ...

    def chain(self, expiry: date, right: Right, at: datetime | None = None) -> ChainSnapshot:
        """The listed contracts of one expiry and right on the bar ending `at` (DEC-32)."""
        ...

    def expiries(self, kind: ExpiryKind, at: datetime | None = None) -> tuple[date, ...]:
        """Expiries of `kind` with a listed call at `at`, not yet expired, in date order."""
        ...

    def close_trades(self, at: datetime | None = None) -> Mapping[datetime, Price]:
        """Close-bar TRDPRC_1 of the sessions whose close is at or before `at`, by `bar_end`
        (RV20, DEC-26)."""
        ...

    def calendar(self) -> SessionCalendar:
        """Reference data published in advance, so it answers for any day (DEC-33)."""
        ...


@final
@dataclass(frozen=True, slots=True)
class Selection:
    """A contract a selector chose on a bar, and the values that justified it."""

    option: OptionId
    values: Values = field(default_factory=dict[str, Value])


@final
@dataclass(frozen=True, slots=True)
class HeldLeg:
    """An open leg as the strategy sees it. `entry_fill` is the long's cost basis for E-S5, or the
    short's credit for X-S1; `em_at_entry` is the short's EM at its entry bar (X-S3)."""

    option: OptionId
    qty: int
    entry_fill: Price
    entry_time: datetime
    em_at_entry: Price | None = None


@final
@dataclass(frozen=True, slots=True)
class PositionState:
    long: HeldLeg | None
    short: HeldLeg | None


@final
@dataclass(frozen=True, slots=True)
class TriggerResult:
    """E-T1 on one bar: whether the contract's quote passes, the quote, and its spread % of mid."""

    passed: bool
    quote: Quote | None
    spread_pct: float | None


class GateStatus(StrEnum):
    PASS = "pass"
    FIRE = "fire"
    NA = "n/a"  # its inputs are unavailable: it doesn't fire (DEC-22)
    NOT_EVALUATED = "not_evaluated"  # G-1 fired first (DEC-22)


@final
@dataclass(frozen=True, slots=True)
class GateResult:
    rule_id: RuleId
    status: GateStatus
    values: Values = field(default_factory=dict[str, Value])
    reason: str = ""


@final
@dataclass(frozen=True, slots=True)
class ShortDecision:
    """The short at its decision bar: the frozen selection, its quote there, and the long it would
    be sold against. Gates G-2 to G-5 read it (DEC-22)."""

    selection: Selection
    quote: Quote
    long: HeldLeg


class ExitStatus(StrEnum):
    FIRE = "fire"
    PASS = "pass"
    UNEVALUATED = "unevaluated"  # a fresh quote, but an input the rule needs is missing (DEC-27)


@final
@dataclass(frozen=True, slots=True)
class ExitOutcome:
    rule_id: RuleId
    status: ExitStatus
    values: Values = field(default_factory=dict[str, Value])
    reason: str = ""

    @property
    def fired(self) -> bool:
        return self.status is ExitStatus.FIRE
