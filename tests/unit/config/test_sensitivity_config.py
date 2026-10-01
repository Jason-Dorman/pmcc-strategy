"""The run matrix and `configs/sensitivity.yaml` (P5-02): 24 run IDs per symbol in ARCHITECTURE
§11's order, each sensitivity variant differing from its strategy only in what its check varies
(Spec › Sensitivity checks; PO, DEC-31; DEC-53), and the loader's refusals."""

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from pmcc.config.calendar import load_calendar
from pmcc.config.extends import ConfigError
from pmcc.config.kinds import FixedBarTrigger, SpreadTrigger
from pmcc.config.matrix import (
    SENSITIVITY_PATH,
    Family,
    load_sensitivity,
    run_families,
    run_matrix,
    strategy_configs,
)
from pmcc.config.strategy import CONFIGS_DIR, Detail, StrategyConfig, load_strategy
from pmcc.config.universe import load_universe
from pmcc.domain import RuleId
from pmcc.strategy.registry import build_strategy

BASELINE = load_strategy(CONFIGS_DIR / "baseline_pmcc.yaml")
QUANT = load_strategy(CONFIGS_DIR / "quant_pmcc.yaml")
VARIANTS = {v.id: v for v in load_sensitivity()}
STRATEGIES = {"baseline_pmcc": BASELINE, "quant_pmcc": QUANT}

# ARCHITECTURE §11's table, in its order.
RUN_IDS = (
    "baseline_pmcc", "quant_pmcc",
    *(f"quant_pmcc--a{n}" for n in range(1, 6)),
    "baseline_pmcc--sc025", "baseline_pmcc--sc050", "quant_pmcc--sc025", "quant_pmcc--sc050",
    *(f"baseline_pmcc--t{k}" for k in range(1, 8)),
    "quant_pmcc--k075", "quant_pmcc--k125", "quant_pmcc--g4r090", "quant_pmcc--g4r110",
    "quant_pmcc--g3r110", "quant_pmcc--g3r130",
)  # fmt: skip


def strategy_of(variant: StrategyConfig) -> StrategyConfig:
    return STRATEGIES[variant.id.split("--")[0]]


def changed_rules(variant: StrategyConfig) -> list[str]:
    strategy = strategy_of(variant)
    assert variant.rule_ids == strategy.rule_ids
    return [str(r.id) for r in variant.rules if r != strategy.rule(r.id)]


# ---- the matrix ---------------------------------------------------------------------------------


def test_p5_02_matrix_gives_24_run_ids_per_symbol_in_section_11s_order() -> None:
    matrix = run_matrix(load_universe(load_calendar()))
    assert tuple(c.strategy.id for c in matrix) == RUN_IDS
    assert len(RUN_IDS) == 24


def test_p5_02_matrix_runs_over_the_universes_window_and_r() -> None:
    universe = load_universe(load_calendar())
    for config in run_matrix(universe):
        assert (config.window, config.risk_free_rate) == (universe.window, universe.risk_free_rate)


def test_p5_02_every_run_builds() -> None:
    for strategy in strategy_configs():
        assert build_strategy(strategy).config == strategy


def test_dec_54_only_the_two_strategies_keep_full_detail() -> None:
    full = [s.id for s in strategy_configs() if s.report.detail is Detail.FULL]
    assert full == ["baseline_pmcc", "quant_pmcc"]


# ---- friction -----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("run_id", "capture"),
    [("baseline_pmcc--sc025", 0.25), ("baseline_pmcc--sc050", 0.50),
     ("quant_pmcc--sc025", 0.25), ("quant_pmcc--sc050", 0.50)],
)  # fmt: skip
def test_friction_variant_changes_only_spread_capture(run_id: str, capture: float) -> None:
    variant = VARIANTS[run_id]
    strategy = strategy_of(variant)
    assert strategy.fill_model.spread_capture == 0  # Spec › Fill model: default 0
    assert variant.fill_model.spread_capture == capture
    assert variant.fill_model.fee_per_contract == strategy.fill_model.fee_per_contract
    assert changed_rules(variant) == []


# ---- entry timing (DEC-31) ----------------------------------------------------------------------


@pytest.mark.parametrize("bar", range(1, 8))
def test_dec_31_timing_variant_replaces_only_e_t1_with_its_bar(bar: int) -> None:
    variant = VARIANTS[f"baseline_pmcc--t{bar}"]
    assert changed_rules(variant) == ["E-T1"]
    assert variant.fill_model == BASELINE.fill_model
    rule = variant.rule(RuleId("E-T1"))
    assert rule.kind == "fixed_bar_trigger"
    assert isinstance(rule.params, FixedBarTrigger)
    assert rule.params.bar == bar
    assert rule.text().action == (
        "Enter the long on the first bar of the session where the condition holds. Decide the "
        f"short only on session bar {bar} of the week-open session (bar 1 ends at 10:00): sell "
        "it if the condition holds there, or else G-1 skips the week"
    )


def test_dec_31_timing_variants_keep_e_t1s_spread_limits() -> None:
    e_t1 = BASELINE.rule(RuleId("E-T1")).params
    assert isinstance(e_t1, SpreadTrigger)
    for bar in range(1, 8):
        fixed = VARIANTS[f"baseline_pmcc--t{bar}"].rule(RuleId("E-T1")).params
        assert isinstance(fixed, FixedBarTrigger)
        assert (fixed.long_max_spread, fixed.short_max_spread) == (
            e_t1.long_max_spread, e_t1.short_max_spread)  # fmt: skip


def test_dec_31_timing_runs_cover_every_session_bar() -> None:
    triggers = {v.id: v.rule(RuleId("E-T1")).params for v in VARIANTS.values()}
    fixed = {i: p.bar for i, p in triggers.items() if isinstance(p, FixedBarTrigger)}
    assert sorted(fixed.values()) == list(range(1, 8))
    assert all(i.startswith("baseline_pmcc--") for i in fixed)  # Spec: the baseline only


def test_dec_31_fixed_bar_refuses_a_bar_outside_the_session() -> None:
    for bar in (0, 8):
        with pytest.raises(ValidationError, match="bar"):
            FixedBarTrigger(bar=bar, long_max_spread=0.03, short_max_spread=0.10)


# ---- parameter grid -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("run_id", "rule_id", "param", "value", "default"),
    [
        ("quant_pmcc--k075", "E-S3", "k", 0.75, 1.00),
        ("quant_pmcc--k125", "E-S3", "k", 1.25, 1.00),
        ("quant_pmcc--g4r090", "G-4", "min_ratio", 0.90, 1.00),
        ("quant_pmcc--g4r110", "G-4", "min_ratio", 1.10, 1.00),
        ("quant_pmcc--g3r110", "G-3", "max_ratio", 1.10, 1.20),
        ("quant_pmcc--g3r130", "G-3", "max_ratio", 1.30, 1.20),
    ],
)
def test_grid_variant_moves_one_parameter_from_the_quant_default(
    run_id: str, rule_id: str, param: str, value: float, default: float
) -> None:
    variant = VARIANTS[run_id]
    assert changed_rules(variant) == [rule_id]
    assert variant.fill_model == QUANT.fill_model
    assert getattr(QUANT.rule(RuleId(rule_id)).params, param) == default
    new, old = variant.rule(RuleId(rule_id)), QUANT.rule(RuleId(rule_id))
    assert new.params.model_dump() == {**old.params.model_dump(), param: value}
    assert new.model_dump(exclude={"params"}) == old.model_dump(exclude={"params"})


# ---- the loader's refusals ----------------------------------------------------------------------


def _configs(tmp_path: Path, variants: str, check: str = "friction") -> Path:
    """A copy of configs/ whose sensitivity.yaml holds `variants` (YAML list items) as `check`'s."""
    copied = tmp_path / "configs"
    shutil.copytree(CONFIGS_DIR, copied)
    (copied / "sensitivity.yaml").write_text(f"{check}:\n{variants}", encoding="utf-8",
                                             newline="\n")  # fmt: skip
    return copied


VARIANT = """  - id: {id}
    name: Test
    extends: {extends}
    fill_model: {{spread_capture: 0.25}}
"""


@pytest.mark.parametrize(
    ("variants", "message"),
    [
        (VARIANT.format(id="quant_pmcc--x", extends="baseline_pmcc.yaml"), "baseline_pmcc--"),
        (VARIANT.format(id="baseline_pmcc", extends="baseline_pmcc.yaml"), "baseline_pmcc--"),
        ("  - {id: baseline_pmcc--x, name: Test, fill_model: {spread_capture: 0.25}}\n",
         "must extend"),
        (VARIANT.format(id="quant_pmcc--a1", extends="quant_pmcc.yaml"), "more than once"),
        (VARIANT.format(id="baseline_pmcc--x", extends="baseline_pmcc.yaml") * 2,
         "more than once"),
        (VARIANT.format(id="baseline_pmcc--x", extends="missing.yaml"), "no config file"),
        ("  - {id: baseline_pmcc--x, name: T, extends: baseline_pmcc.yaml,"
         " fill_model: {spread_capture: 1.5}}\n", "variant baseline_pmcc--x: "),
    ],
)  # fmt: skip
def test_p5_02_matrix_refuses_a_bad_variant(tmp_path: Path, variants: str, message: str) -> None:
    configs = _configs(tmp_path, variants)
    with pytest.raises((ConfigError, FileNotFoundError), match=message):
        strategy_configs(configs, configs / "sensitivity.yaml")


def test_p5_02_sensitivity_file_refuses_unknown_keys_and_an_empty_list(tmp_path: Path) -> None:
    cases = {
        "  - {id: baseline_pmcc--x, name: T, extends: baseline_pmcc.yaml, x: 1}\n": "x",
        " []\n": "lists no variants",
    }
    for text, field in cases.items():
        configs = _configs(tmp_path / str(len(text)), text)
        with pytest.raises(ValidationError, match=field):
            load_sensitivity(configs / "sensitivity.yaml")


def test_p6_06_sensitivity_file_refuses_a_list_outside_the_three_checks(tmp_path: Path) -> None:
    variant = VARIANT.format(id="baseline_pmcc--x", extends="baseline_pmcc.yaml")
    configs = _configs(tmp_path, variant, check="variants")
    with pytest.raises(ValidationError, match="variants"):
        load_sensitivity(configs / "sensitivity.yaml")


# ---- families (P6-06) ---------------------------------------------------------------------------


def test_p6_06_every_run_has_its_family_in_section_11s_order() -> None:
    families = run_families()

    assert tuple(families) == RUN_IDS
    expected = [Family.STRATEGY] * 2 + [Family.ABLATION] * 5 + [Family.FRICTION] * 4 + [
        Family.TIMING] * 7 + [Family.GRID] * 6  # fmt: skip
    assert list(families.values()) == expected


@pytest.mark.parametrize("check", ["friction", "timing", "grid"])
def test_p6_06_a_variants_family_is_the_list_it_sits_in(tmp_path: Path, check: str) -> None:
    """A friction-looking variant under `grid` is grid's: the list decides, never the run ID."""
    configs = _configs(tmp_path, VARIANT.format(id="baseline_pmcc--sc099",
                                                extends="baseline_pmcc.yaml"), check)  # fmt: skip

    families = run_families(configs, configs / "sensitivity.yaml")

    assert families["baseline_pmcc--sc099"] is Family(check)


def test_p5_02_sensitivity_file_ships_next_to_the_strategies() -> None:
    assert SENSITIVITY_PATH == CONFIGS_DIR / "sensitivity.yaml"
