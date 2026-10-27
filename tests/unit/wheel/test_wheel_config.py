"""The wheel's config (W2-02): every rule, its typed params and its write-up."""

from pathlib import Path

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.config.universe import load_universe
from pmcc.domain.money import Money
from pmcc.domain.rules import RuleId
from pmcc.wheel.config import (
    WHEEL_PATH,
    WHEEL_RULE_IDS,
    WheelConfigError,
    load_wheel,
    load_wheel_run,
)

SHIPPED = WHEEL_PATH.read_text(encoding="utf-8")


def _load(tmp_path: Path, text: str) -> object:
    path = tmp_path / "wheel.yaml"
    path.write_text(text, encoding="utf-8", newline="\n")
    return load_wheel(path)


def test_w_config_ships_every_rule_in_the_specs_order() -> None:
    wheel = load_wheel()
    assert wheel.id == "wheel"
    assert tuple(r.id for r in wheel.rules) == WHEEL_RULE_IDS
    assert wheel.rule_ids == frozenset(WHEEL_RULE_IDS)


def test_w_config_ships_the_pos_values() -> None:
    wheel = load_wheel()
    assert wheel.starting_cash == Money.from_dollars(25_000)  # WD-10
    assert (wheel.fill_model.spread_capture, wheel.fill_model.fee_per_contract) == (
        0.0,
        Money.zero(),
    )  # WD-19, WD-23
    assert wheel.max_spread == 0.10  # WD-14
    assert wheel.put_delta == 0.30  # WD-07
    assert wheel.contracts == 1  # WD-10
    assert wheel.call_delta == 0.30  # WD-08


def test_w_config_renders_each_rules_text_with_its_values() -> None:
    wheel = load_wheel()
    assert "−0.30" in wheel.rule(RuleId("W-P3")).text().summary
    assert "10%" in wheel.rule(RuleId("W-T1")).text().summary
    assert wheel.rule(RuleId("W-C3")).shown_params() == {"target_delta": "0.30"}


def test_w_config_refuses_a_missing_rule(tmp_path: Path) -> None:
    start = SHIPPED.index("  - id: W-X5")
    with pytest.raises(WheelConfigError, match="W-X5"):
        _load(tmp_path, SHIPPED[:start])


def test_w_config_refuses_a_rule_given_twice(tmp_path: Path) -> None:
    start = SHIPPED.index("  - id: W-X5")
    with pytest.raises(WheelConfigError, match="more than once"):
        _load(tmp_path, SHIPPED + SHIPPED[start:])


def test_w_config_refuses_an_unknown_param(tmp_path: Path) -> None:
    text = SHIPPED.replace("params: {max_spread: 0.10}", "params: {max_spread: 0.10, bar: 2}")
    with pytest.raises(WheelConfigError, match="W-T1"):
        _load(tmp_path, text)


def test_w_config_refuses_a_param_out_of_range(tmp_path: Path) -> None:
    text = SHIPPED.replace("params: {max_spread: 0.10}", "params: {max_spread: 1.5}")
    with pytest.raises(WheelConfigError, match="W-T1"):
        _load(tmp_path, text)


def test_w_config_refuses_a_threshold_its_summary_doesnt_show(tmp_path: Path) -> None:
    text = SHIPPED.replace(
        "The out-of-the-money put whose delta is closest to −{target_delta:.2f}.",
        "The out-of-the-money put nearest the target delta.",
    )
    with pytest.raises(WheelConfigError, match="summary"):
        _load(tmp_path, text)


def test_w_config_refuses_an_unknown_key(tmp_path: Path) -> None:
    with pytest.raises(WheelConfigError):
        _load(tmp_path, SHIPPED + "margin: true\n")


def test_w_config_run_hash_follows_the_config(tmp_path: Path) -> None:
    universe = load_universe(load_calendar())
    shipped = load_wheel_run(universe)
    path = tmp_path / "wheel.yaml"
    path.write_text(SHIPPED.replace("{target_delta: 0.30}", "{target_delta: 0.25}", 1),
                    encoding="utf-8", newline="\n")  # fmt: skip
    changed = load_wheel_run(universe, path)
    assert shipped.config_hash() == load_wheel_run(universe).config_hash()
    assert shipped.config_hash() != changed.config_hash()
    assert shipped.window == universe.window
    assert shipped.risk_free_rate.value == 0.0371  # WD-16
