"""The wheel's bar loop (Spec › Trade rules, Accounting, Invariants).

Every session bar of the window, in time order, is a decision bar: the rules see the market as of
the bar's end through `MarketView`. Within a bar:

1. **Sell (week's first session, W-P1/W-C1).** Holding cash, pick the put (W-P2, W-P3); holding
   shares, the call (W-C2, W-C3, never below the cost basis). Sell on the first bar the pick passes
   the entry trigger (W-T1), at the fill model's price; a put only if cash secures it (W-P4). The
   pick is made afresh on each bar until one sells, so a put W-P4 refused on one bar can still
   sell on a later one. A week that sells nothing gets a skipped
   gate-log row at the session's close, with the rule that stopped it.
2. **Settle (the option's expiry session, its close bar).** The stock's closing trade decides
   (WD-15): a put below its strike is assigned and 100 shares a contract are bought at the strike
   (W-X2), else it expires (W-X1); a call above its strike is assigned and the shares sold at the
   strike (W-X4), else it expires (W-X3).
3. **Mark.** Every holding at its mid, or its last mid flagged stale; shares an assignment just
   bought with no quote yet are marked at the closing trade that assigned them, flagged stale.
   Then the ledger row and the runtime invariants (WINV-01 to 03, 05 to 09; `invariants.py`).

W-X5: the last bar's row marks everything; nothing is liquidated. The cost basis is the assigned
put's strike × shares, less the put's credit and every call credit since, net of fees (WD-08).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from fractions import Fraction
from typing import final

from pmcc.accounting.events import Event, Instrument, StockId
from pmcc.accounting.ledger import LegGreeks
from pmcc.accounting.marks import Mark, Marks, carry
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OPTION_MULTIPLIER, OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId
from pmcc.domain.sessions import Session
from pmcc.engine.fills import fill
from pmcc.engine.greeks import leg_greeks
from pmcc.engine.invariants import check_event
from pmcc.engine.loop import closing_spot
from pmcc.engine.market_view import MarketData
from pmcc.strategy.ports import MarketView, Values
from pmcc.wheel.book import WheelBook, WheelState, WheelValuation, value
from pmcc.wheel.config import WheelConfig, WheelRunConfig
from pmcc.wheel.invariants import check_bar
from pmcc.wheel.rules import Pick, finishes_itm, passes_trigger, select_call, select_put

W_T1, W_P1, W_P4 = RuleId("W-T1"), RuleId("W-P1"), RuleId("W-P4")
W_C1, W_C3 = RuleId("W-C1"), RuleId("W-C3")
W_X1, W_X2, W_X3, W_X4 = RuleId("W-X1"), RuleId("W-X2"), RuleId("W-X3"), RuleId("W-X4")


@final
@dataclass(frozen=True, slots=True)
class OptionLeg:
    """A held short option on a bar: contracts (positive), mark, and its IV and Greeks."""

    option: OptionId
    qty: int
    mark: Price
    stale: bool
    greeks: LegGreeks


@final
@dataclass(frozen=True, slots=True)
class WheelLedgerRow:
    """One bar's portfolio (requirement 2): what is held, at what marks, and what it's worth."""

    time: datetime
    spot: Price | None
    state: WheelState
    cash: Money
    reserved: Money  # securing the short put
    free_cash: Money
    shares: int
    stock_mark: Price | None
    put: OptionLeg | None
    call: OptionLeg | None
    cost_basis: Price | None  # per share, while shares are held
    nav: Money
    flags: tuple[str, ...]


@final
@dataclass(frozen=True, slots=True)
class WheelGateRow:
    """One week's sale decision: sold, or skipped with the rule that stopped it."""

    session: date
    state: WheelState  # cash (a put) or shares (a call)
    decision_time: datetime | None
    selected: Values | None
    outcome: str  # "sold" or "skipped"
    rule_id: RuleId
    notes: str = ""


@final
@dataclass(frozen=True, slots=True)
class WheelRun:
    starting_cash: Money
    blotter: tuple[Event, ...]
    ledger: tuple[WheelLedgerRow, ...]
    gate_log: tuple[WheelGateRow, ...]
    book: WheelBook


@dataclass
class _Week:
    """The week's first session: whether it sold, and if not, what stopped it."""

    session: date
    state: WheelState
    sold: bool = False
    candidate: bool = False  # some bar had an option the selector could pick
    refused: bool = False  # W-P4 refused a put on some bar
    selected: Values | None = None
    notes: str = ""

    @property
    def selling(self) -> bool:
        return self.state in (WheelState.CASH, WheelState.SHARES)

    def skip_reason(self) -> tuple[RuleId, str]:
        if self.refused:
            return W_P4, self.notes
        if self.state is WheelState.SHARES and not self.candidate:
            return W_C3, self.notes or "no call at or above the cost basis had a quote"
        return W_T1, self.notes or "no bar had an option with a valid bid and ask"


@dataclass
class _Wheel:
    config: WheelConfig
    book: WheelBook
    stock: StockId
    blotter: list[Event] = field(default_factory=list[Event])
    gate_log: list[WheelGateRow] = field(default_factory=list[WheelGateRow])
    marks: dict[Instrument, Mark] = field(default_factory=dict[Instrument, Mark])
    basis: Money | None = None  # for all the shares held
    credit: Money = field(default_factory=Money.zero)  # the open put's
    week: _Week | None = None

    def book_event(self, event: Event) -> None:
        self.book = self.book.apply(event)
        self.blotter.append(event)


def run_wheel(data: MarketData, config: WheelRunConfig) -> WheelRun:
    """Run the wheel over `config`'s window on `data`. Raises `EngineError` (an
    `InvariantViolation` included) on any state the rules guarantee can't happen; nothing is
    returned then."""
    if data.rate != config.risk_free_rate.value:
        raise EngineError(f"the market is priced at r {data.rate}, the config's r is different")
    wheel = _Wheel(config.wheel, WheelBook(config.wheel.starting_cash), StockId(data.root))
    calendar = data.calendar
    ledger: list[WheelLedgerRow] = []
    for session in calendar.sessions(config.window.start, config.window.end):
        week_open = calendar.week_open(session.day).day == session.day
        if week_open:
            wheel.week = _Week(session.day, wheel.book.state)
        for end in session.bar_ends():
            ledger.append(_bar(data.view(end), session, week_open, wheel))
    return WheelRun(config.wheel.starting_cash, tuple(wheel.blotter), tuple(ledger),
                    tuple(wheel.gate_log), wheel.book)  # fmt: skip


def _bar(view: MarketView, session: Session, week_open: bool, wheel: _Wheel) -> WheelLedgerRow:
    cash_before, first = wheel.book.cash, len(wheel.blotter)
    if week_open:
        _sell(view, session, wheel)
    if session.is_close_bar(view.now):
        _settle(view, session, wheel)
    events = wheel.blotter[first:]
    for event in events:
        check_event(event, wheel.config.rule_ids, wheel.config.fill_model.spread_capture)
    return _mark(view, session, wheel, cash_before, events)


# --- 1. Sell ----------------------------------------------------------------------------------


def _sell(view: MarketView, session: Session, wheel: _Wheel) -> None:
    week = wheel.week
    if week is None or not week.selling:
        return
    if not week.sold:
        _try_sale(view, session, wheel, week)
    if session.is_close_bar(view.now) and not week.sold:
        rule, notes = week.skip_reason()
        wheel.gate_log.append(WheelGateRow(week.session, week.state, None, week.selected,
                                           "skipped", rule, notes))  # fmt: skip


def _try_sale(view: MarketView, session: Session, wheel: _Wheel, week: _Week) -> None:
    config = wheel.config
    expiry = view.calendar().week_final(session.day).day
    if week.state is WheelState.CASH:
        pick, rule = select_put(view, expiry, config.put_delta), W_P1
    else:
        floor = _basis_per_share(wheel)
        pick, rule = select_call(view, expiry, config.call_delta, floor), W_C1
        if pick is None and not week.candidate:
            week.notes = _no_call(view, expiry, floor)
    if pick is None:
        return
    week.candidate, week.selected = True, pick.values
    if not passes_trigger(pick, config.max_spread):
        week.notes = f"the spread stayed over {config.max_spread:.0%} of mid"
        return
    _sale(view, wheel, week, pick, rule)


def _sale(view: MarketView, wheel: _Wheel, week: _Week, pick: Pick, rule: RuleId) -> None:
    config = wheel.config
    qty = config.contracts
    kind = "put" if pick.option.right is Right.PUT else "call"
    notes = (f"Sell {kind}: delta {pick.delta:+.2f} (target {pick.values['target_delta']:+.2f}), "
             f"spot ${pick.spot.to_dollars()}, spread {pick.spread_pct:.1%} of mid")  # fmt: skip
    event = fill(time=view.now, side=Side.SELL, instrument=pick.option, qty=qty, quote=pick.quote,
                 model=config.fill_model, rule_id=rule, notes=notes,
                 audit={**pick.values, "spot_units": pick.spot.units})  # fmt: skip
    if event is None:  # the pick has a valid quote, so this can't happen
        raise EngineError(f"{pick.option} was picked without a quote at {view.now}")
    if pick.option.right is Right.PUT:
        secured = pick.option.strike.notional(OPTION_MULTIPLIER, qty)
        if wheel.book.cash + event.cash_delta < secured:
            week.refused = True
            cash = wheel.book.cash.to_dollars()
            week.notes = f"cash ${cash} can't secure ${secured.to_dollars()}"
            return
        wheel.credit = event.cash_delta
    elif wheel.basis is not None:
        wheel.basis -= event.cash_delta
    wheel.book_event(event)
    week.sold = True
    wheel.gate_log.append(WheelGateRow(week.session, week.state, view.now, pick.values, "sold",
                                       rule, notes))  # fmt: skip


def _no_call(view: MarketView, expiry: date, floor: Price) -> str:
    """W-C3's note, naming the highest call listed, so a chain that stops short of the basis (a
    data limit) reads differently from a market with no bid up there."""
    strikes = view.chain(expiry, Right.CALL).strikes()
    listed = f"highest listed ${max(strikes).to_dollars()}" if strikes else "no call listed"
    return f"no call at or above the cost basis ${floor.to_dollars()} had a quote ({listed})"


def _basis_per_share(wheel: _Wheel) -> Price:
    if wheel.basis is None or not wheel.book.shares:
        raise EngineError("shares are held with no cost basis")
    return Price(round(Fraction(wheel.basis.units, wheel.book.shares)))


# --- 2. Settle --------------------------------------------------------------------------------


def _settle(view: MarketView, session: Session, wheel: _Wheel) -> None:
    short = wheel.book.short_put or wheel.book.short_call
    if short is None or short[0].expiry != session.day:
        return
    option, qty = short
    try:
        spot = closing_spot(view, session)
    except EngineError:
        raise EngineError(
            f"{option} expires on {session.day}, a session with no stock trade: there is no "
            "closing trade to settle it by (W-X1 to W-X4)"
        ) from None
    audit: Values = {"closing_spot_units": spot.units, "strike_units": option.strike.units}
    if not finishes_itm(option, spot):
        rule = W_X1 if option.right is Right.PUT else W_X3
        notes = f"Expires: close ${spot.to_dollars()} vs strike ${option.strike.to_dollars()}"
        wheel.book_event(Event(view.now, Side.EXPIRE, option, qty, None, Price(0), Money.zero(),
                               rule, notes, audit=audit))  # fmt: skip
        return
    if option.right is Right.PUT:
        _assigned(view, wheel, option, qty, spot, audit)
    else:
        _called_away(view, wheel, option, qty, spot, audit)


def _assigned(view: MarketView, wheel: _Wheel, option: OptionId, qty: int, spot: Price,
              audit: Values) -> None:  # fmt: skip
    shares = OPTION_MULTIPLIER * qty
    notes = f"Put assigned: close ${spot.to_dollars()} below strike ${option.strike.to_dollars()}"
    _assignment(view, wheel, option, qty, W_X2, notes, audit)
    cost = option.strike.notional(1, shares)
    wheel.book_event(Event(view.now, Side.BUY, wheel.stock, shares, None, option.strike, -cost,
                           W_X2, f"Buy {shares} shares at the strike",
                           audit={**audit, "assignment": True}))  # fmt: skip
    wheel.basis = cost - wheel.credit
    wheel.credit = Money.zero()


def _called_away(view: MarketView, wheel: _Wheel, option: OptionId, qty: int, spot: Price,
                 audit: Values) -> None:  # fmt: skip
    shares = OPTION_MULTIPLIER * qty
    notes = f"Called away: close ${spot.to_dollars()} above strike ${option.strike.to_dollars()}"
    _assignment(view, wheel, option, qty, W_X4, notes, audit)
    proceeds = option.strike.notional(1, shares)
    wheel.book_event(Event(view.now, Side.SELL, wheel.stock, shares, None, option.strike, proceeds,
                           W_X4, f"Sell {shares} shares at the strike",
                           audit={**audit, "assignment": True}))  # fmt: skip
    if wheel.book.shares == 0:
        wheel.basis = None


def _assignment(view: MarketView, wheel: _Wheel, option: OptionId, qty: int, rule: RuleId,
                notes: str, audit: Values) -> None:  # fmt: skip
    wheel.book_event(Event(view.now, Side.ASSIGN, option, qty, None, None, Money.zero(), rule,
                           notes, audit=audit))  # fmt: skip


# --- 3. Mark ----------------------------------------------------------------------------------


def _mark(view: MarketView, session: Session, wheel: _Wheel, cash_before: Money,
          events: Sequence[Event]) -> WheelLedgerRow:  # fmt: skip
    book = wheel.book
    fresh = {i: _mid(view, i) for i in book.positions}
    marks = carry(wheel.marks, fresh, view.now)
    for event in events:  # a holding with no mid yet, marked stale until a mid arrives
        i = event.instrument
        if i in book.positions and i not in marks:
            marks[i] = Mark(_first_mark(event), view.now, stale=True)
    wheel.marks = marks
    valuation = value(book, wheel.marks)
    check_bar(view.now, book, wheel.marks, cash_before, events, valuation, view.calendar())
    return _row(view, wheel, valuation)


def _first_mark(event: Event) -> Price:
    """Shares an assignment bought: the closing trade that assigned them, not the strike they
    were bought at, which the close has just gone through (WD-25). Otherwise the fill."""
    close = event.audit.get("closing_spot_units")
    if isinstance(close, int):
        return Price(close)
    if event.fill is None:
        raise EngineError(f"{event.instrument} is held with neither a mid nor a fill to mark it")
    return event.fill


def _row(view: MarketView, wheel: _Wheel, valuation: WheelValuation) -> WheelLedgerRow:
    book = wheel.book
    return WheelLedgerRow(
        time=view.now,
        spot=view.spot(),
        state=book.state,
        cash=book.cash,
        reserved=valuation.reserved,
        free_cash=valuation.free_cash,
        shares=book.shares,
        stock_mark=wheel.marks[wheel.stock].price if book.shares else None,
        put=_leg(view, wheel.marks, book.short_put),
        call=_leg(view, wheel.marks, book.short_call),
        cost_basis=_basis_per_share(wheel) if book.shares else None,
        nav=valuation.nav,
        flags=valuation.stale_flags,
    )


def _leg(view: MarketView, marks: Marks, short: tuple[OptionId, int] | None) -> OptionLeg | None:
    if short is None:
        return None
    option, qty = short
    mark = marks[option]
    return OptionLeg(option, qty, mark.price, mark.stale, leg_greeks(view, option))


def _mid(view: MarketView, instrument: Instrument) -> Price | None:
    quote = view.stock_quote() if isinstance(instrument, StockId) else view.quote(instrument)
    return None if quote is None else quote.mid
