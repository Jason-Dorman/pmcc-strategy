"""Run summaries made by hand for the robustness and universe tests (P6-05, P6-06): what each
table reads from a result, with every other figure a placeholder."""

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal

from pmcc.analytics.scores import RunScore
from pmcc.export.analytics_models import CycleStats, MeanCI, Metrics, WeeklyReturn
from pmcc.export.models import Summary

FIRST_FRIDAY = date(2026, 9, 18)


def weekly(values: Sequence[float], first: date = FIRST_FRIDAY) -> tuple[WeeklyReturn, ...]:
    """Weekly returns ending on consecutive Fridays; the NAVs are placeholders."""
    return tuple(WeeklyReturn(week_final=first + timedelta(weeks=i), nav=Decimal(10_000), value=v)
                 for i, v in enumerate(values))  # fmt: skip


def ci(mean: float) -> MeanCI:
    return MeanCI(mean=mean, low=mean - 0.01, high=mean + 0.01, level=0.95, resamples=10_000,
                  seed=535, weeks=26)  # fmt: skip


def score(
    run_id: str,
    pnl: str,
    *,
    drawdown: str = "100",
    payoff: float | None = 1.5,
    weeks: Sequence[float] = (0.01, -0.01),
    label: str | None = None,
) -> RunScore:
    """A run whose P&L is `pnl` dollars; its strategy is its run ID's part before `--`."""
    metrics = Metrics(
        pnl=Decimal(pnl), return_on_starting_nav=0.0, return_on_capital=None, peak_long_cost=None,
        max_drawdown=Decimal(drawdown), max_drawdown_pct=0.01, longest_underwater_sessions=0,
        sharpe_daily=None, sortino_daily=None, sessions=125, weekly_return=ci(float(pnl) / 1e6),
    )  # fmt: skip
    stats = CycleStats(
        weeks=26, weeks_traded=13, weeks_skipped=13, weeks_long_held=26, win_rate=0.5,
        average_win=None, average_loss=None, payoff_ratio=payoff, premium_captured_pct=None,
        credit_pct_of_long_cost=None,
    )  # fmt: skip
    summary = Summary(metrics=metrics, cycle_stats=stats, weekly_returns=weekly(weeks),
                      flag_counts={}, invariants=())  # fmt: skip
    return RunScore(run_id, label or f"Run {run_id}", run_id.split("--")[0], summary)
