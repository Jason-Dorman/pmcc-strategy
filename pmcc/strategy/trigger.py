"""E-T1: enter on the first bar where the selected contract has a valid bid and ask and its spread
is at most a share of mid, the long leg's and the short leg's (Spec › Trade rules: entry).

The spread test is exact: (ASK − BID) ≤ limit × (BID + ASK) / 2 in integer units against the
limit as written in the YAML (0.03 is 3/100), so a spread right on the limit passes.

The entry-timing runs swap E-T1 for `FixedBarTrigger` (PO, DEC-31): the short is decided on one
fixed bar of the week-open session, where it must pass the same spread test or G-1 skips the week;
the long still enters on the first bar that passes.
"""

from dataclasses import dataclass
from fractions import Fraction
from typing import Protocol, final, runtime_checkable

from pmcc.domain.clock import to_et
from pmcc.domain.instruments import OptionId
from pmcc.domain.quotes import Quote
from pmcc.strategy.ports import Leg, MarketView, TriggerResult


def as_fraction(value: float) -> Fraction:
    """A YAML threshold as the decimal it was written as: 0.03 → 3/100, not its binary float."""
    return Fraction(float.__repr__(float(value)))


def spread_share(quote: Quote) -> Fraction:
    """(ASK − BID) ÷ mid, exactly."""
    bid, ask = quote.bid.units, quote.ask.units
    return Fraction(2 * (ask - bid), ask + bid)


@runtime_checkable
class EntryTrigger(Protocol):
    """E-T1's port: which bars may decide an entry, and whether one does. The loop selects
    (and freezes) a contract only on a bar that `can_decide`, so a trigger that decides on one
    fixed bar (DEC-31's timing runs, P5-02) swaps in by kind, with no change to the loop."""

    def can_decide(self, view: MarketView, leg: Leg) -> bool: ...

    def check(self, view: MarketView, option: OptionId, leg: Leg) -> TriggerResult: ...


@final
@dataclass(frozen=True, slots=True)
class SpreadTrigger:
    long_max_spread: float
    short_max_spread: float

    def can_decide(self, view: MarketView, leg: Leg) -> bool:
        """Any bar of the session may decide: the first that passes does (Spec › E-T1)."""
        return True

    def limit(self, leg: Leg) -> Fraction:
        return as_fraction(self.long_max_spread if leg is Leg.LONG else self.short_max_spread)

    def check(self, view: MarketView, option: OptionId, leg: Leg) -> TriggerResult:
        quote = view.quote(option)
        if quote is None:
            return TriggerResult(passed=False, quote=None, spread_pct=None)
        share = spread_share(quote)
        return TriggerResult(passed=share <= self.limit(leg), quote=quote, spread_pct=float(share))


@final
@dataclass(frozen=True, slots=True)
class FixedBarTrigger:
    """E-T1 in the entry-timing runs (Spec › Sensitivity checks; PO, DEC-31). The short may be
    decided only on session bar `bar` (1 = the bar ending 10:00) of the week-open session: the
    loop selects and freezes the contract there, and if it fails `spread`'s test no later bar is
    tried, so G-1 skips the week. The long enters as under E-T1, on the first bar that passes."""

    bar: int
    spread: SpreadTrigger

    def can_decide(self, view: MarketView, leg: Leg) -> bool:
        if leg is Leg.LONG:
            return True
        now = to_et(view.now)
        ends = view.calendar().session(now.date()).bar_ends()
        return self.bar <= len(ends) and now == ends[self.bar - 1]

    def check(self, view: MarketView, option: OptionId, leg: Leg) -> TriggerResult:
        return self.spread.check(view, option, leg)
