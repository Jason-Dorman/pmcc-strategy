"""Exit rules (Spec › Trade rules: exits). Both strategies use them unchanged.

A check returns None when the rule doesn't apply on the bar (no such leg, not its bar, or no fresh
quote: rules run only on fresh quotes, DEC-27). Otherwise it returns an `ExitOutcome`: fire, pass,
or unevaluated when an input it needs is missing on a bar that has a fresh quote (a delta the IV
solve couldn't give, a spot, an EM), which doesn't fire and is logged (PO, DEC-27).

| Rule | Checked on | Fires when |
| --- | --- | --- |
| X-S1 | any bar before the Friday check bar | short mid ≤ share × credit received |
| X-S2 | any bar | short delta > limit |
| X-S3 | the Friday check bar | spot ≥ short strike − buffer × EM at entry |
| X-L1 | the week-open check bar (the engine's) | long delta < limit |
| X-L2 | the week-open check bar (the engine's) | long DTE < limit |
| X-S4/X-S5 | the short's expiry close bar (the engine's) | closing spot ≤ / > strike (DEC-23) |

Thresholds compare exactly, against the YAML's decimals, in integer units where money is involved.
"""

import math
from dataclasses import dataclass
from datetime import date, datetime, time
from typing import Protocol, final, runtime_checkable

from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import to_et
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.domain.rules import RuleId
from pmcc.pricing.expiry import days_to_expiry
from pmcc.pricing.iv import IvCode
from pmcc.pricing.measures import itm_at_expiry
from pmcc.strategy.ports import (
    ExitOutcome,
    ExitStatus,
    HeldLeg,
    MarketView,
    PositionState,
    Values,
)
from pmcc.strategy.trigger import as_fraction

X_S1, X_S2, X_S3 = RuleId("X-S1"), RuleId("X-S2"), RuleId("X-S3")
X_S4, X_S5, X_L1, X_L2 = RuleId("X-S4"), RuleId("X-S5"), RuleId("X-L1"), RuleId("X-L2")


@runtime_checkable
class ExitRule(Protocol):
    @property
    def rule_id(self) -> RuleId: ...

    def check(self, view: MarketView, position: PositionState) -> ExitOutcome | None: ...


def friday_check_bar(calendar: SessionCalendar, expiry: date, check_by: time) -> datetime | None:
    """The last session bar of the expiry session ending at or before `check_by` ET (X-S3)."""
    ends = [t for t in calendar.session(expiry).bar_ends() if t.time() <= check_by]
    return ends[-1] if ends else None


def _outcome(rule_id: RuleId, fired: bool, values: Values) -> ExitOutcome:
    return ExitOutcome(rule_id, ExitStatus.FIRE if fired else ExitStatus.PASS, values)


def _delta(view: MarketView, option: OptionId) -> tuple[float, IvCode] | None:
    """The contract's delta on this bar, with its IV code; None without a fresh quote."""
    chain = view.chain(option.expiry, Right.CALL)
    row = chain.row(option.strike)
    if row is None or not chain.quotes.valid[row]:
        return None
    return float(chain.quotes.delta[row]), IvCode(int(chain.quotes.code[row]))


def _unevaluated(rule_id: RuleId, code: IvCode) -> ExitOutcome:
    return ExitOutcome(rule_id, ExitStatus.UNEVALUATED, {"iv_code": code.name},
                       f"no delta on this bar ({code.name})")  # fmt: skip


@final
@dataclass(frozen=True, slots=True)
class TakeProfit:
    """X-S1: buy the short back once its mid is at most `max_credit_fraction` of the credit, on
    any bar before the Friday check."""

    max_credit_fraction: float
    check_by: time
    rule_id: RuleId = X_S1

    def check(self, view: MarketView, position: PositionState) -> ExitOutcome | None:
        short = position.short
        if short is None:
            return None
        check_bar = friday_check_bar(view.calendar(), short.option.expiry, self.check_by)
        quote = view.quote(short.option)
        if quote is None or (check_bar is not None and view.now >= check_bar):
            return None
        limit = as_fraction(self.max_credit_fraction) * short.entry_fill.units
        values: Values = {"mid": str(quote.mid.to_dollars()),
                          "credit": str(short.entry_fill.to_dollars()),
                          "max_credit_fraction": self.max_credit_fraction}  # fmt: skip
        return _outcome(self.rule_id, quote.mid.units <= limit, values)


@final
@dataclass(frozen=True, slots=True)
class DefensiveDelta:
    """X-S2: buy the short back once its delta is above `max_delta`, on any bar."""

    max_delta: float
    rule_id: RuleId = X_S2

    def check(self, view: MarketView, position: PositionState) -> ExitOutcome | None:
        short = position.short
        found = None if short is None else _delta(view, short.option)
        if found is None:
            return None
        delta, code = found
        if math.isnan(delta):
            return _unevaluated(self.rule_id, code)
        values: Values = {"delta": round(delta, 6), "max_delta": self.max_delta}
        return _outcome(self.rule_id, delta > self.max_delta, values)


@final
@dataclass(frozen=True, slots=True)
class FridayCheck:
    """X-S3: at the Friday check bar, close the short if spot ≥ strike − `em_buffer` × EM, with EM
    measured at the short's entry. It fires on spot alone; the fill needs a quote (DEC-28)."""

    check_by: time
    em_buffer: float
    rule_id: RuleId = X_S3

    def is_check_bar(self, view: MarketView, short: HeldLeg) -> bool:
        return friday_check_bar(view.calendar(), short.option.expiry, self.check_by) == view.now

    def check(self, view: MarketView, position: PositionState) -> ExitOutcome | None:
        short = position.short
        if short is None or not self.is_check_bar(view, short):
            return None
        spot, em = view.spot(), short.em_at_entry
        if spot is None or em is None:
            missing = "spot" if spot is None else "EM at entry"
            return ExitOutcome(self.rule_id, ExitStatus.UNEVALUATED, {}, f"no {missing}")
        threshold = short.option.strike.units - as_fraction(self.em_buffer) * em.units
        values: Values = {"spot": str(spot.to_dollars()),
                          "strike": str(short.option.strike.to_dollars()),
                          "em_at_entry": str(em.to_dollars()), "em_buffer": self.em_buffer,
                          "threshold": round(float(threshold) / 10_000, 4)}  # fmt: skip
        return _outcome(self.rule_id, spot.units >= threshold, values)


@final
@dataclass(frozen=True, slots=True)
class LongDeltaReset:
    """X-L1: sell the long once its delta is below `min_delta` at the week-open check bar."""

    min_delta: float
    rule_id: RuleId = X_L1

    def check(self, view: MarketView, position: PositionState) -> ExitOutcome | None:
        long = position.long
        found = None if long is None else _delta(view, long.option)
        if found is None:
            return None
        delta, code = found
        if math.isnan(delta):
            return _unevaluated(self.rule_id, code)
        values: Values = {"delta": round(delta, 6), "min_delta": self.min_delta}
        return _outcome(self.rule_id, delta < self.min_delta, values)


@final
@dataclass(frozen=True, slots=True)
class LongDteRoll:
    """X-L2: sell the long once it has fewer than `min_dte` days left at the week-open check bar."""

    min_dte: int
    rule_id: RuleId = X_L2

    def check(self, view: MarketView, position: PositionState) -> ExitOutcome | None:
        long = position.long
        if long is None or view.quote(long.option) is None:
            return None
        dte = days_to_expiry(view.now, long.option.expiry)
        return _outcome(self.rule_id, dte < self.min_dte, {"dte": dte, "min_dte": self.min_dte})


@final
@dataclass(frozen=True, slots=True)
class ExpiryResolver:
    """X-S4 / X-S5 at the short's expiry close: out of the money (closing spot ≤ strike) expires
    at $0; in the money is a missed assignment (DEC-23)."""

    def resolve(self, closing_spot: Price, short: OptionId) -> RuleId:
        return X_S5 if itm_at_expiry(closing_spot, short.strike) else X_S4

    @staticmethod
    def is_close_bar(calendar: SessionCalendar, now: datetime, expiry: date) -> bool:
        return to_et(now) == calendar.session(expiry).close_bar_end
