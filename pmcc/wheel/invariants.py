"""The wheel's runtime invariants after every bar (Spec › Invariants): WINV-01, 02, 05 to 08.

WINV-03 (every fill had a valid quote at the fill model's price) and WINV-09 (every row's rule ID
is the config's) are checked per event by the engine's shared `check_event`. A failure raises
`InvariantViolation`: the run stops and returns nothing.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime

from pmcc.accounting.events import Event, Instrument, multiplier
from pmcc.accounting.marks import Mark
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import to_et
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId
from pmcc.domain.money import Money
from pmcc.engine.invariants import InvariantViolation
from pmcc.wheel.book import WheelBook, WheelValuation

RUNTIME_INVARIANTS = ("WINV-01", "WINV-02", "WINV-03", "WINV-05", "WINV-06", "WINV-07",
                      "WINV-08", "WINV-09")  # fmt: skip


def check_bar(
    now: datetime,
    book: WheelBook,
    marks: Mapping[Instrument, Mark],
    cash_before: Money,
    events: Sequence[Event],
    valuation: WheelValuation,
    calendar: SessionCalendar,
) -> None:
    """WINV-01, 02, 05 to 08 on the book after the bar ending `now`."""
    moved = sum((e.cash_delta for e in events), Money.zero())
    if book.cash != cash_before + moved:
        raise InvariantViolation(f"WINV-01: cash moved {book.cash - cash_before}, rows {moved}")
    nav = book.cash
    for instrument, qty in book.positions.items():
        nav += marks[instrument].price.notional(multiplier(instrument), qty)
    if valuation.nav != nav:
        raise InvariantViolation(f"WINV-02: NAV {valuation.nav} doesn't reconcile with {nav}")
    try:
        book.check()
    except EngineError as exc:
        raise InvariantViolation(f"WINV-05/06/07: {exc}") from exc
    for i in book.positions:
        if isinstance(i, OptionId) and to_et(now) > calendar.session(i.expiry).close_bar_end:
            raise InvariantViolation(f"WINV-08: {i} is open after its expiry session")
