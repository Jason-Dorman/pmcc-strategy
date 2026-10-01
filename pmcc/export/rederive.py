"""The runtime invariants, re-derived from a full result's rows alone (DEC-51, ARCHITECTURE §12).

`pmcc verify` runs in CI, which has neither the cache nor the engine's state, so each check here
works only from the blotter, ledger, gate log, config and starting cash a result file carries. The
arithmetic is this module's own, not the engine's: a bug in the fill model or the book can't hide
from a check that reuses it. Every amount is compared in integer $0.0001 units (DEC-44).

The blotter is walked once, holding each instrument's position row by row, so a row is judged by
what it does (opens a long, opens a short), never by the rule ID it carries (DEC-96).

- **positions:** after each bar's rows, the ledger holds exactly the long, short and stock the rows
  booked; a deleted, duplicated, resized or moved row can't hide.
- **INV-01:** each row's Cash Δ follows from its fill, quantity and fee, and cash walks from the
  starting cash bar by bar, moving by exactly the rows booked on that bar.
- **INV-02:** NAV = cash + long MV − short call MV + stock MV on every bar.
- **INV-03:** every BUY and SELL had a valid BID/ASK (from its audit), its Limit is that quote's mid
  and its Fill is mid ± capture × half-spread. Only X-S5's stock sale is exempt, and it must be at
  the strike of the call assigned on the same bar, for its shares.
- **INV-05, INV-10:** every bar's short is covered by its long (strike, expiry) in equal quantity.
- **INV-06:** every row that opens a short is an E-S1 sale that satisfied E-S5 against the long's
  entry fill.
- **INV-07:** no bar holds a short after its expiry session.
- **INV-08:** every row that opens a leg is its entry rule's (E-L1, E-S1), and its audit records
  available funds ≥ 0 after it; with no stock held at that moment, the amount must follow from
  cash and the short's value.
- **INV-09:** every blotter, gate-log and gate row carries a rule ID the config defines.

A row missing a value its check needs (an option without a strike) is itself a finding, never a
crash.
"""

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from typing import final

from pmcc.domain.clock import to_et
from pmcc.export.models import BlotterRow, LedgerRowOut, LegOut, RunResult

OPTION_MULTIPLIER = 100  # shares per contract
LONG_ENTRY, SHORT_ENTRY, ASSIGNMENT = "E-L1", "E-S1", "X-S5"
_SIGN = {"BUY": 1, "SELL": -1, "EXPIRE": 1, "ASSIGN": 1}


@final
@dataclass(frozen=True, slots=True)
class Finding:
    invariant: str  # the check: an invariant ("INV-01") or "positions" / "rows"
    message: str


class _MissingValueError(ValueError):
    """A row lacks a value a check needs; reported as a finding."""


@final
@dataclass(frozen=True, slots=True)
class _Booked:
    """A blotter row with what it did: the leg it opened, and the positions just before it."""

    row: BlotterRow
    opens: str | None  # "long" or "short" when it opens an option leg
    before: Mapping[str, int]  # RIC → signed quantity (contracts; shares for the stock)


@final
@dataclass(frozen=True, slots=True)
class _Rows:
    """A full result's rows, as the checks read them."""

    result: RunResult
    blotter: tuple[BlotterRow, ...]
    ledger: tuple[LedgerRowOut, ...]
    booked: tuple[_Booked, ...]
    stock: frozenset[str]  # the RICs the blotter trades as stock


def rederive(result: RunResult) -> list[Finding]:
    """Every invariant a full result breaks; empty when it holds them all. A summary result has
    no rows to re-derive from."""
    if result.blotter is None or result.ledger is None or result.gate_log is None:
        return []
    stock = frozenset(r.instrument.ric for r in result.blotter if r.instrument.kind == "stock")
    rows = _Rows(result, result.blotter, result.ledger, _walk(result.blotter), stock)
    findings: list[Finding] = []
    for check in _CHECKS:
        try:
            findings += check(rows)
        except _MissingValueError as e:
            findings.append(Finding("rows", f"{check.__name__.strip('_')}: {e}"))
    return findings


def _walk(blotter: Iterable[BlotterRow]) -> tuple[_Booked, ...]:
    held: dict[str, int] = {}
    booked: list[_Booked] = []
    for row in blotter:
        ric = row.instrument.ric
        before = held.get(ric, 0)
        booked.append(_Booked(row, _opens(row, before), dict(held)))
        held[ric] = before + _SIGN.get(row.side, 0) * row.qty
        if held[ric] == 0:
            del held[ric]
    return tuple(booked)


def _opens(row: BlotterRow, before: int) -> str | None:
    if row.instrument.kind == "stock":
        return None
    if row.side == "BUY" and before >= 0:
        return "long"
    if row.side == "SELL" and before <= 0:
        return "short"
    return None


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


def _need[T](value: T | None, what: str) -> T:
    if value is None:
        raise _MissingValueError(f"a row has no {what}")
    return value


# ---- positions ----------------------------------------------------------------------------------


def _positions(rows: _Rows) -> Iterator[Finding]:
    """The ledger's legs and stock, bar by bar, against the positions the rows booked."""
    held: dict[str, int] = {}
    booked = iter(rows.blotter)
    row = next(booked, None)
    for bar in rows.ledger:
        while row is not None and row.time <= bar.time:
            held[row.instrument.ric] = held.get(row.instrument.ric, 0) + (
                _SIGN.get(row.side, 0) * row.qty)  # fmt: skip
            row = next(booked, None)
        if _ledger_holds(bar) != {ric: q for ric, q in held.items() if q}:
            yield Finding("positions", f"the ledger at {bar.time.isoformat()} holds "
                                       f"{_ledger_holds(bar)}, the rows booked "
                                       f"{ {r: q for r, q in held.items() if q} }")  # fmt: skip


def _ledger_holds(bar: LedgerRowOut) -> dict[str, int]:
    holds: dict[str, int] = {}
    if bar.long is not None:
        holds[bar.long.instrument.ric] = holds.get(bar.long.instrument.ric, 0) + bar.long.qty
    if bar.short is not None:
        holds[bar.short.instrument.ric] = holds.get(bar.short.instrument.ric, 0) - bar.short.qty
    if bar.stock is not None:
        holds[bar.stock.instrument.ric] = bar.stock.shares
    return {ric: q for ric, q in holds.items() if q}


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
        if row.side not in ("BUY", "SELL"):
            continue
        problem = (_assignment_problem(row, rows.blotter) if row.audit.get("assignment")
                   else _fill_problem(row, capture))  # fmt: skip
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


def _assignment_problem(row: BlotterRow, blotter: tuple[BlotterRow, ...]) -> str:
    """The one sale not at a quote: X-S5's short stock, at the strike of the call assigned on the
    same bar, 100 shares a contract."""
    assigned = [
        r
        for r in blotter  # the call assigned on this bar
        if r.side == "ASSIGN" and r.rule_id == ASSIGNMENT and r.time == row.time
    ]
    is_sale = row.side == "SELL" and row.rule_id == ASSIGNMENT and row.instrument.kind == "stock"
    if not is_sale or len(assigned) != 1:
        return "claims the assignment exemption but isn't X-S5's stock sale on an assignment"
    call = assigned[0]
    if row.fill != call.instrument.strike or row.qty != call.qty * OPTION_MULTIPLIER:
        return (
            f"sold {row.qty} shares at {row.fill}, not {call.qty * OPTION_MULTIPLIER} at "
            f"the assigned strike {call.instrument.strike}"
        )
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
        strike_ok = _need(long_i.strike, "strike") <= _need(short_i.strike, "strike")
        if not (strike_ok and _need(long_i.expiry, "expiry") >= _need(short_i.expiry, "expiry")):
            yield Finding("INV-05", f"short {short_i.ric} at {when} isn't covered by long "
                                    f"{long_i.ric}")  # fmt: skip
        if long.qty != short.qty:
            yield Finding("INV-10", f"at {when} the short is {short.qty}, the long {long.qty}")


def _expired(rows: _Rows) -> Iterator[Finding]:
    for bar in rows.ledger:
        short = bar.short
        if short is not None and to_et(bar.time).date() > _need(short.instrument.expiry, "expiry"):
            yield Finding("INV-07", f"short {short.instrument.ric} is open at "
                                    f"{bar.time.isoformat()}, after its expiry")  # fmt: skip


# ---- INV-06 -------------------------------------------------------------------------------------


def _e_s5(rows: _Rows) -> Iterator[Finding]:
    by_time = {bar.time: bar for bar in rows.ledger}
    for i, booked in enumerate(rows.booked):
        if booked.opens != "short":
            continue
        row = booked.row
        bar = by_time.get(row.time)
        long = None if bar is None else bar.long
        entry = None if long is None else _long_entry(rows.booked[:i], long.instrument.ric)
        if row.rule_id != SHORT_ENTRY or row.audit.get("e_s5_satisfied") is not True:
            yield Finding("INV-06", f"{_label(row)}: opens a short without an E-S1 sale that "
                                    "satisfied E-S5")  # fmt: skip
            continue
        if long is None or entry is None:
            yield Finding("INV-06", f"{_label(row)}: no long entry it satisfied E-S5 against")
            continue
        gap = _need(row.instrument.strike, "strike") - _need(long.instrument.strike, "strike")
        debit = _need(entry.fill, "fill") - _need(row.limit, "limit")
        recorded = (row.audit.get("e_s5_strike_gap"), row.audit.get("e_s5_net_debit"))
        if not gap > debit or tuple(map(_amount, recorded)) != (gap, debit):
            yield Finding("INV-06", f"{_label(row)}: strike gap {gap} against net debit {debit} "
                                    f"(recorded {recorded[0]}, {recorded[1]})")  # fmt: skip


def _long_entry(before: Iterable[_Booked], ric: str) -> BlotterRow | None:
    """The row that opened the long `ric` most recently."""
    return next((b.row for b in reversed(tuple(before))
                 if b.opens == "long" and b.row.instrument.ric == ric), None)  # fmt: skip


def _amount(text: object) -> Decimal | None:
    """An audit's dollar string ("45.0000") as a number; compared by value, not by spelling."""
    try:
        return Decimal(text) if isinstance(text, str) else None
    except ArithmeticError:
        return None


# ---- INV-08 -------------------------------------------------------------------------------------


def _funds(rows: _Rows) -> Iterator[Finding]:
    """Available funds = NAV − IM, which with no stock held is cash − short call MV (the long's
    requirement is its whole value). The entry's own leg is marked at its Limit, as the engine's
    check marks it; a short held before a long entry at its last bar's mark."""
    cash, previous = units(rows.result.starting_cash), None
    bars = iter(rows.ledger)
    bar = next(bars, None)
    for booked in rows.booked:
        row = booked.row
        while bar is not None and bar.time < row.time:
            cash, previous, bar = units(bar.cash), bar, next(bars, None)
        cash += units(row.cash_delta)
        if booked.opens is not None:
            stock_held = any(booked.before.get(ric) for ric in rows.stock)
            problem = _funds_problem(booked, cash, previous, stock_held)
            if problem:
                yield Finding("INV-08", f"{_label(row)}: {problem}")


def _funds_problem(booked: _Booked, cash: int, previous: LedgerRowOut | None,
                   stock_held: bool) -> str:  # fmt: skip
    row = booked.row
    entry_rule = LONG_ENTRY if booked.opens == "long" else SHORT_ENTRY
    if row.rule_id != entry_rule:
        return f"opens a {booked.opens} leg under {row.rule_id}, not {entry_rule}"
    funds = row.audit.get("funds_after")
    if type(funds) is not int or funds < 0:
        return f"available funds after it were {funds!r}"
    if stock_held:
        return ""  # stock held: the audit's figure is all there is to check
    short = (units(_need(row.limit, "limit")) * OPTION_MULTIPLIER * row.qty
             if booked.opens == "short"
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
    _positions, _row_cash, _cash_walk, _nav, _fills, _covered, _e_s5, _expired, _funds, _rule_ids,
)  # fmt: skip
