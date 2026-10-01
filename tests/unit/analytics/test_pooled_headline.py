"""The universe files: `headline.json` (P6-01), each symbol's two strategies, and `pooled.json`
(P6-05), each strategy over every symbol with the week-block bootstrap (PO, DEC-61)."""

import dataclasses
from decimal import Decimal

import pytest

from pmcc.analytics.bootstrap import mean_ci
from pmcc.analytics.universe import headline, pooled
from tests.fakes.scores import FIRST_FRIDAY, score, weekly

SEED = 535
NVDA_B, NVDA_Q = [0.02, -0.01, 0.03], [0.01, 0.0, 0.02]
TSLA_B, TSLA_Q = [-0.03, 0.04, 0.01], [0.05, -0.02, 0.0]
SCORES = {
    "TSLA": [score("baseline_pmcc", "900", weeks=TSLA_B), score("quant_pmcc", "1200", weeks=TSLA_Q),
             score("quant_pmcc--a1", "5000")],
    "NVDA": [score("baseline_pmcc", "3672.50", weeks=NVDA_B),
             score("quant_pmcc", "3303.50", weeks=NVDA_Q), score("baseline_pmcc--t1", "1")],
}  # fmt: skip


def test_p6_01_headline_has_each_symbols_two_strategies_and_no_variant() -> None:
    rows = headline(SCORES).rows

    assert [(r.symbol, r.strategy_id, r.pnl) for r in rows] == [
        ("NVDA", "baseline_pmcc", Decimal("3672.50")), ("NVDA", "quant_pmcc", Decimal("3303.50")),
        ("TSLA", "baseline_pmcc", Decimal(900)), ("TSLA", "quant_pmcc", Decimal(1200)),
    ]  # fmt: skip
    nvda_quant = SCORES["NVDA"][1].metrics
    assert (rows[1].max_drawdown, rows[1].payoff_ratio, rows[1].weekly_return) == (
        nvda_quant.max_drawdown, 1.5, nvda_quant.weekly_return)  # fmt: skip
    assert rows[1].return_on_capital == nvda_quant.return_on_capital


def test_dec_61_pooled_ci_resamples_a_week_by_symbol_table() -> None:
    """Columns in symbol order (NVDA, TSLA), one row per week."""
    got = pooled(SCORES, SEED)

    baseline, quant = got.strategies
    assert baseline.weekly_return == mean_ci([list(w) for w in zip(NVDA_B, TSLA_B, strict=True)],
                                             SEED)  # fmt: skip
    assert quant.weekly_return == mean_ci([list(w) for w in zip(NVDA_Q, TSLA_Q, strict=True)], SEED)
    assert baseline.weekly_return is not None
    assert baseline.weekly_return.mean == pytest.approx(sum(NVDA_B + TSLA_B) / 6)


def test_p6_05_pooled_totals_pnl_and_names_where_quant_beat_baseline() -> None:
    got = pooled(SCORES, SEED)

    assert got.symbols == ("NVDA", "TSLA")
    assert [(s.strategy_id, s.total_pnl) for s in got.strategies] == [
        ("baseline_pmcc", Decimal("4572.50")), ("quant_pmcc", Decimal("4503.50"))]  # fmt: skip
    assert got.quant_beat_baseline == ("TSLA",)


def test_p6_05_pooled_over_one_symbol_is_its_own_ci() -> None:
    """The universe is NVDA alone for now (DEC-15): pooling it is its baseline's own CI."""
    got = pooled({"NVDA": SCORES["NVDA"]}, SEED)

    assert got.strategies[0].weekly_return == mean_ci([[w] for w in NVDA_B], SEED)
    assert got.quant_beat_baseline == ()


def test_dec_61_pooled_refuses_symbols_whose_weeks_differ() -> None:
    late = score("baseline_pmcc", "1", weeks=TSLA_B)
    shifted = late.summary.model_copy(
        update={"weekly_returns": weekly(TSLA_B, FIRST_FRIDAY.replace(day=25))}
    )
    scores = {"NVDA": SCORES["NVDA"][:1], "TSLA": [dataclasses.replace(late, summary=shifted)]}

    with pytest.raises(ValueError, match="weeks"):
        pooled(scores, SEED)


def test_p6_05_a_tie_is_not_quant_beating_the_baseline() -> None:
    tied = {"NVDA": [score("baseline_pmcc", "100", weeks=NVDA_B),
                     score("quant_pmcc", "100", weeks=NVDA_Q)]}  # fmt: skip

    assert pooled(tied, SEED).quant_beat_baseline == ()
