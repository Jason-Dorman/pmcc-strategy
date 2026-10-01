"""One run's analytics, computed from its records when it finishes (P6-01, P6-02, P6-05).

Every run gets them, whatever its detail: a summary run's summary is what the robustness tables
and the universe files read (PO, DEC-54). The cycles themselves go only into a full run's file.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import final

from pmcc.analytics.cycles import cycle_stats, cycles, exit_mix, skips_by_rule
from pmcc.analytics.performance import metrics, nav_close, weekly_returns
from pmcc.analytics.records import RunRecords
from pmcc.export.analytics_models import Cycle, CycleStats, Metrics, NavPoint, WeeklyReturn


@final
@dataclass(frozen=True, slots=True)
class RunAnalytics:
    metrics: Metrics
    cycle_stats: CycleStats
    exit_mix: Mapping[str, int]
    skips_by_rule: Mapping[str, int]
    nav_close: tuple[NavPoint, ...]
    weekly_returns: tuple[WeeklyReturn, ...]
    cycles: tuple[Cycle, ...]


def analyze(run: RunRecords, seed: int) -> RunAnalytics:
    """`run`'s analytics, its bootstrap seeded with `seed` (DEC-61)."""
    weekly = cycles(run)
    return RunAnalytics(
        metrics=metrics(run, seed),
        cycle_stats=cycle_stats(weekly),
        exit_mix=exit_mix(run.blotter),
        skips_by_rule=skips_by_rule(run.gate_log),
        nav_close=nav_close(run.ledger),
        weekly_returns=weekly_returns(run.ledger, run.starting_cash),
        cycles=weekly,
    )
