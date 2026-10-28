"""The wheel's result file: `results/{SYM}/wheel.json` (Spec › Accounting, Metrics, Invariants;
W2-03, W3-01).

The PMCC's `RunResult` stays its own, as the wheel's book and config do (WD-24). A wheel result
holds the manifest, the config it ran (`WheelRunConfig`: the wheel, the window and r), its rule
text, the starting cash, a summary, and every row: the blotter, a ledger row per bar, and a
gate-log row per week. Instruments, legs and the manifest are the PMCC's models unchanged; a
blotter row is the PMCC's with its Trade P&L (WD-28); the ledger and gate log are the wheel's
(requirement 2's portfolio at any bar). The summary holds the metrics, the cycle statistics, the
benchmark table and each thesis claim's verdict (WD-20, WD-29), the runtime invariants the run
held and the ledger's flag counts. Its fill evidence pairs each traded option's prints with its
mids (requirement 3; W3-02).

Written by the same canonical writer as the PMCC's results (`pmcc.export.results`), and checked
by `pmcc verify`, which re-derives the invariants from these rows (`wheel_rederive`), and the
benchmarks and verdicts from the files and numbers they come from.
"""

import re
from collections.abc import Mapping
from datetime import date, datetime
from typing import Literal

from pydantic import Field

from pmcc.export.analytics_models import FillPoints, Fit
from pmcc.export.base import SCHEMA_VERSION, Dollars, ScalarMap, SchemaVersion
from pmcc.export.base import Model as _Model
from pmcc.export.models import BlotterRow, LegOut, Manifest, OutcomeOut, RuleTextOut
from pmcc.wheel.config import WheelRunConfig

WHEEL_RUN_FILE = re.compile(r"wheel(--[a-z0-9]+)*\.json")
"""A wheel run's file name: the wheel's run ID, `wheel` or a variant of it."""

type State = Literal["cash", "put", "shares", "call"]


class WheelInvariantCheck(_Model):
    """A runtime invariant the engine checked on every bar or event (`pmcc.wheel.invariants`).
    A run that broke one writes nothing, so a result records only invariants that held."""

    id: str = Field(pattern=r"^WINV-\d{2}$")
    held: bool


class WheelBlotterRow(BlotterRow):
    """A booked trade, with its Trade P&L (PO, WD-28): on the row that closes a position, the cash
    it brought in plus the cash its position was opened for, net of fees; null on a row that opens
    one. An option's is its credit (on its EXPIRE or ASSIGN row), the shares' their sale less their
    purchase (on the call-away's SELL), so the rows sum to the realized P&L."""

    trade_pnl: Dollars | None


class WheelMetrics(_Model):
    """Performance (PO, WD-20): the PMCC's definitions (`pmcc.analytics.performance`), so the
    benchmark table compares like with like. Daily returns are session-close NAV ÷ the previous
    close − 1, the first against the starting cash; Sharpe is their mean excess over e^(r/252) − 1
    ÷ its sample standard deviation × √252, null if that is 0; drawdown is on every bar's NAV."""

    pnl: Dollars  # final NAV − starting cash; shares still held are marked (W-X5)
    return_on_starting_cash: float  # over the window, not annualized
    max_drawdown: Dollars  # a fall, so never negative
    max_drawdown_pct: float
    sharpe_annualized: float | None
    sessions: int  # session closes, so daily returns: the Sharpe's sample length


class WheelCycleStats(_Model):
    """What the wheel did (PO, WD-20, WD-29). A complete cycle is a put assigned and its shares
    later called away; a put that expires is a put expired, not a cycle."""

    puts_sold: int
    puts_expired: int
    puts_assigned: int
    calls_sold: int
    calls_expired: int
    calls_called_away: int
    weeks: int
    weeks_sold: int
    weeks_skipped: Mapping[str, int]  # by the rule that stopped the sale
    premium: Dollars  # every option sale's credit, net of fees
    complete_cycles: int
    open_at_end: bool  # shares still held at the last bar: a cycle not complete
    time_in_state: Mapping[str, float]  # the share of ledger bars in each state


class PmccBenchmark(_Model):
    """The baseline PMCC on the same symbol, window and r (WD-03), from its committed result."""

    run_id: str
    config_hash: str
    starting_cash: Dollars
    return_on_starting_cash: float
    sharpe_annualized: float | None
    max_drawdown_pct: float


class IndexBenchmarkOut(_Model):
    """An index's price return over the window (WD-17): the last close before it to its last."""

    series: str
    start: date
    start_close: Dollars
    end: date
    end_close: Dollars
    price_return: float
    source: str


class Benchmarks(_Model):
    baseline_pmcc: PmccBenchmark
    sp500: IndexBenchmarkOut


class ThesisVerdict(_Model):
    """One thesis claim judged from the results (PO, WD-29): met when `wheel` > `benchmark`."""

    claim: int  # 1 makes money, 2 beats the baseline PMCC's Sharpe, 3 beats the S&P 500's return
    test: str
    wheel: float | None
    benchmark: float | None
    met: bool


class WheelSummary(_Model):
    metrics: WheelMetrics
    cycle_stats: WheelCycleStats
    benchmarks: Benchmarks
    thesis: tuple[ThesisVerdict, ...]
    flag_counts: Mapping[str, int]  # ledger rows carrying each flag
    invariants: tuple[WheelInvariantCheck, ...]


class WheelLedgerRowOut(_Model):
    """One bar's portfolio (Spec › Ledger). A leg's `qty` is its contracts, positive though
    short; `cost_basis` is per share, while shares are held."""

    time: datetime
    spot: Dollars | None
    state: State
    cash: Dollars
    reserved: Dollars  # securing the short put: strike × 100 × contracts
    free_cash: Dollars
    shares: int
    stock_mark: Dollars | None
    put: LegOut | None
    call: LegOut | None
    cost_basis: Dollars | None
    nav: Dollars
    flags: tuple[str, ...]


class WheelGateRowOut(_Model):
    """One week's sale decision: sold, or skipped under the rule that stopped it."""

    session: date
    state: State  # cash (a put) or shares (a call)
    decision_time: datetime | None
    selected: ScalarMap | None
    outcome: OutcomeOut
    notes: str


class WheelFillGroup(_Model):
    """One right's pairs: the PMCC's points and fit (OLS of print on mid, R², the median gap as a
    fraction of the spread), and the share of prints at or inside the quote, BID ≤ print ≤ ASK."""

    group: str  # "puts" or "calls"
    points: FillPoints
    fit: Fit | None  # null under 2 pairs, or when every mid is the same
    within_spread: float | None  # null without a pair


class FillEvidence(_Model):
    """Requirement 3's evidence (Spec › Fill model; W3-02): for every option the run sold, each
    session bar from its sale to its expiry close with a trade print and a valid quote, its print
    (TRDPRC_1, up to an hour older than the quote) against the bar's mid; puts, then calls, and a
    fit over both."""

    contracts: int  # the options sold, whose bars these are
    groups: tuple[WheelFillGroup, ...]
    fit: Fit | None
    within_spread: float | None


class WheelResult(_Model):
    """One wheel run on one symbol: `results/{symbol}/{run_id}.json`."""

    schema_version: SchemaVersion = Field(default=SCHEMA_VERSION)
    manifest: Manifest
    config: WheelRunConfig
    rule_text: Mapping[str, RuleTextOut]
    starting_cash: Dollars
    summary: WheelSummary
    blotter: tuple[WheelBlotterRow, ...]
    ledger: tuple[WheelLedgerRowOut, ...]
    gate_log: tuple[WheelGateRowOut, ...]
    fill_evidence: FillEvidence
