"""The structural constraint E-S5 and the skip-week gates (Spec › Trade rules; PO, DEC-22).

- **E-S5:** short strike − long strike > long entry fill − short mid, per share, strictly. It uses
  the long's entry fill, not its mark, and the short's mid at its decision bar, in integer units.
- **G-1** fires when the frozen short never passes E-T1 in the week-open session (or no short was
  ever selected). It is decided when the session ends, so it isn't a `Gate`; when it fires, the
  other gates are `not_evaluated`.
- **G-2 to G-5** are evaluated at the decision bar, all of them, each recorded pass or fire with
  its values; a gate whose inputs are unavailable records `n/a`, with its reason, and doesn't
  fire. The week's outcome is the first gate, in spec order, that fired.
- **G-3 to G-5** are the quant layer (P4-02). G-3 and G-4 read ATM IV (the ATM call's, DEC-25)
  and RV20 (DEC-26) at the decision bar; G-5 reads the short's mid there. An IV ratio is a float,
  rounded to 6 places before it's compared: a ratio on its threshold but for float noise compares
  equal to it, and the ratio compared is the one a result file prints (DEC-50, DEC-95). G-5
  compares integer units.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol, final, runtime_checkable

from pmcc.domain.money import Price
from pmcc.domain.rules import RuleId
from pmcc.strategy.measures import atm_reading, rv20_at
from pmcc.strategy.ports import (
    GateResult,
    GateStatus,
    HeldLeg,
    MarketView,
    ShortDecision,
    Value,
    Values,
)

E_S5, G_1, G_2 = RuleId("E-S5"), RuleId("G-1"), RuleId("G-2")
G_3, G_4, G_5 = RuleId("G-3"), RuleId("G-4"), RuleId("G-5")
RATIO_PLACES = 6  # results print floats to 6 places (DEC-50): compare what is published


@final
@dataclass(frozen=True, slots=True)
class ConstraintCheck:
    satisfied: bool
    gap: Price  # short strike − long strike
    debit: Price  # long entry fill − short mid

    @property
    def values(self) -> Values:
        return {
            "strike_gap": str(self.gap.to_dollars()),
            "net_debit": str(self.debit.to_dollars()),
            "satisfied": self.satisfied,
        }


@final
@dataclass(frozen=True, slots=True)
class StructuralConstraint:
    """E-S5."""

    rule_id: RuleId = E_S5

    def check(self, long: HeldLeg, short_strike: Price, short_mid: Price) -> ConstraintCheck:
        gap = short_strike - long.option.strike
        debit = long.entry_fill - short_mid
        return ConstraintCheck(gap > debit, gap, debit)


@runtime_checkable
class Gate(Protocol):
    @property
    def rule_id(self) -> RuleId: ...

    def evaluate(self, view: MarketView, decision: ShortDecision) -> GateResult: ...


@final
@dataclass(frozen=True, slots=True)
class NoQuoteGate:
    """G-1: the selected short never passes E-T1 on any bar of the week-open session."""

    rule_id: RuleId = G_1

    def fire(self, values: Values, reason: str) -> GateResult:
        return GateResult(self.rule_id, GateStatus.FIRE, values, reason)

    def passed(self, values: Values) -> GateResult:
        return GateResult(self.rule_id, GateStatus.PASS, values)


@final
@dataclass(frozen=True, slots=True)
class StructuralGate:
    """G-2: the selected short fails E-S5."""

    constraint: StructuralConstraint
    rule_id: RuleId = G_2

    def evaluate(self, view: MarketView, decision: ShortDecision) -> GateResult:
        check = self.constraint.check(
            decision.long, decision.selection.option.strike, decision.quote.mid
        )
        status = GateStatus.PASS if check.satisfied else GateStatus.FIRE
        return GateResult(self.rule_id, status, check.values)


def _ratio(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, RATIO_PLACES)


def _decided(rule_id: RuleId, fired: bool, values: Values) -> GateResult:
    return GateResult(rule_id, GateStatus.FIRE if fired else GateStatus.PASS, values)


def _iv(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def _dollars(price: Price | None) -> str | None:
    return None if price is None else str(price.to_dollars())


@final
@dataclass(frozen=True, slots=True)
class EventRatioGate:
    """G-3: front-week ATM IV ÷ next-week ATM IV above `max_ratio`. The front week is the short's
    expiry; the next week's expiry is the following calendar week's final session. `n/a` when
    either ATM IV is unavailable (DEC-22, DEC-25)."""

    max_ratio: float
    rule_id: RuleId = G_3

    def evaluate(self, view: MarketView, decision: ShortDecision) -> GateResult:
        front_expiry = decision.selection.option.expiry
        next_expiry = view.calendar().week_final(front_expiry + timedelta(days=7)).day
        front, following = atm_reading(view, front_expiry), atm_reading(view, next_expiry)
        values: dict[str, Value] = {
            "front_expiry": front_expiry.isoformat(),
            "front_atm_strike": _dollars(front.strike),
            "front_atm_iv": _iv(front.iv),
            "next_expiry": next_expiry.isoformat(),
            "next_atm_strike": _dollars(following.strike),
            "next_atm_iv": _iv(following.iv),
            "ratio": None,
            "max_ratio": self.max_ratio,
        }
        if front.iv is None:
            return GateResult(self.rule_id, GateStatus.NA, values, "no front-week ATM IV")
        if following.iv is None:
            return GateResult(self.rule_id, GateStatus.NA, values, "no next-week ATM IV")
        values["ratio"] = ratio = _ratio(front.iv, following.iv)
        return _decided(self.rule_id, ratio > self.max_ratio, values)


@final
@dataclass(frozen=True, slots=True)
class VrpGate:
    """G-4: front-week ATM IV ÷ RV20 below `min_ratio`. `n/a` when the ATM IV or RV20 is
    unavailable (DEC-22, DEC-26). An RV20 of zero makes the ratio unbounded, so it passes."""

    min_ratio: float
    rule_id: RuleId = G_4

    def evaluate(self, view: MarketView, decision: ShortDecision) -> GateResult:
        front = atm_reading(view, decision.selection.option.expiry)
        rv = rv20_at(view)
        values: dict[str, Value] = {
            "front_atm_strike": _dollars(front.strike),
            "front_atm_iv": _iv(front.iv),
            "rv20": _iv(rv),
            "ratio": None,
            "min_ratio": self.min_ratio,
        }
        if front.iv is None:
            return GateResult(self.rule_id, GateStatus.NA, values, "no front-week ATM IV")
        if rv is None:
            return GateResult(self.rule_id, GateStatus.NA, values, "no RV20")
        if rv == 0:
            return _decided(self.rule_id, False, values)
        values["ratio"] = ratio = _ratio(front.iv, rv)
        return _decided(self.rule_id, ratio < self.min_ratio, values)


@final
@dataclass(frozen=True, slots=True)
class MinPremiumGate:
    """G-5: the selected short's mid at the decision bar below `min_mid`, in exact units."""

    min_mid: Price
    rule_id: RuleId = G_5

    def evaluate(self, view: MarketView, decision: ShortDecision) -> GateResult:
        mid = decision.quote.mid
        values: Values = {"mid": str(mid.to_dollars()), "min_mid": str(self.min_mid.to_dollars())}
        return _decided(self.rule_id, mid < self.min_mid, values)
