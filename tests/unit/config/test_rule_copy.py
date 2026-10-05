"""The rules as a reader sees them name no rule by its ID (PO, DEC-113): every run's name and every
rule's rendered condition, action and rationale, across the whole run matrix. The IDs stay in
the results and in the site's ID columns."""

import re

import pytest

from pmcc.config.matrix import strategy_configs
from pmcc.config.strategy import StrategyConfig

RULE_ID = re.compile(r"\b[EGX]-[A-Z]?\d\b")
MATRIX = strategy_configs()
FIELDS = ("title", "summary", "condition", "action", "rationale")


@pytest.mark.parametrize("config", MATRIX, ids=lambda c: c.id)
def test_dec_113_a_runs_name_names_no_rule_id(config: StrategyConfig) -> None:
    assert not RULE_ID.search(config.name), config.name


@pytest.mark.parametrize("config", MATRIX, ids=lambda c: c.id)
def test_dec_113_rule_text_names_no_rule_id(config: StrategyConfig) -> None:
    found = [
        (str(rule.id), field, getattr(rule.text(), field))
        for rule in config.rules
        for field in FIELDS
        if RULE_ID.search(getattr(rule.text(), field))
    ]
    assert found == []
