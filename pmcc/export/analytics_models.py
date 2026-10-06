"""Result models for the analytics (ARCHITECTURE §12): a run's P6 sections, the per-symbol files
and the universe files.

These are the shapes the site reads, fixed at P4-05 so the frontend is typed against every output
it will load (INV-14). Their fields follow Spec › Analytics and metrics and the panels of UI-SPEC
§6, and `pmcc.analytics` computes them as the PO defined each number (DEC-60 to DEC-66, DEC-76):
the performance metrics, cycles and bootstrap CIs at P6-01, P6-02 and P6-05, the attribution at
P6-03 and P6-04, the robustness tables at P6-06, the fill-assumption check at P6-07 and the
suitability screen at P6-08. A P6 item may reshape a model when it builds it, regenerating the
schema, and `tsc` then shows the site what changed (ARCHITECTURE §16).

Every ratio is a fraction, whatever its name says (0.25 is 25%); the site formats it.
"""

from collections.abc import Mapping
from datetime import date, datetime
from typing import Self

from pydantic import model_validator

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
    1, the first session's against the starting cash. Sharpe and Sortino are on excess daily
    returns, each less e^(r/252) − 1: Sharpe their mean ÷ sample standard deviation, Sortino their
    mean ÷ √mean(min(excess, 0)²), both × √252 (PO, DEC-111; null when the divisor is 0).
    Drawdown is on every bar's NAV, from the starting cash as the first peak; the largest fall in
    dollars and the largest as a fraction of its peak are each their own maximum. Time underwater
    counts sessions from a close at a peak to the close that regains it, or to the last
    session."""

    pnl: Dollars
    return_on_starting_nav: float  # over the window, not annualized (DEC-111)
    max_drawdown: Dollars  # a fall, so never negative
    max_drawdown_pct: float
    longest_underwater_sessions: int
    sharpe_annualized: float | None  # from `sessions` daily returns, × √252
    sortino_annualized: float | None
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


class GreekPoint(Model):
    """The position's Greeks at a bar's end (PO, DEC-120), in dollars from DEC-24's units: δ in
    shares (δ × 100 × contracts), Γ in shares per $1 of spot, θ in $ a calendar day (θ ÷ 365),
    vega in $ a vol point (vega ÷ 100). Each is the long's plus the short's, negated, plus X-S5's
    stock for δ (its shares); null when nothing is held or a held leg's Greek is unknown."""

    time: datetime
    short_open: bool
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None


class PositionGreekRow(Model):
    """One Greek over the bars that end with both legs held and it known for both: each leg's mean
    (the short's negated), the net's (X-S5's stock included), and the share of those bars on which
    the net had the textbook PMCC's sign (+δ, −Γ, +θ, +vega). The means and share are null over no
    bars."""

    component: str  # "delta", "gamma", "theta" or "vega"
    expected_sign: int  # +1 or −1
    long: float | None
    short: float | None
    net: float | None
    share_with_sign: float | None
    bars: int


class PositionGreeks(Model):
    """The position's Greeks, bar by bar and averaged per leg (PO, DEC-120)."""

    rows: tuple[PositionGreekRow, ...]  # delta, gamma, theta, vega
    series: tuple[GreekPoint, ...]  # one per bar


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


class FillPoints(Model):
    """Every pair, not bins (PO, DEC-05), as three columns of one length: the i-th of each is one
    contract's session bar. `mid` is (BID + ASK) ÷ 2 at the bar's end, rounded half-even to
    $0.0001 as a fill at mid is; `trade` is the bar's TRDPRC_1, its last trade, which can be up to
    an hour older than the quote; `spread` is ASK − BID. Ordered by bar, expiry and strike."""

    mid: tuple[Dollars, ...]
    trade: tuple[Dollars, ...]
    spread: tuple[Dollars, ...]

    @model_validator(mode="after")
    def _one_length(self) -> Self:
        if not len(self.mid) == len(self.trade) == len(self.spread):
            raise ValueError("mid, trade and spread must be one length")
        return self


class Fit(Model):
    """OLS of trade on mid (DEC-64), computed exactly from the $0.0001 units: `trade ≈ slope × mid
    + intercept`, the intercept in dollars. `r2` is null when every trade is the same. The median
    gap is |trade − mid| ÷ spread, so 0.5 is a print at the bid or the ask; a locked quote (BID =
    ASK) has no spread and is left out of it, and counted in `locked`."""

    slope: float
    intercept: float
    r2: float | None
    n: int
    median_abs_gap_pct_spread: float | None  # a fraction of the spread; null if every quote locked
    locked: int


class FillGroup(Model):
    """`shorts`: weekly calls over the weekly's dates (the prior week's first session to its
    expiry). `longs`: the long candidates, monthly calls before those dates (DEC-64). A monthly
    that is also a weekly expiry is split by the bands it was fetched with: its shorts are the
    strikes from its near-money band's padded floor up, its longs those up to its deep bands'
    padded top. `fit` is null under 2 pairs, or when every mid is the same."""

    group: str  # "shorts" or "longs"
    points: FillPoints
    fit: Fit | None


class FillCheck(Model):
    """`{SYM}/fill_check.json`: TRDPRC_1 against mid on session bars of the window with a trade
    and a valid quote (P6-07; PO, DEC-64), shorts then longs."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    symbol: str
    groups: tuple[FillGroup, ...]


class PooledFillGroup(Model):
    group: str  # "shorts" or "longs"
    fit: Fit | None  # over every symbol's points in the group


class PooledFillCheck(Model):
    """`universe/pooled_fill_check.json` (P6-07; PO, DEC-64): each group's fit over every symbol's
    pairs together. The points are each symbol's own file's."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    symbols: tuple[str, ...]
    groups: tuple[PooledFillGroup, ...]


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
    return_on_starting_nav: float
    max_drawdown: Dollars
    sharpe_annualized: float | None
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
    """One symbol's screen (P6-08; PO, DEC-66), read once a week at the first bar of each
    week-open session in the window, from what quant's rules see there: its E-L3 long (lowest
    extrinsic ÷ delta) and its E-S3 short (lowest strike at or above spot + k × EM), picked
    whether or not they would pass E-T1. A week without a long has no short, since a short is
    sold against a long. Each measure is over the weeks it could be read, which its count gives:
    - long extrinsic per delta: the mean of extrinsic ÷ (delta × spot), over `long_weeks`;
    - median spread: (ASK − BID) ÷ mid of the picks, exactly as E-T1 tests it, the long's over
      `long_weeks`, the short's over `short_weeks`;
    - weekly credit after half-spread: the mean of the short's bid (mid − half-spread) ÷ the
      long's mid, over `short_weeks`;
    - IV ÷ RV20: the mean of the front week's ATM IV ÷ RV20 (G-4's inputs), over `iv_rv20_weeks`;
    - G-3 fires: the weeks G-3 fired at quant's `g3_max_ratio`, out of `g3_weeks`, the weeks it
      could be evaluated (not `n/a`).

    The spreads' medians and the credit's mean are taken over exact fractions of the integer BID
    and ASK, so no figure depends on the weeks' order. A week whose RV20 is 0 has no IV ÷ RV20
    and is left out of that mean."""

    symbol: str
    weeks: int  # week-open sessions sampled
    long_weeks: int
    long_extrinsic_per_delta_pct_spot: float | None
    median_spread_long_pct: float | None
    short_weeks: int
    median_spread_short_pct: float | None
    weekly_credit_after_half_spread_pct_long_cost: float | None
    iv_rv20_weeks: int
    iv_over_rv20: float | None
    g3_weeks: int
    g3_fires: int
    g3_max_ratio: float


class Suitability(Model):
    """`universe/suitability.json`: the symbol screen (P6-08; PO, DEC-66), a row per symbol in
    alphabetical order."""

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
    "pooled_fill_check": PooledFillCheck,
    "suitability": Suitability,
}
