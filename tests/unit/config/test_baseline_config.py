"""The shipped `configs/_shared.yaml` and `configs/baseline_pmcc.yaml` (P3-01): every spec rule
the baseline runs, at the spec's thresholds, with text rendered from those thresholds (DEC-52) and
the PO's rationales (DEC-35)."""

import re
from datetime import time
from pathlib import Path

import pytest

from pmcc.config.kinds import SPEC_RULE_IDS
from pmcc.config.rule_text import placeholders
from pmcc.config.strategy import CONFIGS_DIR, Rule, RunConfig, load_run_config, load_strategy
from pmcc.config.universe import read_universe_file
from pmcc.domain import Money, RuleId

BASELINE = load_strategy(CONFIGS_DIR / "baseline_pmcc.yaml")
QUANT_ONLY_GATES = {RuleId("G-3"), RuleId("G-4"), RuleId("G-5")}
SHORT_EXITS = ("X-S1", "X-S2", "X-S3", "X-S4", "X-S5")
SPEC = (Path(__file__).resolve().parents[3] / "docs" / "PMCC-Backtest-System-Spec.md").read_text(
    encoding="utf-8"
)


def _spec_rows() -> dict[str, list[str]]:
    """Each rule's row in the spec's rule tables, after the ID, with backticks removed."""
    rows = re.findall(r"^\| ((?:E-[TLS]|G-|X-[SLE])\d) \| (.+) \|$", SPEC, flags=re.MULTILINE)
    return {
        rule_id: [c.strip().replace("`", "") for c in rest.split(" | ")] for rule_id, rest in rows
    }


SPEC_ROWS = _spec_rows()


def _spec_name(rule_id: str) -> str:
    """The entry table's Rule column, the gate table's Gate column, or an exit trigger's label."""
    if rule_id == "X-S4":
        return "Expires out of the money"  # unnamed in the spec; the PO's name (DEC-35)
    return re.split(r":| \(", SPEC_ROWS[rule_id][0])[0]  # "Friday check (bar ending …): …"


def _param(rule_id: str, name: str) -> object:
    return getattr(BASELINE.rule(RuleId(rule_id)).params, name)


def test_config_baseline_defines_every_spec_rule_but_the_quant_gates() -> None:
    # Spec › Strategies: "gates G-1 and G-2 only, shared exits".
    assert BASELINE.rule_ids == frozenset(SPEC_RULE_IDS) - QUANT_ONLY_GATES


def test_config_baseline_rule_ids_are_unique() -> None:
    ids = [r.id for r in BASELINE.rules]
    assert len(ids) == len(set(ids))


def test_config_baseline_rules_are_in_spec_order() -> None:
    assert [r.id for r in BASELINE.rules] == [i for i in SPEC_RULE_IDS if i in BASELINE.rule_ids]


def test_config_baseline_is_named() -> None:
    assert (BASELINE.id, BASELINE.name) == ("baseline_pmcc", "Baseline PMCC")


@pytest.mark.parametrize("rule", BASELINE.rules, ids=lambda r: str(r.id))
def test_config_every_placeholder_resolves_to_a_param(rule: Rule) -> None:
    used = placeholders(rule.condition) | placeholders(rule.action) | placeholders(rule.rationale)
    assert used <= set(type(rule.params).model_fields)


@pytest.mark.parametrize("rule", BASELINE.rules, ids=lambda r: str(r.id))
def test_config_every_param_is_referenced_in_condition_or_action(rule: Rule) -> None:
    used = placeholders(rule.condition) | placeholders(rule.action)
    assert set(type(rule.params).model_fields) <= used


@pytest.mark.parametrize("rule", BASELINE.rules, ids=lambda r: str(r.id))
def test_config_every_rule_has_its_write_up(rule: Rule) -> None:
    text = rule.text()
    assert all(s.strip() for s in (rule.name, text.condition, text.action, text.rationale))
    assert not any("{" in s or "}" in s for s in (text.condition, text.action, text.rationale))


@pytest.mark.parametrize(
    ("rule_id", "name", "value"),
    [
        ("E-T1", "long_max_spread", 0.03),
        ("E-T1", "short_max_spread", 0.10),
        ("E-L2", "target_dte", 180),
        ("E-L3", "target_delta", 0.80),
        ("E-L4", "contracts", 1),
        ("E-S3", "target_delta", 0.30),
        ("X-S1", "max_credit_fraction", 0.25),
        ("X-S2", "max_delta", 0.60),
        ("X-S3", "check_by", time(15, 0)),
        ("X-S3", "em_buffer", 0.25),
        ("X-L1", "min_delta", 0.50),
        ("X-L2", "min_dte", 90),
    ],
)
def test_config_baseline_holds_the_spec_threshold(rule_id: str, name: str, value: object) -> None:
    assert _param(rule_id, name) == value


def test_config_baseline_fill_model_is_the_spec_default() -> None:
    # Spec › Fill model: spread_capture defaults to 0; the per-contract fee to $0.
    assert BASELINE.fill_model.spread_capture == 0
    assert BASELINE.fill_model.fee_per_contract == Money(0)


def test_config_baseline_kinds_are_the_baseline_selectors() -> None:
    kinds = {str(r.id): r.kind for r in BASELINE.rules}
    assert (kinds["E-L2"], kinds["E-L3"], kinds["E-S3"]) == (
        "nearest_dte_expiry",
        "nearest_delta_long",
        "nearest_delta_short",
    )


@pytest.mark.parametrize(
    ("rule_id", "field", "rendered"),
    [
        ("E-T1", "condition", "at most 3% of mid for the long leg or 10% for the short leg"),
        ("E-L2", "action", "nearest 180 days to expiry"),
        ("E-L3", "action", "delta nearest 0.80"),
        ("E-S3", "action", "delta nearest 0.30"),
        ("X-S1", "condition", "Short mid ≤ 25% of the credit received"),
        ("X-S2", "condition", "Short delta > 0.60"),
        ("X-S3", "condition", "at or before 15:00 ET"),
        ("X-S3", "condition", "spot ≥ short strike − 0.25 × EM"),
        ("X-L1", "condition", "Long delta < 0.50"),
        ("X-L2", "condition", "Long DTE < 90"),
    ],
)
def test_config_rule_text_renders_live_values(rule_id: str, field: str, rendered: str) -> None:
    assert rendered in getattr(BASELINE.rule(RuleId(rule_id)).text(), field)


@pytest.mark.parametrize("rule", BASELINE.rules, ids=lambda r: str(r.id))
def test_config_rule_name_is_the_spec_name(rule: Rule) -> None:
    assert rule.name == _spec_name(rule.id)


@pytest.mark.parametrize("rule_id", ["G-1", "G-2"])
def test_config_gate_condition_is_the_spec_condition(rule_id: str) -> None:
    assert BASELINE.rule(RuleId(rule_id)).text().condition == SPEC_ROWS[rule_id][1]


@pytest.mark.parametrize("rule_id", [i for i in SPEC_ROWS if i.startswith("X-")])
def test_config_exit_action_is_the_spec_action(rule_id: str) -> None:
    assert BASELINE.rule(RuleId(rule_id)).text().action == SPEC_ROWS[rule_id][1]


@pytest.mark.parametrize(
    ("rule_id", "condition"),
    [
        ("E-S5", "Short strike − long strike > long entry fill − short mid, per share"),
        ("X-S4", "out of the money at the close (closing spot ≤ strike)"),  # DEC-23
        ("X-S5", "in the money at the close (closing spot > strike)"),
    ],
)
def test_config_condition_keeps_the_spec_comparison(rule_id: str, condition: str) -> None:
    assert condition in BASELINE.rule(RuleId(rule_id)).text().condition


def test_config_short_exits_share_the_no_roll_rationale() -> None:
    # DEC-35: the spec's "Why there are no rolls" opens every short exit, word for word, after the
    # PO's line.
    spec = re.search(r"^\*\*Why there are no rolls\.\*\* (.+)$", SPEC, flags=re.MULTILINE)
    assert spec
    no_roll = "There are no rolls, and the plan is never to get assigned. " + spec[1]
    for rule_id in SHORT_EXITS:
        assert BASELINE.rule(RuleId(rule_id)).text().rationale.split("\n")[0] == no_roll


@pytest.mark.parametrize(
    ("rule_id", "rationale"),
    [
        ("X-S1", "once it's worth 25% or less of the credit received"),
        ("X-S2", "keeps the short from sitting deep in the money, where early exercise"),
        ("X-S4", "The call expires worthless, and the full credit is kept."),
        ("E-S2", "when the Friday is a holiday, it expires on Thursday"),
    ],
)
def test_config_rationale_says_why(rule_id: str, rationale: str) -> None:
    assert rationale in BASELINE.rule(RuleId(rule_id)).text().rationale


def test_config_x_s3_rationale_is_the_spec_friday_buffer() -> None:
    rationale = BASELINE.rule(RuleId("X-S3")).text().rationale
    assert "The stock can move into the money in the final hour after the check" in rationale
    assert "within 0.25 × EM of the strike" in rationale


def test_config_x_s5_rationale_is_why_the_short_is_never_exercised() -> None:
    rationale = BASELINE.rule(RuleId("X-S5")).text().rationale
    assert "economically equal to assignment and covering" in rationale
    assert "weekend gap risk on short stock" in rationale


def test_config_e_s5_rationale_uses_the_long_entry_fill() -> None:
    rationale = BASELINE.rule(RuleId("E-S5")).text().rationale
    assert "entry fill, not its current mark" in rationale


def test_config_g_1_rationale_says_it_replaces_the_spread_gate() -> None:
    assert "E-T1" in BASELINE.rule(RuleId("G-1")).text().rationale


def test_config_baseline_run_config_carries_the_universe_window_and_r() -> None:
    universe = read_universe_file()
    run = load_run_config(CONFIGS_DIR / "baseline_pmcc.yaml", universe)
    assert run.strategy == BASELINE
    assert (run.window, run.risk_free_rate) == (universe.window, universe.risk_free_rate)


def test_config_shared_file_alone_is_not_a_strategy() -> None:
    with pytest.raises(ValueError, match=r"(?m)^id\n  Input should be a valid string"):
        load_strategy(CONFIGS_DIR / "_shared.yaml")


def test_config_schema_describes_params_as_they_dump() -> None:
    # Each kind has its own params model, so the schema says what every dump holds (P4-05 exports
    # it): names to numbers or strings.
    schema = RunConfig.model_json_schema(mode="serialization")
    params = schema["$defs"]["Rule"]["properties"]["params"]
    assert params == {"type": "object", "additionalProperties": {"type": ["number", "string"]}}
    for rule in BASELINE.model_dump(mode="json")["rules"]:
        assert all(isinstance(v, int | float | str) for v in rule["params"].values())
