"""The wheel's config (`configs/wheel.yaml`; Spec › Trade rules): its rules, fill model and cash.

Each rule has its spec ID, its params (each rule ID has its own params model, so an unknown or
out-of-range threshold fails at load) and its write-up, validated as the PMCC's rules are: every
placeholder resolves, every param appears in the condition or action, and every param shows in
the summary. Rules come out in the spec's order; all are required, since the wheel has one rule
set (WD-05). The PMCC's `Rule` stays its own: it is keyed by the PMCC's kinds (WD-24).

`load_wheel_run` adds the universe's window and r; `config_hash` is the sha256 of the result as
canonical JSON, so a result's manifest names the exact config that produced it.

**Variants (W3-02):** a file that `extends` another (a path relative to itself, `.yaml`, forward
slashes) gives its own `id` and `name` and patches the parent's `fill_model` field by field; it
can change nothing else, since the wheel's rules are fixed (WD-05). The friction runs are two such
files in `configs/wheel_friction/`, at spread capture 0.25 and 0.50 (Spec › Fill model).
"""

import hashlib
import json
from pathlib import Path
from types import MappingProxyType
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

from pmcc.config.fields import DollarMoney, RuleIdField
from pmcc.config.kinds import Fraction, NoParams, Params
from pmcc.config.rule_text import placeholders, render, shown
from pmcc.config.strategy import CONFIGS_DIR, FillModel, RuleText
from pmcc.config.universe import RiskFreeRate, Universe, Window
from pmcc.config.yaml_file import read_yaml
from pmcc.domain import RuleId

WHEEL_PATH = CONFIGS_DIR / "wheel.yaml"
FRICTION_DIR = CONFIGS_DIR / "wheel_friction"


class WheelConfigError(Exception):
    """The wheel's config is malformed."""


class SpreadTrigger(Params):  # W-T1
    max_spread: Fraction


class NearestDelta(Params):  # W-P3, W-C3: the delta's size; a put's is negative
    target_delta: Fraction


class Contracts(Params):  # W-P4
    contracts: int = Field(ge=1)


_PARAMS: MappingProxyType[str, type[Params]] = MappingProxyType(
    {
        "W-T1": SpreadTrigger,
        "W-P1": NoParams,
        "W-P2": NoParams,
        "W-P3": NearestDelta,
        "W-P4": Contracts,
        "W-C1": NoParams,
        "W-C2": NoParams,
        "W-C3": NearestDelta,
        "W-X1": NoParams,
        "W-X2": NoParams,
        "W-X3": NoParams,
        "W-X4": NoParams,
        "W-X5": NoParams,
    }
)
WHEEL_RULE_IDS: tuple[RuleId, ...] = tuple(RuleId(i) for i in _PARAMS)
"""Every rule in the spec's Trade rules table, in its order."""
_ORDER = {rule_id: i for i, rule_id in enumerate(WHEEL_RULE_IDS)}

AnyParams = Annotated[
    SerializeAsAny[Params],
    WithJsonSchema(
        {"type": "object", "additionalProperties": {"type": ["number", "string"]}},
        mode="serialization",
    ),
]


class WheelRule(BaseModel):
    """One rule: its spec ID, its params and its write-up templates."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: RuleIdField
    name: str = Field(pattern=r"\S")
    params: AnyParams
    title: str = Field(pattern=r"\S")
    summary: str = Field(pattern=r"\S")
    condition: str = Field(pattern=r"\S")
    action: str = Field(pattern=r"\S")
    rationale: str = Field(pattern=r"\S")

    @model_validator(mode="before")
    @classmethod
    def _typed_params(cls, data: object) -> object:
        """Validates `params` with the rule's own model, so an unknown param fails here."""
        raw = cast(dict[str, object], data) if isinstance(data, dict) else None
        if raw is None or "id" not in raw:
            return cast(object, data)  # pydantic reports what's missing
        model = _PARAMS.get(str(raw["id"]))
        if model is None:
            raise ValueError(f"{raw['id']} isn't a wheel rule")
        try:
            params = model.model_validate(raw.get("params", {}))
        except ValidationError as e:
            raise ValueError(f"{raw['id']} params: {e}") from None
        return {**raw, "params": params}

    @model_validator(mode="after")
    def _check_text(self) -> Self:
        declared = set(type(self.params).model_fields)
        unused = declared - placeholders(self.condition) - placeholders(self.action)
        if unused:
            raise ValueError(f"{self.id}: params never referenced in condition or action: {unused}")
        unshown = declared - placeholders(self.summary)
        if unshown:
            raise ValueError(f"{self.id}: params never shown in the summary: {sorted(unshown)}")
        self.text()
        return self

    def text(self) -> RuleText:
        """The write-up rendered from this rule's params."""
        try:
            return RuleText(*(render(t, self._values()) for t in self._templates()))
        except ValueError as e:
            raise ValueError(f"{self.id}: {e}") from None

    def shown_params(self) -> dict[str, str]:
        """Each param as the rule's text shows it."""
        return shown(self._templates(), self._values())

    def _templates(self) -> tuple[str, str, str, str, str]:
        return self.title, self.summary, self.condition, self.action, self.rationale

    def _values(self) -> dict[str, object]:
        return {name: getattr(self.params, name) for name in type(self.params).model_fields}


class WheelConfig(BaseModel):
    """The wheel: its run ID, name, starting cash, fill model and rules in the spec's order."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*(--[a-z0-9]+)*$")
    name: str = Field(pattern=r"\S")
    starting_cash: DollarMoney
    fill_model: FillModel
    rules: tuple[WheelRule, ...]

    @field_validator("rules")
    @classmethod
    def _complete(cls, rules: tuple[WheelRule, ...]) -> tuple[WheelRule, ...]:
        ids = [r.id for r in rules]
        twice = sorted({i for i in ids if ids.count(i) > 1})
        if twice:
            raise ValueError(f"rules defined more than once: {twice}")
        missing = [i for i in WHEEL_RULE_IDS if i not in ids]
        if missing:
            raise ValueError(f"missing rules: {missing}")
        return tuple(sorted(rules, key=lambda r: _ORDER[r.id]))

    @property
    def rule_ids(self) -> frozenset[RuleId]:
        """The valid stamps for the blotter and gate log (WINV-09)."""
        return frozenset(r.id for r in self.rules)

    def rule(self, rule_id: RuleId) -> WheelRule:
        for r in self.rules:
            if r.id == rule_id:
                return r
        raise KeyError(f"{self.id} doesn't define {rule_id}")

    @property
    def max_spread(self) -> float:
        return cast(SpreadTrigger, self.rule(RuleId("W-T1")).params).max_spread

    @property
    def put_delta(self) -> float:
        return cast(NearestDelta, self.rule(RuleId("W-P3")).params).target_delta

    @property
    def contracts(self) -> int:
        return cast(Contracts, self.rule(RuleId("W-P4")).params).contracts

    @property
    def call_delta(self) -> float:
        return cast(NearestDelta, self.rule(RuleId("W-C3")).params).target_delta


class WheelRunConfig(BaseModel):
    """What a wheel run is configured with: the wheel, and the universe's window and r."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    wheel: WheelConfig
    window: Window
    risk_free_rate: RiskFreeRate

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )

    def config_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class WheelVariant(BaseModel):
    """A variant file as written: a new name, and the parent's fill model patched."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    name: str
    extends: str
    fill_model: dict[str, object] = {}

    @field_validator("extends")
    @classmethod
    def _relative_yaml(cls, extends: str) -> str:
        """Relative, with forward slashes, so a config means the same on every machine."""
        if extends.startswith("/") or ":" in extends or "\\" in extends:
            raise ValueError(f"extends must be a relative path with forward slashes: {extends!r}")
        if not extends.endswith(".yaml"):
            raise ValueError(f"extends must name a .yaml file: {extends!r}")
        return extends


def load_wheel(path: Path = WHEEL_PATH) -> WheelConfig:
    """The wheel `path` defines, its `extends` chain folded in. Raises `WheelConfigError`."""
    try:
        return WheelConfig.model_validate(_raw(path.resolve(), ()))
    except (ValidationError, ValueError, OSError) as exc:
        raise WheelConfigError(f"{path}: {exc}") from exc


def _raw(path: Path, chain: tuple[Path, ...]) -> dict[str, object]:
    if path in chain:
        raise ValueError(f"extends cycle: {' → '.join(p.name for p in (*chain, path))}")
    data = read_yaml(path)
    if not isinstance(data, dict) or "extends" not in data:
        return cast(dict[str, object], data)
    variant = WheelVariant.model_validate(data)
    parent = _raw((path.parent / variant.extends).resolve(), (*chain, path))
    fill_model = cast(dict[str, object], parent.get("fill_model", {}))
    return {**parent, "id": variant.id, "name": variant.name,
            "fill_model": {**fill_model, **variant.fill_model}}  # fmt: skip


def load_wheel_run(universe: Universe, path: Path = WHEEL_PATH) -> WheelRunConfig:
    """The wheel at `path`, over `universe`'s window at its r."""
    return WheelRunConfig(
        wheel=load_wheel(path), window=universe.window, risk_free_rate=universe.risk_free_rate
    )
