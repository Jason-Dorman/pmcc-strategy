"""The structural constraint E-S5 and the skip-week gates (Spec › Trade rules; PO, DEC-22).

- **E-S5:** short strike − long strike > long entry fill − short mid, per share, strictly. It uses
  the long's entry fill, not its mark, and the short's mid at its decision bar, in integer units.
- **G-1** fires when the frozen short never passes E-T1 in the week-open session (or no short was
  ever selected). It is decided when the session ends, so it isn't a `Gate`; when it fires, the
  other gates are `not_evaluated`.
- **G-2 to G-5** are evaluated at the decision bar, all of them, each recorded pass or fire with
  its values; a gate whose inputs are unavailable records `n/a` and doesn't fire. The week's
  outcome is the first gate, in spec order, that fired. G-3 to G-5 are the quant layer (P4-02).
"""

from dataclasses import dataclass
from typing import Protocol, final, runtime_checkable

from pmcc.domain.money import Price
from pmcc.domain.rules import RuleId
from pmcc.strategy.ports import (
    GateResult,
    GateStatus,
    HeldLeg,
    MarketView,
    ShortDecision,
    Values,
)

E_S5, G_1, G_2 = RuleId("E-S5"), RuleId("G-1"), RuleId("G-2")


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
