"""Calibrating the starting cash on synthetic markets (Spec › E-L4; P3-09, DEC-30): measure each
run's first long-leg entry with ample cash, then check the value covers every entry the runs make.
"""

from collections.abc import Callable
from datetime import date, datetime
from pathlib import Path

import pytest

from pmcc import calibration
from pmcc.accounting.events import Event
from pmcc.calibration import (
    CALIBRATION_CASH,
    CalibrationError,
    blocked_entries,
    calibrate,
    first_long_entry,
    measure,
    run_funds,
    verify,
)
from pmcc.config.capital import starting_cash_for
from pmcc.config.strategy import RunConfig
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId
from pmcc.engine.loop import run_backtest
from pmcc.runner import Market
from pmcc.strategy.registry import build_strategy
from tests.fixtures.synthetic import scenarios as sc
from tests.fixtures.synthetic.market import RATE, SyntheticSpec
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario.harness import at, config, only, run


def _market(synthetic: SyntheticMarkets, name: str = "quiet",
            build: Callable[[], SyntheticSpec] = sc.quiet) -> Market:  # fmt: skip
    loaded = synthetic.get(name, build)
    return Market.prepare(loaded.symbol, loaded.market.spec.symbol, RATE)


def _config(tmp: Path, overrides: str = "", fill_model: str = "",
            build: Callable[[], SyntheticSpec] = sc.quiet) -> RunConfig:  # fmt: skip
    spec = build()
    return config(tmp, overrides, spec.window_start, spec.window_end, fill_model)


def _as(cfg: RunConfig, run_id: str) -> RunConfig:
    """`cfg` under another run ID: a second strategy whose entries the test controls,
    standing in for the quant strategy."""
    return cfg.model_copy(update={"strategy": cfg.strategy.model_copy(update={"id": run_id})})


def test_dec_30_measure_takes_the_first_long_entry_at_calibration_cash(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    market = _market(synthetic)
    cfg = _config(tmp_path)

    entry = measure("SYN", market, cfg)

    out = run_backtest(market.data, cfg, build_strategy(cfg.strategy), CALIBRATION_CASH)
    long = only(out, "E-L1", Side.BUY)
    assert (entry.symbol, entry.strategy, entry.time) == ("SYN", "baseline_pmcc", at(sc.MON, 10))
    assert entry.cost == -long.cash_delta  # fill × 100 × qty + fees
    assert entry.contract == market.names.instrument(long.instrument).ric  # the cache's RIC


def test_dec_30_calibrate_sets_the_value_by_e_l4s_rule_provisionally(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    cfg = _config(tmp_path)

    cash = calibrate({"SYN": _market(synthetic)}, [cfg], ["SYN"]).cash

    (entry,) = cash.entries
    assert cash.value == starting_cash_for([entry.cost], 2, Money.from_dollars(5_000))
    assert cash.value.units % Money.from_dollars(5_000).units == 0
    assert cash.provisional  # quant_pmcc isn't calibrated
    assert cash.calibration_cash == CALIBRATION_CASH


def test_dec_30_calibrate_is_reproducible(synthetic: SyntheticMarkets, tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    market = _market(synthetic)
    assert calibrate({"SYN": market}, [cfg], ["SYN"]) == calibrate({"SYN": market}, [cfg], ["SYN"])


def test_dec_30_calibrate_final_once_every_symbol_and_strategy_is_in(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    base = _config(tmp_path)

    cash = calibrate({"SYN": _market(synthetic)}, [base, _as(base, "quant_pmcc")], ["SYN"]).cash

    assert not cash.provisional
    assert [e.strategy for e in cash.entries] == ["baseline_pmcc", "quant_pmcc"]


def test_dec_30_calibrate_provisional_on_part_of_a_larger_universe(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """P3-09's own case: one symbol of three. Both strategies on it don't make the value final."""
    base = _config(tmp_path)

    cash = calibrate({"SYN": _market(synthetic)}, [base, _as(base, "quant_pmcc")],
                     ["QQQ", "SYN", "TSLA"]).cash  # fmt: skip

    assert cash.provisional


def test_dec_30_calibrate_orders_entries_whatever_the_argument_order(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """The universe's symbol order, then the strategy ID, so equal calibrations write equal
    blocks and `--check` doesn't depend on the order of --symbol or --config flags."""
    base = _config(tmp_path)
    quant = _as(base, "quant_pmcc")
    quiet = _market(synthetic)
    drop = _market(synthetic, "long_delta_drop", sc.long_delta_drop)
    universe = ["AAA", "BBB"]

    one = calibrate({"BBB": quiet, "AAA": drop}, [quant, base], universe)
    two = calibrate({"AAA": drop, "BBB": quiet}, [base, quant], universe)

    assert one == two
    assert [e.pair for e in one.cash.entries] == [
        ("AAA", "baseline_pmcc"), ("AAA", "quant_pmcc"),
        ("BBB", "baseline_pmcc"), ("BBB", "quant_pmcc"),
    ]  # fmt: skip


def test_dec_30_measure_takes_the_first_entry_not_a_later_re_entry(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """long_delta_drop buys twice: the first long, then a re-entry after X-L1."""
    market = _market(synthetic, "long_delta_drop", sc.long_delta_drop)
    cfg = _config(tmp_path, build=sc.long_delta_drop)
    out = run_backtest(market.data, cfg, build_strategy(cfg.strategy), CALIBRATION_CASH)
    buys = [e for e in out.blotter if e.rule_id == "E-L1" and e.side is Side.BUY]
    assert len(buys) == 2

    entry = measure("SYN", market, cfg)

    assert (entry.time, entry.cost) == (buys[0].time, -buys[0].cash_delta)


def test_dec_30_first_long_entry_is_the_earliest_buy_not_the_dearest(tmp_path: Path) -> None:
    """The PO's rule (DEC-30): the first E-L1 buy, even when a later one costs more and whatever
    order the rows come in; sells and other rules never count."""
    cheap = _event(at(sc.MON, 10), Side.BUY, "E-L1", "10.00")
    short = _event(at(sc.MON, 11), Side.SELL, "E-S1", "1.00")
    dear = _event(at(sc.WEEK2_OPEN, 10), Side.BUY, "E-L1", "30.00")
    stock = _event(at(sc.MON, 9), Side.BUY, "X-S2", "50.00")

    assert first_long_entry([dear, short, cheap, stock]) is cheap
    assert first_long_entry([short, stock]) is None


def _event(when: datetime, side: Side, rule: str, fill: str) -> Event:
    option = OptionId("SYN", date(2027, 3, 19), Right.CALL, Price.from_dollars(80))
    price = Price.from_dollars(fill)
    cash = price.notional(100, 1)
    return Event(when, side, option, 1, price, price, -cash if side is Side.BUY else cash,
                 RuleId(rule))  # fmt: skip


def test_dec_30_measure_counts_the_entrys_fee(synthetic: SyntheticMarkets, tmp_path: Path) -> None:
    """cost = fill × 100 × qty + fees (DEC-30), checked against the fill, not the cash Δ."""
    market = _market(synthetic)
    cfg = _config(tmp_path, fill_model="{fee_per_contract: 0.65}",
                  overrides="E-L4: {params: {contracts: 2}}")  # fmt: skip
    out = run_backtest(market.data, cfg, build_strategy(cfg.strategy), CALIBRATION_CASH)
    long = only(out, "E-L1", Side.BUY)
    assert long.fill is not None

    entry = measure("SYN", market, cfg)

    assert entry.cost == long.fill.notional(100, 2) + Money.from_dollars("1.30")


def test_dec_30_calibrate_fails_when_any_later_run_is_blocked(
    synthetic: SyntheticMarkets, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every run is verified, not only the first: at $2,000 the one-contract baseline enters,
    and the two-contract run, measured second, is blocked."""
    market = _market(synthetic)
    one = _config(tmp_path)
    (tmp_path / "two").mkdir()
    two = _as(_config(tmp_path / "two", overrides="E-L4: {params: {contracts: 2}}"), "quant_pmcc")
    monkeypatch.setattr(calibration, "starting_cash_for", _fixed(Money.from_dollars(2_000)))

    with pytest.raises(CalibrationError, match="SYN quant_pmcc: at 2000"):
        calibrate({"SYN": market}, [one, two], ["SYN"])


def test_dec_30_blocked_entries_finds_e_l4_blocks(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    market, cfg = _market(synthetic), _config(tmp_path)
    poor = run_backtest(market.data, cfg, build_strategy(cfg.strategy), Money.from_dollars(1_000))
    rich = run_backtest(market.data, cfg, build_strategy(cfg.strategy), CALIBRATION_CASH)

    assert blocked_entries(poor)[0] == at(sc.MON, 10)
    assert blocked_entries(rich) == []


def test_dec_30_blocked_entries_counts_a_short_skipped_by_e_l4(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """Cash for the long but not for the second week's short (DEC-91's scenario)."""
    out = run(synthetic, tmp_path, "late_friday_surge", sc.BUILDERS["late_friday_surge"],
              overrides="X-S1: {remove: true}", cash=Money.from_dollars(1_300))  # fmt: skip

    week2 = out.gate_log[1]
    assert week2.rule_id == "E-L4"
    assert blocked_entries(out) == [week2.decision_time]


def test_dec_30_blocked_entries_counts_a_re_entry_after_the_first(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """The first long enters, and the re-entry after X-L1 is blocked: the value must cover every
    entry, not only the first one it was calibrated from."""
    out = run(synthetic, tmp_path, "long_delta_drop", sc.long_delta_drop,
              cash=Money.from_dollars(1_300))  # fmt: skip

    first = only(out, "E-L1", Side.BUY)
    blocked = blocked_entries(out)
    assert blocked
    assert blocked[0] > first.time


def test_dec_30_verify_fails_when_the_value_doesnt_cover_an_entry(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    with pytest.raises(CalibrationError, match="E-L4 blocks an entry on 9 bar"):
        verify("SYN", _market(synthetic), _config(tmp_path), Money.from_dollars(1_000))


def test_dec_30_calibrate_fails_rather_than_publish_a_value_that_blocks_entries(
    synthetic: SyntheticMarkets, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(calibration, "starting_cash_for", _fixed(Money.from_dollars(1_000)))
    with pytest.raises(CalibrationError, match="doesn't cover this run's entries"):
        calibrate({"SYN": _market(synthetic)}, [_config(tmp_path)], ["SYN"])


def test_dec_30_measure_fails_when_calibration_cash_is_blocked(
    synthetic: SyntheticMarkets, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(calibration, "CALIBRATION_CASH", Money.from_dollars(1_000))
    with pytest.raises(CalibrationError, match=r"E-L4 blocked an entry at .* even with 1000"):
        measure("SYN", _market(synthetic), _config(tmp_path))


def test_dec_30_measure_fails_without_a_long_entry(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    cfg = _config(tmp_path, overrides="E-T1: {params: {long_max_spread: 0.0001}}")
    with pytest.raises(CalibrationError, match=r"no long-leg entry \(E-L1\)"):
        measure("SYN", _market(synthetic), cfg)


def test_dec_30_measure_refuses_a_spread_capture_other_than_zero(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    cfg = _config(tmp_path, fill_model="{spread_capture: 0.25}")
    with pytest.raises(CalibrationError, match=r"spread_capture 0\.25; calibration is at 0"):
        measure("SYN", _market(synthetic), cfg)


# --- E-L4's rule from the YAML, and the funds report (PO, DEC-30) -----------------------------


def test_dec_30_calibrate_takes_the_rule_from_e_l4s_params(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    rule = "E-L4: {params: {cash_multiple: 3, cash_round_to: 1000}}"
    cfg = _as(_config(tmp_path, overrides=rule), "baseline_pmcc")

    cash = calibrate({"SYN": _market(synthetic)}, [cfg], ["SYN"]).cash

    (entry,) = cash.entries
    assert (cash.cash_multiple, cash.cash_round_to) == (3, Money.from_dollars(1_000))
    assert cash.value == starting_cash_for([entry.cost], 3, Money.from_dollars(1_000))


def test_dec_30_calibrate_refuses_configs_that_disagree_on_the_rule(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    (tmp_path / "quant").mkdir()
    base = _config(tmp_path)
    other = _config(tmp_path / "quant", overrides="E-L4: {params: {cash_multiple: 3}}")

    with pytest.raises(CalibrationError, match="different starting-cash rules"):
        calibrate({"SYN": _market(synthetic)}, [base, _as(other, "quant_pmcc")], ["SYN"])


def test_dec_30_calibrate_refuses_a_variant_before_running_anything(
    synthetic: SyntheticMarkets, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the two strategies set the starting cash (DEC-30), never an ablation or variant."""

    def never(*_args: object) -> None:
        raise AssertionError("a run started")

    monkeypatch.setattr(calibration, "run_output", never)
    variant = _as(_config(tmp_path), "quant_pmcc--a1")

    with pytest.raises(CalibrationError, match=r"not \['quant_pmcc--a1'\]"):
        calibrate({"SYN": _market(synthetic)}, [_config(tmp_path), variant], ["SYN"])


def test_dec_30_calibrate_reports_each_runs_funds_at_the_value(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    market, cfg = _market(synthetic), _config(tmp_path)

    result = calibrate({"SYN": market}, [cfg], ["SYN"])

    out = run_backtest(market.data, cfg, build_strategy(cfg.strategy), result.cash.value)
    low = min(r.available_funds for r in out.ledger)
    (funds,) = result.funds
    assert (funds.symbol, funds.strategy, funds.lowest) == ("SYN", "baseline_pmcc", low)
    assert funds.lowest_at == next(r.time for r in out.ledger if r.available_funds == low)
    assert funds.negative_bars == 0


def test_dec_30_calibrate_reports_funds_below_zero_and_still_calibrates(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """At $1,300 (E-L4's rule set to 1× rounded up to $1,300) X-S5's stock loss takes funds below
    zero on the Friday close with no entry blocked, since the window ends that Friday: reported,
    never refused (PO, DEC-30)."""
    loaded = synthetic.get("late_friday_surge", sc.BUILDERS["late_friday_surge"])
    market = Market.prepare(loaded.symbol, loaded.market.spec.symbol, RATE)
    rules = "X-S1: {remove: true}\nE-L4: {params: {cash_multiple: 1, cash_round_to: 1300}}"
    cfg = config(tmp_path, rules, loaded.market.spec.window_start, sc.FRI)

    result = calibrate({"SYN": market}, [_as(cfg, "baseline_pmcc")], ["SYN"])

    (funds,) = result.funds
    assert result.cash.value == Money.from_dollars(1_300)
    assert (funds.negative_bars, funds.lowest) == (1, Money.from_dollars("-93.50"))
    assert funds.lowest_at == at(sc.FRI, 16)


def test_dec_30_run_funds_counts_bars_below_zero_without_refusing(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """X-S5's stock at $1,300 leaves funds negative (TEST-STRATEGY §5): reported, not raised."""
    out = run(synthetic, tmp_path, "late_friday_surge", sc.BUILDERS["late_friday_surge"],
              overrides="X-S1: {remove: true}", cash=Money.from_dollars(1_300))  # fmt: skip
    negative = [r for r in out.ledger if r.available_funds.units < 0]

    funds = run_funds("SYN", "baseline_pmcc", out)

    assert funds.negative_bars == len(negative) > 0
    assert funds.lowest == min(r.available_funds for r in out.ledger)
    assert funds.lowest.units < 0


def _fixed(value: Money) -> Callable[..., Money]:
    """A stand-in for `starting_cash_for` that always answers `value`."""

    def rule(*_args: object) -> Money:
        return value

    return rule
