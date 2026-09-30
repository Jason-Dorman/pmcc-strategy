"""The kind registry and `build_strategy` (P3-06; DEC-53, DEC-90)."""

from pathlib import Path

import pytest

from pmcc.config.kinds import KINDS
from pmcc.config.strategy import CONFIGS_DIR, load_strategy
from pmcc.domain.money import Price
from pmcc.domain.rules import RuleId
from pmcc.strategy.exits import DefensiveDelta, FridayCheck, LongDeltaReset, LongDteRoll, TakeProfit
from pmcc.strategy.gates import EventRatioGate, MinPremiumGate, StructuralGate, VrpGate
from pmcc.strategy.registry import FACTORIES, Strategy, build_strategy
from pmcc.strategy.selectors import (
    CheapestReplacement,
    DteRangeExpiry,
    ExpectedMoveStrike,
    NearestDeltaLong,
    NearestDeltaShort,
    NearestDteExpiry,
)
from pmcc.strategy.trigger import SpreadTrigger

BASELINE = CONFIGS_DIR / "baseline_pmcc.yaml"
QUANT = CONFIGS_DIR / "quant_pmcc.yaml"


def _write(tmp_path: Path, name: str, text: str) -> Path:
    (tmp_path / "_shared.yaml").write_bytes((CONFIGS_DIR / "_shared.yaml").read_bytes())
    (tmp_path / "baseline_pmcc.yaml").write_bytes(BASELINE.read_bytes())
    path = tmp_path / name
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def test_every_kind_has_a_factory_and_nothing_else_does() -> None:
    assert set(FACTORIES) == set(KINDS)


def test_the_baseline_builds_from_its_rules() -> None:
    strategy = build_strategy(load_strategy(BASELINE))
    assert isinstance(strategy.long_selector.expiry, NearestDteExpiry)
    assert strategy.long_selector.expiry.target_dte == 180
    assert isinstance(strategy.long_selector.strike, NearestDeltaLong)
    assert strategy.long_selector.strike.target_delta == 0.80
    assert isinstance(strategy.short_selector.strike, NearestDeltaShort)
    assert strategy.short_selector.strike.target_delta == 0.30
    assert isinstance(strategy.trigger, SpreadTrigger)
    assert strategy.trigger.long_max_spread == 0.03
    assert strategy.trigger.short_max_spread == 0.10
    assert strategy.long_contracts == 1
    assert [type(g) for g in strategy.gates] == [StructuralGate]
    assert [type(x) for x in strategy.long_exits] == [LongDeltaReset, LongDteRoll]
    assert [type(x) for x in strategy.short_exits] == [TakeProfit, DefensiveDelta, FridayCheck]


def test_the_baseline_carries_its_thresholds() -> None:
    strategy = build_strategy(load_strategy(BASELINE))
    take, defend, friday = strategy.short_exits
    assert isinstance(take, TakeProfit)
    assert take.max_credit_fraction == 0.25
    assert isinstance(defend, DefensiveDelta)
    assert defend.max_delta == 0.60
    assert isinstance(friday, FridayCheck)
    assert friday.em_buffer == 0.25
    reset, roll = strategy.long_exits
    assert isinstance(reset, LongDeltaReset)
    assert reset.min_delta == 0.50
    assert isinstance(roll, LongDteRoll)
    assert roll.min_dte == 90


def test_x_s1_runs_until_x_s3s_check_time(tmp_path: Path) -> None:
    path = _write(tmp_path, "later.yaml", """\
id: baseline_pmcc--late
name: Later check
extends: baseline_pmcc.yaml
overrides:
  X-S3: {params: {check_by: "15:30"}}
""")  # fmt: skip
    take = build_strategy(load_strategy(path)).short_exits[0]
    assert isinstance(take, TakeProfit)
    assert take.check_by.hour == 15
    assert take.check_by.minute == 30


def test_an_optional_rule_left_out_is_not_built(tmp_path: Path) -> None:
    path = _write(tmp_path, "no_tp.yaml", """\
id: baseline_pmcc--a5
name: Without take profit
extends: baseline_pmcc.yaml
overrides:
  X-S1: {remove: true}
""")  # fmt: skip
    strategy = build_strategy(load_strategy(path))
    assert [type(x) for x in strategy.short_exits] == [DefensiveDelta, FridayCheck]
    assert RuleId("X-S1") not in strategy.rule_ids


def test_the_quant_strategy_builds_from_its_rules() -> None:
    strategy = build_strategy(load_strategy(QUANT))
    expiry, strike = strategy.long_selector.expiry, strategy.long_selector.strike
    assert isinstance(expiry, DteRangeExpiry)
    assert (expiry.min_dte, expiry.max_dte) == (120, 270)
    assert isinstance(strike, CheapestReplacement)
    assert (strike.min_delta, strike.max_delta) == (0.70, 0.90)
    short = strategy.short_selector.strike
    assert isinstance(short, ExpectedMoveStrike)
    assert short.k == 1.0
    assert [type(g) for g in strategy.gates] == [StructuralGate, EventRatioGate, VrpGate,
                                                 MinPremiumGate]  # fmt: skip
    _, g3, g4, g5 = strategy.gates
    assert isinstance(g3, EventRatioGate)
    assert g3.max_ratio == 1.20
    assert isinstance(g4, VrpGate)
    assert g4.min_ratio == 1.00
    assert isinstance(g5, MinPremiumGate)
    assert g5.min_mid == Price.from_dollars("0.10")


def test_the_quant_strategy_shares_the_baselines_exits() -> None:
    quant, baseline = build_strategy(load_strategy(QUANT)), build_strategy(load_strategy(BASELINE))
    assert quant.long_exits == baseline.long_exits
    assert quant.short_exits == baseline.short_exits
    assert quant.trigger == baseline.trigger


def _shape(strategy: Strategy) -> dict[str, object]:
    """Which rule class fills each slot a quant layer occupies."""
    return {
        "E-L2": type(strategy.long_selector.expiry),
        "E-L3": type(strategy.long_selector.strike),
        "E-S3": type(strategy.short_selector.strike),
        "gates": [type(g) for g in strategy.gates],
        "short_exits": [type(x) for x in strategy.short_exits],
    }


@pytest.mark.parametrize(
    ("ablation", "layer"),
    [
        ("a1", {"E-L2": NearestDteExpiry, "E-L3": NearestDeltaLong}),
        ("a2", {"E-S3": NearestDeltaShort}),
        ("a3", {"gates": [StructuralGate, VrpGate, MinPremiumGate]}),
        ("a4", {"gates": [StructuralGate, EventRatioGate, MinPremiumGate]}),
        ("a5", {"short_exits": [DefensiveDelta, FridayCheck]}),
    ],
)
def test_each_ablation_builds_as_quant_but_for_its_layer(
    ablation: str, layer: dict[str, object]
) -> None:
    built = build_strategy(load_strategy(CONFIGS_DIR / "ablations" / f"{ablation}.yaml"))
    assert _shape(built) == {**_shape(build_strategy(load_strategy(QUANT))), **layer}
