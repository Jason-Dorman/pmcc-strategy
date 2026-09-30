"""The rule kinds a strategy YAML may name, and the params each one takes (DEC-53, DEC-90).

A kind implements exactly one spec rule ID: `nearest_delta_short` and `expected_move_strike` are two
ways to do E-S3, so a variant swaps kinds under the same ID. Its params model holds every threshold
the rule reads (Spec › Config-driven rules). `strategy/registry.py` maps each kind to the code that
runs it (P3-06); the config package can't import strategy, so the params live here.
"""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pmcc.config.fields import ClockTime, DollarPrice
from pmcc.domain import RuleId

SPEC_RULE_IDS: tuple[RuleId, ...] = tuple(
    RuleId(i)
    for i in (
        *("E-T1", "E-L1", "E-L2", "E-L3", "E-L4", "E-S1", "E-S2", "E-S3", "E-S4", "E-S5"),
        *("G-1", "G-2", "G-3", "G-4", "G-5"),
        *("X-S1", "X-S2", "X-S3", "X-S4", "X-S5", "X-L1", "X-L2", "X-E1"),
    )
)
"""Every rule ID in the spec's entry, skip-week gate and exit tables, in their order."""

OPTIONAL_RULE_IDS: frozenset[RuleId] = frozenset(RuleId(i) for i in ("G-3", "G-4", "G-5", "X-S1"))
"""The layers the spec's strategies and ablations switch off. "Off" is absence (DEC-53); every
other spec rule must be in a strategy."""

Fraction = Annotated[float, Field(gt=0, lt=1)]  # a share of mid, a delta, a share of the credit
Ratio = Annotated[float, Field(gt=0)]  # an IV ratio, an EM multiple
Days = Annotated[int, Field(ge=1)]


class Params(BaseModel):
    """A kind's params: strict, so "0.3" or `true` isn't read as a number, and closed to extras."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class NoParams(Params):
    """A rule with no threshold."""


class SpreadTrigger(Params):  # E-T1
    long_max_spread: Fraction
    short_max_spread: Fraction


class NearestDteExpiry(Params):  # E-L2 baseline
    target_dte: Days


class DteRangeExpiry(Params):  # E-L2 quant
    min_dte: Days
    max_dte: Days

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.min_dte > self.max_dte:
            raise ValueError(f"min_dte {self.min_dte} is above max_dte {self.max_dte}")
        return self


class NearestDelta(Params):  # E-L3 and E-S3 baseline
    target_delta: Fraction


class DeltaBand(Params):  # E-L3 quant
    min_delta: Fraction
    max_delta: Fraction

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.min_delta > self.max_delta:
            raise ValueError(f"min_delta {self.min_delta} is above max_delta {self.max_delta}")
        return self


class FixedContracts(Params):  # E-L4
    contracts: int = Field(ge=1)


class ExpectedMoveStrike(Params):  # E-S3 quant
    k: Ratio


class MaxRatio(Params):  # G-3
    max_ratio: Ratio


class MinRatio(Params):  # G-4
    min_ratio: Ratio


class MinPremium(Params):  # G-5
    min_mid: DollarPrice


class TakeProfit(Params):  # X-S1
    max_credit_fraction: Fraction


class MaxDelta(Params):  # X-S2
    max_delta: Fraction


class FridayCheck(Params):  # X-S3
    check_by: ClockTime  # ET
    em_buffer: float = Field(ge=0)


class MinDelta(Params):  # X-L1
    min_delta: Fraction


class MinDte(Params):  # X-L2
    min_dte: Days


@dataclass(frozen=True, slots=True)
class Kind:
    """What a kind name in YAML stands for: the rule it implements and the params it takes."""

    rule_id: RuleId
    params: type[Params]


def _kind(rule_id: str, params: type[Params] = NoParams) -> Kind:
    return Kind(RuleId(rule_id), params)


KINDS = MappingProxyType(
    {
        "spread_trigger": _kind("E-T1", SpreadTrigger),
        "first_session_retry": _kind("E-L1"),
        "nearest_dte_expiry": _kind("E-L2", NearestDteExpiry),
        "dte_range_expiry": _kind("E-L2", DteRangeExpiry),
        "nearest_delta_long": _kind("E-L3", NearestDelta),
        "cheapest_replacement": _kind("E-L3", DeltaBand),
        "fixed_contracts": _kind("E-L4", FixedContracts),
        "week_open_short": _kind("E-S1"),
        "week_final_expiry": _kind("E-S2"),
        "nearest_delta_short": _kind("E-S3", NearestDelta),
        "expected_move_strike": _kind("E-S3", ExpectedMoveStrike),
        "match_long_qty": _kind("E-S4"),
        "strike_covers_debit": _kind("E-S5"),
        "no_quote_gate": _kind("G-1"),
        "structural_gate": _kind("G-2"),
        "event_ratio_gate": _kind("G-3", MaxRatio),
        "vrp_gate": _kind("G-4", MinRatio),
        "min_premium_gate": _kind("G-5", MinPremium),
        "take_profit": _kind("X-S1", TakeProfit),
        "defensive_delta": _kind("X-S2", MaxDelta),
        "friday_check": _kind("X-S3", FridayCheck),
        "expire_otm": _kind("X-S4"),
        "missed_assignment": _kind("X-S5"),
        "long_delta_reset": _kind("X-L1", MinDelta),
        "long_dte_roll": _kind("X-L2", MinDte),
        "end_of_backtest": _kind("X-E1"),
    }
)
"""Every kind a strategy YAML may name."""
