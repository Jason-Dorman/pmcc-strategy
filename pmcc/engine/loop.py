"""The bar loop (ARCHITECTURE §8.1; PO, DEC-20).

Every session bar of the window, in time order, is a decision bar: the strategy sees the market
as of the bar's end through `MarketView`, and within the bar the steps run in DEC-20's order:

0. cover X-S5's short stock;  1. the long check (week-open session);  2. long entry if flat;
3. short exits;  4. short entry (week-open session);  5. X-S4/X-S5 on the short's expiry close bar;
6. marks, the ledger row and the runtime invariants.

X-E1: the last bar's ledger row marks everything at its mids; nothing is liquidated.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import final

from pmcc.accounting.book import Book
from pmcc.accounting.events import Event, Instrument, StockId
from pmcc.accounting.ledger import LedgerRow, ledger_row
from pmcc.accounting.marks import carry
from pmcc.accounting.regt import regt
from pmcc.accounting.valuation import value
from pmcc.config.strategy import RunConfig
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId
from pmcc.domain.money import Money, Price
from pmcc.domain.sessions import Session
from pmcc.engine.invariants import check_bar, check_event
from pmcc.engine.legs import GateLogRow, Trader
from pmcc.engine.market_view import MarketData
from pmcc.strategy.ports import MarketView
from pmcc.strategy.registry import Strategy


@final
@dataclass(frozen=True, slots=True)
class RunOutput:
    """One run's blotter, ledger (one row per bar) and gate log (one row per week-open session)."""

    starting_cash: Money
    blotter: tuple[Event, ...]
    ledger: tuple[LedgerRow, ...]
    gate_log: tuple[GateLogRow, ...]
    book: Book


def run_backtest(
    data: MarketData, config: RunConfig, strategy: Strategy, starting_cash: Money
) -> RunOutput:
    """Run `strategy` over `config`'s window on `data`. Raises `EngineError` (an
    `InvariantViolation` included) on any state the rules guarantee can't happen; nothing is
    returned then (DEC-49)."""
    trader = Trader(strategy, Book(starting_cash), config.strategy.fill_model)
    calendar = data.calendar
    ledger: list[LedgerRow] = []
    for session in calendar.sessions(config.window.start, config.window.end):
        week_open = calendar.week_open(session.day).day == session.day
        for end in session.bar_ends():
            ledger.append(_bar(data.view(end), session, week_open, trader, config))
    return RunOutput(starting_cash, tuple(trader.blotter), tuple(ledger), tuple(trader.gate_log),
                     trader.book)  # fmt: skip


def _bar(view: MarketView, session: Session, week_open: bool, trader: Trader,
         config: RunConfig) -> LedgerRow:  # fmt: skip
    cash_before, first_event = trader.book.cash, len(trader.blotter)
    _decide(view, session, week_open, trader)
    events = trader.blotter[first_event:]
    for event in events:
        check_event(event, trader.strategy.rule_ids, config.strategy.fill_model.spread_capture)
    return _mark(view, trader, cash_before, events)


def _decide(view: MarketView, session: Session, week_open: bool, trader: Trader) -> None:
    """Steps 0 to 5 of DEC-20, in order."""
    trader.cover_short_stock(view, session)
    if week_open:
        trader.check_long(view, session)
    trader.enter_long(view, session)
    trader.exit_short(view)
    if week_open:
        trader.enter_short(view, session)
    close_bar = session.is_close_bar(view.now)
    if week_open and close_bar:
        trader.close_week(view, session)
    short = trader.short
    if close_bar and short is not None and short.option.expiry == session.day:
        trader.resolve_expiry(view, closing_spot(view, session))
    _check_long_not_expired(view.now, trader, session)


def closing_spot(view: MarketView, session: Session) -> Price:
    """The close bar's TRDPRC_1, or else the session's last trade at or before it (PO, DEC-23).
    Raises `EngineError` if the session had no trade at all."""
    for end in reversed(session.bar_ends()):
        if end <= view.now:
            spot = view.spot(end)
            if spot is not None:
                return spot
    raise EngineError(f"no trade in the session of {session.day}: no closing spot for X-S4/X-S5")


def _check_long_not_expired(now: datetime, trader: Trader, session: Session) -> None:
    long = trader.long
    if long is not None and long.option.expiry <= session.day and session.is_close_bar(now):
        raise EngineError(f"long {long.option} reached its expiry; X-L2 should have rolled it")


def _mark(view: MarketView, trader: Trader, cash_before: Money,
          events: list[Event]) -> LedgerRow:  # fmt: skip
    """Step 6: marks, valuation, Reg T, the ledger row, then the bar's invariants."""
    book = trader.book
    fresh = {i: _mid(view, i) for i in book.positions}
    trader.marks = carry(trader.marks, fresh, view.now)
    valuation = value(book, trader.marks)
    requirements = regt(book, valuation, trader.marks)
    deltas = {o: _delta(view, o) for o in book.positions if isinstance(o, OptionId)}
    flags = {*trader.flags, *(("exit_pending",) if trader.exit_pending else ())}
    trader.flags.clear()
    row = ledger_row(view.now, book, trader.marks, valuation, requirements, deltas, flags)
    check_bar(view.now, book, cash_before, events, valuation, trader.marks, view.calendar())
    return row


def _mid(view: MarketView, instrument: Instrument) -> Price | None:
    quote = view.stock_quote() if isinstance(instrument, StockId) else view.quote(instrument)
    return None if quote is None else quote.mid


def _delta(view: MarketView, option: OptionId) -> float | None:
    chain = view.chain(option.expiry, option.right)
    row = chain.row(option.strike)
    if row is None or not chain.quotes.valid[row]:
        return None
    delta = float(chain.quotes.delta[row])
    return None if delta != delta else delta  # NaN: unknown
