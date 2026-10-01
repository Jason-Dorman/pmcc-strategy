"""A run as the tables across runs read it: its identity and summary (P6-05, P6-06).

The robustness tables and the universe files compare finished runs, so they read each result's
summary, never re-run anything. A summary computed before P6 has no metrics, and is refused.
"""

from dataclasses import dataclass
from typing import Self, final

from pmcc.export.analytics_models import Metrics, WeeklyReturn
from pmcc.export.models import RunResult, Summary


@final
@dataclass(frozen=True, slots=True)
class RunScore:
    run_id: str
    label: str  # the run's name
    strategy_id: str  # the run's own ID for a strategy, the strategy it varies otherwise
    summary: Summary

    @classmethod
    def of(cls, result: RunResult) -> Self:
        manifest = result.manifest
        return cls(manifest.run_id, result.config.strategy.name, manifest.strategy_id,
                   result.summary)  # fmt: skip

    @property
    def is_strategy(self) -> bool:
        return self.run_id == self.strategy_id

    @property
    def metrics(self) -> Metrics:
        if self.summary.metrics is None:
            raise ValueError(f"{self.run_id} has no metrics: run it again with the analytics (P6)")
        return self.summary.metrics

    @property
    def payoff_ratio(self) -> float | None:
        stats = self.summary.cycle_stats
        return None if stats is None else stats.payoff_ratio

    @property
    def weekly_returns(self) -> tuple[WeeklyReturn, ...]:
        if self.summary.weekly_returns is None:
            raise ValueError(f"{self.run_id} has no weekly returns: run it again (P6)")
        return self.summary.weekly_returns
