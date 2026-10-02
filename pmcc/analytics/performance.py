"""Performance (Spec › Performance; P6-01; PO, DEC-60): NAV at each session's close, daily and
weekly returns, and the run's metrics.

- **Daily return:** a session's close NAV ÷ the previous session's − 1; the first session's is
  against the starting cash, as the first week's is.
- **Weekly return:** the week-final session's close ÷ the previous week-final close − 1; the first
  week's is against the starting cash. It is kept at the 6 places results publish, and the CI is
  drawn from those published values, so it can be rebuilt from the file and a one-symbol pooled
  CI equals the run's own.
- **Sharpe:** on excess daily returns, each less the risk-free rate's trading day, e^(r/252) − 1
  (r continuously compounded, DEC-11): their mean ÷ their sample standard deviation, × √252.
  **Sortino:** their mean ÷ √mean(min(excess, 0)²) over every day, × √252. Both annualized by
  √252 trading days (PO, DEC-111); null when the divisor is 0.
- **Max drawdown:** on every bar's NAV, the starting cash the first peak. The largest fall in
  dollars and the largest as a share of its peak are each their own maximum.
- **Longest time underwater:** the most sessions from a close at a peak to the close that regains
  it, or to the last session if none does; the starting cash is the peak before the first close.
- **Return:** P&L ÷ the starting cash, over the window, not annualized (PO, DEC-111).

Ratios are floats from exact integer money; the metrics here use `statistics`, which sums floats
exactly, so they don't depend on summation order. The CI's means are numpy's (`bootstrap`).
"""

import math
from collections.abc import Sequence
from statistics import fmean, stdev

from pmcc.accounting.ledger import LedgerRow
from pmcc.analytics.bootstrap import mean_ci
from pmcc.analytics.records import RunRecords, session_closes, weeks
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


TRADING_DAYS = 252  # a year of sessions, for the daily risk-free rate and annualizing (DEC-111)
_ANNUALIZE = math.sqrt(TRADING_DAYS)


def daily_rate(risk_free_rate: float) -> float:
    """The risk-free return over one trading day; `risk_free_rate` is continuously compounded."""
    return math.expm1(risk_free_rate / TRADING_DAYS)


def sharpe(returns: Sequence[float], rf_daily: float) -> float | None:
    """Excess daily returns' mean ÷ their sample standard deviation, annualized."""
    if len(returns) < 2:
        return None
    excess = [r - rf_daily for r in returns]
    spread = stdev(excess)
    return fmean(excess) / spread * _ANNUALIZE if spread else None


def sortino(returns: Sequence[float], rf_daily: float) -> float | None:
    """Excess daily returns' mean ÷ √mean(min(excess, 0)²) over every day, annualized; like
    Sharpe, it needs two days."""
    if len(returns) < 2:
        return None
    excess = [r - rf_daily for r in returns]
    downside = fmean([min(e, 0.0) ** 2 for e in excess])
    return fmean(excess) / math.sqrt(downside) * _ANNUALIZE if downside else None


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


def metrics(run: RunRecords, seed: int, risk_free_rate: float) -> Metrics:
    """The run's metrics, its weekly CI seeded with `seed` (DEC-61), its Sharpe and Sortino in
    excess of `risk_free_rate` (DEC-111)."""
    start = run.starting_cash
    closes = [c.nav for c in session_closes(run.ledger)]
    daily = daily_returns(closes, start)
    pnl = (closes[-1] if closes else start) - start
    rf_daily = daily_rate(risk_free_rate)
    fall, share = max_drawdown([row.nav for row in run.ledger], start)
    weekly = [[w.value] for w in weekly_returns(run.ledger, start)]
    return Metrics(
        pnl=pnl.to_dollars(),
        return_on_starting_nav=pnl.units / start.units,
        max_drawdown=fall.to_dollars(),
        max_drawdown_pct=share,
        longest_underwater_sessions=longest_underwater(closes, start),
        sharpe_annualized=sharpe(daily, rf_daily),
        sortino_annualized=sortino(daily, rf_daily),
        sessions=len(closes),
        weekly_return=mean_ci(weekly, seed),
    )
