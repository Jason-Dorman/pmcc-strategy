"""Calibrating the starting cash (`pmcc calibrate`; Spec › E-L4; P3-09, DEC-30).

Two passes over the same prepared markets (PO, DEC-30):

1. **Measure.** Each symbol runs under each config with `CALIBRATION_CASH`, enough that E-L4 never
   blocks; the run's first long-leg entry (E-L1) gives its cost, fill × 100 × qty + fees. Nothing
   from this pass is kept but those entries, and its cash is never a run's starting cash.
2. **Verify.** Each symbol's value is E-L4's `cash_multiple` × that symbol's most expensive cost,
   rounded up to its `cash_round_to` (`starting_cash_for`; 2× and $5,000; per symbol, PO,
   2026-10-05). Each run is repeated at its symbol's value, and calibration fails if E-L4 blocks
   any entry, long or short, so the value covers every entry the symbol's runs make. Each run's
   lowest available funds, and its bars below zero, are reported, not refused (PO, DEC-30).

Calibration runs at `spread_capture` 0 only, and writes no results.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import final

import structlog

from pmcc.accounting.events import Event
from pmcc.config.capital import (
    CALIBRATED_STRATEGIES,
    CalibrationEntry,
    StartingCash,
    SymbolCash,
    in_order,
    starting_cash_for,
)
from pmcc.config.kinds import FixedContracts
from pmcc.config.strategy import RunConfig
from pmcc.domain.instruments import Side
from pmcc.domain.money import Money
from pmcc.domain.rules import RuleId
from pmcc.engine.loop import RunOutput
from pmcc.runner import Market, run_output

log = structlog.get_logger()

CALIBRATION_CASH = Money.from_dollars(1_000_000)
E_L1, E_L4 = RuleId("E-L1"), RuleId("E-L4")


class CalibrationError(Exception):
    """No starting cash can be calibrated from these runs."""


@final
@dataclass(frozen=True, slots=True)
class RunFunds:
    """One run at the calibrated value: its lowest available funds, when, and how many bars went
    below zero. Reported, never refused: E-L4 guards entries, and the site reports Reg T breaches
    (PO, DEC-30)."""

    symbol: str
    strategy: str
    lowest: Money
    lowest_at: datetime
    negative_bars: int


@final
@dataclass(frozen=True, slots=True)
class Calibration:
    """Each calibrated symbol's starting cash, and each run's funds at its symbol's."""

    cash: StartingCash
    funds: tuple[RunFunds, ...]


def calibrate(markets: Mapping[str, Market], configs: Sequence[RunConfig],
              universe: Sequence[str]) -> Calibration:  # fmt: skip
    """Each symbol's starting cash for `configs` on `markets` (keyed by symbol), provisional unless
    `configs` hold both strategies. Symbols follow the universe's order, entries the strategy's
    ID, whatever order the arguments came in, so equal calibrations write equal blocks."""
    others = sorted({c.strategy.id for c in configs} - set(CALIBRATED_STRATEGIES))
    if others:
        raise CalibrationError(f"calibration runs {CALIBRATED_STRATEGIES} only, not {others}")
    if not markets:
        raise CalibrationError("no symbol to calibrate")
    multiple, round_to = cash_rule(configs)
    ordered = sorted(configs, key=lambda c: c.strategy.id)
    results = {symbol: _symbol_cash(symbol, market, ordered, multiple, round_to)
               for symbol, market in markets.items()}  # fmt: skip
    cash = StartingCash(
        cash_multiple=multiple,
        cash_round_to=round_to,
        calibration_cash=CALIBRATION_CASH,
        symbols=in_order((c for c, _ in results.values()), universe),
    )
    funds = tuple(f for c in cash.symbols for f in results[c.symbol][1])
    log.info("calibrate.done", symbols=len(cash.symbols), runs=len(funds))
    return Calibration(cash, funds)


def _symbol_cash(symbol: str, market: Market, configs: Sequence[RunConfig], multiple: int,
                 round_to: Money) -> tuple[SymbolCash, tuple[RunFunds, ...]]:  # fmt: skip
    """One symbol's value from its own runs' first entries, and each run's funds at it."""
    entries = tuple(measure(symbol, market, config) for config in configs)
    value = starting_cash_for((e.cost for e in entries), multiple, round_to)
    funds = tuple(verify(symbol, market, config, value) for config in configs)
    done = {e.strategy for e in entries}
    cash = SymbolCash(symbol=symbol, value=value, entries=entries,
                      provisional=any(t not in done for t in CALIBRATED_STRATEGIES))  # fmt: skip
    log.info("calibrate.symbol", symbol=symbol, value=str(value.to_dollars()),
             provisional=cash.provisional)  # fmt: skip
    return cash, funds


def cash_rule(configs: Sequence[RunConfig]) -> tuple[int, Money]:
    """E-L4's `cash_multiple` and `cash_round_to`, which every config must give alike."""
    rules = {_cash_rule(config) for config in configs}
    if len(rules) != 1:
        found = sorted((m, str(r.to_dollars())) for m, r in rules)
        raise CalibrationError(f"the configs give E-L4 different starting-cash rules: {found}")
    return rules.pop()


def _cash_rule(config: RunConfig) -> tuple[int, Money]:
    params = next(r.params for r in config.strategy.rules if r.id == E_L4)
    if not isinstance(params, FixedContracts):
        raise CalibrationError(f"{config.strategy.id}: E-L4 has no starting-cash rule")
    return params.cash_multiple, params.cash_round_to


def measure(symbol: str, market: Market, config: RunConfig) -> CalibrationEntry:
    """The run's first long-leg entry, at `CALIBRATION_CASH` and `spread_capture` 0."""
    run_id = config.strategy.id
    capture = config.strategy.fill_model.spread_capture
    if capture != 0:
        raise CalibrationError(f"{run_id} fills at spread_capture {capture}; calibration is at 0")
    output = run_output(market, config, CALIBRATION_CASH)
    blocked = blocked_entries(output)
    if blocked:
        raise CalibrationError(
            f"{symbol} {run_id}: E-L4 blocked an entry at {blocked[0].isoformat()} even with "
            f"{CALIBRATION_CASH.to_dollars()}"
        )
    first = first_long_entry(output.blotter)
    if first is None:
        raise CalibrationError(f"{symbol} {run_id}: no long-leg entry (E-L1) in the window, so "
                               "no cost to calibrate from")  # fmt: skip
    entry = CalibrationEntry(
        strategy=run_id,
        time=first.time,
        contract=market.names.instrument(first.instrument).ric,
        cost=-first.cash_delta,
    )
    log.info("calibrate.measured", symbol=symbol, run_id=run_id, time=first.time.isoformat(),
             contract=entry.contract, cost=str(entry.cost.to_dollars()))  # fmt: skip
    return entry


def first_long_entry(blotter: Sequence[Event]) -> Event | None:
    """The run's first long-leg entry: the earliest E-L1 buy, not a later re-entry after X-L1 or
    X-L2, however much more that costs (PO, DEC-30)."""
    return min(
        (e for e in blotter if e.rule_id == E_L1 and e.side is Side.BUY),
        key=lambda e: e.time,
        default=None,
    )


def verify(symbol: str, market: Market, config: RunConfig, value: Money) -> RunFunds:
    """The run's funds at `value`. Raises `CalibrationError` if E-L4 blocks any entry in it."""
    output = run_output(market, config, value)
    blocked = blocked_entries(output)
    if blocked:
        raise CalibrationError(
            f"{symbol} {config.strategy.id}: at {value.to_dollars()}, E-L4 blocks an entry on "
            f"{len(blocked)} bar(s), first at {blocked[0].isoformat()}; E-L4's rule doesn't "
            "cover this run's entries (DEC-30)"
        )
    funds = run_funds(symbol, config.strategy.id, output)
    log.info("calibrate.verified", symbol=symbol, run_id=config.strategy.id,
             lowest=str(funds.lowest.to_dollars()), lowest_at=funds.lowest_at.isoformat(),
             negative_bars=funds.negative_bars)  # fmt: skip
    return funds


def run_funds(symbol: str, strategy: str, output: RunOutput) -> RunFunds:
    """The run's lowest available funds (the first bar, on a tie) and its bars below zero."""
    low = min(output.ledger, key=lambda row: (row.available_funds, row.time))
    negative = sum(row.available_funds.units < 0 for row in output.ledger)
    return RunFunds(symbol, strategy, low.available_funds, low.time, negative)


def blocked_entries(output: RunOutput) -> list[datetime]:
    """When E-L4 blocked an entry: a long (the bar's `entry_blocked` flag) or a short (the week's
    gate-log row, skipped as E-L4)."""
    longs = [row.time for row in output.ledger if "entry_blocked" in row.flags]
    shorts = [g.decision_time for g in output.gate_log if g.rule_id == E_L4 and g.decision_time]
    return sorted([*longs, *shorts])
