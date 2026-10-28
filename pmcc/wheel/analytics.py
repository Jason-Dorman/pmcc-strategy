"""The wheel's numbers (Spec › Metrics; PO, WD-20, WD-28, WD-29; W3-01): its metrics, cycle
statistics, each blotter row's Trade P&L, and each thesis claim's verdict.

- **Metrics** are the PMCC's (`pmcc.analytics.performance`), so the benchmark table compares the
  wheel with the baseline PMCC by one method: P&L and return on starting cash; max drawdown in
  dollars and as a share of its peak, on every bar's NAV; Sharpe on daily session-close NAV
  returns in excess of r, × √252, with the sessions that make its sample.
- **Cycle statistics** count the blotter's rows by rule, the weeks by their gate-log outcome, and
  the ledger's bars by state. A complete cycle is a put assigned and its shares later called away
  (WD-29), so it is counted by its call-away.
- **Trade P&L** (WD-28) is per instrument: on the row that closes a position, the Cash Δ of every
  row since it opened; null on the others.
- **Fill evidence** (requirement 3, W3-02): each sold option's trade prints against its bars' mids,
  puts and calls, each fitted as the PMCC's fill check fits its own, with the share of prints at
  or inside the quote.
- **Verdicts** (WD-29): the wheel makes money if its P&L > 0; it improves on the baseline PMCC's
  Sharpe if its own is higher; it beats the S&P 500 if its return on starting cash is above the
  index's price return. A claim with a number missing is not met.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal

from pmcc.accounting.events import Event, Instrument
from pmcc.analytics.fillcheck import fit
from pmcc.analytics.performance import daily_rate, daily_returns, max_drawdown, sharpe
from pmcc.domain.clock import to_et
from pmcc.domain.instruments import Right, Side
from pmcc.domain.money import Money, Price
from pmcc.export.analytics_models import FillPoints
from pmcc.export.canonical import FLOAT_PLACES
from pmcc.export.wheel_models import (
    Benchmarks,
    FillEvidence,
    ThesisVerdict,
    WheelCycleStats,
    WheelFillGroup,
    WheelMetrics,
)
from pmcc.wheel.book import WheelState
from pmcc.wheel.engine import WheelRun
from pmcc.wheel.market import PrintPairs

_SIGN = {Side.BUY: 1, Side.SELL: -1, Side.EXPIRE: 1, Side.ASSIGN: 1}
MAKES_MONEY = "P&L over the window > $0"
BEATS_SHARPE = "annualized Sharpe > the baseline PMCC's"
BEATS_SP500 = "return on starting cash > the S&P 500's price return"


def session_closes(run: WheelRun) -> list[Money]:
    """Each session's NAV at its last bar, in order."""
    last: dict[date, Money] = {}
    for row in run.ledger:
        last[to_et(row.time).date()] = row.nav
    return list(last.values())


def metrics(run: WheelRun, risk_free_rate: float) -> WheelMetrics:
    start = run.starting_cash
    closes = session_closes(run)
    pnl = (closes[-1] if closes else start) - start
    fall, share = max_drawdown([row.nav for row in run.ledger], start)
    return WheelMetrics(
        pnl=pnl.to_dollars(),
        return_on_starting_cash=pnl.units / start.units,
        max_drawdown=fall.to_dollars(),
        max_drawdown_pct=share,
        sharpe_annualized=sharpe(daily_returns(closes, start), daily_rate(risk_free_rate)),
        sessions=len(closes),
    )


def cycle_stats(run: WheelRun) -> WheelCycleStats:
    rows = Counter((str(e.rule_id), e.side) for e in run.blotter if e.is_option)
    skipped = Counter(str(g.rule_id) for g in run.gate_log if g.outcome == "skipped")
    states = Counter(row.state for row in run.ledger)
    bars = len(run.ledger) or 1
    premium = sum((e.cash_delta for e in run.blotter if e.is_option and e.side is Side.SELL),
                  Money.zero())  # fmt: skip
    return WheelCycleStats(
        puts_sold=rows["W-P1", Side.SELL],
        puts_expired=rows["W-X1", Side.EXPIRE],
        puts_assigned=rows["W-X2", Side.ASSIGN],
        calls_sold=rows["W-C1", Side.SELL],
        calls_expired=rows["W-X3", Side.EXPIRE],
        calls_called_away=rows["W-X4", Side.ASSIGN],
        weeks=len(run.gate_log),
        weeks_sold=sum(g.outcome == "sold" for g in run.gate_log),
        weeks_skipped=dict(sorted(skipped.items())),
        premium=premium.to_dollars(),
        complete_cycles=rows["W-X4", Side.ASSIGN],
        open_at_end=run.book.shares > 0,
        time_in_state={s.value: states[s] / bars for s in WheelState},
    )


def trade_pnls(blotter: Sequence[Event]) -> list[Money | None]:
    """Each row's Trade P&L: on the row that closes a position, the Cash Δ of every row since it
    opened; None on the rows that don't close one."""
    held: dict[Instrument, int] = {}
    cash: dict[Instrument, Money] = {}
    out: list[Money | None] = []
    for event in blotter:
        i = event.instrument
        held[i] = held.get(i, 0) + _SIGN[event.side] * event.qty
        cash[i] = cash.get(i, Money.zero()) + event.cash_delta
        if held[i]:
            out.append(None)
            continue
        out.append(cash.pop(i))
        del held[i]
    return out


def verdicts(summary: WheelMetrics, benchmarks: Benchmarks) -> tuple[ThesisVerdict, ...]:
    """The three thesis claims (Spec › Thesis), judged as WD-29 fixed before the first run."""
    pmcc, sp500 = benchmarks.baseline_pmcc, benchmarks.sp500
    return (
        _verdict(1, MAKES_MONEY, float(summary.pnl), 0.0),
        _verdict(2, BEATS_SHARPE, summary.sharpe_annualized, pmcc.sharpe_annualized),
        _verdict(3, BEATS_SP500, summary.return_on_starting_cash, sp500.price_return),
    )


def _verdict(claim: int, test: str, wheel: float | None, benchmark: float | None) -> ThesisVerdict:
    """Judged on the values as published, so `pmcc verify` re-judges it from the file alike."""
    wheel, benchmark = _published(wheel), _published(benchmark)
    met = wheel is not None and benchmark is not None and wheel > benchmark
    return ThesisVerdict(claim=claim, test=test, wheel=wheel, benchmark=benchmark, met=met)


def _published(value: float | None) -> float | None:
    return None if value is None else round(value, FLOAT_PLACES) + 0.0


def fill_evidence(pairs: Mapping[Right, PrintPairs], contracts: int) -> FillEvidence:
    """Requirement 3's evidence (W3-02): each right's points and fit, puts then calls, and a fit
    over both. The fit is the PMCC's (`pmcc.analytics.fillcheck`), exact in $0.0001 units."""
    each = [pairs.get(right, PrintPairs()) for _, right in _RIGHTS]
    groups = tuple(_group(name, p) for (name, _), p in zip(_RIGHTS, each, strict=True))
    every = PrintPairs(
        mid=tuple(v for p in each for v in p.mid),
        trade=tuple(v for p in each for v in p.trade),
        spread=tuple(v for p in each for v in p.spread),
        within=tuple(v for p in each for v in p.within),
    )
    return FillEvidence(contracts=contracts, groups=groups, fit=fit(every),
                        within_spread=_share(every.within))  # fmt: skip


_RIGHTS = (("puts", Right.PUT), ("calls", Right.CALL))


def _group(name: str, pairs: PrintPairs) -> WheelFillGroup:
    points = FillPoints(mid=_dollars(pairs.mid), trade=_dollars(pairs.trade),
                        spread=_dollars(pairs.spread))  # fmt: skip
    return WheelFillGroup(group=name, points=points, fit=fit(pairs),
                          within_spread=_share(pairs.within))  # fmt: skip


def _dollars(units: Sequence[int]) -> tuple[Decimal, ...]:
    return tuple(Price(u).to_dollars() for u in units)


def _share(flags: Sequence[bool]) -> float | None:
    return sum(flags) / len(flags) if flags else None
