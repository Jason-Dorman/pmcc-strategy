"""What the analytics read from one run (ARCHITECTURE §3.2): its starting cash, blotter, ledger and
gate log, as protocols the engine's `RunOutput` satisfies, so `pmcc.analytics` never imports the
engine (§3.3).

The ledger has one row per session bar, in time order, so a session's last row is its close bar
and a calendar week's last close is its week-final session's. Which leg a blotter row trades
follows from the rule that made it (Spec › Trade rules): an E-L entry buys the long and an X-L
exit sells it; E-S1 sells the short, and X-S1 to X-S5 close it (a buyback, X-S4's expiry or
X-S5's assignment). X-S5's stock rows are the stock's, never a leg's.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Protocol, final

from pmcc.accounting.events import Event
from pmcc.accounting.ledger import LedgerRow
from pmcc.domain.clock import to_et
from pmcc.domain.instruments import Side
from pmcc.domain.money import Money
from pmcc.domain.rules import RuleId


class WeekDecision(Protocol):
    """A gate-log row: the week-open session's short decision (DEC-22)."""

    @property
    def session(self) -> date: ...
    @property
    def outcome(self) -> str: ...  # "sold" or "skipped"
    @property
    def rule_id(self) -> RuleId: ...


class RunRecords(Protocol):
    """One run's records, as the engine returns them."""

    @property
    def starting_cash(self) -> Money: ...
    @property
    def blotter(self) -> Sequence[Event]: ...
    @property
    def ledger(self) -> Sequence[LedgerRow]: ...
    @property
    def gate_log(self) -> Sequence[WeekDecision]: ...


@final
@dataclass(frozen=True, slots=True)
class Close:
    """A session's close-bar NAV."""

    session: date
    nav: Money


@final
@dataclass(frozen=True, slots=True)
class Week:
    """A calendar week of the window: its sessions' closes, and whether a long was held."""

    closes: tuple[Close, ...]
    long_held: bool

    @property
    def open(self) -> date:
        return self.closes[0].session

    @property
    def final(self) -> Close:
        return self.closes[-1]


def monday(day: date) -> date:
    """The Monday of `day`'s calendar week (Monday to Sunday, ARCHITECTURE §4.2)."""
    return day - timedelta(days=day.weekday())


def session_closes(ledger: Sequence[LedgerRow]) -> tuple[Close, ...]:
    """Each session's NAV at its last bar, in order."""
    last: dict[date, Money] = {}
    for row in ledger:
        last[to_et(row.time).date()] = row.nav
    return tuple(Close(day, nav) for day, nav in last.items())


def weeks(ledger: Sequence[LedgerRow]) -> tuple[Week, ...]:
    """The window's calendar weeks, in order. A week held a long if any of its bars ends with
    one, or one was carried into it: a row is the state after its bar's trades, so a long sold on
    the week's first bar (an X-L reset whose re-entry never completes) shows on none of its rows,
    yet the week's P&L is that long's."""
    closes: dict[date, list[Close]] = {}
    held: dict[date, bool] = {}
    for close in session_closes(ledger):
        closes.setdefault(monday(close.session), []).append(close)
    carried = False  # the last row before this one ended with a long
    for row in ledger:
        key = monday(to_et(row.time).date())
        held[key] = held.get(key, carried) or row.long is not None
        carried = row.long is not None
    return tuple(Week(tuple(c), held[key]) for key, c in closes.items())


def event_week(event: Event) -> date:
    return monday(to_et(event.time).date())


def opens_long(event: Event) -> bool:
    return event.is_option and event.side is Side.BUY and event.rule_id.startswith("E-L")


def closes_long(event: Event) -> bool:
    return event.is_option and event.side is Side.SELL and event.rule_id.startswith("X-L")


def opens_short(event: Event) -> bool:
    return event.is_option and event.side is Side.SELL and event.rule_id.startswith("E-S")


def closes_short(event: Event) -> bool:
    """A buyback (X-S1 to X-S3), an expiry (X-S4) or an assignment (X-S5)."""
    return event.is_option and event.side is not Side.SELL and event.rule_id.startswith("X-S")


def entry_cost(event: Event) -> Money:
    """What a long entry paid: fill × 100 × qty plus fees."""
    return -event.cash_delta
