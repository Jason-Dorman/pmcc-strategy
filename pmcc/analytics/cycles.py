"""Cycle statistics (Spec › Cycle statistics; P6-02; PO, DEC-62): one cycle is one calendar week.

- **A cycle's P&L** is the NAV change from the previous week-final close (the starting cash, for
  the first week) to this week's, both legs included.
- **Traded and skipped** weeks are the gate log's outcomes; skips are counted by the rule that
  skipped the week.
- **Credit and buyback** are the short's cash, net of fees: the sale's cash in, and what closing it
  paid out (0 for X-S4's expiry and for X-S5's assignment, whose stock is reported apart, DEC-63).
  The long's cost is the entry cost of the long the short was sold against.
- **Wins and losses** are weeks with a long held whose P&L is above or below 0; the win rate is
  wins ÷ those weeks, and payoff is the average win ÷ |average loss|. A flat week is neither.
- **Premium captured** is Σ(credit − buyback) ÷ Σcredit over traded weeks, weighted by credit;
  **credit as a share of the long's cost** is the mean of each traded week's.
- **Exit mix:** blotter rows closing a leg, by rule, every exit rule listed even at 0.

The statistics read the published cycles, so the site can check them against the table it shows.
"""

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from decimal import Decimal
from fractions import Fraction
from statistics import fmean

from pmcc.accounting.events import Event
from pmcc.analytics.records import (
    RunRecords,
    Week,
    WeekDecision,
    closes_long,
    closes_short,
    entry_cost,
    event_week,
    monday,
    opens_long,
    opens_short,
    weeks,
)
from pmcc.domain.money import Money
from pmcc.export.analytics_models import Cycle, CycleStats

EXIT_RULES = ("X-S1", "X-S2", "X-S3", "X-S4", "X-S5", "X-L1", "X-L2")
SOLD, SKIPPED = "sold", "skipped"


def cycles(run: RunRecords) -> tuple[Cycle, ...]:
    """One cycle per week of the ledger. Raises `ValueError` for a week the gate log lacks."""
    decisions = {monday(d.session): d for d in run.gate_log}
    shorts = _shorts_by_week(run.blotter)
    found: list[Cycle] = []
    before = run.starting_cash
    for week in weeks(run.ledger):
        decision = decisions.get(monday(week.open))
        if decision is None:
            raise ValueError(f"no gate-log row for the week of {week.open}")
        found.append(_cycle(week, decision, shorts.get(monday(week.open), ()), before))
        before = week.final.nav
    return tuple(found)


type _Short = tuple[Event, Money | None]  # a short-leg row; for a sale, its long's cost


def _shorts_by_week(blotter: Sequence[Event]) -> dict[date, list[_Short]]:
    """Each week's short-leg rows, every sale with the cost of the long held when it was made."""
    found: dict[date, list[_Short]] = {}
    long_cost: Money | None = None
    for event in blotter:
        if opens_long(event):
            long_cost = entry_cost(event)
        elif closes_long(event):
            long_cost = None
        if opens_short(event) or closes_short(event):
            found.setdefault(event_week(event), []).append((event, long_cost))
    return found


def _cycle(week: Week, decision: WeekDecision, shorts: Iterable[_Short], before: Money) -> Cycle:
    sales = [(e, cost) for e, cost in shorts if opens_short(e)]
    exits = [e for e, _ in shorts if closes_short(e)]
    traded = bool(sales)
    credit = sum((e.cash_delta for e, _ in sales), Money.zero())
    buyback = -sum((e.cash_delta for e in exits), Money.zero())
    long_cost = sales[0][1] if traded else None
    return Cycle(
        week_open=week.open,
        week_final=week.final.session,
        outcome=decision.outcome,
        rule_id=str(decision.rule_id),
        long_held=week.long_held,
        credit=credit.to_dollars() if traded else None,
        buyback=buyback.to_dollars() if traded else None,
        long_cost=None if long_cost is None else long_cost.to_dollars(),
        exit_rule_id=str(exits[-1].rule_id) if exits else None,
        pnl=(week.final.nav - before).to_dollars(),
    )


def cycle_stats(weekly: Sequence[Cycle]) -> CycleStats:
    held = [c.pnl for c in weekly if c.long_held]
    wins, losses = [p for p in held if p > 0], [p for p in held if p < 0]
    average_win, average_loss = _mean(wins), _mean(losses)
    traded = [c for c in weekly if c.credit is not None]
    return CycleStats(
        weeks=len(weekly),
        weeks_traded=sum(c.outcome == SOLD for c in weekly),
        weeks_skipped=sum(c.outcome == SKIPPED for c in weekly),
        weeks_long_held=len(held),
        win_rate=len(wins) / len(held) if held else None,
        average_win=average_win,
        average_loss=average_loss,
        payoff_ratio=_payoff(wins, losses),
        premium_captured_pct=_captured(traded),
        credit_pct_of_long_cost=_credit_share(traded),
    )


def _mean(dollars: Sequence[Decimal]) -> Decimal | None:
    """The mean to $0.0001, half-even, as money rounds (DEC-44)."""
    if not dollars:
        return None
    return Money.from_dollars(Fraction(sum(dollars, Decimal(0))) / len(dollars)).to_dollars()


def _payoff(wins: Sequence[Decimal], losses: Sequence[Decimal]) -> float | None:
    """Average win ÷ |average loss|, from the exact means."""
    if not wins or not losses:
        return None
    win = Fraction(sum(wins, Decimal(0))) / len(wins)
    loss = Fraction(sum(losses, Decimal(0))) / len(losses)
    return float(win / -loss)


def _captured(traded: Sequence[Cycle]) -> float | None:
    credit = sum((c.credit for c in traded if c.credit is not None), Decimal(0))
    kept = sum((c.credit - c.buyback for c in traded if c.credit is not None
                and c.buyback is not None), Decimal(0))  # fmt: skip
    return float(kept / credit) if credit else None


def _credit_share(traded: Sequence[Cycle]) -> float | None:
    shares = [float(c.credit / c.long_cost) for c in traded
              if c.credit is not None and c.long_cost]  # fmt: skip
    return fmean(shares) if shares else None


def exit_mix(blotter: Iterable[Event]) -> dict[str, int]:
    """Rows closing a leg, by rule ID; every exit rule appears, in the spec's order here. The
    published file sorts keys (DEC-50), so a reader orders them by `EXIT_RULES`."""
    counts = Counter(str(e.rule_id) for e in blotter if closes_short(e) or closes_long(e))
    return {rule: counts[rule] for rule in EXIT_RULES}


def skips_by_rule(gate_log: Iterable[WeekDecision]) -> Mapping[str, int]:
    """Skipped weeks by the rule that skipped them, sorted by rule ID."""
    counts = Counter(str(d.rule_id) for d in gate_log if d.outcome == SKIPPED)
    return dict(sorted(counts.items()))
