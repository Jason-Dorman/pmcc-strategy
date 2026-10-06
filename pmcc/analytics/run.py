"""One run's analytics, computed from its records when it finishes (P6-01 to P6-05).

Every run gets its summary analytics, whatever its detail: a summary run's summary is what the
robustness tables and the universe files read (PO, DEC-54). The cycles and the attribution go only
into a full run's file: the leg attribution always, the Greek attribution and the position Greeks
when the strategy's page shows them (`report.sections`; P6-03, P6-04; PO, DEC-120).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import final

from pmcc.analytics.attribution import leg_attribution
from pmcc.analytics.cycles import cycle_stats, cycles, exit_mix, skips_by_rule
from pmcc.analytics.greek_attribution import greek_attribution
from pmcc.analytics.performance import metrics, nav_close, weekly_returns
from pmcc.analytics.position_greeks import position_greeks
from pmcc.analytics.records import RunRecords
from pmcc.config.strategy import Detail, Report, Section
from pmcc.export.analytics_models import (
    Attribution,
    Cycle,
    CycleStats,
    Metrics,
    NavPoint,
    PositionGreeks,
    WeeklyReturn,
)


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
    attribution: Attribution | None  # a full run's only
    position_greeks: PositionGreeks | None  # where its page shows them


def analyze(run: RunRecords, seed: int, report: Report, risk_free_rate: float) -> RunAnalytics:
    """`run`'s analytics, its bootstrap seeded with `seed` (DEC-61), its Sharpe and Sortino in
    excess of `risk_free_rate` (DEC-111), its attribution and position Greeks as `report` asks
    (DEC-54, DEC-120)."""
    weekly = cycles(run)
    return RunAnalytics(
        metrics=metrics(run, seed, risk_free_rate),
        cycle_stats=cycle_stats(weekly),
        exit_mix=exit_mix(run.blotter),
        skips_by_rule=skips_by_rule(run.gate_log),
        nav_close=nav_close(run.ledger),
        weekly_returns=weekly_returns(run.ledger, run.starting_cash),
        cycles=weekly,
        attribution=attribute(run, report),
        position_greeks=position(run, report),
    )


def position(run: RunRecords, report: Report) -> PositionGreeks | None:
    """The position Greeks, if the run's page shows them (DEC-120)."""
    return position_greeks(run) if Section.POSITION_GREEKS in report.sections else None


def attribute(run: RunRecords, report: Report) -> Attribution | None:
    """A full run's attribution: by leg, and by Greek if its page shows it; None for a summary."""
    if report.detail is not Detail.FULL:
        return None
    greek = greek_attribution(run) if Section.GREEK_ATTRIBUTION in report.sections else None
    return Attribution(leg=leg_attribution(run), greek=greek)
