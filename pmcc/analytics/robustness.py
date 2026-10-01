"""The robustness tables (Spec › Robustness tables; P6-06; PO, 2026-10-01): `{SYM}/robustness.json`.

Each table is one family of the run matrix (`pmcc.config.matrix`): the ablations, friction, entry
timing and the parameter grid. A run sits against its reference, the strategy it varies (the
ablations and grid against quant, the timing runs against the baseline, each friction run against
its own strategy at spread capture 0), and the reference's own row leads its rows. Every row has
P&L, P&L against the reference, max drawdown, payoff ratio and the weekly-return CI.

Timing dispersion is the range and sample standard deviation of P&L across the fixed-bar runs
alone: the baseline, which decides on E-T1's liquidity trigger, is shown for comparison, not
counted. Every result is published and none is picked as best (HR-6).
"""

import statistics
from collections.abc import Mapping, Sequence

from pmcc.analytics.scores import RunScore
from pmcc.config.matrix import Family
from pmcc.export.analytics_models import Robustness, RobustnessRow, TimingDispersion


def robustness(symbol: str, scores: Sequence[RunScore],
               families: Mapping[str, Family]) -> Robustness:  # fmt: skip
    """`symbol`'s tables from its runs, in the matrix's order. Raises `ValueError` for a run the
    matrix doesn't hold, a variant whose reference didn't run, or a summary without metrics."""
    unknown = [s.run_id for s in scores if s.run_id not in families]
    if unknown:
        raise ValueError(f"runs outside the matrix: {unknown}")
    by_id = {s.run_id: s for s in scores}

    def family(which: Family) -> list[RunScore]:
        return [s for s in scores if families[s.run_id] is which]

    timing = family(Family.TIMING)
    return Robustness(
        symbol=symbol,
        ablations=_table(family(Family.ABLATION), by_id),
        friction=_table(family(Family.FRICTION), by_id),
        timing=_table(timing, by_id),
        timing_dispersion=_dispersion(timing),
        grid=_table(family(Family.GRID), by_id),
    )


def _table(
    variants: Sequence[RunScore], by_id: Mapping[str, RunScore]
) -> tuple[RobustnessRow, ...]:
    """Per strategy, in order of first appearance: its row, then its variants'."""
    rows: list[RobustnessRow] = []
    for strategy_id in dict.fromkeys(v.strategy_id for v in variants):
        reference = by_id.get(strategy_id)
        if reference is None:
            mine = [v.run_id for v in variants if v.strategy_id == strategy_id]
            raise ValueError(f"{', '.join(mine)} need their reference run {strategy_id}")
        rows.append(_row(reference, reference))
        rows += [_row(v, reference) for v in variants if v.strategy_id == strategy_id]
    return tuple(rows)


def _row(run: RunScore, reference: RunScore) -> RobustnessRow:
    metrics = run.metrics
    return RobustnessRow(
        run_id=run.run_id,
        label=run.label,
        reference=reference.run_id,
        pnl=metrics.pnl,
        max_drawdown=metrics.max_drawdown,
        payoff_ratio=run.payoff_ratio,
        weekly_return=metrics.weekly_return,
        pnl_vs_reference=metrics.pnl - reference.metrics.pnl,
    )


def _dispersion(timing: Sequence[RunScore]) -> TimingDispersion | None:
    pnl = [s.metrics.pnl for s in timing]
    if not pnl:
        return None
    spread = float(statistics.stdev(pnl)) if len(pnl) > 1 else None
    return TimingDispersion(runs=len(pnl), range=max(pnl) - min(pnl), std=spread)
