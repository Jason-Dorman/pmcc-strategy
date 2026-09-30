"""The strategy loader (P3-01): `extends`, `overrides` keyed by rule ID (DEC-53), per-kind params,
rendered rule text (DEC-52), required rules, spec order and the config hash (DEC-90). Variants are
written next to copies of the shipped files, so each test changes one thing."""

import hashlib
import json
import re
import shutil
import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml

from pmcc.config.kinds import SPEC_RULE_IDS
from pmcc.config.strategy import CONFIGS_DIR, StrategyConfig, load_run_config, load_strategy
from pmcc.config.universe import read_universe_file
from pmcc.domain import Money, RuleId

# A field pydantic reports: its location line, then its message (never just a word in the text).
MISSING_ID = r"(?m)^id\n  Input should be a valid string"
MISSING_NAME = r"(?m)^name\n  Input should be a valid string"

X_S2 = RuleId("X-S2")


@pytest.fixture
def configs(tmp_path: Path) -> Path:
    for name in ("_shared.yaml", "baseline_pmcc.yaml"):
        shutil.copy(CONFIGS_DIR / name, tmp_path / name)
    return tmp_path


def _variant(configs: Path, body: str, name: str = "variant.yaml") -> Path:
    head = "id: baseline_pmcc--v\nname: Variant\nextends: baseline_pmcc.yaml\n"
    path = configs / name
    path.write_text(head + textwrap.dedent(body), encoding="utf-8", newline="\n")
    return path


def _flat_rules(configs: Path) -> list[dict[str, Any]]:
    shared = yaml.safe_load((configs / "_shared.yaml").read_text(encoding="utf-8"))
    baseline = yaml.safe_load((configs / "baseline_pmcc.yaml").read_text(encoding="utf-8"))
    return [*shared["rules"], *baseline["rules"]]


def _flat_file(configs: Path, rules: list[dict[str, Any]]) -> Path:
    shared = yaml.safe_load((configs / "_shared.yaml").read_text(encoding="utf-8"))
    doc = {"id": "baseline_pmcc", "name": "Baseline PMCC", "fill_model": shared["fill_model"]}
    path = configs / "flat.yaml"
    path.write_text(yaml.safe_dump({**doc, "rules": rules}, allow_unicode=True), encoding="utf-8")
    return path


# extends


def test_config_extends_resolves_relative_to_the_file(configs: Path) -> None:
    (configs / "ablations").mkdir()
    path = configs / "ablations" / "v.yaml"
    path.write_text("id: baseline_pmcc--v\nname: V\nextends: ../baseline_pmcc.yaml\n")
    assert load_strategy(path).rules == load_strategy(configs / "baseline_pmcc.yaml").rules


def test_config_extends_cycle_is_refused(configs: Path) -> None:
    (configs / "a.yaml").write_text("id: a\nname: A\nextends: b.yaml\n")
    (configs / "b.yaml").write_text("extends: a.yaml\n")
    with pytest.raises(ValueError, match=r"extends cycle: a\.yaml → b\.yaml → a\.yaml$"):
        load_strategy(configs / "a.yaml")


def test_config_extends_itself_is_refused(configs: Path) -> None:
    (configs / "a.yaml").write_text("id: a\nname: A\nextends: ./a.yaml\n")
    with pytest.raises(ValueError, match=r"extends cycle: a\.yaml → a\.yaml$"):
        load_strategy(configs / "a.yaml")


def test_config_extends_a_missing_file_is_refused(configs: Path) -> None:
    path = configs / "v2.yaml"
    path.write_text("id: v\nname: V\nextends: missing.yaml\n")
    with pytest.raises(FileNotFoundError, match=r"missing\.yaml"):
        load_strategy(path)


def test_config_extends_a_directory_is_refused_alike_on_every_os(configs: Path) -> None:
    (configs / "dir.yaml").mkdir()
    path = configs / "v2.yaml"
    path.write_text("id: v\nname: V\nextends: dir.yaml\n")
    with pytest.raises(FileNotFoundError, match="no config file"):
        load_strategy(path)


@pytest.mark.parametrize(
    "extends",
    ["C:/configs/baseline_pmcc.yaml", "/configs/baseline_pmcc.yaml", "..\\baseline_pmcc.yaml"],
)
def test_config_extends_must_be_a_relative_forward_slash_path(configs: Path, extends: str) -> None:
    path = configs / "v2.yaml"
    path.write_text(yaml.safe_dump({"id": "v", "name": "V", "extends": extends}))
    with pytest.raises(ValueError, match="extends must be a relative path"):
        load_strategy(path)


def test_config_extends_must_name_a_yaml_file(configs: Path) -> None:
    shutil.copy(configs / "baseline_pmcc.yaml", configs / "baseline.txt")
    path = configs / "v2.yaml"
    path.write_text("id: v\nname: V\nextends: baseline.txt\n")
    with pytest.raises(ValueError, match=r"extends must name a \.yaml file"):
        load_strategy(path)


def test_config_id_and_name_are_never_inherited(configs: Path) -> None:
    path = configs / "anon.yaml"
    path.write_text("extends: baseline_pmcc.yaml\n")
    with pytest.raises(ValueError, match=MISSING_ID) as refused:
        load_strategy(path)
    assert re.search(MISSING_NAME, str(refused.value))


def test_config_rule_redefined_by_a_child_is_refused(configs: Path) -> None:
    body = """\
        rules:
          - id: X-S2
            name: Defensive
            kind: defensive_delta
            params: {max_delta: 0.7}
            condition: "delta > {max_delta}"
            action: Close
            rationale: Why
        """
    with pytest.raises(ValueError, match=r"^variant\.yaml: X-S2 is defined more than once"):
        load_strategy(_variant(configs, body))


def test_config_rule_given_twice_in_one_file_is_refused(configs: Path) -> None:
    rules = _flat_rules(configs)
    with pytest.raises(ValueError, match="E-T1 is defined more than once"):
        load_strategy(_flat_file(configs, [*rules, rules[0]]))


def test_config_fill_model_is_patched_field_by_field(configs: Path) -> None:
    config = load_strategy(_variant(configs, "fill_model: {spread_capture: 0.25}\n"))
    assert config.fill_model.spread_capture == 0.25
    assert config.fill_model.fee_per_contract == Money(0)


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ("{spred_capture: 0.25}", r"(?m)^fill_model\.spred_capture\n  Extra inputs"),
        ("{spread_capture: '0.25'}", r"(?m)^fill_model\.spread_capture\n  Input should be a valid"),
        ("{spread_capture: 25}", "less than or equal to 1"),
        ("{spread_capture: -0.1}", "greater than or equal to 0"),
        ("{fee_per_contract: '0.65'}", "not a dollar amount"),
    ],
)
def test_config_fill_model_refuses_a_bad_patch(configs: Path, patch: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_strategy(_variant(configs, f"fill_model: {patch}\n"))


def test_config_fill_model_fee_is_money(configs: Path) -> None:
    config = load_strategy(_variant(configs, "fill_model: {fee_per_contract: 0.65}\n"))
    assert config.fill_model.fee_per_contract == Money(6500)


# overrides


def test_config_override_params_patch_changes_only_that_param(configs: Path) -> None:
    config = load_strategy(
        _variant(configs, "overrides:\n  E-T1: {params: {short_max_spread: 0.2}}\n")
    )
    params = config.rule(RuleId("E-T1")).params.model_dump()
    assert params == {"long_max_spread": 0.03, "short_max_spread": 0.2}
    assert "or 20% for the short leg" in config.rule(RuleId("E-T1")).text().condition


def test_config_override_params_patch_with_an_unknown_param_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match="X-S2 params: max_delt: Extra inputs are not permitted"):
        load_strategy(_variant(configs, "overrides:\n  X-S2: {params: {max_delt: 0.7}}\n"))


def test_config_override_empty_params_patch_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match="params patch is empty"):
        load_strategy(_variant(configs, "overrides:\n  X-S2: {params: {}}\n"))


def test_config_override_replace_swaps_the_kind(configs: Path) -> None:
    body = """\
        overrides:
          E-S3:
            replace:
              name: Short leg strike
              kind: expected_move_strike
              params: {k: 1.0}
              condition: Listed calls on the E-S2 expiry
              action: "Lowest listed strike ≥ spot + {k:.2f} × EM"
              rationale: The expected move scales the strike to the week's priced risk.
        """
    rule = load_strategy(_variant(configs, body)).rule(RuleId("E-S3"))
    assert (rule.kind, rule.text().action) == (
        "expected_move_strike",
        "Lowest listed strike ≥ spot + 1.00 × EM",
    )


def test_config_override_replace_under_another_id_is_refused(configs: Path) -> None:
    body = """\
        overrides:
          E-S3:
            replace: {id: E-L3, name: n, kind: nearest_delta_short, params: {target_delta: 0.3},
                      condition: "{target_delta}", action: a, rationale: r}
        """
    with pytest.raises(ValueError, match="the replacement for E-S3 is given another id"):
        load_strategy(_variant(configs, body))


def test_config_override_replace_is_a_whole_rule(configs: Path) -> None:
    # Nothing is filled in from the rule it replaces: a missing rationale is refused.
    body = """\
        overrides:
          E-S3:
            replace:
              name: Short leg strike
              kind: expected_move_strike
              params: {k: 1.0}
              condition: Listed calls on the E-S2 expiry
              action: "Lowest listed strike ≥ spot + {k:.2f} × EM"
        """
    with pytest.raises(ValueError, match=r"(?m)^rules\.\d+\.rationale\n  Field required"):
        load_strategy(_variant(configs, body))


def test_config_override_remove_drops_an_optional_rule(configs: Path) -> None:
    # A5: quant without the X-S1 take profit (Spec › Ablations).
    config = load_strategy(_variant(configs, "overrides:\n  X-S1: {remove: true}\n"))
    assert RuleId("X-S1") not in config.rule_ids


def test_config_override_remove_of_a_required_rule_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match=r"missing required rules: \['G-1'\]"):
        load_strategy(_variant(configs, "overrides:\n  G-1: {remove: true}\n"))


def test_config_override_of_a_rule_the_parent_lacks_is_refused(configs: Path) -> None:
    message = r"^variant\.yaml: overrides G-3, which no parent defines"
    with pytest.raises(ValueError, match=message):
        load_strategy(_variant(configs, "overrides:\n  G-3: {remove: true}\n"))


def test_config_override_of_a_rule_the_same_file_defines_is_refused(configs: Path) -> None:
    body = """\
        rules:
          - id: G-5
            name: Minimum premium
            kind: min_premium_gate
            params: {min_mid: 0.10}
            condition: "Selected short mid < ${min_mid:.2f}"
            action: Skip the week
            rationale: Why
        overrides:
          G-5: {params: {min_mid: 0.20}}
        """
    with pytest.raises(ValueError, match="overrides G-5, which no parent defines"):
        load_strategy(_variant(configs, body))


# X-S1 is optional, so a both-operations override that fell back to `remove` would load.
@pytest.mark.parametrize(
    ("op", "given"),
    [
        ("{}", "[]"),
        ("{remove: true, params: {max_credit_fraction: 0.3}}", "['params', 'remove']"),
        ("{remove: true, replace: {kind: take_profit}}", "['replace', 'remove']"),
    ],
)
def test_config_override_needs_exactly_one_operation(configs: Path, op: str, given: str) -> None:
    message = "an override takes exactly one of params, replace, remove; got " + re.escape(given)
    with pytest.raises(ValueError, match=message):
        load_strategy(_variant(configs, f"overrides:\n  X-S1: {op}\n"))


def test_config_override_remove_must_be_true(configs: Path) -> None:
    message = r"(?m)^overrides\.X-S1\.remove\n  Input should be True"
    with pytest.raises(ValueError, match=message):
        load_strategy(_variant(configs, "overrides:\n  X-S1: {remove: false}\n"))


def test_config_override_refuses_an_unknown_key(configs: Path) -> None:
    with pytest.raises(ValueError, match=r"(?m)^overrides\.X-S1\.note\n  Extra inputs"):
        load_strategy(_variant(configs, "overrides:\n  X-S1: {remove: true, note: A5}\n"))


def test_config_override_key_must_be_a_rule_id(configs: Path) -> None:
    with pytest.raises(ValueError, match="not a rule ID"):
        load_strategy(_variant(configs, "overrides:\n  XS2: {remove: true}\n"))


# rules: kinds, params, required rules, order


def _replace_x_s2(configs: Path, **fields: object) -> Path:
    entry: dict[str, object] = {
        "name": "Defensive",
        "kind": "defensive_delta",
        "params": {"max_delta": 0.6},
        "condition": "Short delta > {max_delta:.2f}",
        "action": "Buy to close",
        "rationale": "Why",
    }
    entry.update(fields)
    body = yaml.safe_dump({"overrides": {"X-S2": {"replace": entry}}}, allow_unicode=True)
    return _variant(configs, body)


def test_config_unknown_kind_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match="unknown kind 'delta_stop'"):
        load_strategy(_replace_x_s2(configs, kind="delta_stop"))


def test_config_kind_for_another_rule_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match="implements X-L1, not X-S2"):
        load_strategy(_replace_x_s2(configs, kind="long_delta_reset", params={"min_delta": 0.6}))


def test_config_missing_param_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match="X-S2 params: max_delta: Field required"):
        load_strategy(_replace_x_s2(configs, params={}, condition="Short delta is high"))


def test_config_param_out_of_range_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match="X-S2 params: max_delta: Input should be less than 1"):
        load_strategy(_replace_x_s2(configs, params={"max_delta": 1.5}))


def test_config_unknown_rule_field_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match=r"(?m)^rules\.\d+\.threshold\n  Extra inputs"):
        load_strategy(_replace_x_s2(configs, threshold=0.6))


@pytest.mark.parametrize("field", ["name", "condition", "action", "rationale"])
def test_config_empty_write_up_field_is_refused(configs: Path, field: str) -> None:
    with pytest.raises(ValueError, match=rf"(?m)^rules\.\d+\.{field}\n  String should match"):
        load_strategy(_replace_x_s2(configs, **{field: " "}))


def test_config_unknown_top_level_key_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match=r"(?m)^gates\n  Extra inputs"):
        load_strategy(_variant(configs, "gates: []\n"))


def test_config_rule_id_outside_the_spec_is_refused(configs: Path) -> None:
    rules = _flat_rules(configs)
    extra = {**rules[0], "id": "E-T2"}
    with pytest.raises(ValueError, match="implements E-T1, not E-T2"):
        load_strategy(_flat_file(configs, [*rules, extra]))


def test_config_strategy_id_must_be_a_run_id(configs: Path) -> None:
    path = configs / "bad.yaml"
    path.write_text("id: Baseline PMCC\nname: B\nextends: baseline_pmcc.yaml\n")
    with pytest.raises(ValueError, match=r"(?m)^id\n  String should match pattern"):
        load_strategy(path)


def test_config_rules_come_out_in_spec_order_whatever_the_file_order(configs: Path) -> None:
    config = load_strategy(_flat_file(configs, _flat_rules(configs)[::-1]))
    assert [r.id for r in config.rules] == [i for i in SPEC_RULE_IDS if i in config.rule_ids]


def test_config_model_refuses_a_rule_given_twice(configs: Path) -> None:
    # The loader can't produce this (rules merge by ID); a config read back from JSON can.
    config = load_strategy(configs / "baseline_pmcc.yaml")
    doc = config.model_dump(mode="json")
    doc["rules"].append(doc["rules"][0])
    with pytest.raises(ValueError, match=r"rules defined more than once: \['E-T1'\]"):
        StrategyConfig.model_validate(doc)


def test_config_model_round_trips_through_json(configs: Path) -> None:
    config = load_strategy(configs / "baseline_pmcc.yaml")
    assert StrategyConfig.model_validate_json(config.model_dump_json()) == config


def test_config_unknown_rule_lookup_raises(configs: Path) -> None:
    with pytest.raises(KeyError, match="G-3"):
        load_strategy(configs / "baseline_pmcc.yaml").rule(RuleId("G-3"))


# rule text (DEC-52)


def test_config_unresolved_placeholder_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match=r"unknown placeholder \['max_dleta'\]"):
        load_strategy(
            _replace_x_s2(configs, action="Close above {max_dleta}", condition="{max_delta}")
        )


def test_config_unreferenced_param_is_refused(configs: Path) -> None:
    message = r"never referenced in condition or action: \['max_delta'\]"
    with pytest.raises(ValueError, match=message):
        load_strategy(
            _replace_x_s2(configs, condition="Short delta is high", rationale="{max_delta}")
        )


@pytest.mark.parametrize(
    "bad", ["{max_delta.real}", "{max_delta[0]}", "{max_delta!r}", "{}", "{0}"]
)
def test_config_placeholder_must_be_a_bare_param_name(configs: Path, bad: str) -> None:
    with pytest.raises(ValueError, match="must be a bare param name"):
        load_strategy(_replace_x_s2(configs, condition=f"{bad} and {{max_delta}}"))


def test_config_bad_format_spec_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match=r"X-S2: can't render 'Short delta > \{max_delta:%H\}'"):
        load_strategy(_replace_x_s2(configs, condition="Short delta > {max_delta:%H}"))


def test_config_unbalanced_brace_is_refused(configs: Path) -> None:
    with pytest.raises(ValueError, match="unbalanced brace"):
        load_strategy(_replace_x_s2(configs, rationale="Why {max_delta"))


def test_config_doubled_braces_render_as_literal_braces(configs: Path) -> None:
    rule = load_strategy(_replace_x_s2(configs, action="Close {{now}}")).rule(X_S2)
    assert rule.text().action == "Close {now}"


def test_config_dollar_param_renders_as_dollars(configs: Path) -> None:
    # G-5's threshold is a Price (DEC-44); its text shows dollars, not units.
    body = """\
        rules:
          - id: G-5
            name: Minimum premium
            kind: min_premium_gate
            params: {min_mid: 0.10}
            condition: "Selected short mid < ${min_mid:.2f} per share"
            action: Skip the week; keep the long
            rationale: Too little premium.
        """
    rule = load_strategy(_variant(configs, body)).rule(RuleId("G-5"))
    assert rule.text().condition == "Selected short mid < $0.10 per share"


def test_config_rationale_follows_a_changed_param(configs: Path) -> None:
    # The thresholds a rationale quotes are placeholders, so a variant can't publish a stale one.
    config = load_strategy(_variant(configs, "overrides:\n  X-S3: {params: {em_buffer: 0.5}}\n"))
    assert "within 0.50 × EM of the strike" in config.rule(RuleId("X-S3")).text().rationale


# the config hash


def test_config_hash_is_the_sha256_of_the_canonical_json() -> None:
    run = load_run_config(CONFIGS_DIR / "baseline_pmcc.yaml", read_universe_file())
    text = run.canonical_json()
    assert run.config_hash() == hashlib.sha256(text.encode("utf-8")).hexdigest()
    canonical = json.dumps(
        json.loads(text), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    assert text == canonical
    assert "≤" in text  # UTF-8, not \\u escapes
    assert json.loads(text) == run.model_dump(mode="json")


def test_config_hash_is_stable_across_loads() -> None:
    universe = read_universe_file()
    first = load_run_config(CONFIGS_DIR / "baseline_pmcc.yaml", universe).config_hash()
    assert load_run_config(CONFIGS_DIR / "baseline_pmcc.yaml", universe).config_hash() == first


def test_config_hash_ignores_file_layout(configs: Path) -> None:
    # The same resolved config, flattened into one file with its rules reversed.
    universe = read_universe_file()
    layered = load_run_config(configs / "baseline_pmcc.yaml", universe)
    flat = load_run_config(_flat_file(configs, _flat_rules(configs)[::-1]), universe)
    assert flat.config_hash() == layered.config_hash()


def test_config_hash_changes_with_a_param(configs: Path) -> None:
    universe = read_universe_file()
    base = load_run_config(_variant(configs, ""), universe).config_hash()
    moved = _variant(configs, "overrides:\n  X-S2: {params: {max_delta: 0.61}}\n")
    assert load_run_config(moved, universe).config_hash() != base


def test_config_hash_changes_with_rule_text(configs: Path) -> None:
    universe = read_universe_file()
    base = load_run_config(_replace_x_s2(configs), universe).config_hash()
    reworded = _replace_x_s2(configs, rationale="Another why")
    assert load_run_config(reworded, universe).config_hash() != base


@pytest.mark.parametrize(
    "change",
    [
        ("Variant", "fill_model: {spread_capture: 0.25}\n"),
        ("Variant", "fill_model: {fee_per_contract: 0.65}\n"),
        ("Another name", ""),
    ],
)
def test_config_hash_changes_with_the_strategy(configs: Path, change: tuple[str, str]) -> None:
    universe = read_universe_file()
    base = load_run_config(_variant(configs, ""), universe).config_hash()
    name, body = change
    changed = _variant(configs, body)
    changed.write_text(changed.read_text().replace("name: Variant", f"name: {name}"))
    assert load_run_config(changed, universe).config_hash() != base


def test_config_hash_changes_with_the_strategy_id(configs: Path) -> None:
    universe = read_universe_file()
    base = load_run_config(_variant(configs, ""), universe)
    other = base.model_copy(update={"strategy": base.strategy.model_copy(update={"id": "other"})})
    assert other.config_hash() != base.config_hash()


def test_config_hash_changes_with_the_window() -> None:
    universe = read_universe_file()
    run = load_run_config(CONFIGS_DIR / "baseline_pmcc.yaml", universe)
    shorter = run.window.model_copy(update={"end": run.window.end.replace(day=18)})
    assert run.model_copy(update={"window": shorter}).config_hash() != run.config_hash()


def test_config_hash_changes_with_the_universe_r() -> None:
    universe = read_universe_file()
    run = load_run_config(CONFIGS_DIR / "baseline_pmcc.yaml", universe)
    other_r = run.model_copy(
        update={"risk_free_rate": run.risk_free_rate.model_copy(update={"value": 0.04})}
    )
    assert other_r.config_hash() != run.config_hash()


def test_config_hash_ignores_the_symbol_list() -> None:
    # The hash covers what a run is configured with; the symbol is in the manifest (DEC-90).
    universe = read_universe_file()
    fewer = universe.model_copy(update={"symbols": universe.symbols[:1]})
    path = CONFIGS_DIR / "baseline_pmcc.yaml"
    assert (
        load_run_config(path, fewer).config_hash() == load_run_config(path, universe).config_hash()
    )
