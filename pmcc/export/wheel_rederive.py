"""The wheel's invariants, re-derived from a result's rows alone (Spec › Invariants; W2-03).

`pmcc verify` has neither the cache nor the engine, so each check works only from the blotter,
ledger, gate log, config and starting cash a wheel result carries. The arithmetic is this module's
own, apart from two row-level checks shared with the PMCC's re-derivation (`rederive`): a row's
Cash Δ from its fill, and a fill from its quote. Every amount is in integer $0.0001 units.

- **positions:** after each bar's rows, the ledger holds exactly the put, call and shares the
  rows booked.
- **WINV-01:** each row's Cash Δ follows from its fill, quantity and fee, and cash walks from the
  starting cash bar by bar, moving by exactly the rows booked on that bar.
- **WINV-02:** NAV = cash + shares × stock mark − put MV − call MV on every bar.
- **WINV-03:** every BUY and SELL had a valid BID/ASK and fills at mid ± capture × half-spread,
  except an assignment's shares: bought (put) or sold (call) at the strike of the option assigned
  on the same bar, 100 a contract.
- **WINV-05:** while a put is open, the cash reserved is its strike × 100 × contracts, cash covers
  it, and free cash is the rest; with no put, nothing is reserved.
- **WINV-06:** while a call is open, shares ≥ 100 × contracts.
- **WINV-07:** each bar's state is what it holds: cash alone, a put, shares, or shares and a call.
- **WINV-08:** no bar holds an option after its expiry session.
- **WINV-09:** every blotter and gate-log row carries a rule ID the config defines.

WINV-04 (no look-ahead) is structural, `MarketView`'s; WINV-10 (byte-identical re-runs) is a test.

The reported numbers are checked the same way (W3-01): each row's Trade P&L follows from the rows
(WD-28); the S&P 500's return from its two closes; each thesis claim compares the summary's own
numbers, and its verdict follows from them (WD-29). `baseline_findings` compares the baseline
PMCC's figures with that run's result file, which `pmcc verify` reads from beside the wheel's.
"""

from collections.abc import Callable, Iterable, Iterator
from datetime import datetime
from decimal import Decimal

from pmcc.domain.clock import to_et
from pmcc.export.canonical import FLOAT_PLACES
from pmcc.export.models import BlotterRow, LegOut, RunResult
from pmcc.export.rederive import Finding, expected_row_cash, fill_problem, units
from pmcc.export.wheel_models import WheelLedgerRowOut, WheelResult

OPTION_MULTIPLIER = 100  # shares per contract
STOCK = "stock"  # the key the shares are held under: the ledger names no stock RIC
_SIGN = {"BUY": 1, "SELL": -1, "EXPIRE": 1, "ASSIGN": 1}
_ASSIGNED_SHARES = {"put": "BUY", "call": "SELL"}  # what an assignment does with the shares


def rederive_wheel(result: WheelResult) -> list[Finding]:
    """Every invariant `result` breaks; empty when it holds them all."""
    findings: list[Finding] = []
    for check in _CHECKS:
        findings += check(result)
    return findings


def _key(row: BlotterRow) -> str:
    return STOCK if row.instrument.kind == "stock" else row.instrument.ric


def _label(row: BlotterRow) -> str:
    return f"{row.side} {row.instrument.ric} at {row.time.isoformat()} ({row.rule_id})"


def _dollars(amount: int) -> Decimal:
    return Decimal(amount).scaleb(-4)


def _mv(leg: LegOut | None) -> int:
    return 0 if leg is None else units(leg.mark) * OPTION_MULTIPLIER * leg.qty


def _secured(leg: LegOut | None) -> int | None:
    """The cash a put secures, or None if its row has no strike."""
    if leg is None:
        return 0
    strike = leg.instrument.strike
    return None if strike is None else units(strike) * OPTION_MULTIPLIER * leg.qty


# ---- positions ----------------------------------------------------------------------------------


def _positions(result: WheelResult) -> Iterator[Finding]:
    held: dict[str, int] = {}
    booked = iter(result.blotter)
    row = next(booked, None)
    for bar in result.ledger:
        while row is not None and row.time <= bar.time:
            held[_key(row)] = held.get(_key(row), 0) + _SIGN.get(row.side, 0) * row.qty
            row = next(booked, None)
        rows = {k: q for k, q in held.items() if q}
        if _ledger_holds(bar) != rows:
            yield Finding("positions", f"the ledger at {bar.time.isoformat()} holds "
                                       f"{_ledger_holds(bar)}, the rows booked {rows}")  # fmt: skip


def _ledger_holds(bar: WheelLedgerRowOut) -> dict[str, int]:
    holds = {leg.instrument.ric: -leg.qty for leg in (bar.put, bar.call) if leg is not None}
    if bar.shares:
        holds[STOCK] = bar.shares
    return holds


# ---- WINV-01 ------------------------------------------------------------------------------------


def _row_cash(result: WheelResult) -> Iterator[Finding]:
    for row in result.blotter:
        expected = expected_row_cash(row)
        if expected is None or units(row.cash_delta) != expected:
            yield Finding("WINV-01", f"{_label(row)}: Cash Δ {row.cash_delta} doesn't follow "
                                     "from its fill, quantity and fee")  # fmt: skip


def _cash_walk(result: WheelResult) -> Iterator[Finding]:
    moved: dict[datetime, int] = {}
    for row in result.blotter:
        moved[row.time] = moved.get(row.time, 0) + units(row.cash_delta)
    bars = {bar.time for bar in result.ledger}
    for time in sorted(t for t in moved if t not in bars):
        yield Finding("WINV-01", f"rows booked at {time.isoformat()} have no ledger bar")
    cash = units(result.starting_cash)
    for bar in result.ledger:
        expected = cash + moved.get(bar.time, 0)
        if units(bar.cash) != expected:
            yield Finding("WINV-01", f"cash at {bar.time.isoformat()} is {bar.cash}, but the "
                                     f"rows booked move it to {_dollars(expected)}")  # fmt: skip
        cash = units(bar.cash)


# ---- WINV-02 ------------------------------------------------------------------------------------


def _nav(result: WheelResult) -> Iterator[Finding]:
    for bar in result.ledger:
        mark = bar.stock_mark
        if bar.shares and mark is None:
            yield Finding("WINV-02", f"{bar.shares} shares at {bar.time.isoformat()} have no mark")
            continue
        stock = 0 if mark is None else bar.shares * units(mark)
        expected = units(bar.cash) + stock - _mv(bar.put) - _mv(bar.call)
        if units(bar.nav) != expected:
            yield Finding("WINV-02", f"NAV at {bar.time.isoformat()} is {bar.nav}, not cash + "
                                     f"shares − put − call = {_dollars(expected)}")  # fmt: skip


# ---- WINV-03 ------------------------------------------------------------------------------------


def _fills(result: WheelResult) -> Iterator[Finding]:
    capture = result.config.wheel.fill_model.spread_capture
    for row in result.blotter:
        if row.side not in ("BUY", "SELL"):
            continue
        problem = (_assignment_problem(row, result.blotter) if row.audit.get("assignment")
                   else fill_problem(row, capture))  # fmt: skip
        if problem:
            yield Finding("WINV-03", f"{_label(row)}: {problem}")


def _assignment_problem(row: BlotterRow, blotter: Iterable[BlotterRow]) -> str:
    """Shares bought or sold at the strike of the one option assigned on the same bar."""
    assigned = [r for r in blotter if r.side == "ASSIGN" and r.time == row.time]
    if row.instrument.kind != "stock" or len(assigned) != 1:
        return "claims the assignment exemption but isn't the shares of one assignment"
    option = assigned[0]
    side = _ASSIGNED_SHARES.get(option.instrument.kind)
    shares = option.qty * OPTION_MULTIPLIER
    if row.side != side or row.fill != option.instrument.strike or row.qty != shares:
        return (f"{row.side} {row.qty} shares at {row.fill}, not {side} {shares} at the "
                f"assigned strike {option.instrument.strike}")  # fmt: skip
    return ""


# ---- WINV-05 to WINV-08 -------------------------------------------------------------------------


def _secured_puts(result: WheelResult) -> Iterator[Finding]:
    for bar in result.ledger:
        secured, when = _secured(bar.put), bar.time.isoformat()
        if secured is None:
            yield Finding("WINV-05", f"the put at {when} has no strike")
            continue
        if units(bar.reserved) != secured or units(bar.free_cash) != units(bar.cash) - secured:
            yield Finding("WINV-05", f"at {when} {bar.reserved} is reserved and {bar.free_cash} "
                                     f"free, but the put secures {_dollars(secured)}")  # fmt: skip
        if units(bar.cash) < secured:
            yield Finding("WINV-05", f"cash {bar.cash} at {when} doesn't secure the put's "
                                     f"{_dollars(secured)}")  # fmt: skip


def _covered_calls(result: WheelResult) -> Iterator[Finding]:
    for bar in result.ledger:
        call = bar.call
        if call is not None and bar.shares < call.qty * OPTION_MULTIPLIER:
            yield Finding("WINV-06", f"call x{call.qty} at {bar.time.isoformat()} isn't covered "
                                     f"by {bar.shares} shares")  # fmt: skip


def _states(result: WheelResult) -> Iterator[Finding]:
    for bar in result.ledger:
        holds = (bar.put is not None, bar.call is not None, bar.shares > 0)
        expected = _STATES.get(holds)
        if bar.state != expected:
            yield Finding("WINV-07", f"at {bar.time.isoformat()} the state is {bar.state}, "
                                     f"holding put/call/shares {holds}")  # fmt: skip


_STATES = {(False, False, False): "cash", (True, False, False): "put",
           (False, False, True): "shares", (False, True, True): "call"}  # fmt: skip
"""(put, call, shares held) → the one state that holds them; any other mix is no state."""


def _expired(result: WheelResult) -> Iterator[Finding]:
    for bar in result.ledger:
        day = to_et(bar.time).date()
        for leg in (bar.put, bar.call):
            expiry = None if leg is None else leg.instrument.expiry
            if leg is not None and (expiry is None or day > expiry):
                yield Finding("WINV-08", f"{leg.instrument.ric} is open at "
                                         f"{bar.time.isoformat()}, after its expiry")  # fmt: skip


# ---- WINV-09 ------------------------------------------------------------------------------------


def _rule_ids(result: WheelResult) -> Iterator[Finding]:
    defined = {str(r.id) for r in result.config.wheel.rules}
    stamped = (*((r.rule_id, _label(r)) for r in result.blotter),
               *((w.outcome.rule_id, f"the gate-log row of {w.session}")
                 for w in result.gate_log))  # fmt: skip
    for rule_id, where in stamped:
        if rule_id not in defined:
            yield Finding("WINV-09", f"{where} carries {rule_id}, which the config doesn't define")


# ---- the reported numbers (W3-01) ---------------------------------------------------------------


def _trade_pnl(result: WheelResult) -> Iterator[Finding]:
    """Each row's Trade P&L (WD-28): on the row that closes a position, the Cash Δ of every row
    since it opened; null on the others."""
    held: dict[str, int] = {}
    cash: dict[str, int] = {}
    for row in result.blotter:
        key = _key(row)
        held[key] = held.get(key, 0) + _SIGN.get(row.side, 0) * row.qty
        cash[key] = cash.get(key, 0) + units(row.cash_delta)
        expected = None if held[key] else cash.pop(key)
        if not held[key]:
            del held[key]
        recorded = None if row.trade_pnl is None else units(row.trade_pnl)
        if recorded != expected:
            shown = None if expected is None else _dollars(expected)
            yield Finding("trade_pnl", f"{_label(row)}: Trade P&L {row.trade_pnl}, not {shown}")


def _sp500(result: WheelResult) -> Iterator[Finding]:
    index = result.summary.benchmarks.sp500
    expected = round(float(index.end_close / index.start_close - 1), FLOAT_PLACES)
    if index.price_return != expected:
        yield Finding("benchmarks", f"the S&P 500's return is {index.price_return}, but its "
                                    f"closes give {expected}")  # fmt: skip


def _thesis(result: WheelResult) -> Iterator[Finding]:
    """Each claim's numbers are the summary's, and its verdict follows from them (WD-29)."""
    summary = result.summary
    metrics, benchmarks = summary.metrics, summary.benchmarks
    expected = [
        (1, float(metrics.pnl), 0.0),
        (2, metrics.sharpe_annualized, benchmarks.baseline_pmcc.sharpe_annualized),
        (3, metrics.return_on_starting_cash, benchmarks.sp500.price_return),
    ]
    recorded = [(v.claim, v.wheel, v.benchmark) for v in summary.thesis]
    if recorded != expected:
        yield Finding("thesis", f"the claims compare {recorded}, not the summary's {expected}")
    for v in summary.thesis:
        met = v.wheel is not None and v.benchmark is not None and v.wheel > v.benchmark
        if v.met != met:
            yield Finding("thesis", f"claim {v.claim} is marked met={v.met}: {v.wheel} against "
                                    f"{v.benchmark}")  # fmt: skip


def baseline_findings(result: WheelResult, baseline: RunResult | None) -> list[Finding]:
    """The baseline PMCC's numbers in `result` against its own result file beside it."""
    if baseline is None:
        return [Finding("benchmarks", "the baseline PMCC it compares with isn't beside it")]
    mine, metrics = result.summary.benchmarks.baseline_pmcc, baseline.summary.metrics
    recorded = (mine.run_id, mine.config_hash, mine.starting_cash, mine.return_on_starting_cash,
                mine.sharpe_annualized, mine.max_drawdown_pct)  # fmt: skip
    theirs = None
    if metrics is not None:
        run = (baseline.manifest.run_id, baseline.manifest.config_hash, baseline.starting_cash)
        theirs = (*run, metrics.return_on_starting_nav, metrics.sharpe_annualized,
                  metrics.max_drawdown_pct)  # fmt: skip
    if recorded != theirs:
        return [Finding("benchmarks", f"its baseline PMCC figures {recorded} aren't the "
                                      f"result's beside it, {theirs}")]  # fmt: skip
    return []


_CHECKS: tuple[Callable[[WheelResult], Iterable[Finding]], ...] = (
    _positions, _row_cash, _cash_walk, _nav, _fills, _secured_puts, _covered_calls, _states,
    _expired, _rule_ids, _trade_pnl, _sp500, _thesis,
)  # fmt: skip
