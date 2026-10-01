"""Result models for the analytics (ARCHITECTURE §12): a run's P6 sections, the per-symbol files
and the universe files.

These are the shapes the site reads, fixed at P4-05 so the frontend is typed against every output
it will load (INV-14). Their fields follow Spec › Analytics and metrics and the panels of UI-SPEC
§6, and `pmcc.analytics` computes them as the PO defined each number (DEC-60 to DEC-64, DEC-76):
the performance metrics, cycles and bootstrap CIs at P6-01, P6-02 and P6-05, the attribution at
P6-03 and P6-04, the robustness tables at P6-06; the rest stay null until their P6 item. A P6 item
may reshape a model when it builds it, regenerating the schema, and `tsc` then shows the site what
changed (ARCHITECTURE §16).

Every ratio is a fraction, whatever its name says (0.25 is 25%); the site formats it.
"""

from collections.abc import Mapping
from datetime import date, datetime

from pmcc.export.base import SCHEMA_VERSION, Dollars, Model, SchemaVersion

# ---- a run's P6 sections ------------------------------------------------------------------------


class MeanCI(Model):
    """A mean weekly return with its percentile bootstrap CI (P6-05; PO, DEC-61): `resamples` draws
    of whole weeks, with replacement, from numpy's PCG64 seeded with `seed`. `weeks` is the
    sample's length; a pooled mean resamples each week across every symbol at once."""

    mean: float
    low: float
    high: float
    level: float
    resamples: int
    seed: int
    weeks: int


class Metrics(Model):
    """Performance (P6-01; PO, DEC-60). Daily returns are session-close NAV ÷ the previous close −
    1, the first session's against the starting cash; Sharpe is their mean ÷ sample standard
    deviation, Sortino their mean ÷ √mean(min(r, 0)²), neither annualized (null when the divisor
    is 0). Drawdown is on every bar's NAV, from the starting cash as the first peak; the largest
    fall in dollars and the largest as a fraction of its peak are each their own maximum. Time
    underwater counts sessions from a close at a peak to the close that regains it, or to the last
    session."""

    pnl: Dollars
    return_on_starting_nav: float
    return_on_capital: float | None  # P&L ÷ peak long-leg cost; None if no long was held
    peak_long_cost: Dollars | None  # the dearest long entry: fill × 100 × qty + fees
    max_drawdown: Dollars  # a fall, so never negative
    max_drawdown_pct: float
    longest_underwater_sessions: int
    sharpe_daily: float | None
    sortino_daily: float | None
    sessions: int  # session closes, so daily returns
    weekly_return: MeanCI | None  # None under 2 weeks


class CycleStats(Model):
    """One cycle is one week (P6-02; PO, DEC-62). A win is a week whose P&L is above 0 and a loss
    one below it, over the weeks a long was held; payoff is the average win ÷ |average loss|.
    Premium captured is Σ(credit − buyback) ÷ Σcredit over traded weeks; credit as a share of the
    long's cost is the mean over traded weeks. Each is null without the weeks it needs."""

    weeks: int
    weeks_traded: int
    weeks_skipped: int
    weeks_long_held: int  # the win rate's denominator
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
    """One week of a full run (P6-02; PO, DEC-62). Its P&L is the NAV change from the previous
    week-final close (the starting cash, for the first week) to this one, both legs included. A
    traded week's credit and buyback are the short's cash, net of fees: X-S4 buys back at $0, and
    X-S5's assignment does too, its stock shown apart (DEC-63). `long_cost` is the entry cost of
    the long the short was sold against."""

    week_open: date
    week_final: date
    outcome: str  # "sold" or "skipped", as the gate log says
    rule_id: str
    long_held: bool  # at any bar of the week, or carried into it
    credit: Dollars | None  # null when skipped
    buyback: Dollars | None
    long_cost: Dollars | None
    exit_rule_id: str | None
    pnl: Dollars


class LegPoint(Model):
    """Both legs at a session's close: the long's P&L so far, realized and at its mark, and the
    net short premium so far."""

    session: date
    long_pnl: Dollars
    net_short_premium: Dollars


class LegAttribution(Model):
    """Net short premium against long-leg P&L (P6-03; PO, DEC-63). Cash is net of fees.

    - **Short leg:** credits − buybacks, X-S4 and X-S5 buying back at $0. `short_open` is a short
      still open at the window's end, at its last mark (0 when none).
    - **X-S5's stock**, shown apart: its sale at the strike, its cover and any open mark.
    - **Long leg:** realized and unrealized P&L. Its intrinsic part is each long's change in
      max(0, S − K) × 100 × contracts from its entry bar to its exit bar (or the last bar), S the
      bar's spot, or the last spot before it on a bar without a trade; the extrinsic part is the
      rest, fees and friction included.

    The parts add up to the run's P&L: long + net short premium − short_open + stock."""

    short_credits: Dollars
    short_buybacks: Dollars
    net_short_premium: Dollars
    short_open: Dollars
    assignment_stock_pnl: Dollars
    long_pnl: Dollars
    long_intrinsic: Dollars
    long_extrinsic: Dollars
    series: tuple[LegPoint, ...]  # one per session


class GreekLeg(Model):
    """One leg's change over the run, and how many of its bars the Greeks priced (P6-04)."""

    leg: str  # "long" or "short"
    change: Dollars  # ΔV over every bar: the leg's P&L
    bars_held: int  # bars that began with the leg held
    bars_unattributed: int  # of those, wholly residual (see GreekAttribution)


class GreekRow(Model):
    """One leg × component: its dollars over the run and its share of the leg's change."""

    leg: str  # "long" or "short"
    component: str  # "delta", "gamma", "theta", "vega" or "residual"
    dollars: float
    share_of_change: float | None  # null when the leg's change is 0


class ResidualPoint(Model):
    """The residual so far, both legs, at a bar's end."""

    time: datetime
    cumulative: float


class GreekAttribution(Model):
    """Bar-by-bar Greek attribution with its residual (P6-04; PO, DEC-63, DEC-76). On each bar a
    leg held at the previous bar's end is predicted to move by δΔS + ½Γ(ΔS)² + θΔt + νΔσ, with
    that bar's Greeks (DEC-24 units, Δt in elapsed years) and the position's sign and size; the
    residual is its actual change less the prediction. The IV at the bar's end is the leg's own,
    or the IV its closing fill was at. A bar with a stale mark or no spot at either end, an IV or
    Greek unknown (a call under its floor has DEC-27's Greeks but no IV, so it counts), or a close
    without a fill (X-S4, X-S5) is residual whole and counted in its leg's `bars_unattributed`. A
    bar's actual change is the leg's P&L over it, so a trade's friction and fees fall in the
    residual."""

    legs: tuple[GreekLeg, ...]
    rows: tuple[GreekRow, ...]  # leg × component
    residual: tuple[ResidualPoint, ...]  # one per bar


class Attribution(Model):
    """A full run's attribution: by leg, and by Greek where its page shows it (DEC-54)."""

    leg: LegAttribution
    greek: GreekAttribution | None


# ---- per-symbol files ---------------------------------------------------------------------------


class RobustnessRow(Model):
    """One run in a robustness table, against its reference: the strategy it varies (P6-06). The
    reference's own row leads its rows, at 0 against itself."""

    run_id: str
    label: str  # the run's name
    reference: str  # the reference's run ID
    pnl: Dollars
    max_drawdown: Dollars
    payoff_ratio: float | None
    weekly_return: MeanCI | None
    pnl_vs_reference: Dollars


class TimingDispersion(Model):
    """The spread of P&L across the fixed-bar timing runs, the baseline left out (P6-06)."""

    runs: int
    range: Dollars  # highest − lowest
    std: float | None  # sample standard deviation, in dollars; None under 2 runs


class Robustness(Model):
    """`{SYM}/robustness.json`: the ablation, friction, timing and grid tables (P6-06), every row
    published, none picked as best (HR-6)."""

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
    """`{SYM}/coverage.json`, written by `pmcc batch` (P5-03): the fetch summary's counts, derived
    from the cache (DEC-16), and the strategies' stale-mark rate (HR-8). `iv_failures` counts
    session bars by reason, out of the `iv_priced` bars with a valid quote before the expiry close;
    `stale_mark_rate` is the share of held positions' marks carried stale over both strategies'
    ledgers."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    symbol: str
    rows: tuple[CoverageRow, ...]
    iv_priced: int
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
    """`universe/headline.json`: symbol × strategy (P6-01)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    rows: tuple[HeadlineRow, ...]


class PooledStrategy(Model):
    strategy_id: str
    weekly_return: MeanCI | None  # the week-block bootstrap (DEC-61)
    total_pnl: Dollars


class Pooled(Model):
    """`universe/pooled.json` (P6-05): each strategy over every symbol. Its CI resamples whole
    weeks of a week × symbol table, so the symbols move together and their correlation isn't
    counted as independent evidence (PO, DEC-61)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    symbols: tuple[str, ...]
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
