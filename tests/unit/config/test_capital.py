"""The starting cash and its basis (Spec › E-L4; P3-09, DEC-30): the rule, the validated block, and
how `pmcc calibrate` writes it into a universe file without touching the rest."""

from datetime import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from pmcc.config.capital import (
    MARKER,
    StartingCash,
    missing_pairs,
    render_block,
    starting_cash_for,
    with_block,
)
from pmcc.config.yaml_file import parse_yaml
from pmcc.domain.clock import ET
from pmcc.domain.money import Money

T = datetime(2026, 3, 30, 10, tzinfo=ET)


def _d(dollars: str) -> Money:
    return Money.from_dollars(dollars)


@pytest.mark.parametrize(
    ("costs", "expected"),
    [
        (["4142.50"], "10000"),  # NVDA's first long entry (P3-09): 8,285 rounds up
        (["2500"], "5000"),  # exactly a multiple stays put
        (["2500.0001"], "10000"),  # a hundredth of a cent over rounds up a whole step
        (["0.0001"], "5000"),
        (["1000", "7600.25", "3000"], "20000"),  # the most expensive entry sets it
    ],
)
def test_e_l4_starting_cash_is_twice_the_largest_cost_rounded_up_to_5000(
    costs: list[str], expected: str
) -> None:
    assert starting_cash_for((_d(c) for c in costs), 2, _d("5000")) == _d(expected)


def test_e_l4_starting_cash_follows_e_l4s_params_not_constants() -> None:
    """The multiple and the step come from E-L4's YAML (PO, DEC-30)."""
    assert starting_cash_for([_d("4142.50")], 3, _d("1000")) == _d("13000")
    assert starting_cash_for([_d("4142.50")], 1, _d("0.0001")) == _d("4142.50")


def _entry(
    symbol: str = "NVDA", strategy: str = "baseline_pmcc", cost: float = 4142.5
) -> dict[str, Any]:
    return {"symbol": symbol, "strategy": strategy, "time": T, "contract": "NVDAI182613500.U",
            "cost": cost}  # fmt: skip


RULE = {"cash_multiple": 2, "cash_round_to": 5_000, "calibration_cash": 1_000_000}


def _cash(*entries: dict[str, Any], value: int = 10_000, provisional: bool = True) -> StartingCash:
    return StartingCash.model_validate(
        {"value": value, "provisional": provisional, **RULE, "entries": list(entries) or [_entry()]}
    )


def test_dec_30_starting_cash_reads_its_basis_as_exact_money() -> None:
    cash = _cash()
    assert cash.value == _d("10000")
    assert cash.entries[0].cost == Money(41_425_000)
    assert cash.entries[0].pair == ("NVDA", "baseline_pmcc")


REFUSED: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {
    "value-not-the-rule": ({"value": 15_000}, [_entry()]),
    "value-not-rounded": ({"value": 8285}, [_entry()]),
    "pair-twice": ({}, [_entry(), _entry(cost=4000)]),
    "variant-strategy": ({}, [_entry(strategy="quant_pmcc--a1")]),
    "free-entry": ({"value": 0}, [_entry(cost=0)]),
    "sub-unit-cost": ({}, [_entry(cost=4142.50005)]),
    "no-entries": ({}, []),
    "value-off-a-3x-rule": ({"cash_multiple": 3}, [_entry()]),  # 3 × 4,142.50 → 15,000
    "no-rounding-step": ({"cash_round_to": 0}, [_entry()]),
    "no-multiple": ({"cash_multiple": 0}, [_entry()]),
}


@pytest.mark.parametrize(("changes", "entries"), REFUSED.values(), ids=REFUSED.keys())
def test_dec_30_starting_cash_refuses_a_value_off_its_basis(
    changes: dict[str, Any], entries: list[dict[str, Any]]
) -> None:
    body = {"value": 10_000, "provisional": True, **RULE, "entries": entries}
    with pytest.raises(ValidationError):
        StartingCash.model_validate({**body, **changes})


def test_dec_30_starting_cash_refuses_an_unknown_key() -> None:
    with pytest.raises(ValidationError):
        StartingCash.model_validate({**_cash().model_dump(mode="json"), "note": "x"})


def test_dec_30_missing_pairs_are_each_symbol_under_both_strategies() -> None:
    cash = _cash()
    assert cash.missing(["NVDA", "TSLA"]) == [
        ("NVDA", "quant_pmcc"), ("TSLA", "baseline_pmcc"), ("TSLA", "quant_pmcc")]  # fmt: skip
    both = _cash(_entry(), _entry(strategy="quant_pmcc"))
    assert missing_pairs(both.entries, ["NVDA"]) == []


# --- The block in the file ---------------------------------------------------------------------

HEAD = "# the universe\nwindow: {start: 2026-03-30, end: 2026-09-25}\nsymbols: []  # kept\n"


def test_dec_30_render_block_round_trips_through_yaml() -> None:
    cash = _cash()
    block = render_block(cash)

    assert block.startswith(MARKER)
    parsed = parse_yaml(block)
    assert isinstance(parsed, dict)
    assert StartingCash.model_validate(parsed["starting_cash"]) == cash
    assert "'10000.0000'" in block  # dollars as exact strings, never floats
    assert "2026-03-30T10:00:00-04:00" in block


def test_dec_30_with_block_appends_after_the_file_untouched() -> None:
    text = with_block(HEAD, render_block(_cash()))

    assert text.startswith(HEAD + "\n" + MARKER)
    assert text.endswith("\n")


def test_dec_30_with_block_replaces_only_its_own_block() -> None:
    first = with_block(HEAD, render_block(_cash()))
    bigger = _cash(_entry(cost=7600), value=20_000)

    second = with_block(first, render_block(bigger))

    assert second == with_block(HEAD, render_block(bigger))
    assert second.count(MARKER) == 1


def test_dec_30_with_block_is_idempotent() -> None:
    block = render_block(_cash())
    once = with_block(HEAD, block)
    assert with_block(once, block) == once


def test_dec_30_with_block_refuses_a_starting_cash_set_by_hand() -> None:
    with pytest.raises(ValueError, match="without pmcc calibrate's block"):
        with_block(HEAD + "starting_cash: 10000\n", render_block(_cash()))


def test_dec_30_with_block_refuses_keys_written_after_the_block() -> None:
    text = with_block(HEAD, render_block(_cash())) + "bootstrap_seed: 7\n"
    with pytest.raises(ValueError, match="keys after the starting_cash block"):
        with_block(text, render_block(_cash()))
