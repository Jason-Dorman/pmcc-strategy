"""The run matrix (ARCHITECTURE §11): every run `pmcc batch` makes on each symbol.

24 runs per symbol, in §11's order: the two strategies, the five ablations (`configs/ablations/`),
then `configs/sensitivity.yaml`'s variants: friction, entry timing (PO, DEC-31) and the quant
parameter grid (Spec › Sensitivity checks). A sensitivity variant is written as an ablation file is,
but inline: it `extends` a strategy file, relative to `configs/`, and changes it through
`fill_model` or `overrides` (DEC-53), so a new variant is a new entry and no code (§16).

A variant's run ID is its strategy's ID, `--`, a suffix (`quant_pmcc--k075`): the manifest's
`strategy_id` is the run ID's part before `--`, so the loader holds every variant to it.

Each run belongs to a family: a strategy, an ablation, or one of the sensitivity file's three
lists (`friction`, `timing`, `grid`). The robustness tables are the families (P6-06), so a run's
family is where its config sits, never read from its ID.
"""

from collections import Counter
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from pmcc.config.extends import ConfigError, StrategyFile
from pmcc.config.strategy import (
    CONFIGS_DIR,
    RunConfig,
    StrategyConfig,
    load_inline,
    load_strategy,
)
from pmcc.config.universe import Universe
from pmcc.config.yaml_file import read_yaml

SENSITIVITY_PATH = CONFIGS_DIR / "sensitivity.yaml"
STRATEGY_FILES = ("baseline_pmcc.yaml", "quant_pmcc.yaml")
ABLATIONS_DIR = "ablations"


class Family(StrEnum):
    """Which part of the matrix a run comes from; each family but the strategies is a robustness
    table (Spec › Robustness tables)."""

    STRATEGY = "strategy"
    ABLATION = "ablation"
    FRICTION = "friction"
    TIMING = "timing"
    GRID = "grid"


class SensitivityFile(BaseModel):
    """`configs/sensitivity.yaml` as written: inline strategy variants, one list per check."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    friction: tuple[StrategyFile, ...] = ()
    timing: tuple[StrategyFile, ...] = ()
    grid: tuple[StrategyFile, ...] = ()

    @model_validator(mode="after")
    def _some(self) -> Self:
        if not any(entries for _, entries in self.checks()):
            raise ValueError("the sensitivity file lists no variants")
        return self

    def checks(self) -> tuple[tuple[Family, tuple[StrategyFile, ...]], ...]:
        """Each check's variants, in the file's fixed order: friction, timing, grid."""
        return ((Family.FRICTION, self.friction), (Family.TIMING, self.timing),
                (Family.GRID, self.grid))  # fmt: skip


def load_sensitivity(path: Path = SENSITIVITY_PATH) -> tuple[StrategyConfig, ...]:
    """Every variant `path` defines, in its order, resolved and validated."""
    return tuple(config for _, config in _sensitivity(path))


def _sensitivity(path: Path) -> tuple[tuple[Family, StrategyConfig], ...]:
    file = SensitivityFile.model_validate(read_yaml(path))
    return tuple(
        (family, _variant(entry, path)) for family, entries in file.checks() for entry in entries
    )


def _variant(entry: StrategyFile, path: Path) -> StrategyConfig:
    if entry.extends is None:
        raise ConfigError(f"{path.name}: variant {entry.id} must extend a strategy file")
    try:
        variant = load_inline(entry, path.parent, path.name)
    except ValueError as e:  # pydantic's ValidationError too: name the entry it came from
        raise ConfigError(f"{path.name}: variant {entry.id}: {e}") from None
    strategy = load_strategy(path.parent / entry.extends)
    if not variant.id.startswith(f"{strategy.id}--"):
        raise ConfigError(
            f"{path.name}: variant {variant.id} extends {strategy.id}, so its run ID must be "
            f"{strategy.id}--<suffix>"
        )
    return variant


def strategy_configs(
    configs: Path = CONFIGS_DIR, sensitivity: Path = SENSITIVITY_PATH
) -> tuple[StrategyConfig, ...]:
    """Every run's strategy in §11's order. Raises `ConfigError` for a run ID given twice."""
    return tuple(config for _, config in _matrix(configs, sensitivity))


def run_families(
    configs: Path = CONFIGS_DIR, sensitivity: Path = SENSITIVITY_PATH
) -> dict[str, Family]:
    """Each run ID's family, in §11's order."""
    return {config.id: family for family, config in _matrix(configs, sensitivity)}


def _matrix(configs: Path, sensitivity: Path) -> tuple[tuple[Family, StrategyConfig], ...]:
    strategies = tuple((Family.STRATEGY, load_strategy(configs / n)) for n in STRATEGY_FILES)
    ablations = tuple((Family.ABLATION, load_strategy(p))
                      for p in sorted((configs / ABLATIONS_DIR).glob("*.yaml")))  # fmt: skip
    every = (*strategies, *ablations, *_sensitivity(sensitivity))
    twice = sorted(i for i, n in Counter(s.id for _, s in every).items() if n > 1)
    if twice:
        raise ConfigError(f"run IDs given more than once: {twice}")
    return every


def run_matrix(universe: Universe, configs: Path = CONFIGS_DIR,
               sensitivity: Path = SENSITIVITY_PATH) -> tuple[RunConfig, ...]:  # fmt: skip
    """Every run's config over `universe`'s window at its r, as `load_run_config` builds one."""
    return tuple(
        RunConfig(strategy=s, window=universe.window, risk_free_rate=universe.risk_free_rate)
        for s in strategy_configs(configs, sensitivity)
    )
