"""The starting cash and its basis (Spec › E-L4; P3-09, DEC-30): the rule, the validated block of
each symbol's own value (PO, 2026-10-05), and how `pmcc calibrate` writes it into a universe file
without touching the rest."""

from datetime import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from pmcc.config.capital import (
    MARKER,
    StartingCash,
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


def _entry(strategy: str = "baseline_pmcc", cost: float = 4142.5) -> dict[str, Any]:
    return {"strategy": strategy, "time": T, "contract": "NVDAI182613500.U", "cost": cost}


def _symbol(symbol: str = "NVDA", *entries: dict[str, Any], value: int = 10_000,
            provisional: bool = True) -> dict[str, Any]:  # fmt: skip
    return {"symbol": symbol, "value": value, "provisional": provisional,
            "entries": list(entries) or [_entry()]}  # fmt: skip


RULE = {"cash_multiple": 2, "cash_round_to": 5_000, "calibration_cash": 1_000_000}


def _cash(*symbols: dict[str, Any], **rule: Any) -> StartingCash:
    return StartingCash.model_validate({**RULE, **rule, "symbols": list(symbols) or [_symbol()]})


BOTH = (_entry(), _entry("quant_pmcc", 5630))


def test_dec_30_starting_cash_reads_its_basis_as_exact_money() -> None:
    cash = _cash()
    nvda = cash.of("NVDA")
    assert nvda is not None
    assert nvda.value == _d("10000")
    assert nvda.entries[0].cost == Money(41_425_000)
    assert cash.of("QQQ") is None  # not calibrated yet


def test_dec_30_starting_cash_is_each_symbols_own() -> None:
    """PO, 2026-10-05: a dear QQQ long doesn't raise NVDA's cash."""
    cash = _cash(_symbol("NVDA", *BOTH, value=15_000, provisional=False),
                 _symbol("QQQ", _entry(cost=13_000), value=30_000))  # fmt: skip
    values = {c.symbol: c.value for c in cash.symbols}
    assert values == {"NVDA": _d("15000"), "QQQ": _d("30000")}


def test_dec_30_a_symbol_is_final_once_both_strategies_are_in() -> None:
    final = _cash(_symbol("NVDA", *BOTH, value=15_000, provisional=False)).of("NVDA")
    assert final is not None
    assert final.missing() == []
    provisional = _cash().of("NVDA")
    assert provisional is not None
    assert provisional.missing() == ["quant_pmcc"]


REFUSED: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {
    "value-not-the-rule": ({}, [_symbol(value=15_000)]),
    "value-not-rounded": ({}, [_symbol(value=8285)]),
    "value-from-another-symbols-entry": (  # one value across symbols is no longer the rule
        {},
        [_symbol("NVDA", value=30_000), _symbol("QQQ", _entry(cost=13_000), value=30_000)],
    ),
    "symbol-twice": ({}, [_symbol(), _symbol()]),
    "strategy-twice": ({}, [_symbol("NVDA", _entry(), _entry(cost=4000))]),
    "variant-strategy": ({}, [_symbol("NVDA", _entry("quant_pmcc--a1"))]),
    "free-entry": ({}, [_symbol("NVDA", _entry(cost=0), value=0)]),
    "sub-unit-cost": ({}, [_symbol("NVDA", _entry(cost=4142.50005))]),
    "no-entries": ({}, [{**_symbol(), "entries": []}]),
    "no-symbols": ({}, []),
    "final-but-missing-quant": ({}, [_symbol(provisional=False)]),
    "provisional-but-complete": ({}, [_symbol("NVDA", *BOTH, value=15_000)]),
    "value-off-a-3x-rule": ({"cash_multiple": 3}, [_symbol()]),  # 3 × 4,142.50 → 15,000
    "no-rounding-step": ({"cash_round_to": 0}, [_symbol()]),
    "no-multiple": ({"cash_multiple": 0}, [_symbol()]),
}


@pytest.mark.parametrize(("rule", "symbols"), REFUSED.values(), ids=REFUSED.keys())
def test_dec_30_starting_cash_refuses_a_value_off_its_basis(
    rule: dict[str, Any], symbols: list[dict[str, Any]]
) -> None:
    with pytest.raises(ValidationError):
        StartingCash.model_validate({**RULE, **rule, "symbols": symbols})


@pytest.mark.parametrize("where", ["block", "symbol", "entry"])
def test_dec_30_starting_cash_refuses_an_unknown_key(where: str) -> None:
    doc = _cash().model_dump(mode="json")
    target = {"block": doc, "symbol": doc["symbols"][0], "entry": doc["symbols"][0]["entries"][0]}
    target[where]["note"] = "x"
    with pytest.raises(ValidationError):
        StartingCash.model_validate(doc)


# --- Merging a calibration into the block --------------------------------------------------------

ORDER = ["QQQ", "NVDA", "TSLA"]


def test_dec_30_merged_adds_a_symbol_and_keeps_the_others() -> None:
    nvda = _symbol("NVDA", *BOTH, value=15_000, provisional=False)
    qqq = _symbol("QQQ", _entry(cost=13_000), value=30_000)

    merged = _cash(nvda).merged(_cash(qqq), ORDER)

    assert merged == _cash(qqq, nvda)  # the universe's order, NVDA's value untouched


def test_dec_30_merged_replaces_a_symbol_it_recalibrated() -> None:
    old, new = _symbol("NVDA"), _symbol("NVDA", *BOTH, value=15_000, provisional=False)
    assert _cash(old).merged(_cash(new), ORDER) == _cash(new)


def test_dec_30_merged_puts_symbols_outside_the_order_last() -> None:
    merged = _cash(_symbol("SPY")).merged(_cash(_symbol("NVDA")), ORDER)
    assert [c.symbol for c in merged.symbols] == ["NVDA", "SPY"]


def test_dec_30_merged_refuses_another_rule() -> None:
    """Values set by different E-L4 rules can't share a block."""
    with pytest.raises(ValueError, match="calibrated under E-L4"):
        _cash().merged(_cash(_symbol("QQQ", value=15_000), cash_multiple=3), ORDER)


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
    bigger = _cash(_symbol("NVDA", _entry(cost=7600), value=20_000))

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
