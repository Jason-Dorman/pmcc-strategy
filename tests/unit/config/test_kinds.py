"""The kind registry (DEC-53): each kind implements one spec rule ID and checks its own params."""

from datetime import time
from typing import Any

import pytest
from pydantic import ValidationError

from pmcc.config.kinds import KINDS, OPTIONAL_RULE_IDS, SPEC_RULE_IDS
from pmcc.domain import Price, RuleId

SPEC_ORDER = [
    *["E-T1", "E-L1", "E-L2", "E-L3", "E-L4", "E-S1", "E-S2", "E-S3", "E-S4", "E-S5"],
    *["G-1", "G-2", "G-3", "G-4", "G-5"],
    *["X-S1", "X-S2", "X-S3", "X-S4", "X-S5", "X-L1", "X-L2", "X-E1"],
]


def _params(kind: str, **values: Any) -> Any:
    return KINDS[kind].params.model_validate(values)


def test_kinds_spec_rule_ids_follow_the_spec_tables() -> None:
    assert [str(i) for i in SPEC_RULE_IDS] == SPEC_ORDER


def test_kinds_optional_rules_are_the_layers_variants_switch_off() -> None:
    # Baseline runs without G-3..G-5; A3, A4 and A5 remove G-3, G-4 and X-S1 (Spec › Ablations).
    assert {str(i) for i in OPTIONAL_RULE_IDS} == {"G-3", "G-4", "G-5", "X-S1"}


def test_kinds_every_spec_rule_has_a_kind() -> None:
    assert {k.rule_id for k in KINDS.values()} == set(SPEC_RULE_IDS)


def test_kinds_quant_and_baseline_selectors_share_their_rule_ids() -> None:
    by_rule: dict[RuleId, set[str]] = {}
    for name, kind in KINDS.items():
        by_rule.setdefault(kind.rule_id, set()).add(name)
    assert by_rule[RuleId("E-L2")] == {"nearest_dte_expiry", "dte_range_expiry"}
    assert by_rule[RuleId("E-L3")] == {"nearest_delta_long", "cheapest_replacement"}
    assert by_rule[RuleId("E-S3")] == {"nearest_delta_short", "expected_move_strike"}


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_kinds_params_refuse_an_unknown_key(kind: str) -> None:
    with pytest.raises(ValidationError, match="extra"):
        KINDS[kind].params.model_validate({"surplus": 1})


@pytest.mark.parametrize(
    ("kind", "values"),
    [
        ("spread_trigger", {"long_max_spread": 0, "short_max_spread": 0.1}),
        ("spread_trigger", {"long_max_spread": 0.03, "short_max_spread": 1}),
        ("nearest_delta_long", {"target_delta": 1.0}),
        ("nearest_delta_short", {"target_delta": 0}),
        ("nearest_dte_expiry", {"target_dte": 0}),
        ("nearest_dte_expiry", {"target_dte": 180.0}),
        ("nearest_dte_expiry", {"target_dte": True}),
        ("dte_range_expiry", {"min_dte": 270, "max_dte": 120}),
        ("cheapest_replacement", {"min_delta": 0.9, "max_delta": 0.7}),
        ("fixed_contracts", {"contracts": 0, "cash_multiple": 2, "cash_round_to": 5000}),
        ("fixed_contracts", {"contracts": 1, "cash_multiple": 0, "cash_round_to": 5000}),
        ("fixed_contracts", {"contracts": 1, "cash_multiple": 2, "cash_round_to": 0}),
        ("fixed_contracts", {"contracts": 1, "cash_multiple": 2.0, "cash_round_to": 5000}),
        ("fixed_contracts", {"contracts": 1, "cash_multiple": 2}),
        ("expected_move_strike", {"k": 0}),
        ("event_ratio_gate", {"max_ratio": "1.2"}),
        ("min_premium_gate", {"min_mid": -0.01}),
        ("min_premium_gate", {"min_mid": True}),
        ("take_profit", {"max_credit_fraction": 1}),
        ("friday_check", {"check_by": 900, "em_buffer": 0.25}),
        ("friday_check", {"check_by": "3pm", "em_buffer": 0.25}),
        ("friday_check", {"check_by": "15:00", "em_buffer": -0.1}),
        ("long_dte_roll", {"min_dte": 0}),
    ],
)
def test_kinds_params_out_of_range_are_refused(kind: str, values: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        _params(kind, **values)


def test_kinds_dte_range_accepts_the_spec_band() -> None:
    assert _params("dte_range_expiry", min_dte=120, max_dte=270).model_dump() == {
        "min_dte": 120,
        "max_dte": 270,
    }


def test_kinds_min_premium_is_a_price_in_integer_units() -> None:
    # G-5's $0.10 is held exactly (DEC-44): a YAML number, or the string it serializes to.
    assert _params("min_premium_gate", min_mid=0.10).min_mid == Price(1000)
    assert _params("min_premium_gate", min_mid=1).min_mid == Price(10_000)
    assert _params("min_premium_gate", min_mid="0.1000").min_mid == Price(1000)


ARABIC_ONE = chr(0x661) + "." + chr(0x660) * 4  # 1.0000 in Arabic-Indic digits


@pytest.mark.parametrize("value", ["0.10", " 0.1000", "1e-5", "0.1000 ", ARABIC_ONE, None])
def test_kinds_dollar_param_refuses_other_strings(value: object) -> None:
    # Strict like the other params: only the serialized "D.DDDD" form is read as dollars.
    with pytest.raises(ValidationError, match="not a dollar amount"):
        _params("min_premium_gate", min_mid=value)


@pytest.mark.parametrize("value", [0.00005, 0.00015, 1e30])
def test_kinds_dollar_param_is_never_rounded(value: float) -> None:
    # A threshold below $0.0001 would round to $0 and the gate could never fire.
    with pytest.raises(ValidationError, match=r"exact to \$0\.0001"):
        _params("min_premium_gate", min_mid=value)


@pytest.mark.parametrize(
    ("kind", "values"),
    [
        ("dte_range_expiry", {"min_dte": 180, "max_dte": 180}),
        ("cheapest_replacement", {"min_delta": 0.8, "max_delta": 0.8}),
    ],
)
def test_kinds_band_may_be_a_single_value(kind: str, values: dict[str, Any]) -> None:
    # min ≤ max (DEC-90): a sensitivity variant can pin one DTE or one delta.
    assert _params(kind, **values).model_dump() == values


def test_kinds_params_are_frozen() -> None:
    # The hashed config can't change after it's loaded.
    params = _params("defensive_delta", max_delta=0.6)
    with pytest.raises(ValidationError, match="frozen"):
        params.max_delta = 0.9


def test_kinds_friday_check_time_is_quoted_hh_mm() -> None:
    # Unquoted, YAML 1.1 reads 15:00 as the integer 900, which is refused above.
    assert _params("friday_check", check_by="15:00", em_buffer=0.25).check_by == time(15, 0)


def test_kinds_dollar_params_serialize_as_dollar_strings() -> None:
    assert _params("min_premium_gate", min_mid=0.1).model_dump(mode="json") == {"min_mid": "0.1000"}
