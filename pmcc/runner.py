"""One backtest: a strategy config on one symbol's cache, as a `RunResult` (Spec › CLI, `pmcc run`).

`run_symbol` loads the cache (no network), prices it, runs the engine and turns its blotter,
ledger and gate log into the result's rows, stamped with the run's manifest. The engine checks the
runtime invariants on every bar and raises on a failure, so a result exists only for a run that
held them all (DEC-49).

The strategy's `report` block decides the detail (PO, DEC-54): a full run keeps its rows, its
cycles and its attribution (by Greek only where its sections ask), a summary run only its summary.
Every result's summary records the runtime invariants the run held, how many ledger rows carried
each flag, and the run's analytics (`pmcc.analytics.run`): its metrics, cycle statistics, exit mix,
skips, session closes and weekly returns, whose bootstrap CI is seeded with the universe's
`bootstrap.seed` (DEC-60 to DEC-62).

A symbol is priced once (`Market.prepare`) and each config runs on it (`run_market`), so
`pmcc calibrate` and `pmcc batch` price a symbol once for all its runs (ARCHITECTURE §11). A run
whose window the cached stock tape doesn't cover is refused before it starts (PO, DEC-92).
"""

from collections import Counter
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
from pmcc.analytics.run import RunAnalytics, analyze
from pmcc.config.strategy import Detail, RunConfig
from pmcc.config.universe import Underlying
from pmcc.data.cache import CacheError
from pmcc.data.load import SymbolData, load_symbol
from pmcc.data.ric import occ_symbol
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import Right
from pmcc.domain.money import Money, Price
from pmcc.engine.invariants import RUNTIME_INVARIANTS
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
    InvariantCheck,
    LedgerRowOut,
    LegOut,
    Manifest,
    OutcomeOut,
    RuleTextOut,
    RunResult,
    StockOut,
    Summary,
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


@final
@dataclass(frozen=True, slots=True)
class Market:
    """One symbol's cache, loaded and priced at one r, ready for any number of runs."""

    loaded: SymbolData
    data: MarketData
    names: "_Names"

    @classmethod
    def prepare(cls, loaded: SymbolData, root: str, rate: float) -> "Market":
        """Price `loaded` at `rate`, its options named under `root`."""
        data = MarketData.build(loaded.stock, loaded.chains, loaded.calendar, rate, root)
        return cls(loaded, data, _Names.of(loaded))


def run_symbol(cache: Path, underlying: Underlying, calendar: SessionCalendar, config: RunConfig,
               starting_cash: Money, stamp: Stamp, *, seed: int) -> RunResult:  # fmt: skip
    """Load `underlying`'s cache under `cache` and run `config` on it."""
    loaded = load_symbol(cache, underlying.symbol, calendar)
    return run_loaded(loaded, underlying.option_root, config, starting_cash, stamp, seed=seed)


def run_loaded(loaded: SymbolData, root: str, config: RunConfig, starting_cash: Money,
               stamp: Stamp, *, seed: int) -> RunResult:  # fmt: skip
    """Run `config` on a loaded cache whose options are named under `root`."""
    check_covers(loaded, config)  # before pricing: a short cache fails fast
    market = Market.prepare(loaded, root, config.risk_free_rate.value)
    return run_market(market, config, starting_cash, stamp, seed=seed)


def run_market(market: Market, config: RunConfig, starting_cash: Money,
               stamp: Stamp, *, seed: int) -> RunResult:  # fmt: skip
    """Run `config` on a prepared market into its result, its bootstrap seeded with `seed`;
    raises as `run_output` does."""
    output = run_output(market, config, starting_cash)
    analytics = analyze(output, seed, config.strategy.report, config.risk_free_rate.value)
    result = to_result(output, market, config, stamp, analytics)
    log.info("run.done", symbol=market.loaded.symbol, run_id=config.strategy.id,
             trades=len(output.blotter), bars=len(output.ledger), weeks=len(output.gate_log),
             detail=config.strategy.report.detail.value,
             git_dirty=stamp.provenance.git.dirty)  # fmt: skip
    return result


def run_output(market: Market, config: RunConfig, starting_cash: Money) -> RunOutput:
    """The engine's output for `config` on a prepared market (`pmcc calibrate` reads it whole).
    Raises `ValueError` if the market was priced at another r, and `CacheError` if its stock tape
    doesn't cover the window."""
    if config.risk_free_rate.value != market.data.rate:
        raise ValueError(
            f"{config.strategy.id} runs at r = {config.risk_free_rate.value}, but the market was "
            f"priced at {market.data.rate}"
        )
    check_covers(market.loaded, config)
    return run_backtest(market.data, config, build_strategy(config.strategy), starting_cash)


def check_covers(loaded: SymbolData, config: RunConfig) -> None:
    """Raises `CacheError` unless the cached stock tape has bars on every session of the window
    (PO, DEC-92): a run over sessions with no data would write a result of empty weeks."""
    window = config.window
    sessions = [s.day for s in loaded.calendar.sessions(window.start, window.end)]
    taped: set[date] = set(
        loaded.stock.filter(pl.col("session_bar"))["bar_end"].dt.date().unique().to_list()
    )
    missing = [day for day in sessions if day not in taped]
    if missing:
        raise CacheError(
            f"{loaded.symbol}'s cache has no stock bars on {len(missing)} of the window's "
            f"{len(sessions)} sessions ({missing[0]} to {missing[-1]}); fetch them with pmcc fetch"
        )


def to_result(output: RunOutput, market: Market, config: RunConfig, stamp: Stamp,
              analytics: RunAnalytics) -> RunResult:  # fmt: skip
    """The run's result, at the detail its strategy's `report` block asks for (DEC-54)."""
    loaded, names = market.loaded, market.names
    full = config.strategy.report.detail is Detail.FULL
    return RunResult(
        manifest=_manifest(loaded, config, stamp),
        config=config,
        rule_text={r.id: RuleTextOut(**asdict(r.text())) for r in config.strategy.rules},
        starting_cash=output.starting_cash.to_dollars(),
        summary=_summary(output, analytics),
        blotter=tuple(_blotter_row(e, names) for e in output.blotter) if full else None,
        ledger=tuple(_ledger_row(r, names) for r in output.ledger) if full else None,
        gate_log=tuple(_gate_row(g) for g in output.gate_log) if full else None,
        cycles=analytics.cycles if full else None,
        attribution=analytics.attribution,
    )


def _summary(output: RunOutput, analytics: RunAnalytics) -> Summary:
    """The run's analytics, the invariants it held (a run that broke one returned nothing,
    DEC-49) and the ledger's flag counts."""
    flags = Counter(flag for row in output.ledger for flag in row.flags)
    return Summary(
        metrics=analytics.metrics,
        cycle_stats=analytics.cycle_stats,
        exit_mix=analytics.exit_mix,
        skips_by_rule=analytics.skips_by_rule,
        nav_close=analytics.nav_close,
        weekly_returns=analytics.weekly_returns,
        flag_counts=dict(sorted(flags.items())),
        invariants=tuple(InvariantCheck(id=i, held=True) for i in RUNTIME_INVARIANTS),
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
