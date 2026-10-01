"""The entry-timing runs (Spec › Sensitivity checks; PO, DEC-31): the shipped `baseline_pmcc--t{k}`
variants from `configs/sensitivity.yaml`, run through the engine on scenario markets.

The short is decided on session bar k of the week-open session and nowhere else: sold there if it
passes E-T1's spread test, or else G-1 skips the week. The long enters as under E-T1.
"""

from collections.abc import Callable
from pathlib import Path

from pmcc.config.matrix import load_sensitivity
from pmcc.config.strategy import RunConfig
from pmcc.config.universe import Window, read_universe_file
from pmcc.domain.instruments import Side
from pmcc.engine.loop import RunOutput, run_backtest
from pmcc.strategy.registry import build_strategy
from tests.fixtures.synthetic import scenarios as sc
from tests.fixtures.synthetic.market import SyntheticSpec
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario.harness import CASH, at, only, rows

VARIANTS = {v.id: v for v in load_sensitivity()}


def timing(synthetic: SyntheticMarkets, name: str, build: Callable[[], SyntheticSpec],
           bar: int) -> RunOutput:  # fmt: skip
    loaded = synthetic.get(name, build)
    spec = loaded.market.spec
    strategy = VARIANTS[f"baseline_pmcc--t{bar}"]
    window = Window(start=spec.window_start, end=spec.window_end)
    rate = read_universe_file().risk_free_rate
    config = RunConfig(strategy=strategy, window=window, risk_free_rate=rate)
    return run_backtest(loaded.data, config, build_strategy(strategy), CASH)


def test_dec_31_t1_skips_the_week_when_bar_1_fails_e_t1(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """Week 1's weeklies quote wide on Monday's 10:00 bar only. E-T1 would sell at 11:00
    (test_e_t1_the_short_enters_on_the_first_bar_that_passes); t1 never looks past bar 1."""
    out = timing(synthetic, "first_bar_wide", sc.first_bar_wide, bar=1)

    week1 = out.gate_log[0]
    assert week1.session == sc.MON
    assert (week1.outcome, str(week1.rule_id), week1.decision_time) == ("skipped", "G-1", None)
    assert [e for e in rows(out, "E-S1", Side.SELL) if e.time.date() == sc.MON] == []
    assert only(out, "E-L1", Side.BUY).time == at(sc.MON, 10)  # the long's E-T1 is unchanged


def test_dec_31_t2_sells_on_bar_2(synthetic: SyntheticMarkets, tmp_path: Path) -> None:
    out = timing(synthetic, "first_bar_wide", sc.first_bar_wide, bar=2)

    short = rows(out, "E-S1", Side.SELL)[0]
    assert short.time == at(sc.MON, 11)
    assert short.audit["selected_at"] == at(sc.MON, 11).isoformat()  # E-T1 froze it at 10:00
    assert out.gate_log[0].decision_time == at(sc.MON, 11)


def test_dec_31_tk_decides_every_week_on_bar_k_not_the_first_that_passes(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """A quiet market passes E-T1 on the 10:00 bar, so E-T1 would sell there; t3 waits for 12:00
    every week, and t7 for the close bar. (G-2 skips week 2 at its decision bar, as it does in
    the baseline.)"""
    for bar, hour in ((3, 12), (7, 16)):
        out = timing(synthetic, "quiet", sc.quiet, bar=bar)

        decided = [at(sc.MON, hour), at(sc.WEEK2_OPEN, hour)]
        selected = rows(out, "E-S1", Side.SELL)[0].audit["selected_at"]
        assert selected == decided[0].isoformat()  # the selector runs at bar k, not before
        assert [g.decision_time for g in out.gate_log] == decided
        assert [e.time for e in rows(out, "E-S1", Side.SELL)] == decided[:1]
        assert only(out, "E-L1", Side.BUY).time == at(sc.MON, 10)
