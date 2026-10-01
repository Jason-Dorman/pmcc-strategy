"""Strategy configs (ARCHITECTURE §10): the resolved rules, the fill model and the run config.

`load_strategy` folds a strategy YAML's `extends` chain and `overrides` (DEC-53), then validates
every rule against its kind: known kind, the rule ID it implements, its params, and text whose
placeholders all resolve and which references every param (DEC-52). Rules come out in the spec's
order whatever the files' order. `load_run_config` adds the universe's window and r, and
`RunConfig.config_hash` is the sha256 of the result as canonical JSON (DEC-90).

A strategy's `report` block says how much detail its results keep and which optional sections its
page shows (PO, DEC-54). It is part of the config, and so of its hash.
"""

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Self, cast

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializeAsAny,
    ValidationError,
    WithJsonSchema,
    field_validator,
    model_validator,
)

from pmcc.config.extends import resolve
from pmcc.config.fields import DollarMoney, RuleIdField
from pmcc.config.kinds import KINDS, OPTIONAL_RULE_IDS, SPEC_RULE_IDS, Params
from pmcc.config.rule_text import placeholders, render
from pmcc.config.universe import RiskFreeRate, Universe, Window
from pmcc.domain import Money, Price, RuleId

CONFIGS_DIR = Path(__file__).resolve().parents[2] / "configs"

_SPEC_ORDER = {rule_id: i for i, rule_id in enumerate(SPEC_RULE_IDS)}
_REQUIRED = frozenset(SPEC_RULE_IDS) - OPTIONAL_RULE_IDS
_RUN_ID = r"^[a-z][a-z0-9_]*(--[a-z0-9]+)*$"  # baseline_pmcc, quant_pmcc--a3 (ARCHITECTURE §11)

# A rule's params as they dump: each kind has its own model, so the schema says only what every
# dump holds, a map of names to numbers or strings (dollars "0.1000", times "15:00").
AnyParams = Annotated[
    SerializeAsAny[Params],
    WithJsonSchema(
        {"type": "object", "additionalProperties": {"type": ["number", "string"]}},
        mode="serialization",
    ),
]


@dataclass(frozen=True, slots=True)
class RuleText:
    """A rule's write-up with its live values filled in (Trade rules page, blotter links)."""

    condition: str
    action: str
    rationale: str


class Rule(BaseModel):
    """One rule: its spec ID, the kind that implements it, its params and its write-up templates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: RuleIdField
    name: str = Field(pattern=r"\S")
    kind: str
    params: AnyParams
    condition: str = Field(pattern=r"\S")
    action: str = Field(pattern=r"\S")
    rationale: str = Field(pattern=r"\S")

    @model_validator(mode="before")
    @classmethod
    def _typed_params(cls, data: object) -> object:
        """Validates `params` with the kind's model, so an unknown kind or param fails here."""
        raw = cast(dict[str, object], data) if isinstance(data, dict) else None
        if raw is None or "kind" not in raw:
            return cast(object, data)  # pydantic reports what's missing
        kind = KINDS.get(str(raw["kind"]))
        if kind is None:
            raise ValueError(f"{raw.get('id')}: unknown kind {raw['kind']!r}")
        try:
            params = kind.params.model_validate(raw.get("params", {}))
        except ValidationError as e:
            raise ValueError(f"{raw.get('id')} params: {_describe(e)}") from None
        return {**raw, "params": params}

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        # Every kind implements a spec rule, so this also refuses an ID outside the spec.
        implements = KINDS[self.kind].rule_id
        if implements != self.id:
            raise ValueError(f"kind {self.kind!r} implements {implements}, not {self.id}")
        self._check_text()
        return self

    def _check_text(self) -> None:
        declared = set(type(self.params).model_fields)
        unused = declared - placeholders(self.condition) - placeholders(self.action)
        if unused:
            raise ValueError(
                f"{self.id}: params never referenced in condition or action: {sorted(unused)}"
            )
        self.text()  # every placeholder resolves and formats

    def text(self) -> RuleText:
        """The write-up rendered from this rule's params: a `Price` or `Money` as `Decimal`
        dollars."""
        values = {
            name: _display(getattr(self.params, name)) for name in type(self.params).model_fields
        }
        try:
            return RuleText(
                *(render(t, values) for t in (self.condition, self.action, self.rationale))
            )
        except ValueError as e:
            raise ValueError(f"{self.id}: {e}") from None


def _describe(error: ValidationError) -> str:
    """Each problem as "field: message", so it reads as the rule's params, not the rule's fields."""
    return "; ".join(
        ": ".join([*(".".join(map(str, e["loc"])),) * bool(e["loc"]), e["msg"]])
        for e in error.errors()
    )


def _display(value: object) -> object:
    return value.to_dollars() if isinstance(value, Price | Money) else value


class FillModel(BaseModel):
    """Spec › Fill model: buys fill at mid + capture × half-spread, sells at mid − it; a fee per
    contract. Not a rule: fills carry the rule ID of the decision that made them."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    spread_capture: float = Field(ge=0, le=1)
    fee_per_contract: DollarMoney


class Detail(StrEnum):
    """How much of a run its result file keeps (PO, DEC-54)."""

    FULL = "full"  # the blotter, ledger and gate log, and at P6 the cycles and attribution
    SUMMARY = "summary"  # the summary only: ablation and sensitivity runs


class Section(StrEnum):
    """A strategy page's optional sections; the rest every strategy page shows (PO, DEC-54)."""

    GATE_LOG = "gate_log"
    GREEK_ATTRIBUTION = "greek_attribution"


class Report(BaseModel):
    """A strategy's `report` block, never inherited: a file without one keeps a summary."""

    # A dump always holds `sections`, so the results schema marks it required.
    model_config = ConfigDict(
        extra="forbid", frozen=True, json_schema_serialization_defaults_required=True
    )

    detail: Detail
    sections: tuple[Section, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        twice = sorted({s for s in self.sections if self.sections.count(s) > 1})
        if twice:
            raise ValueError(f"report sections given more than once: {twice}")
        if self.sections and self.detail is not Detail.FULL:
            raise ValueError("report sections need full detail: a summary has no rows to show")
        return self


class StrategyConfig(BaseModel):
    """A strategy or variant: its run ID, name, fill model, rules in the spec's order, and what its
    results report."""

    # A dump always holds `report`, so the results schema marks it required (P4-05).
    model_config = ConfigDict(
        extra="forbid", frozen=True, json_schema_serialization_defaults_required=True
    )

    id: str = Field(pattern=_RUN_ID)
    name: str = Field(pattern=r"\S")
    fill_model: FillModel
    rules: tuple[Rule, ...]
    report: Report = Report(detail=Detail.SUMMARY)

    @field_validator("rules")
    @classmethod
    def _complete(cls, rules: tuple[Rule, ...]) -> tuple[Rule, ...]:
        ids = [r.id for r in rules]
        twice = sorted({i for i in ids if ids.count(i) > 1})
        if twice:
            raise ValueError(f"rules defined more than once: {twice}")
        missing = sorted(_REQUIRED - set(ids), key=_SPEC_ORDER.__getitem__)
        if missing:
            raise ValueError(f"missing required rules: {missing}")
        return tuple(sorted(rules, key=lambda r: _SPEC_ORDER[r.id]))

    @property
    def rule_ids(self) -> frozenset[RuleId]:
        """The rule IDs defined here: the valid stamps for its blotter and gate log (INV-09)."""
        return frozenset(r.id for r in self.rules)

    def rule(self, rule_id: RuleId) -> Rule:
        for r in self.rules:
            if r.id == rule_id:
                return r
        raise KeyError(f"{self.id} doesn't define {rule_id}")


class RunConfig(BaseModel):
    """What a run is configured with: the strategy, and the universe's window and r. The symbol is
    the run's input, not its config, so every symbol run on one config shares its hash."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy: StrategyConfig
    window: Window
    risk_free_rate: RiskFreeRate

    def canonical_json(self) -> str:
        """The resolved config as JSON with sorted keys and no whitespace; non-ASCII kept as is."""
        return json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def config_hash(self) -> str:
        """sha256 of `canonical_json()` in UTF-8."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def load_strategy(path: Path) -> StrategyConfig:
    """The strategy `path` defines, with its `extends` chain and `overrides` applied."""
    resolved = resolve(path)
    report = {} if resolved.report is None else {"report": resolved.report}
    return StrategyConfig.model_validate(
        {
            "id": resolved.id,
            "name": resolved.name,
            "fill_model": resolved.fill_model,
            "rules": tuple(resolved.rules.values()),
            **report,
        }
    )


def load_run_config(path: Path, universe: Universe) -> RunConfig:
    """The strategy at `path`, run over `universe`'s window at its r."""
    return RunConfig(
        strategy=load_strategy(path),
        window=universe.window,
        risk_free_rate=universe.risk_free_rate,
    )
