"""The run matrix (ARCHITECTURE §11): every run `pmcc batch` makes on each symbol.

24 runs per symbol, in §11's order: the two strategies, the five ablations (`configs/ablations/`),
then `configs/sensitivity.yaml`'s variants: friction, entry timing (PO, DEC-31) and the quant
parameter grid (Spec › Sensitivity checks). A sensitivity variant is written as an ablation file is,
but inline: it `extends` a strategy file, relative to `configs/`, and changes it through
`fill_model` or `overrides` (DEC-53), so a new variant is a new entry and no code (§16).

A variant's run ID is its strategy's ID, `--`, a suffix (`quant_pmcc--k075`): the manifest's
`strategy_id` is the run ID's part before `--`, so the loader holds every variant to it.
"""

from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

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


class SensitivityFile(BaseModel):
    """`configs/sensitivity.yaml` as written: a list of inline strategy variants."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    variants: tuple[StrategyFile, ...] = Field(min_length=1)


def load_sensitivity(path: Path = SENSITIVITY_PATH) -> tuple[StrategyConfig, ...]:
    """Every variant `path` defines, in its order, resolved and validated."""
    file = SensitivityFile.model_validate(read_yaml(path))
    return tuple(_variant(entry, path) for entry in file.variants)


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
    strategies = tuple(load_strategy(configs / name) for name in STRATEGY_FILES)
    ablations = tuple(load_strategy(p) for p in sorted((configs / ABLATIONS_DIR).glob("*.yaml")))
    every = (*strategies, *ablations, *load_sensitivity(sensitivity))
    twice = sorted(i for i, n in Counter(s.id for s in every).items() if n > 1)
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
