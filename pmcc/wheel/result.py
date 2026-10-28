"""A wheel run on one symbol's cache, as its result (W2-03, W3-01; `pmcc wheel`).

`run_wheel_symbol` loads the wheel's market (the cache's stock and calls with the wheel part's
puts, WD-11; no network), runs the wheel, and turns its blotter (each row with its Trade P&L,
WD-28), ledger and gate log into the result's rows, stamped with the run's manifest. Its summary
holds the run's metrics and cycle statistics, the benchmarks it is given (`load_benchmarks`), and
each thesis claim's verdict (`pmcc.wheel.analytics`), and its fill evidence: every sold option's
prints against its mids (W3-02). The engine checks the runtime invariants on
every bar and event and raises on a failure, so a result exists only for a run that held them all.
"""

from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

import structlog

from pmcc.config.universe import Underlying
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import OptionId, Side
from pmcc.domain.money import Money, Price
from pmcc.export.models import LegOut, Manifest, OutcomeOut, RuleTextOut
from pmcc.export.wheel_models import (
    Benchmarks,
    WheelBlotterRow,
    WheelGateRowOut,
    WheelInvariantCheck,
    WheelLedgerRowOut,
    WheelResult,
    WheelSummary,
)
from pmcc.runner import Names, Stamp, blotter_row
from pmcc.wheel.analytics import cycle_stats, fill_evidence, metrics, trade_pnls, verdicts
from pmcc.wheel.config import WheelRunConfig
from pmcc.wheel.engine import OptionLeg, WheelGateRow, WheelLedgerRow, WheelRun, run_wheel
from pmcc.wheel.invariants import RUNTIME_INVARIANTS
from pmcc.wheel.market import WheelMarket, load_wheel_market, print_pairs

log = structlog.get_logger()


def run_wheel_symbol(cache: Path, underlying: Underlying, calendar: SessionCalendar,
                     config: WheelRunConfig, stamp: Stamp,
                     benchmarks: Benchmarks) -> WheelResult:  # fmt: skip
    """Load `underlying`'s wheel market under `cache` and run `config` on it. Raises
    `CacheError` for a cache that doesn't cover the window, and `EngineError` as the run does."""
    window = (config.window.start, config.window.end)
    market = load_wheel_market(cache, underlying.symbol, underlying.option_root, calendar,
                               config.risk_free_rate.value, window)  # fmt: skip
    return run_wheel_market(market, config, stamp, benchmarks)


def run_wheel_market(market: WheelMarket, config: WheelRunConfig, stamp: Stamp,
                     benchmarks: Benchmarks) -> WheelResult:  # fmt: skip
    run = run_wheel(market.data, config)
    result = to_wheel_result(run, market, config, stamp, benchmarks)
    log.info("wheel.done", symbol=market.symbol, run_id=config.wheel.id, trades=len(run.blotter),
             bars=len(run.ledger), weeks=len(run.gate_log),
             git_dirty=stamp.provenance.git.dirty)  # fmt: skip
    return result


def to_wheel_result(run: WheelRun, market: WheelMarket, config: WheelRunConfig, stamp: Stamp,
                    benchmarks: Benchmarks) -> WheelResult:  # fmt: skip
    names = market.names
    flags = Counter(flag for row in run.ledger for flag in row.flags)
    performance = metrics(run, config.risk_free_rate.value)
    pnls = trade_pnls(run.blotter)
    sold = [(e.instrument, e.time) for e in run.blotter
            if isinstance(e.instrument, OptionId) and e.side is Side.SELL]  # fmt: skip
    return WheelResult(
        manifest=_manifest(market, config, stamp),
        config=config,
        rule_text={str(r.id): RuleTextOut(**asdict(r.text())) for r in config.wheel.rules},
        starting_cash=run.starting_cash.to_dollars(),
        summary=WheelSummary(
            metrics=performance,
            cycle_stats=cycle_stats(run),
            benchmarks=benchmarks,
            thesis=verdicts(performance, benchmarks),
            flag_counts=dict(sorted(flags.items())),
            invariants=tuple(WheelInvariantCheck(id=i, held=True) for i in RUNTIME_INVARIANTS),
        ),
        blotter=tuple(
            WheelBlotterRow(**dict(blotter_row(e, names)), trade_pnl=_dollars(pnl))
            for e, pnl in zip(run.blotter, pnls, strict=True)
        ),
        ledger=tuple(_ledger_row(r, names) for r in run.ledger),
        gate_log=tuple(_gate_row(g) for g in run.gate_log),
        fill_evidence=fill_evidence(print_pairs(market, sold), len(sold)),
    )


def _manifest(market: WheelMarket, config: WheelRunConfig, stamp: Stamp) -> Manifest:
    run_id, provenance = config.wheel.id, stamp.provenance
    return Manifest(
        run_id=run_id,
        symbol=market.symbol,
        strategy_id=run_id.split("--")[0],  # wheel--sc025 is a variant of wheel
        git_sha=provenance.git.sha,
        git_dirty=provenance.git.dirty,
        config_hash=config.config_hash(),
        data_manifest_hash=market.data_manifest_hash,
        lock_hash=provenance.lock_hash,
        run_timestamp=stamp.run_timestamp,
        data_source=stamp.data_source,
        pmcc_version=provenance.pmcc_version,
    )


def _ledger_row(row: WheelLedgerRow, names: Names) -> WheelLedgerRowOut:
    return WheelLedgerRowOut(
        time=row.time,
        spot=_dollars(row.spot),
        state=row.state.value,
        cash=row.cash.to_dollars(),
        reserved=row.reserved.to_dollars(),
        free_cash=row.free_cash.to_dollars(),
        shares=row.shares,
        stock_mark=_dollars(row.stock_mark),
        put=_leg(row.put, names),
        call=_leg(row.call, names),
        cost_basis=_dollars(row.cost_basis),
        nav=row.nav.to_dollars(),
        flags=row.flags,
    )


def _leg(leg: OptionLeg | None, names: Names) -> LegOut | None:
    if leg is None:
        return None
    return LegOut(instrument=names.instrument(leg.option), qty=leg.qty, mark=leg.mark.to_dollars(),
                  stale=leg.stale, delta=leg.greeks.delta)  # fmt: skip


def _gate_row(row: WheelGateRow) -> WheelGateRowOut:
    return WheelGateRowOut(
        session=row.session,
        state=row.state.value,
        decision_time=row.decision_time,
        selected=None if row.selected is None else dict(row.selected),
        outcome=OutcomeOut(kind=row.outcome, rule_id=str(row.rule_id)),
        notes=row.notes,
    )


def _dollars(price: Money | Price | None) -> Decimal | None:
    return None if price is None else price.to_dollars()
