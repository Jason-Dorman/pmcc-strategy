"""Performance (Spec › Performance; P6-01; PO, DEC-60): NAV at each session's close, daily and
weekly returns, and the run's metrics.

- **Daily return:** a session's close NAV ÷ the previous session's − 1; the first session's is
  against the starting cash, as the first week's is.
- **Weekly return:** the week-final session's close ÷ the previous week-final close − 1; the first
  week's is against the starting cash. It is kept at the 6 places results publish, and the CI is
  drawn from those published values, so it can be rebuilt from the file and a one-symbol pooled
  CI equals the run's own.
- **Sharpe:** the daily returns' mean ÷ their sample standard deviation. **Sortino:** their mean ÷
  √mean(min(r, 0)²), over every day. Target 0, neither annualized; null when the divisor is 0.
- **Max drawdown:** on every bar's NAV, the starting cash the first peak. The largest fall in
  dollars and the largest as a share of its peak are each their own maximum.
- **Longest time underwater:** the most sessions from a close at a peak to the close that regains
  it, or to the last session if none does; the starting cash is the peak before the first close.
- **Returns:** P&L ÷ the starting cash, and P&L ÷ the dearest long entry (the capital deployed).

Ratios are floats from exact integer money; the metrics here use `statistics`, which sums floats
exactly, so they don't depend on summation order. The CI's means are numpy's (`bootstrap`).
"""

import math
from collections.abc import Sequence
from statistics import fmean, stdev

from pmcc.accounting.ledger import LedgerRow
from pmcc.analytics.bootstrap import mean_ci
from pmcc.analytics.records import RunRecords, entry_cost, opens_long, session_closes, weeks
from pmcc.domain.money import Money
from pmcc.export.analytics_models import Metrics, NavPoint, WeeklyReturn
from pmcc.export.canonical import FLOAT_PLACES


def nav_close(ledger: Sequence[LedgerRow]) -> tuple[NavPoint, ...]:
    return tuple(
        NavPoint(session=c.session, nav=c.nav.to_dollars()) for c in session_closes(ledger)
    )


def weekly_returns(ledger: Sequence[LedgerRow], starting_cash: Money) -> tuple[WeeklyReturn, ...]:
    finals = [week.final for week in weeks(ledger)]
    values = daily_returns([c.nav for c in finals], starting_cash)
    return tuple(WeeklyReturn(week_final=c.session, nav=c.nav.to_dollars(), value=_published(v))
                 for c, v in zip(finals, values, strict=True))  # fmt: skip


def _published(value: float) -> float:
    """`value` as canonical JSON prints it (DEC-50)."""
    return round(value, FLOAT_PLACES) + 0.0


def daily_returns(navs: Sequence[Money], starting_cash: Money) -> list[float]:
    """Each NAV ÷ the one before it − 1, the first ÷ `starting_cash` − 1."""
    before = [starting_cash, *navs[:-1]]
    return [now.units / then.units - 1 for now, then in zip(navs, before, strict=True)]


def sharpe(returns: Sequence[float]) -> float | None:
    if len(returns) < 2:
        return None
    spread = stdev(returns)
    return fmean(returns) / spread if spread else None


def sortino(returns: Sequence[float]) -> float | None:
    if not returns:
        return None
    downside = fmean([min(r, 0.0) ** 2 for r in returns])
    return fmean(returns) / math.sqrt(downside) if downside else None


def max_drawdown(navs: Sequence[Money], starting_cash: Money) -> tuple[Money, float]:
    """The largest fall from a running peak, in dollars, and the largest as a share of its peak."""
    peak, fall, share = starting_cash, Money.zero(), 0.0
    for nav in navs:
        peak = max(peak, nav)
        fall = max(fall, peak - nav)
        share = max(share, (peak - nav).units / peak.units)
    return fall, share


def longest_underwater(closes: Sequence[Money], starting_cash: Money) -> int:
    """The most sessions from a close at a peak to the close regaining it, or to the last close.
    Index 0 is the starting cash, before the first close."""
    peak, peak_at, longest = starting_cash, 0, 0
    for at, nav in enumerate(closes, start=1):
        if nav >= peak:
            if at - peak_at > 1:  # closes below the peak came between
                longest = max(longest, at - peak_at)
            peak, peak_at = nav, at
    if peak_at < len(closes):
        longest = max(longest, len(closes) - peak_at)
    return longest


def metrics(run: RunRecords, seed: int) -> Metrics:
    """The run's metrics, its weekly CI seeded with `seed` (DEC-61)."""
    start = run.starting_cash
    closes = [c.nav for c in session_closes(run.ledger)]
    daily = daily_returns(closes, start)
    pnl = (closes[-1] if closes else start) - start
    peak_long = max((entry_cost(e) for e in run.blotter if opens_long(e)), default=None)
    fall, share = max_drawdown([row.nav for row in run.ledger], start)
    weekly = [[w.value] for w in weekly_returns(run.ledger, start)]
    return Metrics(
        pnl=pnl.to_dollars(),
        return_on_starting_nav=pnl.units / start.units,
        return_on_capital=None if peak_long is None else pnl.units / peak_long.units,
        peak_long_cost=None if peak_long is None else peak_long.to_dollars(),
        max_drawdown=fall.to_dollars(),
        max_drawdown_pct=share,
        longest_underwater_sessions=longest_underwater(closes, start),
        sharpe_daily=sharpe(daily),
        sortino_daily=sortino(daily),
        sessions=len(closes),
        weekly_return=mean_ci(weekly, seed),
    )
