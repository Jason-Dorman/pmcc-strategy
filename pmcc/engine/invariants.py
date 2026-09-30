"""Runtime invariants, checked on every bar and every event of every run (ARCHITECTURE §8.4).

- **Every event:** INV-03 (a fill had a valid BID/ASK and is mid ± capture × half-spread),
  INV-06 (a short entry satisfied E-S5), INV-08 (available funds ≥ 0 after an entry), INV-09 (its
  rule ID is the config's).
- **Every bar:** INV-01 (cash moved by exactly the bar's Cash Δ), INV-02 (NAV reconciles), INV-05
  and INV-10 (the short is covered and matches the long), INV-07 (no short open after its expiry
  session).

A failure logs `invariant.failed` and raises `InvariantViolation`: the run stops and writes nothing
(DEC-49).
"""

from collections.abc import Iterable, Sequence
from datetime import datetime

import structlog

from pmcc.accounting.book import Book
from pmcc.accounting.events import Event, multiplier
from pmcc.accounting.marks import Marks
from pmcc.accounting.valuation import Valuation
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import to_et
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.quotes import Quote
from pmcc.domain.rules import RuleId
from pmcc.engine.fills import fill_price

log = structlog.get_logger()

ENTRY_RULES = frozenset({RuleId("E-L1"), RuleId("E-S1")})
# What every run checks, on every bar or event; a result records them (PO, DEC-54).
RUNTIME_INVARIANTS = ("INV-01", "INV-02", "INV-03", "INV-05", "INV-06", "INV-07", "INV-08",
                      "INV-09", "INV-10")  # fmt: skip


class InvariantViolation(EngineError):  # noqa: N818 (the spec's name)
    """A runtime invariant failed."""


def _fail(inv: str, message: str) -> None:
    log.error("invariant.failed", invariant=inv, message=message)
    raise InvariantViolation(f"{inv}: {message}")


def check_event(event: Event, rule_ids: frozenset[RuleId], capture: float) -> None:
    """INV-03, 06, 08 and 09 on one blotter row."""
    if event.rule_id not in rule_ids:
        _fail("INV-09", f"{event.rule_id} isn't a rule of this strategy")
    if event.side in (Side.BUY, Side.SELL) and not event.audit.get("assignment"):
        _check_fill(event, capture)
    if event.rule_id in ENTRY_RULES and event.side in (Side.BUY, Side.SELL):
        _check_entry(event)


def _check_fill(event: Event, capture: float) -> None:
    bid, ask = event.audit.get("bid"), event.audit.get("ask")
    if not isinstance(bid, int) or not isinstance(ask, int) or not 0 < bid <= ask:
        _fail("INV-03", f"{event.side} {event.instrument} filled without a valid BID/ASK")
        return
    quote = Quote(Price(bid), Price(ask))
    if event.fill != fill_price(quote, event.side, capture) or event.limit != quote.mid:
        _fail("INV-03", f"{event.side} {event.instrument} at {event.fill} isn't the fill model's")


def _check_entry(event: Event) -> None:
    funds = event.audit.get("funds_after")
    if not isinstance(funds, int) or funds < 0:
        _fail("INV-08", f"{event.rule_id} at {event.time} left available funds at {funds}")
    if event.rule_id == RuleId("E-S1") and event.audit.get("e_s5_satisfied") is not True:
        _fail("INV-06", f"short entry at {event.time} didn't satisfy E-S5")


def check_bar(
    now: datetime,
    book: Book,
    cash_before: Money,
    events: Sequence[Event],
    valuation: Valuation,
    marks: Marks,
    calendar: SessionCalendar,
) -> None:
    """INV-01, 02, 05, 07 and 10 after a bar."""
    moved = sum((e.cash_delta for e in events), Money.zero())
    if book.cash != cash_before + moved:
        _fail("INV-01", f"cash moved {book.cash - cash_before} on a bar whose rows moved {moved}")
    if valuation.nav != _nav(book, marks):
        _fail("INV-02", f"NAV {valuation.nav} doesn't reconcile at {now}")
    try:
        book.check_covered()
    except EngineError as exc:
        _fail("INV-05/INV-10", str(exc))
    for option in _expired(book.short_calls, now, calendar):
        _fail("INV-07", f"short {option} is open after its expiry session")


def _nav(book: Book, marks: Marks) -> Money:
    total = book.cash
    for instrument, qty in book.positions.items():
        total += marks[instrument].price.notional(multiplier(instrument), qty)
    return total


def _expired(
    shorts: Iterable[OptionId], now: datetime, calendar: SessionCalendar
) -> list[OptionId]:
    return [o for o in shorts if to_et(now) > calendar.session(o.expiry).close_bar_end]
