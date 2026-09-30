"""Resolving a strategy file's `extends` chain and `overrides` into one set of raw rules (DEC-53).

A file may extend one parent, named by a path relative to itself. It adds rules the parent doesn't
define, patches `fill_model` field by field, and changes the parent's rules only through
`overrides`, keyed by rule ID, each with exactly one operation:

- `params`: patch those params, keeping the rest;
- `replace`: a whole new rule under the same ID (a variant swaps a kind this way);
- `remove: true`: drop the rule ("off" is absence, never a flag).

`id` and `name` are never inherited: the file loaded names the strategy. Rules stay raw mappings
here; `pmcc.config.strategy` validates the result.
"""

from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from pmcc.config.fields import RuleIdField
from pmcc.config.yaml_file import read_yaml
from pmcc.domain import RuleId

type RawRule = dict[str, object]


class Override(BaseModel):
    """One `overrides` entry: exactly one operation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    params: dict[str, object] | None = None
    replace: RawRule | None = None
    remove: Literal[True] | None = None

    @model_validator(mode="after")
    def _one_operation(self) -> Self:
        given = [op for op in ("params", "replace", "remove") if getattr(self, op) is not None]
        if len(given) != 1:
            raise ValueError(
                f"an override takes exactly one of params, replace, remove; got {given}"
            )
        if self.params == {}:
            raise ValueError("an override's params patch is empty, so it would change nothing")
        return self


class StrategyFile(BaseModel):
    """One YAML file as written. `_shared.yaml` has no `id`: it's only ever extended."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str | None = None
    name: str | None = None
    extends: str | None = None
    fill_model: dict[str, object] = {}
    rules: tuple[RawRule, ...] = ()
    overrides: dict[RuleIdField, Override] = {}

    @field_validator("extends")
    @classmethod
    def _relative_yaml(cls, extends: str | None) -> str | None:
        """A parent is a `.yaml` file named relative to this one, so a config means the same on
        every machine (DEC-58)."""
        if extends is not None and (extends.startswith("/") or ":" in extends or "\\" in extends):
            raise ValueError(
                f"extends must be a relative path with forward slashes, not {extends!r}"
            )
        if extends is not None and PurePath(extends).suffix != ".yaml":
            raise ValueError(f"extends must name a .yaml file, not {extends!r}")
        return extends


@dataclass(frozen=True, slots=True)
class Resolved:
    """A file with its parents folded in: the loaded file's id and name, and raw rules by ID."""

    id: str | None = None
    name: str | None = None
    fill_model: dict[str, object] = field(default_factory=dict[str, object])
    rules: dict[RuleId, RawRule] = field(default_factory=dict[RuleId, RawRule])


class ConfigError(ValueError):
    """A strategy file that can't be resolved: a cycle, a rule defined twice, a bad override."""


def resolve(path: Path) -> Resolved:
    """`path` with its `extends` chain and `overrides` applied."""
    return _resolve(path.resolve(), ())


def _resolve(path: Path, chain: tuple[Path, ...]) -> Resolved:
    if path in chain:
        raise ConfigError(f"extends cycle: {' → '.join(p.name for p in (*chain, path))}")
    if not path.is_file():  # a directory too, which Windows and Linux would report differently
        raise FileNotFoundError(f"no config file at {path}")
    file = StrategyFile.model_validate(read_yaml(path))
    parent = (
        _resolve((path.parent / file.extends).resolve(), (*chain, path))
        if file.extends
        else Resolved()
    )
    try:
        return _fold(parent, file)
    except ConfigError as e:
        raise ConfigError(f"{path.name}: {e}") from None


def _fold(parent: Resolved, file: StrategyFile) -> Resolved:
    rules = dict(parent.rules)
    for raw in file.rules:
        rule_id = _rule_id(raw)
        if rule_id in rules:
            raise ConfigError(
                f"{rule_id} is defined more than once; change a parent's rule with overrides"
            )
        rules[rule_id] = raw
    for rule_id, override in file.overrides.items():
        if rule_id not in parent.rules:
            raise ConfigError(f"overrides {rule_id}, which no parent defines")
        _apply(rules, rule_id, override)
    return Resolved(file.id, file.name, {**parent.fill_model, **file.fill_model}, rules)


def _apply(rules: dict[RuleId, RawRule], rule_id: RuleId, override: Override) -> None:
    if override.remove:
        del rules[rule_id]
    elif override.replace is not None:
        if override.replace.get("id", rule_id) != rule_id:
            raise ConfigError(f"the replacement for {rule_id} is given another id")
        rules[rule_id] = {**override.replace, "id": rule_id}
    elif override.params is not None:
        old = rules[rule_id].get("params", {})
        if not isinstance(old, dict):
            raise ConfigError(f"{rule_id}'s params aren't a mapping, so they can't be patched")
        rules[rule_id] = {**rules[rule_id], "params": {**old, **override.params}}


def _rule_id(raw: RawRule) -> RuleId:
    value = raw.get("id")
    if not isinstance(value, str):
        raise ConfigError(f"a rule needs an id: {raw!r}")
    return RuleId(value)
