"""The quant PMCC in full runs: gates G-3, G-4 and G-5 firing on their markets, `n/a` in the gate
log, the quant selectors' entries, and the ablations (TEST-STRATEGY §4, §5; P4-02, P4-03; DEC-22).
Every run checks INV-01 to INV-10 on every bar.

Week 1 is the one each market scripts. In week 2 the next week expires on Fri Sep 18, a third
Friday, which the synthetic market prices at the monthly IV (20%) against the weeklies' 40%, so G-3
fires there on every default surface.
"""

from pathlib import Path

import pytest

from pmcc.domain.instruments import OptionId, Side
from pmcc.domain.money import Price
from pmcc.engine.legs import GateLogRow
from pmcc.engine.loop import RunOutput
from pmcc.strategy.ports import GateStatus
from tests.fixtures.synthetic import scenarios as sc
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario.harness import NO_TAKE_PROFIT, QUANT, at, only, rows, run

GATES = ["G-1", "G-2", "G-3", "G-4", "G-5"]


def _quant(synthetic: SyntheticMarkets, tmp: Path, name: str) -> RunOutput:
    return run(synthetic, tmp, name, sc.BUILDERS[name], strategy=QUANT)


def _statuses(week: GateLogRow) -> dict[str, GateStatus]:
    return {str(g.rule_id): g.status for g in week.gates}


def _skipped_by(out: RunOutput, rule: str) -> GateLogRow:
    """Week 1 skipped by `rule`, with every gate evaluated and recorded, in spec order, at the
    decision bar (DEC-22), and the long kept."""
    week1 = out.gate_log[0]
    assert (week1.outcome, week1.rule_id) == ("skipped", rule)
    assert [str(g.rule_id) for g in week1.gates] == GATES
    assert week1.decision_time is not None
    assert not [e for e in out.blotter if e.time < at(sc.WEEK2_OPEN, 10) and e.side is Side.SELL]
    assert only(out, "E-L1", Side.BUY).time == at(sc.MON, 10)
    return week1


def test_g_3_an_event_week_skips_the_short(synthetic: SyntheticMarkets, tmp_path: Path) -> None:
    week1 = _skipped_by(_quant(synthetic, tmp_path, "event_week"), "G-3")
    assert _statuses(week1) == {"G-1": GateStatus.PASS, "G-2": GateStatus.PASS,
                                "G-3": GateStatus.FIRE, "G-4": GateStatus.PASS,
                                "G-5": GateStatus.PASS}  # fmt: skip
    g3 = week1.gates[2].values
    ratio = g3["ratio"]
    assert isinstance(ratio, float)
    assert ratio > 1.20
    assert (g3["front_expiry"], g3["next_expiry"]) == ("2026-09-04", "2026-09-11")
    assert week1.notes.startswith("front_expiry 2026-09-04")


def test_g_4_realized_vol_above_implied_skips_the_short(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    week1 = _skipped_by(_quant(synthetic, tmp_path, "rv_above_iv"), "G-4")
    assert _statuses(week1)["G-4"] is GateStatus.FIRE
    g4 = week1.gates[3].values
    iv, rv, ratio = g4["front_atm_iv"], g4["rv20"], g4["ratio"]
    assert isinstance(iv, float)
    assert isinstance(rv, float)
    assert isinstance(ratio, float)
    assert iv < rv
    assert ratio < 1.00


def test_g_5_a_tiny_premium_skips_the_short(synthetic: SyntheticMarkets, tmp_path: Path) -> None:
    """The short passes E-T1 only on a locked quote: at a one-cent spread its mid would need to be
    $0.10 or more (the tiny_premium builder)."""
    week1 = _skipped_by(_quant(synthetic, tmp_path, "tiny_premium"), "G-5")
    assert _statuses(week1)["G-5"] is GateStatus.FIRE
    assert week1.gates[4].values == {"mid": "0.0800", "min_mid": "0.1000"}
    assert week1.selected is not None
    assert week1.selected["strike"] == "104.0000"


def test_dec_22_a_gate_without_its_inputs_is_n_a_and_the_short_is_sold(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = _quant(synthetic, tmp_path, "next_week_unquoted")
    week1 = out.gate_log[0]
    assert (week1.outcome, week1.rule_id) == ("sold", "E-S1")
    g3 = week1.gates[2]
    assert (str(g3.rule_id), g3.status, g3.reason) == ("G-3", GateStatus.NA, "no next-week ATM IV")
    assert only(out, "E-S1", Side.SELL).time == at(sc.MON, 10)


def test_dec_22_g_1_leaves_the_quant_gates_not_evaluated(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    week1 = _quant(synthetic, tmp_path, "no_quote_monday").gate_log[0]
    assert week1.rule_id == "G-1"
    assert _statuses(week1) == {"G-1": GateStatus.FIRE, **dict.fromkeys(GATES[1:],
                                GateStatus.NOT_EVALUATED)}  # fmt: skip


def test_quant_selectors_enter_with_their_values(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """E-L3 quant buys the cheapest replacement (the nearest eligible monthly), and E-S3 quant
    sells the lowest strike at or above spot + 1 × EM (DEC-34's notes)."""
    out = _quant(synthetic, tmp_path, "quiet")
    long, short = only(out, "E-L1", Side.BUY), only(out, "E-S1", Side.SELL)
    assert isinstance(long.instrument, OptionId)
    assert long.audit["dte"] == 137  # Jan 15 2027: the shortest expiry in 120-270 DTE
    assert "extrinsic_per_delta" in long.notes
    assert isinstance(short.instrument, OptionId)
    floor = short.audit["min_strike"]
    assert isinstance(floor, str)
    assert short.instrument.strike >= Price.from_dollars(floor)
    assert short.audit["em"] is not None
    assert short.audit["em"] == short.audit["em_at_entry"]  # measured on the same bar
    assert out.gate_log[0].outcome == "sold"


def test_a3_without_the_event_gate_sells_the_event_week(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """ "Off" is absence (DEC-53): A3 has no G-3 to evaluate, so the gate log doesn't record one."""
    out = run(synthetic, tmp_path, "event_week", sc.event_week, strategy="ablations/a3")
    week1 = out.gate_log[0]
    assert (week1.outcome, week1.rule_id) == ("sold", "E-S1")
    assert [str(g.rule_id) for g in week1.gates] == ["G-1", "G-2", "G-4", "G-5"]
    assert len(rows(out, "E-S1", Side.SELL)) == 2


def test_an_ablation_takes_overrides_like_any_strategy(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """A3 without X-S1 as well: the short is held to the Friday check and expires (X-S4)."""
    out = run(synthetic, tmp_path, "quiet", sc.quiet, strategy="ablations/a3",
              overrides=NO_TAKE_PROFIT)  # fmt: skip
    assert rows(out, "X-S4")
    assert not rows(out, "X-S1")
    assert "G-3" not in {str(g.rule_id) for w in out.gate_log for g in w.gates}


@pytest.mark.parametrize(
    "strategy", [QUANT, *(f"ablations/a{n}" for n in range(1, 6))], ids=lambda s: s.split("/")[-1]
)
def test_every_quant_config_runs_clean_on_a_random_market(
    synthetic: SyntheticMarkets, tmp_path: Path, strategy: str
) -> None:
    out = run(synthetic, tmp_path, "random_walk", sc.random_walk, strategy=strategy)
    assert out.blotter
    assert len(out.gate_log) == 4
