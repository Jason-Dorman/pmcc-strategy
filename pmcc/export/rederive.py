"""The runtime invariants, re-derived from a full result's rows alone (DEC-51, ARCHITECTURE §12).

`pmcc verify` runs in CI, which has neither the cache nor the engine's state, so each check here
works only from the blotter, ledger, gate log, config and starting cash a result file carries. The
arithmetic is this module's own, not the engine's: a bug in the fill model or the book can't hide
from a check that reuses it. Every amount is compared in integer $0.0001 units (DEC-44).

- **INV-01:** each row's Cash Δ follows from its fill, quantity and fee, and cash walks from the
  starting cash bar by bar, moving by exactly the rows booked on that bar.
- **INV-02:** NAV = cash + long MV − short call MV + stock MV on every bar.
- **INV-03:** every BUY and SELL had a valid BID/ASK (from its audit), its Limit is that quote's mid
  and its Fill is mid ± capture × half-spread; X-S5's stock sale at the strike is exempt.
- **INV-05, INV-10:** every bar's short is covered by its long (strike, expiry) in equal quantity.
- **INV-06:** every short entry satisfied E-S5 against the long's entry fill.
- **INV-07:** no bar holds a short after its expiry session.
- **INV-08:** every entry's audit records available funds ≥ 0 after it, and, where no stock is held,
  the amount follows from cash and the short's value.
- **INV-09:** every blotter, gate-log and gate row carries a rule ID the config defines.
"""

from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from typing import final

from pmcc.domain.clock import to_et
from pmcc.export.models import BlotterRow, LedgerRowOut, LegOut, RunResult

OPTION_MULTIPLIER = 100  # shares per contract
LONG_ENTRY, SHORT_ENTRY = "E-L1", "E-S1"


@final
@dataclass(frozen=True, slots=True)
class Finding:
    invariant: str
    message: str


@final
@dataclass(frozen=True, slots=True)
class _Rows:
    """A full result's rows, as the checks read them."""

    result: RunResult
    blotter: tuple[BlotterRow, ...]
    ledger: tuple[LedgerRowOut, ...]


def rederive(result: RunResult) -> list[Finding]:
    """Every invariant a full result breaks; empty when it holds them all. A summary result has
    no rows to re-derive from."""
    if result.blotter is None or result.ledger is None or result.gate_log is None:
        return []
    rows = _Rows(result, result.blotter, result.ledger)
    return [finding for check in _CHECKS for finding in check(rows)]


def units(amount: Decimal) -> int:
    """Dollars as $0.0001 units; the models hold only whole units."""
    return int(amount.scaleb(4))


def _dollars(amount: int) -> Decimal:
    return Decimal(amount).scaleb(-4)


def _leg_mv(leg: LegOut | None) -> int:
    return 0 if leg is None else units(leg.mark) * OPTION_MULTIPLIER * leg.qty


def _multiplier(row: BlotterRow) -> int:
    return 1 if row.instrument.kind == "stock" else OPTION_MULTIPLIER


def _label(row: BlotterRow) -> str:
    return f"{row.side} {row.instrument.ric} at {row.time.isoformat()} ({row.rule_id})"


# ---- INV-01 -------------------------------------------------------------------------------------


def _row_cash(rows: _Rows) -> Iterator[Finding]:
    for row in rows.blotter:
        expected = _expected_cash(row)
        if expected is None or units(row.cash_delta) != expected:
            yield Finding("INV-01", f"{_label(row)}: Cash Δ {row.cash_delta} doesn't follow "
                                    "from its fill, quantity and fee")  # fmt: skip


def _expected_cash(row: BlotterRow) -> int | None:
    if row.side in ("EXPIRE", "ASSIGN"):
        return 0 if units(row.fee) == 0 else None
    if row.side not in ("BUY", "SELL") or row.fill is None:
        return None
    notional = units(row.fill) * _multiplier(row) * row.qty
    return (-notional if row.side == "BUY" else notional) - units(row.fee)


def _cash_walk(rows: _Rows) -> Iterator[Finding]:
    moved: dict[datetime, int] = {}
    for row in rows.blotter:
        moved[row.time] = moved.get(row.time, 0) + units(row.cash_delta)
    bars = {bar.time for bar in rows.ledger}
    for time in sorted(t for t in moved if t not in bars):
        yield Finding("INV-01", f"rows booked at {time.isoformat()} have no ledger bar")
    cash = units(rows.result.starting_cash)
    for bar in rows.ledger:
        expected = cash + moved.get(bar.time, 0)
        if units(bar.cash) != expected:
            yield Finding("INV-01", f"cash at {bar.time.isoformat()} is {bar.cash}, but the "
                                    f"rows booked move it to {_dollars(expected)}")  # fmt: skip
        cash = units(bar.cash)


# ---- INV-02 -------------------------------------------------------------------------------------


def _nav(rows: _Rows) -> Iterator[Finding]:
    for bar in rows.ledger:
        stock = 0 if bar.stock is None else bar.stock.shares * units(bar.stock.mark)
        expected = units(bar.cash) + _leg_mv(bar.long) - _leg_mv(bar.short) + stock
        if units(bar.nav) != expected:
            yield Finding("INV-02", f"NAV at {bar.time.isoformat()} is {bar.nav}, not cash + "
                                    f"long − short + stock = {_dollars(expected)}")  # fmt: skip


# ---- INV-03 -------------------------------------------------------------------------------------


def _fills(rows: _Rows) -> Iterator[Finding]:
    capture = rows.result.config.strategy.fill_model.spread_capture
    for row in rows.blotter:
        if row.side in ("BUY", "SELL") and not row.audit.get("assignment"):
            problem = _fill_problem(row, capture)
            if problem:
                yield Finding("INV-03", f"{_label(row)}: {problem}")


def _fill_problem(row: BlotterRow, capture: float) -> str:
    bid, ask = row.audit.get("bid"), row.audit.get("ask")
    if type(bid) is not int or type(ask) is not int or not 0 < bid <= ask:
        return f"no valid BID/ASK in its audit (bid {bid!r}, ask {ask!r})"
    if row.audit.get("spread_capture") != capture:
        return f"filled at spread_capture {row.audit.get('spread_capture')}, not the config's"
    mid, half = Fraction(bid + ask, 2), Fraction(ask - bid, 2)
    share = Fraction(float.__repr__(capture))
    fill = round(mid + share * half if row.side == "BUY" else mid - share * half)
    if row.limit is None or units(row.limit) != round(mid):
        return f"Limit {row.limit} isn't the quote's mid"
    if row.fill is None or units(row.fill) != fill:
        return f"Fill {row.fill} isn't mid ± {capture} × half-spread"
    return ""


# ---- INV-05, INV-10, INV-07 ---------------------------------------------------------------------


def _covered(rows: _Rows) -> Iterator[Finding]:
    for bar in rows.ledger:
        long, short = bar.long, bar.short
        if short is None:
            continue
        when = bar.time.isoformat()
        if long is None:
            yield Finding("INV-05", f"a short is open at {when} with no long")
            continue
        long_i, short_i = long.instrument, short.instrument
        if not (_strike(long_i.strike) <= _strike(short_i.strike)
                and _day(long_i.expiry) >= _day(short_i.expiry)):  # fmt: skip
            yield Finding("INV-05", f"short {short_i.ric} at {when} isn't covered by long "
                                    f"{long_i.ric}")  # fmt: skip
        if long.qty != short.qty:
            yield Finding("INV-10", f"at {when} the short is {short.qty}, the long {long.qty}")


def _strike(strike: Decimal | None) -> Decimal:
    if strike is None:
        raise ValueError("an option row has no strike")
    return strike


def _day[T](value: T | None) -> T:
    if value is None:
        raise ValueError("an option row has no expiry")
    return value


def _expired(rows: _Rows) -> Iterator[Finding]:
    for bar in rows.ledger:
        short = bar.short
        if short is not None and to_et(bar.time).date() > _day(short.instrument.expiry):
            yield Finding("INV-07", f"short {short.instrument.ric} is open at "
                                    f"{bar.time.isoformat()}, after its expiry")  # fmt: skip


# ---- INV-06 -------------------------------------------------------------------------------------


def _e_s5(rows: _Rows) -> Iterator[Finding]:
    by_time = {bar.time: bar for bar in rows.ledger}
    for i, row in enumerate(rows.blotter):
        if row.rule_id != SHORT_ENTRY or row.side != "SELL":
            continue
        bar = by_time.get(row.time)
        long = None if bar is None else bar.long
        entry = None if long is None else _long_entry(rows.blotter[:i], long.instrument.ric)
        if row.audit.get("e_s5_satisfied") is not True or long is None or entry is None:
            yield Finding("INV-06", f"{_label(row)}: no long entry it satisfied E-S5 against")
            continue
        gap = _strike(row.instrument.strike) - _strike(long.instrument.strike)
        debit = _need(entry.fill) - _need(row.limit)
        recorded = (row.audit.get("e_s5_strike_gap"), row.audit.get("e_s5_net_debit"))
        if not gap > debit or tuple(map(_amount, recorded)) != (gap, debit):
            yield Finding("INV-06", f"{_label(row)}: strike gap {gap} against net debit {debit} "
                                    f"(recorded {recorded[0]}, {recorded[1]})")  # fmt: skip


def _long_entry(before: Sequence[BlotterRow], ric: str) -> BlotterRow | None:
    return next((r for r in reversed(before)
                 if r.rule_id == LONG_ENTRY and r.side == "BUY" and r.instrument.ric == ric),
                None)  # fmt: skip


def _amount(text: object) -> Decimal | None:
    """An audit's dollar string ("45.0000") as a number; compared by value, not by spelling."""
    try:
        return Decimal(text) if isinstance(text, str) else None
    except ArithmeticError:
        return None


def _need(price: Decimal | None) -> Decimal:
    if price is None:
        raise ValueError("an entry row has no price")
    return price


# ---- INV-08 -------------------------------------------------------------------------------------


def _funds(rows: _Rows) -> Iterator[Finding]:
    """Available funds = NAV − IM, which with no stock held is cash − short call MV (the long's
    requirement is its whole value). The entry's own leg is marked at its Limit, as the engine's
    check marks it."""
    cash, previous = units(rows.result.starting_cash), None
    bars = iter(rows.ledger)
    bar = next(bars, None)
    for row in rows.blotter:
        while bar is not None and bar.time < row.time:
            cash, previous, bar = units(bar.cash), bar, next(bars, None)
        cash += units(row.cash_delta)
        if row.rule_id in (LONG_ENTRY, SHORT_ENTRY) and row.side in ("BUY", "SELL"):
            problem = _funds_problem(row, cash, previous, bar)
            if problem:
                yield Finding("INV-08", f"{_label(row)}: {problem}")


def _funds_problem(row: BlotterRow, cash: int, previous: LedgerRowOut | None,
                   bar: LedgerRowOut | None) -> str:  # fmt: skip
    funds = row.audit.get("funds_after")
    if type(funds) is not int or funds < 0:
        return f"available funds after it were {funds!r}"
    if any(b is not None and b.stock is not None for b in (previous, bar)):
        return ""  # stock held: the audit's figure is all there is to check
    short = (units(_need(row.limit)) * OPTION_MULTIPLIER * row.qty if row.rule_id == SHORT_ENTRY
             else _leg_mv(None if previous is None else previous.short))  # fmt: skip
    if funds != cash - short:
        return f"funds_after {funds} isn't cash − short call MV = {cash - short}"
    return ""


# ---- INV-09 -------------------------------------------------------------------------------------


def _rule_ids(rows: _Rows) -> Iterator[Finding]:
    result = rows.result
    defined = {str(r.id) for r in result.config.strategy.rules}
    stamped: Iterable[tuple[str, str]] = (
        *((r.rule_id, _label(r)) for r in rows.blotter),
        *((w.outcome.rule_id, f"the gate-log row of {w.session}") for w in result.gate_log or ()),
        *((g.rule_id, f"a gate of {w.session}") for w in result.gate_log or () for g in w.gates),
    )
    for rule_id, where in stamped:
        if rule_id not in defined:
            yield Finding("INV-09", f"{where} carries {rule_id}, which the config doesn't define")


_CHECKS: tuple[Callable[[_Rows], Iterable[Finding]], ...] = (
    _row_cash, _cash_walk, _nav, _fills, _covered, _e_s5, _expired, _funds, _rule_ids,
)  # fmt: skip
