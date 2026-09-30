"""Result models for the analytics (ARCHITECTURE §12): a run's P6 sections, the per-symbol files
and the universe files.

These are the shapes the site reads, fixed at P4-05 so the frontend is typed against every output
it will load (INV-14). Their fields follow Spec › Analytics and metrics and the panels of UI-SPEC
§6. Nothing computes them yet: a run's P6 sections are null until P6 fills them, and the other
files are written by `pmcc batch` (P5-03) and the analytics (P6). How each number is defined is
the PO's answer to DEC-60 to DEC-64 and DEC-76, asked when P6 starts; P6 may reshape a model when
it builds it, regenerating the schema, and `tsc` then shows the site what changed (ARCHITECTURE
§16).
"""

from collections.abc import Mapping
from datetime import date, datetime

from pmcc.export.base import SCHEMA_VERSION, Dollars, Model, SchemaVersion

# ---- a run's P6 sections ------------------------------------------------------------------------


class MeanCI(Model):
    """A mean with its bootstrap confidence interval (P6-05, DEC-61)."""

    mean: float
    low: float
    high: float
    level: float
    resamples: int
    seed: int


class Metrics(Model):
    """Performance (P6-01, DEC-60)."""

    pnl: Dollars
    return_on_starting_nav: float
    return_on_capital: float | None  # P&L ÷ peak long-leg cost; None if no long was held
    peak_long_cost: Dollars | None
    max_drawdown: Dollars
    max_drawdown_pct: float
    longest_underwater_sessions: int
    sharpe_daily: float | None
    sortino_daily: float | None
    sessions: int
    weekly_return: MeanCI | None


class CycleStats(Model):
    """One cycle is one week (P6-02, DEC-62)."""

    weeks: int
    weeks_traded: int
    weeks_skipped: int
    win_rate: float | None
    average_win: Dollars | None
    average_loss: Dollars | None
    payoff_ratio: float | None
    premium_captured_pct: float | None
    credit_pct_of_long_cost: float | None


class NavPoint(Model):
    """NAV at a session's close (DEC-60)."""

    session: date
    nav: Dollars


class WeeklyReturn(Model):
    week_final: date
    nav: Dollars
    value: float


class Cycle(Model):
    """One week of a full run (P6-02, DEC-62)."""

    week_open: date
    week_final: date
    outcome: str  # "sold" or "skipped", as the gate log says
    rule_id: str
    credit: Dollars | None
    buyback: Dollars | None
    exit_rule_id: str | None
    pnl: Dollars


class LegPoint(Model):
    session: date
    long_pnl: Dollars
    net_short_premium: Dollars


class LegAttribution(Model):
    """Net short premium against long-leg P&L (P6-03, DEC-63)."""

    short_credits: Dollars
    short_buybacks: Dollars
    net_short_premium: Dollars
    assignment_loss: Dollars  # X-S5's stock, shown apart
    long_pnl: Dollars
    long_intrinsic: Dollars
    long_extrinsic: Dollars
    series: tuple[LegPoint, ...]


class GreekRow(Model):
    leg: str  # "long" or "short"
    component: str  # "delta", "gamma", "theta", "vega" or "residual"
    dollars: float
    share_of_change: float | None


class ResidualPoint(Model):
    time: datetime
    cumulative: float


class GreekAttribution(Model):
    """Bar-by-bar Greek attribution with its residual (P6-04, DEC-63, DEC-76)."""

    rows: tuple[GreekRow, ...]
    residual: tuple[ResidualPoint, ...]
    bars_unattributed: int


class Attribution(Model):
    leg: LegAttribution | None
    greek: GreekAttribution | None


# ---- per-symbol files ---------------------------------------------------------------------------


class RobustnessRow(Model):
    """One run in a robustness table, against its reference run."""

    run_id: str
    label: str
    pnl: Dollars | None
    max_drawdown: Dollars | None
    payoff_ratio: float | None
    weekly_return: MeanCI | None
    pnl_vs_reference: Dollars | None


class TimingDispersion(Model):
    range: Dollars
    std: Dollars


class Robustness(Model):
    """`{SYM}/robustness.json`: the ablation, friction, timing and grid tables (P6-06)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    symbol: str
    ablations: tuple[RobustnessRow, ...]
    friction: tuple[RobustnessRow, ...]
    timing: tuple[RobustnessRow, ...]
    timing_dispersion: TimingDispersion | None
    grid: tuple[RobustnessRow, ...]


class FillPoint(Model):
    mid: Dollars
    trade: Dollars  # TRDPRC_1


class Fit(Model):
    slope: float
    intercept: float
    r2: float
    n: int
    median_abs_gap_pct_spread: float | None


class FillGroup(Model):
    group: str  # "shorts" or "longs"
    points: tuple[FillPoint, ...]  # every pair, not bins (PO, DEC-05)
    fit: Fit | None


class FillCheck(Model):
    """`{SYM}/fill_check.json`: TRDPRC_1 against mid (P6-07, DEC-64)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    symbol: str
    groups: tuple[FillGroup, ...]


class CoverageRow(Model):
    kind: str  # "stock", "weekly calls", "monthly calls", "puts"
    requested: int
    answered: int
    unanswered: int
    mid_availability: float | None


class Coverage(Model):
    """`{SYM}/coverage.json`: counts derived from the cache (P5-03, DEC-16)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    symbol: str
    rows: tuple[CoverageRow, ...]
    iv_failures: Mapping[str, int]
    stale_mark_rate: float | None
    unavailable_fields: tuple[str, ...]


# ---- universe files -----------------------------------------------------------------------------


class HeadlineRow(Model):
    symbol: str
    strategy_id: str
    pnl: Dollars
    return_on_capital: float | None
    max_drawdown: Dollars
    payoff_ratio: float | None
    weekly_return: MeanCI | None


class Headline(Model):
    """`universe/headline.json`: symbol × strategy (P6)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    rows: tuple[HeadlineRow, ...]


class PooledStrategy(Model):
    strategy_id: str
    weekly_return: MeanCI | None  # the week-block bootstrap (DEC-61)
    total_pnl: Dollars


class Pooled(Model):
    """`universe/pooled.json` (P6-05)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    strategies: tuple[PooledStrategy, ...]
    quant_beat_baseline: tuple[str, ...]  # symbols


class SuitabilityRow(Model):
    symbol: str
    long_extrinsic_per_delta_pct_spot: float | None
    median_spread_long_pct: float | None
    median_spread_short_pct: float | None
    weekly_credit_after_half_spread_pct_long_cost: float | None
    iv_over_rv20: float | None
    g3_fires: int


class Suitability(Model):
    """`universe/suitability.json`: the symbol screen (P6-08)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    rows: tuple[SuitabilityRow, ...]


SYMBOL_FILES: Mapping[str, type[Model]] = {
    "robustness": Robustness,
    "fill_check": FillCheck,
    "coverage": Coverage,
}
UNIVERSE_FILES: Mapping[str, type[Model]] = {
    "pooled": Pooled,
    "headline": Headline,
    "suitability": Suitability,
}
