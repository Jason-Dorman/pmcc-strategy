"""The shipped `configs/quant_pmcc.yaml` and `configs/ablations/a1…a5.yaml` (P4-03): the quant
rules at the spec's thresholds, with the spec's names and gate conditions, and each ablation
differing from the quant PMCC only in its named layer (Spec › Ablations; DEC-53)."""

import re
from pathlib import Path

import pytest

from pmcc.config.kinds import SPEC_RULE_IDS
from pmcc.config.rule_text import placeholders
from pmcc.config.strategy import CONFIGS_DIR, Rule, StrategyConfig, load_strategy
from pmcc.domain import Price, RuleId

QUANT = load_strategy(CONFIGS_DIR / "quant_pmcc.yaml")
BASELINE = load_strategy(CONFIGS_DIR / "baseline_pmcc.yaml")
QUANT_LAYER = ("E-L2", "E-L3", "E-S3", "G-3", "G-4", "G-5")
SPEC = (Path(__file__).resolve().parents[3] / "docs" / "PMCC-Backtest-System-Spec.md").read_text(
    encoding="utf-8"
)
SPEC_ROWS = {
    rule_id: [c.strip() for c in rest.split(" | ")]
    for rule_id, rest in re.findall(r"^\| ((?:E-[LS]|G-)\d) \| (.+) \|$", SPEC, flags=re.MULTILINE)
}


def ablation(n: int) -> StrategyConfig:
    return load_strategy(CONFIGS_DIR / "ablations" / f"a{n}.yaml")


def rule(config: StrategyConfig, rule_id: str) -> Rule:
    return config.rule(RuleId(rule_id))


# ---- quant_pmcc -----------------------------------------------------------------------------


def test_config_quant_defines_every_spec_rule() -> None:
    # Spec › Strategies: "gates G-1 to G-5, shared exits".
    assert QUANT.rule_ids == frozenset(SPEC_RULE_IDS)
    assert [r.id for r in QUANT.rules] == list(SPEC_RULE_IDS)


def test_config_quant_is_named() -> None:
    assert (QUANT.id, QUANT.name) == ("quant_pmcc", "Quant PMCC")


def test_config_quant_shares_every_other_rule_and_the_fill_model_with_the_baseline() -> None:
    """Both strategies use the same entry timing and exits (DEC-35): only selection and skips
    differ."""
    shared = [r for r in QUANT.rules if str(r.id) not in QUANT_LAYER]
    assert shared == [r for r in BASELINE.rules if str(r.id) not in QUANT_LAYER]
    assert QUANT.fill_model == BASELINE.fill_model


@pytest.mark.parametrize(
    ("rule_id", "kind"),
    [("E-L2", "dte_range_expiry"), ("E-L3", "cheapest_replacement"),
     ("E-S3", "expected_move_strike"), ("G-3", "event_ratio_gate"), ("G-4", "vrp_gate"),
     ("G-5", "min_premium_gate")],
)  # fmt: skip
def test_config_quant_kinds_are_the_quant_rules(rule_id: str, kind: str) -> None:
    assert rule(QUANT, rule_id).kind == kind


@pytest.mark.parametrize(
    ("rule_id", "name", "value"),
    [
        ("E-L2", "min_dte", 120),
        ("E-L2", "max_dte", 270),
        ("E-L3", "min_delta", 0.70),
        ("E-L3", "max_delta", 0.90),
        ("E-S3", "k", 1.0),
        ("G-3", "max_ratio", 1.20),
        ("G-4", "min_ratio", 1.00),
        ("G-5", "min_mid", Price.from_dollars("0.10")),
    ],
)
def test_config_quant_holds_the_spec_threshold(rule_id: str, name: str, value: object) -> None:
    assert getattr(rule(QUANT, rule_id).params, name) == value


@pytest.mark.parametrize("rule_id", QUANT_LAYER)
def test_config_quant_rule_name_is_the_spec_name(rule_id: str) -> None:
    assert rule(QUANT, rule_id).name == SPEC_ROWS[rule_id][0]


@pytest.mark.parametrize("rule_id", ["G-3", "G-4", "G-5"])
def test_config_quant_gate_condition_is_the_spec_condition(rule_id: str) -> None:
    assert rule(QUANT, rule_id).text().condition == SPEC_ROWS[rule_id][1]


@pytest.mark.parametrize(
    ("rule_id", "field", "rendered"),
    [
        ("E-L2", "action", "from 120 to 270 days to expiry"),
        ("E-L3", "condition", "delta from 0.70 to 0.90 across the E-L2 expiries"),
        (
            "E-L3",
            "action",
            "lowest extrinsic ÷ delta, where extrinsic = mid − max(0, spot − strike)",
        ),
        ("E-L3", "action", "lower spread % of mid, then the earlier expiry, then the lower strike"),
        ("E-S3", "action", "lowest listed strike ≥ spot + 1.0 × EM"),
    ],
)
def test_config_quant_rule_text_renders_the_spec_rule(rule_id: str, field: str,
                                                      rendered: str) -> None:  # fmt: skip
    assert rendered in getattr(rule(QUANT, rule_id).text(), field)


def test_config_g_3_rationale_is_the_spec_paragraph() -> None:
    spec = re.search(r"^(G-3 detects events .+)$", SPEC, flags=re.MULTILINE)
    assert spec
    assert rule(QUANT, "G-3").text().rationale == spec[1]


@pytest.mark.parametrize("rule_id", QUANT_LAYER)
def test_config_quant_every_param_is_referenced_and_rendered(rule_id: str) -> None:
    r = rule(QUANT, rule_id)
    assert set(type(r.params).model_fields) <= placeholders(r.condition) | placeholders(r.action)
    text = r.text()
    assert all(s.strip() for s in (r.name, text.condition, text.action, text.rationale))
    assert not any("{" in s or "}" in s for s in (text.condition, text.action, text.rationale))


# ---- the ablations (config-diff) -------------------------------------------------------------

LAYERS = {
    1: {"E-L2", "E-L3"},  # cheapest-replacement long leg → the baseline's long selection
    2: {"E-S3"},  # expected-move short strike → the 0.30-delta short
    3: {"G-3"},  # off
    4: {"G-4"},  # off
    5: {"X-S1"},  # off: hold to the Friday check
}


def _differing(config: StrategyConfig) -> set[str]:
    """Rule IDs defined differently, or only on one side, against the quant PMCC."""
    ids = QUANT.rule_ids | config.rule_ids
    return {
        str(i) for i in ids
        if i not in QUANT.rule_ids or i not in config.rule_ids or rule(QUANT, i) != rule(config, i)
    }  # fmt: skip


@pytest.mark.parametrize("n", sorted(LAYERS))
def test_config_ablation_differs_from_quant_only_in_its_layer(n: int) -> None:
    config = ablation(n)
    assert _differing(config) == LAYERS[n]
    assert config.fill_model == QUANT.fill_model


@pytest.mark.parametrize("n", [3, 4, 5])
def test_config_ablation_switches_its_layer_off(n: int) -> None:
    assert ablation(n).rule_ids == QUANT.rule_ids - {RuleId(i) for i in LAYERS[n]}


@pytest.mark.parametrize("n", [1, 2])
def test_config_ablation_replaces_its_layer_with_the_baselines_rule(n: int) -> None:
    """Spec › Ablations: A1 uses the baseline long selection, A2 the 0.30-delta short. The rules
    are the baseline's, word for word, so the write-up can't drift between them."""
    for rule_id in LAYERS[n]:
        assert rule(ablation(n), rule_id) == rule(BASELINE, rule_id)


@pytest.mark.parametrize(
    ("n", "name"),
    [(1, "A1: quant with the baseline long leg"), (2, "A2: quant with the 0.30-delta short"),
     (3, "A3: quant without the event gate"), (4, "A4: quant without the VRP gate"),
     (5, "A5: quant without take profit")],
)  # fmt: skip
def test_config_ablation_run_id_and_name(n: int, name: str) -> None:
    # ARCHITECTURE §11: quant_pmcc--a1 … --a5.
    assert (ablation(n).id, ablation(n).name) == (f"quant_pmcc--a{n}", name)


def test_config_ablations_are_the_spec_five() -> None:
    table = re.findall(r"^\| (A\d) \| ", SPEC, flags=re.MULTILINE)
    assert table == [f"A{n}" for n in sorted(LAYERS)]
    assert sorted(p.name for p in (CONFIGS_DIR / "ablations").iterdir()) == [
        f"a{n}.yaml" for n in sorted(LAYERS)
    ]
