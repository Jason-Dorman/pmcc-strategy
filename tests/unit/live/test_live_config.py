"""`configs/live.yaml` (LIVE-SPEC › Trade rules; L2-03): every rule the spec defines, in its order,
with the params its logic reads, under its rule ID (CLAUDE.md › Hard rules)."""

import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from pmcc.live.config import LIVE_PATH, RULE_IDS, LiveConfigError, load_live_config
from pmcc.live.orders import Order


def _raw() -> dict[str, Any]:
    return yaml.safe_load(LIVE_PATH.read_text(encoding="utf-8"))


def _load(tmp_path: Path, raw: dict[str, Any]) -> None:
    path = tmp_path / "live.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    load_live_config(path)


def test_linv_07_the_config_holds_every_rule_the_spec_defines_in_order() -> None:
    config = load_live_config()

    assert tuple(r.id for r in config.rules) == RULE_IDS


def test_ld_03_it_trades_nvda_one_contract_with_25000() -> None:
    config = load_live_config()

    assert (config.symbol, config.underlying_conid) == ("NVDA", 4815747)
    assert config.cash.to_dollars() == 25000
    assert config.cash_rule.contracts == 1


def test_ld_13_r_is_the_bill_yield_continuously_compounded() -> None:
    risk_free = load_live_config().risk_free

    assert risk_free.investment_yield_pct == 4.32
    assert math.isclose(risk_free.rate, 0.042969, abs_tol=1e-6)


def test_l_p3_and_l_c3_target_a_030_delta_and_l_t1_a_10_percent_spread() -> None:
    config = load_live_config()

    assert config.strike("L-P3").target_delta == 0.30
    assert config.strike("L-C3").target_delta == 0.30
    assert config.max_spread == 0.10


def test_l_o1_makes_an_order_the_language_takes() -> None:
    fields = {
        "id": "x",
        "for": "2026-11-16",
        "action": "SHT",
        "underlying": 4815747,
        "contract": "put",
        "expiry": "2026-11-20",
        "strike": "155",
        **load_live_config().order_fields(),
    }

    order = Order.model_validate(fields)

    assert (order.order_type, order.lmt_prc, order.ref, order.qty) == ("lmt", "mid", "open", 1)


def test_ld_21_the_strike_rules_hold_the_band_ten_percent_in_250_cent_steps() -> None:
    config = load_live_config()

    for rule in ("L-P3", "L-C3"):
        band = config.strike(rule)
        assert (band.band_percent, band.step_cents) == (10, 250)


def test_every_rules_words_fill_their_placeholders() -> None:
    words = {r.id: r.words() for r in load_live_config().rules}

    assert "0.30" in words["L-P3"]
    assert "10%" in words["L-T1"]
    assert "{" not in "".join(words.values())


Mutation = Callable[[dict[str, Any]], object]
MUTATIONS: list[Mutation] = [
    lambda raw: raw["rules"].pop(3),
    lambda raw: raw["rules"].reverse(),
    lambda raw: raw["rules"][5]["params"].update(extra=1),
    lambda raw: raw["rules"][5].pop("params"),
    lambda raw: raw["rules"][0].update(params={"stray": 1}),
    lambda raw: raw.update(colour="red"),
    lambda raw: raw["rules"][5]["params"].update(step="2.505"),
    lambda raw: raw["rules"][5]["params"].update(target_delta="0.30"),
    lambda raw: raw["rules"][5]["params"].update(target_delta=1.5),
    lambda raw: raw["rules"][6]["params"].update(contracts=1.5),
    lambda raw: raw["rules"][6]["params"].update(starting_cash=25000),
    lambda raw: raw["rules"][6]["params"].update(starting_cash="-1"),
    lambda raw: raw["rules"][10]["params"].update(max_spread="10%"),
    lambda raw: raw["rules"][11]["params"].update(qty=True),
]


@pytest.mark.parametrize("change", MUTATIONS)
def test_linv_07_a_config_missing_or_garbling_a_rule_fails_to_load(
    tmp_path: Path, change: Mutation
) -> None:
    raw = _raw()
    change(raw)

    with pytest.raises(LiveConfigError):
        _load(tmp_path, raw)


def test_l_p4_the_starting_cash_is_l_p4s() -> None:
    config = load_live_config()

    assert config.cash_rule.starting_cash == "25000.00"
    assert config.cash.to_dollars() == 25000
