"""Rule text templates (DEC-52): bare-name placeholders, rendered from a rule's params."""

from datetime import time
from decimal import Decimal

import pytest

from pmcc.config.rule_text import placeholders, render, shown


def test_rule_text_placeholders_are_the_named_fields() -> None:
    assert placeholders("delta > {max_delta:.2f} or DTE < {min_dte}") == {"max_delta", "min_dte"}


def test_rule_text_doubled_braces_are_not_placeholders() -> None:
    assert placeholders("{{literal}} and {x}") == {"x"}


@pytest.mark.parametrize("template", ["{a.b}", "{a[0]}", "{a!r}", "{}", "{0}", "{a:{b}}"])
def test_rule_text_placeholder_must_be_a_bare_name(template: str) -> None:
    with pytest.raises(ValueError, match="placeholder"):
        placeholders(template)


@pytest.mark.parametrize("template", ["{a", "a}"])
def test_rule_text_unbalanced_brace_is_refused(template: str) -> None:
    with pytest.raises(ValueError, match="brace"):
        placeholders(template)


def test_rule_text_renders_format_specs() -> None:
    values = {"spread": 0.03, "delta": 0.8, "by": time(15, 0), "mid": Decimal("0.1000"), "n": 90}
    template = "{spread:.0%} · {delta:.2f} · {by:%H:%M} · ${mid:.2f} · {n}"
    assert render(template, values) == "3% · 0.80 · 15:00 · $0.10 · 90"


def test_rule_text_unknown_placeholder_is_refused() -> None:
    with pytest.raises(ValueError, match=r"unknown placeholder \['max_dleta'\]"):
        render("{max_dleta}", {"max_delta": 0.6})


def test_rule_text_format_spec_the_value_refuses_is_refused() -> None:
    with pytest.raises(ValueError, match="max_delta"):
        render("{max_delta:%H}", {"max_delta": 0.6})


# ---- each value as the text shows it (the Trade rules page's thresholds, P7-03) ---------------


def test_rule_text_shown_formats_each_value_as_its_placeholder_does() -> None:
    values = {"ratio": 1.0, "spread": 0.03, "by": time(15, 0), "mid": Decimal("0.1000")}
    templates = ("ratio > {ratio:.2f} and spread {spread:.0%}", "by {by:%H:%M}, ${mid:.2f}")
    assert shown(templates, values) == {"ratio": "1.00", "spread": "3%", "by": "15:00",
                                        "mid": "0.10"}  # fmt: skip


def test_rule_text_shown_takes_a_values_first_placeholder() -> None:
    assert shown(("{k:.1f}", "{k:.3f}"), {"k": 0.75}) == {"k": "0.8"}


def test_rule_text_shown_falls_back_to_str_for_a_value_no_template_formats() -> None:
    assert shown(("{n}",), {"n": 90, "unused": 0.25}) == {"n": "90", "unused": "0.25"}
