"""The legs' state machines and the gate log (ARCHITECTURE §8.2; PO, DEC-20 to DEC-22, DEC-27,
DEC-28, DEC-34).

`Trader` holds one run's position state and books its trades. The loop (`engine.loop`) calls its
steps on every bar in DEC-20's order:

0. `cover_short_stock`: X-S5's short stock is bought back at the first bar of a later session
   with a valid stock BID/ASK (DEC-28).
1. `check_long` (week-open session only): X-L1 and X-L2 are checked once, at the first bar where
   the long has a fresh quote, and a sale fills there. Short entry waits for this check (DEC-28).
2. `enter_long` (whenever no long is held): E-L2/E-L3 select, and the first bar a contract is
   selected freezes it for the session; E-T1 then decides the bar; E-L4 blocks an entry that would
   leave available funds negative. If the session ends first, E-L1 retries the next session with
   a fresh selection (DEC-21).
3. `exit_short`: X-S1, X-S2 on any bar, X-S3 on the Friday check bar; the first that fires closes
   the short. A fire without a quote (X-S3 only) fills at the next bar of the session that has
   one, or X-S4/X-S5 resolve it at the close (DEC-28).
4. `enter_short` (week-open session only, once a week): E-S2/E-S3 select and freeze; the first bar
   E-T1 passes is the decision bar, where G-2 to G-5 are all evaluated and the first to fire skips
   the week; else the short is sold (DEC-21, DEC-22).
5. `resolve_expiry`: on the short's expiry close bar, X-S4 expires it at $0 or X-S5 assigns it
   (ASSIGN, then short stock sold at the strike).

`close_week` writes the week's gate-log row at the end of the week-open session if the short
wasn't decided: G-1 when no selected short ever passed E-T1, E-S1 when no long was held or it
couldn't be checked, X-L1/X-L2 when a reset's re-entry didn't complete (DEC-22, DEC-28).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import final

import structlog

from pmcc.accounting.book import Book
from pmcc.accounting.events import AuditValue, Event, StockId
from pmcc.accounting.marks import Mark
from pmcc.accounting.regt import funds_after
from pmcc.config.strategy import FillModel
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OPTION_MULTIPLIER, OptionId, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId
from pmcc.domain.sessions import Session
from pmcc.engine.fills import fill
from pmcc.strategy.exits import ExitRule
from pmcc.strategy.measures import expected_move_at
from pmcc.strategy.ports import (
    ExitOutcome,
    ExitStatus,
    GateResult,
    GateStatus,
    HeldLeg,
    Leg,
    MarketView,
    PositionState,
    Selection,
    ShortDecision,
    Values,
)
from pmcc.strategy.registry import Strategy

log = structlog.get_logger()

E_L1, E_L4, E_S1 = RuleId("E-L1"), RuleId("E-L4"), RuleId("E-S1")
X_S4, X_S5 = RuleId("X-S4"), RuleId("X-S5")


@final
@dataclass(frozen=True, slots=True)
class GateLogRow:
    """One week-open session's short decision (Spec › Gate log; DEC-22)."""

    session: date
    decision_time: datetime | None
    selected: Values | None
    gates: tuple[GateResult, ...]
    outcome: str  # "sold" or "skipped"
    rule_id: RuleId
    notes: str = ""


@dataclass
class _Week:
    """The week-open session's short-entry state."""

    session: date
    frozen: Selection | None = None
    frozen_at: datetime | None = None
    bars_checked: int = 0
    best_spread: float | None = None
    decision_spread: float | None = None
    decided: bool = False


@dataclass
class Trader:
    """One run's positions, its blotter and its gate log."""

    strategy: Strategy
    book: Book
    fill_model: FillModel
    marks: dict[OptionId | StockId, Mark] = field(default_factory=dict[OptionId | StockId, Mark])
    blotter: list[Event] = field(default_factory=list[Event])
    gate_log: list[GateLogRow] = field(default_factory=list[GateLogRow])
    flags: set[str] = field(default_factory=set[str])
    long: HeldLeg | None = None
    short: HeldLeg | None = None
    _long_candidate: tuple[Selection, date, datetime] | None = None  # frozen: session, bar
    _long_blocked: date | None = None  # a session whose long entry E-L4 blocked
    _long_checked: date | None = None  # the week-open session whose long check is done
    _reset: RuleId | None = None  # this week's X-L1/X-L2, until the re-entry completes
    _pending_exit: ExitOutcome | None = None
    _assigned: date | None = None  # the session X-S5 sold stock short
    _week: _Week | None = None
    _long_block_funds: Money | None = None

    # ---- booking ---------------------------------------------------------------------------

    def _book(self, event: Event) -> None:
        self.book = self.book.apply(event)
        self.blotter.append(event)
        if event.limit is not None and event.instrument in self.book.positions:
            self.marks[event.instrument] = Mark(event.limit, event.time, stale=False)

    def _trade(self, view: MarketView, side: Side, instrument: OptionId | StockId, qty: int,
               rule_id: RuleId, notes: str,
               audit: Mapping[str, AuditValue]) -> Event | None:  # fmt: skip
        quote = view.stock_quote() if isinstance(instrument, StockId) else view.quote(instrument)
        return fill(time=view.now, side=side, instrument=instrument, qty=qty, quote=quote,
                    model=self.fill_model, rule_id=rule_id, notes=notes, audit=audit)  # fmt: skip

    def _entry(self, event: Event) -> tuple[Event, Money]:
        """The entry with its post-trade available funds in its audit (INV-08)."""
        funds = funds_after(self.book, self.marks, event)
        audit = {**event.audit, "funds_after": funds.units}
        return _with_audit(event, audit), funds

    # ---- 0. X-S5's short stock -------------------------------------------------------------

    def cover_short_stock(self, view: MarketView, session: Session) -> None:
        stock = next((s for s, q in self.book.stock.items() if q < 0), None)
        if stock is None or self._assigned is None or session.day <= self._assigned:
            return
        shares = -self.book.shares(stock)
        event = self._trade(view, Side.BUY, stock, shares, X_S5,
                            "cover the short stock left by X-S5", {})  # fmt: skip
        if event is not None:
            self._book(event)
            self._assigned = None

    # ---- 1. the week-open long check -------------------------------------------------------

    def check_long(self, view: MarketView, session: Session) -> None:
        long = self.long
        if long is None or self._long_checked == session.day:
            return
        if view.quote(long.option) is None:
            return  # checked at the first bar with a fresh long quote (DEC-28)
        self._long_checked = session.day
        fired = self._first_fired(view, self.strategy.long_exits, long.option)
        if fired is None:
            return
        event = self._trade(view, Side.SELL, long.option, long.qty, fired.rule_id,
                            _notes(fired.values), fired.values)  # fmt: skip
        if event is None:
            raise EngineError(f"{fired.rule_id} fired with a fresh quote but didn't fill")
        self._book(event)
        self.long, self._reset = None, fired.rule_id

    def _first_fired(self, view: MarketView, rules: tuple[ExitRule, ...],
                     option: OptionId) -> ExitOutcome | None:  # fmt: skip
        """The first rule, in spec order, that fires on this bar; unevaluated ones are logged with
        the rule, the contract and the IV code (PO, DEC-27)."""
        position = PositionState(self.long, self.short)
        for rule in rules:
            outcome = rule.check(view, position)
            if outcome is None:
                continue
            if outcome.status is ExitStatus.UNEVALUATED:
                log.info("engine.exit.unevaluated", rule=outcome.rule_id, time=view.now.isoformat(),
                         option=_describe(option), iv_code=outcome.values.get("iv_code"),
                         reason=outcome.reason)  # fmt: skip
            elif outcome.fired:
                return outcome
        return None

    # ---- 2. long entry ---------------------------------------------------------------------

    def enter_long(self, view: MarketView, session: Session) -> None:
        if self.long is not None or self._long_blocked == session.day:
            return
        if not self.strategy.trigger.can_decide(view, Leg.LONG):
            return
        frozen = self._long_selection(view, session)
        if frozen is None:
            return
        selection, selected_at = frozen
        trigger = self.strategy.trigger.check(view, selection.option, Leg.LONG)
        if not trigger.passed:
            return
        qty = self.strategy.long_contracts
        values = _entry_values(selection, selected_at, trigger.spread_pct)
        notes = _notes(values, re_entry=self._reset)
        event = self._trade(view, Side.BUY, selection.option, qty, E_L1, notes, values)
        if event is None:
            return
        event, funds = self._entry(event)
        if funds.units < 0:
            self._block_long(view, session, funds)
            return
        self._book(event)
        self.long = HeldLeg(selection.option, qty, _fill(event), view.now)
        self._long_candidate, self._reset = None, None
        self._long_checked = session.day  # a long bought this session needs no reset check

    def _long_selection(
        self, view: MarketView, session: Session
    ) -> tuple[Selection, datetime] | None:
        """The session's frozen long selection and the bar it froze on, selecting it on the first
        bar that can (DEC-21)."""
        if self._long_candidate is None or self._long_candidate[1] != session.day:
            selection = self.strategy.long_selector.select(view)
            self._long_candidate = None if selection is None else (selection, session.day, view.now)
        if self._long_candidate is None:
            return None
        return self._long_candidate[0], self._long_candidate[2]

    def _block_long(self, view: MarketView, session: Session, funds: Money) -> None:
        self._long_blocked = session.day
        self._long_block_funds = funds
        self.flags.add("entry_blocked")
        log.info("engine.entry.retry", rule=E_L4, time=view.now.isoformat(),
                 funds_after=str(funds.to_dollars()))  # fmt: skip

    # ---- 3. short exits --------------------------------------------------------------------

    def exit_short(self, view: MarketView) -> None:
        short = self.short
        if short is None:
            return
        fired = self._pending_exit or self._first_fired(
            view, self.strategy.short_exits, short.option
        )
        if fired is None:
            return
        notes = _notes(fired.values) + ("; delayed fill" if self._pending_exit else "")
        event = self._trade(view, Side.BUY, short.option, short.qty, fired.rule_id, notes,
                            fired.values)  # fmt: skip
        if event is None:
            self._pending_exit = fired  # X-S3 without a quote: fill later in the session
            log.info("engine.exit.pending", rule=fired.rule_id, time=view.now.isoformat())
            return
        self._book(event)
        self.short, self._pending_exit = None, None

    # ---- 4. short entry --------------------------------------------------------------------

    def enter_short(self, view: MarketView, session: Session) -> None:
        week = self._this_week(session)
        long = self.long
        if week.decided or self.short is not None or long is None:
            return
        if self._long_checked != session.day:
            return  # the long must be checked first (DEC-28)
        if not self.strategy.trigger.can_decide(view, Leg.SHORT):
            return
        if week.frozen is None:
            week.frozen = self.strategy.short_selector.select(view, long)
            week.frozen_at = view.now
        week.bars_checked += 1
        if week.frozen is None:
            return
        trigger = self.strategy.trigger.check(view, week.frozen.option, Leg.SHORT)
        if trigger.spread_pct is not None:
            week.best_spread = min(week.best_spread or trigger.spread_pct, trigger.spread_pct)
        if trigger.passed and trigger.quote is not None:
            week.decision_spread = trigger.spread_pct
            self._decide(view, week, ShortDecision(week.frozen, trigger.quote, long))

    def _this_week(self, session: Session) -> _Week:
        if self._week is None or self._week.session != session.day:
            self._week = _Week(session.day)
        return self._week

    def _decide(self, view: MarketView, week: _Week, decision: ShortDecision) -> None:
        """The decision bar: every gate, then the sale unless one fires (DEC-22)."""
        week.decided = True
        g1 = self.strategy.no_quote.passed({"bars_checked": week.bars_checked})
        gates = (g1, *(g.evaluate(view, decision) for g in self.strategy.gates))
        fired = next((g for g in gates if g.status is GateStatus.FIRE), None)
        if fired is not None:
            log.info("engine.gate.fired", rule=fired.rule_id, time=view.now.isoformat())
            self._log_week(view, week, gates, "skipped", fired.rule_id, _notes(fired.values))
            return
        self._sell_short(view, week, decision, gates)

    def _sell_short(self, view: MarketView, week: _Week, decision: ShortDecision,
                    gates: tuple[GateResult, ...]) -> None:  # fmt: skip
        selection = decision.selection
        check = self.strategy.constraint.check(decision.long, selection.option.strike,
                                               decision.quote.mid)  # fmt: skip
        em = expected_move_at(view, selection.option.expiry)  # for X-S3
        values = _entry_values(selection, week.frozen_at or view.now, week.decision_spread)
        values.update({k: check.values[k] for k in ("strike_gap", "net_debit")})
        notes = _notes(values)
        audit: dict[str, AuditValue] = {**values, **_prefixed("e_s5", check.values)}
        audit["em_at_entry"] = None if em is None else str(em.to_dollars())
        event = self._trade(view, Side.SELL, selection.option, decision.long.qty, E_S1, notes,
                            audit)  # fmt: skip
        if event is None:
            raise EngineError("E-T1 passed on a fresh quote but the short didn't fill")
        event, funds = self._entry(event)
        if funds.units < 0:
            note = f"available funds would go negative ({funds.to_dollars()})"
            self._log_week(view, week, gates, "skipped", E_L4, note)
            return
        self._book(event)
        self.short = HeldLeg(selection.option, decision.long.qty, _fill(event), view.now, em)
        self._log_week(view, week, gates, "sold", E_S1, notes)

    def _log_week(self, view: MarketView, week: _Week, gates: tuple[GateResult, ...],
                  outcome: str, rule_id: RuleId, notes: str) -> None:  # fmt: skip
        selected = None if week.frozen is None else _selected(week.frozen)
        self.gate_log.append(
            GateLogRow(week.session, view.now, selected, gates, outcome, rule_id, notes)
        )

    def close_week(self, view: MarketView, session: Session) -> None:
        """At the week-open session's close: the row for a week the short wasn't decided in."""
        week = self._this_week(session)
        if week.decided:
            return
        week.decided = True
        rule_id, notes, gates = self._undecided(week)
        selected = None if week.frozen is None else _selected(week.frozen)
        self.gate_log.append(GateLogRow(week.session, None, selected, gates, "skipped", rule_id,
                                        notes))  # fmt: skip

    def _undecided(self, week: _Week) -> tuple[RuleId, str, tuple[GateResult, ...]]:
        if self.long is None:
            if self._reset is not None:
                return self._reset, self._reset_reason(week.session), ()
            return E_S1, "no long held", ()
        if self._long_checked != week.session:
            return E_S1, "long not checked: no fresh long quote", ()
        reason = "no short selected" if week.frozen is None else "never passed E-T1"
        values: Values = {"bars_checked": week.bars_checked, "best_spread": week.best_spread}
        g1 = self.strategy.no_quote.fire(values, reason)
        skipped = tuple(GateResult(g.rule_id, GateStatus.NOT_EVALUATED)
                        for g in self.strategy.gates)  # fmt: skip
        return g1.rule_id, reason, (g1, *skipped)

    def _reset_reason(self, session: date) -> str:
        """Why the re-entry after this week's reset didn't complete (DEC-22)."""
        reset = f"re-entry after {self._reset}"
        if self._long_blocked == session:
            funds = self._long_block_funds
            shown = "" if funds is None else f" ({funds.to_dollars()})"
            return f"{reset} blocked by E-L4: available funds would go negative{shown}"
        if self._long_candidate is None or self._long_candidate[1] != session:
            return f"{reset}: no long selected"
        return f"{reset} didn't pass E-T1"

    # ---- 5. expiry -------------------------------------------------------------------------

    def resolve_expiry(self, view: MarketView, closing_spot: Price) -> None:
        short = self.short
        if short is None:
            return
        rule_id = self.strategy.expiry.resolve(closing_spot, short.option)
        values: Values = {"closing_spot": str(closing_spot.to_dollars()),
                          "strike": str(short.option.strike.to_dollars())}  # fmt: skip
        if rule_id == X_S4:
            self._book(Event(view.now, Side.EXPIRE, short.option, short.qty, None, Price(0),
                             Money.zero(), X_S4, _notes(values), audit=values))  # fmt: skip
        else:
            self._assign(view, short, closing_spot, values)
        self.short, self._pending_exit = None, None

    def _assign(self, view: MarketView, short: HeldLeg, closing: Price, values: Values) -> None:
        self._book(Event(view.now, Side.ASSIGN, short.option, short.qty, None, None, Money.zero(),
                         X_S5, _notes(values), audit=values))  # fmt: skip
        stock = StockId(short.option.root)
        shares = short.qty * OPTION_MULTIPLIER
        strike = short.option.strike
        self._book(Event(view.now, Side.SELL, stock, shares, None, strike,
                         strike.notional(1, shares), X_S5, "short stock at the strike (assigned)",
                         audit={**values, "assignment": True}))  # fmt: skip
        quote = view.stock_quote()
        self.marks[stock] = (Mark(quote.mid, view.now, stale=False) if quote is not None
                             else Mark(closing, view.now, stale=True))  # fmt: skip
        self._assigned = view.now.date()

    @property
    def exit_pending(self) -> bool:
        return self._pending_exit is not None


def _fill(event: Event) -> Price:
    if event.fill is None:
        raise EngineError(f"{event.side} {event.instrument} has no fill")
    return event.fill


def _with_audit(event: Event, audit: Mapping[str, AuditValue]) -> Event:
    return Event(event.time, event.side, event.instrument, event.qty, event.limit, event.fill,
                 event.cash_delta, event.rule_id, event.notes, event.fee, audit)  # fmt: skip


def _prefixed(prefix: str, values: Values) -> dict[str, AuditValue]:
    return {f"{prefix}_{k}": v for k, v in values.items()}


def _describe(option: OptionId) -> str:
    return f"{option.root} {option.expiry} {option.right} {option.strike.to_dollars()}"


def _selected(selection: Selection) -> Values:
    return {"option": _describe(selection.option), **selection.values}


_FREEZE_BAR_ONLY = ("mid", "spread_pct")  # a selection's quote on its freeze bar, not the fill's


def _entry_values(selection: Selection, selected_at: datetime,
                  e_t1_spread: float | None) -> dict[str, AuditValue]:  # fmt: skip
    """An entry row's notes and audit (PO, DEC-34): the selection's values from the bar it froze
    on (DEC-21), without that bar's mid and spread, which the fill's own Limit and the E-T1 spread
    on the decision bar replace."""
    values: dict[str, AuditValue] = {
        k: v for k, v in selection.values.items() if k not in _FREEZE_BAR_ONLY
    }
    values["selected_at"] = selected_at.isoformat()
    values["e_t1_spread"] = None if e_t1_spread is None else round(e_t1_spread, 6)
    return values


def _notes(values: Values, re_entry: RuleId | None = None) -> str:
    text = ", ".join(f"{k} {v}" for k, v in values.items() if v is not None)
    return f"re-entry after {re_entry}; {text}" if re_entry is not None else text
