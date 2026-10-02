"""The universe files (ARCHITECTURE §12): `headline.json` (P6-01) and `pooled.json` (P6-05).

Both read each symbol's two strategy runs, never a variant.

- **Headline:** symbol × strategy, with P&L, return on starting NAV, max drawdown, annualized
  Sharpe, payoff ratio and the weekly-return CI, symbols in alphabetical order.
- **Pooled:** per strategy, the P&L summed over the symbols and the mean weekly return's CI from
  the week-block bootstrap over a week × symbol table (PO, DEC-61), plus the symbols where quant
  made more than the baseline. Every symbol runs the same window, so their weeks must match.
"""

from collections.abc import Mapping, Sequence
from decimal import Decimal

from pmcc.analytics.bootstrap import mean_ci
from pmcc.analytics.scores import RunScore
from pmcc.export.analytics_models import Headline, HeadlineRow, Pooled, PooledStrategy

BASELINE, QUANT = "baseline_pmcc", "quant_pmcc"  # the spec's two strategies

type Scores = Mapping[str, Sequence[RunScore]]  # symbol → its runs


def headline(scores: Scores) -> Headline:
    return Headline(rows=tuple(_headline_row(symbol, run) for symbol in sorted(scores)
                               for run in _strategies(scores[symbol])))  # fmt: skip


def _headline_row(symbol: str, run: RunScore) -> HeadlineRow:
    metrics = run.metrics
    return HeadlineRow(symbol=symbol, strategy_id=run.run_id, pnl=metrics.pnl,
                       return_on_starting_nav=metrics.return_on_starting_nav,
                       max_drawdown=metrics.max_drawdown,
                       sharpe_annualized=metrics.sharpe_annualized, payoff_ratio=run.payoff_ratio,
                       weekly_return=metrics.weekly_return)  # fmt: skip


def pooled(scores: Scores, seed: int) -> Pooled:
    """Raises `ValueError` if the symbols' weeks differ."""
    symbols = sorted(scores)
    runs = {symbol: {r.run_id: r for r in _strategies(scores[symbol])} for symbol in symbols}
    strategy_ids = list(dict.fromkeys(i for symbol in symbols for i in runs[symbol]))
    return Pooled(
        symbols=tuple(symbols),
        strategies=tuple(
            _pooled(i, [runs[s][i] for s in symbols if i in runs[s]], seed) for i in strategy_ids
        ),
        quant_beat_baseline=tuple(s for s in symbols if _beat(runs[s])),
    )


def _pooled(strategy_id: str, runs: Sequence[RunScore], seed: int) -> PooledStrategy:
    columns = [r.weekly_returns for r in runs]
    if len({tuple(w.week_final for w in column) for column in columns}) > 1:
        raise ValueError(f"{strategy_id}'s symbols ran over different weeks; re-run them together")
    table = [[w.value for w in week] for week in zip(*columns, strict=True)]
    return PooledStrategy(strategy_id=strategy_id, weekly_return=mean_ci(table, seed),
                          total_pnl=sum((r.metrics.pnl for r in runs), Decimal(0)))  # fmt: skip


def _beat(runs: Mapping[str, RunScore]) -> bool:
    baseline, quant = runs.get(BASELINE), runs.get(QUANT)
    return baseline is not None and quant is not None and quant.metrics.pnl > baseline.metrics.pnl


def _strategies(runs: Sequence[RunScore]) -> list[RunScore]:
    return [r for r in runs if r.is_strategy]
