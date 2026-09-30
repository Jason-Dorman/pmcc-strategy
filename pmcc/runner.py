"""One backtest: a strategy config on one symbol's cache, as a `RunResult` (Spec › CLI, `pmcc run`).

`run_symbol` loads the cache (no network), prices it, runs the engine and turns its blotter,
ledger and gate log into the result's rows, stamped with the run's manifest. The engine checks the
runtime invariants on every bar and raises on a failure, so a result exists only for a run that
held them all (DEC-49). `pmcc calibrate` and `pmcc batch` reuse `run_loaded` on a loaded cache.
"""

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import final

import polars as pl
import structlog

from pmcc.accounting.events import Event, Instrument, StockId
from pmcc.accounting.ledger import LedgerRow, LegRow, StockRow
from pmcc.config.strategy import RunConfig
from pmcc.config.universe import Underlying
from pmcc.data.load import SymbolData, load_symbol
from pmcc.data.ric import occ_symbol
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import Right
from pmcc.domain.money import Money, Price
from pmcc.engine.legs import GateLogRow
from pmcc.engine.loop import RunOutput, run_backtest
from pmcc.engine.market_view import MarketData
from pmcc.export.manifest import Provenance
from pmcc.export.models import (
    BlotterRow,
    DataSource,
    GateLogRowOut,
    GateOut,
    InstrumentOut,
    LedgerRowOut,
    LegOut,
    Manifest,
    OutcomeOut,
    RuleTextOut,
    RunResult,
    StockOut,
)
from pmcc.strategy.ports import GateResult
from pmcc.strategy.registry import build_strategy

log = structlog.get_logger()

type _ContractKey = tuple[date, Right, int]  # expiry, right, strike in cents


@final
@dataclass(frozen=True, slots=True)
class Stamp:
    """What the manifest records beyond the run itself."""

    provenance: Provenance
    data_source: DataSource
    run_timestamp: datetime


def run_symbol(cache: Path, underlying: Underlying, calendar: SessionCalendar, config: RunConfig,
               starting_cash: Money, stamp: Stamp) -> RunResult:  # fmt: skip
    """Load `underlying`'s cache under `cache` and run `config` on it."""
    loaded = load_symbol(cache, underlying.symbol, calendar)
    return run_loaded(loaded, underlying.option_root, config, starting_cash, stamp)


def run_loaded(loaded: SymbolData, root: str, config: RunConfig, starting_cash: Money,
               stamp: Stamp) -> RunResult:  # fmt: skip
    """Run `config` on a loaded cache whose options are named under `root`."""
    rate = config.risk_free_rate.value
    data = MarketData.build(loaded.stock, loaded.chains, loaded.calendar, rate, root)
    output = run_backtest(data, config, build_strategy(config.strategy), starting_cash)
    result = to_result(output, loaded, config, stamp)
    log.info("run.done", symbol=loaded.symbol, run_id=config.strategy.id,
             trades=len(result.blotter), bars=len(result.ledger), weeks=len(result.gate_log),
             git_dirty=stamp.provenance.git.dirty)  # fmt: skip
    return result


def to_result(output: RunOutput, loaded: SymbolData, config: RunConfig,
              stamp: Stamp) -> RunResult:  # fmt: skip
    names = _Names.of(loaded)
    return RunResult(
        manifest=_manifest(loaded, config, stamp),
        config=config,
        rule_text={r.id: RuleTextOut(**asdict(r.text())) for r in config.strategy.rules},
        starting_cash=output.starting_cash.to_dollars(),
        blotter=tuple(_blotter_row(e, names) for e in output.blotter),
        ledger=tuple(_ledger_row(r, names) for r in output.ledger),
        gate_log=tuple(_gate_row(g) for g in output.gate_log),
    )


def _manifest(loaded: SymbolData, config: RunConfig, stamp: Stamp) -> Manifest:
    run_id = config.strategy.id
    provenance = stamp.provenance
    return Manifest(
        run_id=run_id,
        symbol=loaded.symbol,
        strategy_id=run_id.split("--")[0],  # quant_pmcc--a3 is a variant of quant_pmcc
        git_sha=provenance.git.sha,
        git_dirty=provenance.git.dirty,
        config_hash=config.config_hash(),
        data_manifest_hash=loaded.data_manifest_hash,
        lock_hash=provenance.lock_hash,
        run_timestamp=stamp.run_timestamp,
        data_source=stamp.data_source,
        pmcc_version=provenance.pmcc_version,
    )


@final
@dataclass(frozen=True, slots=True)
class _Names:
    """The RIC each instrument answered with in the cache."""

    stock: str
    options: Mapping[_ContractKey, str]

    @classmethod
    def of(cls, loaded: SymbolData) -> "_Names":
        options: dict[_ContractKey, str] = {}
        for (expiry, right), frame in loaded.chains.items():
            for strike_cents, ric in frame.select("strike_cents", "ric").unique().iter_rows():
                key = (expiry, right, int(strike_cents))
                if options.setdefault(key, ric) != ric:
                    raise ValueError(f"{key} answered as both {options[key]} and {ric}")
        return cls(_one_ric(loaded.stock, loaded.symbol), options)

    def instrument(self, instrument: Instrument) -> InstrumentOut:
        if isinstance(instrument, StockId):
            return InstrumentOut(ric=self.stock, occ=None, kind="stock", expiry=None, strike=None)
        key = (instrument.expiry, instrument.right, instrument.strike_cents)
        return InstrumentOut(
            ric=self.options[key],
            occ=occ_symbol(instrument),
            kind="call" if instrument.right is Right.CALL else "put",
            expiry=instrument.expiry,
            strike=instrument.strike.to_dollars(),
        )


def _one_ric(stock: pl.DataFrame, symbol: str) -> str:
    rics: list[str] = stock["ric"].unique().sort().to_list()
    if len(rics) != 1:
        raise ValueError(f"{symbol}'s stock tape holds {len(rics)} RICs, not one: {rics}")
    return rics[0]


def _blotter_row(event: Event, names: _Names) -> BlotterRow:
    return BlotterRow(
        time=event.time,
        instrument=names.instrument(event.instrument),
        side=event.side.value,
        qty=event.qty,
        limit=_dollars(event.limit),
        fill=_dollars(event.fill),
        fee=event.fee.to_dollars(),
        cash_delta=event.cash_delta.to_dollars(),
        rule_id=str(event.rule_id),
        notes=event.notes,
        audit=dict(event.audit),
    )


def _dollars(price: Price | None) -> Decimal | None:
    return None if price is None else price.to_dollars()


def _ledger_row(row: LedgerRow, names: _Names) -> LedgerRowOut:
    return LedgerRowOut(
        time=row.time,
        long=_leg(row.long, names),
        short=_leg(row.short, names),
        stock=_stock(row.stock, names),
        cash=row.cash.to_dollars(),
        nav=row.nav.to_dollars(),
        im=row.im.to_dollars(),
        mm=row.mm.to_dollars(),
        available_funds=row.available_funds.to_dollars(),
        excess_equity=row.excess_equity.to_dollars(),
        flags=row.flags,
    )


def _leg(leg: LegRow | None, names: _Names) -> LegOut | None:
    if leg is None:
        return None
    return LegOut(instrument=names.instrument(leg.option), qty=leg.qty,
                  mark=leg.mark.to_dollars(), stale=leg.stale, delta=leg.delta)  # fmt: skip


def _stock(stock: StockRow | None, names: _Names) -> StockOut | None:
    if stock is None:
        return None
    return StockOut(instrument=names.instrument(stock.stock), shares=stock.shares,
                    mark=stock.mark.to_dollars(), stale=stock.stale)  # fmt: skip


def _gate_row(row: GateLogRow) -> GateLogRowOut:
    return GateLogRowOut(
        session=row.session,
        decision_time=row.decision_time,
        selected=None if row.selected is None else dict(row.selected),
        gates=tuple(_gate(g) for g in row.gates),
        outcome=OutcomeOut(kind=row.outcome, rule_id=str(row.rule_id)),
        notes=row.notes,
    )


def _gate(gate: GateResult) -> GateOut:
    return GateOut(rule_id=str(gate.rule_id), status=gate.status.value, values=dict(gate.values),
                   reason=gate.reason)  # fmt: skip
