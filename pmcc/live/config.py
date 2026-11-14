"""`configs/live.yaml`: the live wheel's rules, thresholds and settings (LIVE-SPEC › Trade rules).

Every rule the spec defines is in the file exactly once, in the spec's order. Every threshold sits
under the rule that uses it (CLAUDE.md › Hard rules): the strike band and the target delta under
L-P3 and L-C3, the starting cash under L-P4, the spread limit under L-T1, the order's shape under
L-O1. Each rule's params are checked against their types and ranges at load, so a missing,
misspelt or mistyped threshold fails before the run asks LSEG anything. Each rule's `text` is its
words for the page, `{param}` placeholders filled from its params. The file is found from this
module, not the working directory.
"""

from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidationError,
    model_validator,
)

from pmcc.config.universe import continuous_rate
from pmcc.config.yaml_file import read_yaml
from pmcc.domain.money import UNITS_PER_CENT, Money, Price

LIVE_PATH = Path(__file__).resolve().parents[2] / "configs" / "live.yaml"

RULE_IDS = (
    "L-B1",
    "L-B2",
    "L-S1",
    "L-P1",
    "L-P2",
    "L-P3",
    "L-P4",
    "L-C1",
    "L-C2",
    "L-C3",
    "L-T1",
    "L-O1",
    "L-O2",
)

type Param = float | int | str


class LiveConfigError(ValueError):
    """`configs/live.yaml` doesn't hold what the spec's rules need."""


class _Params(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StrikeParams(_Params):
    """L-P3's and L-C3's: the delta aimed at, and the strikes asked of LSEG around the close."""

    target_delta: StrictFloat = Field(gt=0, lt=1)
    band_percent: StrictInt = Field(ge=1, le=50)
    step: StrictStr

    @model_validator(mode="after")
    def _whole_cents(self) -> Self:
        cents = _decimal(self.step, "step") * 100
        if cents <= 0 or cents != cents.to_integral_value():
            raise ValueError(f"step must be a positive whole number of cents, got {self.step}")
        return self

    @property
    def step_cents(self) -> int:
        return int(Decimal(self.step) * 100)

    @property
    def step_price(self) -> Price:
        return Price(self.step_cents * UNITS_PER_CENT)


class CashParams(_Params):
    """L-P4's: contracts per order, shares per contract, and the cash the book starts with."""

    contracts: StrictInt = Field(ge=1)
    multiplier: StrictInt = Field(ge=1)
    starting_cash: StrictStr

    @model_validator(mode="after")
    def _positive(self) -> Self:
        if _decimal(self.starting_cash, "starting_cash") <= 0:
            raise ValueError(f"starting_cash must be above zero, got {self.starting_cash}")
        return self


class SpreadParams(_Params):
    """L-T1's: the widest spread, as a share of the mid, an order may be placed at."""

    max_spread: StrictFloat = Field(gt=0, lt=1)


class OrderParams(_Params):
    """L-O1's: the order's type, limit, reference and size, checked again by `Order`."""

    order_type: StrictStr
    lmt_prc: StrictStr
    ref: StrictStr
    qty: StrictInt = Field(ge=1)


PARAMS: dict[str, type[_Params]] = {
    "L-P3": StrikeParams,
    "L-P4": CashParams,
    "L-C3": StrikeParams,
    "L-T1": SpreadParams,
    "L-O1": OrderParams,
}


class LiveRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    rule: str = Field(min_length=1)
    text: str = Field(min_length=1)
    params: dict[str, Param] = Field(default_factory=dict[str, Param])

    def words(self) -> str:
        """`text` with its params filled in."""
        return self.text.format(**self.params)


class RiskFree(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    investment_yield_pct: float = Field(gt=0, lt=20)
    observed: date
    source: str = Field(min_length=1)

    @property
    def rate(self) -> float:
        """Continuously compounded, as the backtests' r is (LD-13)."""
        return continuous_rate(self.investment_yield_pct)


class LiveConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str = Field(pattern=r"^[A-Z][A-Z0-9]*$")
    underlying_conid: int = Field(ge=1)
    risk_free: RiskFree
    rules: tuple[LiveRule, ...]

    @model_validator(mode="after")
    def _the_specs_rules(self) -> Self:
        ids = tuple(r.id for r in self.rules)
        if ids != RULE_IDS:
            raise ValueError(f"rules must be the spec's, in its order: {RULE_IDS}; got {ids}")
        for rule in self.rules:
            _check_params(rule)
            rule.words()  # every placeholder has its param
        return self

    def rule(self, rule_id: str) -> LiveRule:
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        raise KeyError(rule_id)

    def strike(self, rule_id: str) -> StrikeParams:
        """L-P3's or L-C3's params."""
        return StrikeParams.model_validate(self.rule(rule_id).params)

    @property
    def cash_rule(self) -> CashParams:
        return CashParams.model_validate(self.rule("L-P4").params)

    @property
    def cash(self) -> Money:
        """The book's starting cash (L-P4; LD-09): Sanji starts no book."""
        return Money.from_dollars(self.cash_rule.starting_cash)

    @property
    def max_spread(self) -> float:
        return SpreadParams.model_validate(self.rule("L-T1").params).max_spread

    def order_fields(self) -> dict[str, Param]:
        """L-O1's order type, limit token, reference and quantity, for an `Order`, which checks
        them against the order language when the order is made."""
        return dict(OrderParams.model_validate(self.rule("L-O1").params).model_dump())


def load_live_config(path: Path = LIVE_PATH) -> LiveConfig:
    """The live wheel's config. Raises `LiveConfigError` naming what's wrong."""
    try:
        return LiveConfig.model_validate(read_yaml(path))
    except ValueError as exc:
        raise LiveConfigError(f"{path.name}: {exc}") from None


def _check_params(rule: LiveRule) -> None:
    model = PARAMS.get(rule.id)
    if model is None:
        if rule.params:
            raise ValueError(f"{rule.id} takes no params, got {sorted(rule.params)}")
        return
    try:
        model.model_validate(rule.params)
    except ValidationError as exc:
        raise ValueError(f"{rule.id}'s params: {exc}") from None


def _decimal(text: str, name: str) -> Decimal:
    try:
        return Decimal(text)
    except InvalidOperation:
        raise ValueError(f"{name} must be a number written as text, got {text!r}") from None
