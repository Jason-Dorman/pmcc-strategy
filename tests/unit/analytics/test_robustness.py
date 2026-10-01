"""The robustness tables (P6-06; PO, 2026-10-01): each family's runs against the strategy they
vary, the reference's own row first; the timing runs' P&L dispersion without the baseline; every
row published (HR-6)."""

import statistics
from collections.abc import Sequence
from decimal import Decimal

import pytest

from pmcc.analytics.robustness import robustness
from pmcc.config.matrix import Family
from pmcc.export.analytics_models import RobustnessRow
from tests.fakes.scores import score

F = Family
FAMILIES = {
    "baseline_pmcc": F.STRATEGY, "quant_pmcc": F.STRATEGY,
    "quant_pmcc--a1": F.ABLATION, "quant_pmcc--a2": F.ABLATION,
    "baseline_pmcc--sc025": F.FRICTION, "quant_pmcc--sc025": F.FRICTION,
    "baseline_pmcc--t1": F.TIMING, "baseline_pmcc--t2": F.TIMING, "baseline_pmcc--t3": F.TIMING,
    "quant_pmcc--k075": F.GRID,
}  # fmt: skip
PNL = {
    "baseline_pmcc": "3672.50", "quant_pmcc": "3303.50",
    "quant_pmcc--a1": "3100.00", "quant_pmcc--a2": "3500.25",
    "baseline_pmcc--sc025": "3571.79", "quant_pmcc--sc025": "3117.05",
    "baseline_pmcc--t1": "3672.50", "baseline_pmcc--t2": "3019.00", "baseline_pmcc--t3": "2788.00",
    "quant_pmcc--k075": "3489.00",
}  # fmt: skip
SCORES = [score(run_id, pnl) for run_id, pnl in PNL.items()]


def _rows(table: Sequence[RobustnessRow]) -> list[tuple[str, str, Decimal]]:
    return [(r.run_id, r.reference, r.pnl_vs_reference) for r in table]


def test_p6_06_ablations_against_quant_its_row_first() -> None:
    table = robustness("NVDA", SCORES, FAMILIES).ablations

    assert _rows(table) == [
        ("quant_pmcc", "quant_pmcc", Decimal(0)),
        ("quant_pmcc--a1", "quant_pmcc", Decimal("-203.50")),
        ("quant_pmcc--a2", "quant_pmcc", Decimal("196.75")),
    ]


def test_p6_06_friction_rows_sit_under_their_own_strategy() -> None:
    table = robustness("NVDA", SCORES, FAMILIES).friction

    assert _rows(table) == [
        ("baseline_pmcc", "baseline_pmcc", Decimal(0)),
        ("baseline_pmcc--sc025", "baseline_pmcc", Decimal("-100.71")),
        ("quant_pmcc", "quant_pmcc", Decimal(0)),
        ("quant_pmcc--sc025", "quant_pmcc", Decimal("-186.45")),
    ]


def test_p6_06_timing_against_the_baseline_and_grid_against_quant() -> None:
    tables = robustness("NVDA", SCORES, FAMILIES)

    assert [r for r, _, _ in _rows(tables.timing)] == [
        "baseline_pmcc", "baseline_pmcc--t1", "baseline_pmcc--t2", "baseline_pmcc--t3"]  # fmt: skip
    assert _rows(tables.grid) == [
        ("quant_pmcc", "quant_pmcc", Decimal(0)),
        ("quant_pmcc--k075", "quant_pmcc", Decimal("185.50")),
    ]


def test_p6_06_timing_dispersion_is_over_the_fixed_bar_runs_only() -> None:
    """3,672.50, 3,019.00 and 2,788.00: range 884.50; the baseline (also 3,672.50 here) is left
    out, so it can't count twice."""
    dispersion = robustness("NVDA", SCORES, FAMILIES).timing_dispersion

    assert dispersion is not None
    assert (dispersion.runs, dispersion.range) == (3, Decimal("884.50"))
    assert dispersion.std == pytest.approx(statistics.stdev([3672.50, 3019.00, 2788.00]))


def test_p6_06_a_row_carries_the_runs_label_drawdown_payoff_and_ci() -> None:
    scores = [score("quant_pmcc", "10"),
              score("quant_pmcc--a1", "25", drawdown="40", payoff=None, label="A1: x")]  # fmt: skip

    (_, row) = robustness("SYN", scores, FAMILIES).ablations

    assert (row.label, row.pnl, row.max_drawdown, row.payoff_ratio) == (
        "A1: x", Decimal(25), Decimal(40), None)  # fmt: skip
    assert row.weekly_return == scores[1].metrics.weekly_return


def test_p6_06_a_family_with_no_runs_is_an_empty_table() -> None:
    tables = robustness("SYN", [score("quant_pmcc", "10")], {"quant_pmcc": F.STRATEGY})

    assert (tables.symbol, tables.ablations, tables.friction, tables.timing, tables.grid) == (
        "SYN", (), (), (), ())  # fmt: skip
    assert tables.timing_dispersion is None


def test_p6_06_one_timing_run_has_a_range_but_no_std() -> None:
    scores = [score("baseline_pmcc", "10"), score("baseline_pmcc--t1", "12")]

    dispersion = robustness("SYN", scores, FAMILIES).timing_dispersion

    assert dispersion is not None
    assert (dispersion.runs, dispersion.range, dispersion.std) == (1, Decimal(0), None)


def test_p6_06_a_variant_without_its_reference_run_is_refused() -> None:
    with pytest.raises(ValueError, match=r"quant_pmcc--a1 need their reference run quant_pmcc"):
        robustness("SYN", [score("quant_pmcc--a1", "10")], FAMILIES)


def test_p6_06_a_run_not_in_the_matrix_is_refused() -> None:
    with pytest.raises(ValueError, match="quant_pmcc--zz"):
        robustness("SYN", [score("quant_pmcc", "1"), score("quant_pmcc--zz", "1")], FAMILIES)
