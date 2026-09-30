"""The `pmcc` command line. Each command is a stub until its backlog item lands."""

from datetime import datetime
from pathlib import Path
from typing import Annotated, NoReturn

import structlog
import typer
import yaml

from pmcc.config.calendar import load_calendar
from pmcc.config.strategy import RunConfig, load_run_config
from pmcc.config.universe import Underlying, load_universe
from pmcc.config.universe import Universe as UniverseConfig
from pmcc.data import coverage, estimate
from pmcc.data.cache import CacheError, SymbolCache
from pmcc.data.calendar import CalendarMismatchError
from pmcc.data.lseg import lseg_session
from pmcc.data.probe import ProbeStoppedError, probe_path, run_probe, write_report
from pmcc.data.provider import ProviderOutageError
from pmcc.data.pull import PlanError, Target, prepare, pull_units
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET
from pmcc.domain.errors import EngineError
from pmcc.domain.money import Money
from pmcc.export.manifest import ProvenanceError, provenance
from pmcc.export.models import DataSource, RunResult
from pmcc.export.results import write_result
from pmcc.log import configure_logging
from pmcc.runner import Stamp, run_symbol
from pmcc.strategy.registry import NotBuiltError

app = typer.Typer(help="PMCC backtester: fetch LSEG data, run backtests, export the site.")
log = structlog.get_logger()


def _now() -> datetime:
    return datetime.now(ET)


def _say(text: str) -> None:
    typer.echo(text)


Symbol = Annotated[str, typer.Option(help="Underlying ticker, e.g. NVDA.")]
Day = Annotated[datetime, typer.Option(formats=["%Y-%m-%d"])]
Universe = Annotated[Path, typer.Option(help="Universe YAML.")]


def _not_built(item: str) -> NoReturn:
    typer.echo(f"Not built yet: see docs/BUILD-PLAN.md {item}.", err=True)
    raise typer.Exit(code=1)


Cache = Annotated[Path, typer.Option(help="The raw cache.")]


@app.command()
def fetch(
    symbol: Symbol,
    start: Day,
    end: Day,
    plan_only: Annotated[bool, typer.Option(help="Print the request estimate and stop.")] = False,
    cache: Cache = Path("data_cache"),
    probes: Annotated[Path, typer.Option(help="Probe reports.")] = Path("data_cache/probes"),
) -> None:
    """Pull a symbol's stock and option history from LSEG into the local cache."""
    log_path = configure_logging("fetch")
    sym, calendar = symbol.upper(), load_calendar()
    universe = load_universe(calendar)
    target = _target(sym, universe)
    try:
        steps = estimate.assumed_steps(estimate.latest_probe_report(probes, sym))
    except estimate.NoProbeReportError as exc:
        _fail(str(exc))
    store = SymbolCache(cache, sym)
    window = (start.date(), end.date())
    try:
        with lseg_session() as provider:
            prepared = prepare(provider, store, calendar, target, window, _now)
            _say(estimate.describe(estimate.estimate(prepared, steps)))
            if plan_only:
                return
            written = pull_units(provider, store, prepared, steps.steps, _now)
    except ProviderOutageError as exc:
        log.error("fetch.abort.outage", symbol=sym, message=str(exc))
        _fail(
            f"{sym}: LSEG stopped answering; the unit in flight wrote nothing. "
            f"{len(store.unit_names())} units are cached; run the same command again to resume. "
            f"({exc})"
        )
    except (PlanError, CalendarMismatchError, CacheError, FileExistsError) as exc:
        _fail(f"{sym}: {exc}")
    _say(f"{sym}: {len(written)} units written.")
    rate = universe.risk_free_rate.value
    _say(coverage.describe(coverage.coverage(cache, sym, calendar, rate)))
    _say(f"Log: {log_path.as_posix()}")


def _target(symbol: str, universe: UniverseConfig) -> Target:
    """The symbol's identifiers from `configs/universe.yaml`."""
    underlying = _underlying(symbol, universe)
    return Target(symbol, underlying.stock_ric, underlying.option_root)


def _underlying(symbol: str, universe: UniverseConfig) -> Underlying:
    for underlying in universe.symbols:
        if underlying.symbol == symbol:
            return underlying
    _fail(f"{symbol} isn't in configs/universe.yaml (DEC-15)")


@app.command()
def probe(
    symbol: Symbol,
    out: Annotated[Path, typer.Option(help="Where probe reports go.")] = Path("data_cache/probes"),
) -> None:
    """Run the LSEG spikes for a symbol and write a probe report."""
    configure_logging("probe")
    sym, now = symbol.upper(), _now()
    path = probe_path(out, sym, now.date())
    if path.exists():
        _fail(f"{path} exists; a probe report is never overwritten. Rename it to probe again.")
    try:
        with lseg_session() as provider:
            report = run_probe(provider, sym, load_calendar(), now)
    except (ProviderOutageError, ProbeStoppedError) as exc:
        _fail(f"{sym}: the probe stopped and wrote nothing: {exc}")
    write_report(report, path)
    typer.echo(f"{sym}: {report['requests']} requests; report written to {path}")
    if report["stopped"] is not None:
        _fail(f"{sym}: stopped early: {report['stopped']}")


def _fail(message: str) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(code=1)


@app.command()
def run(
    symbol: Symbol,
    config: Annotated[Path, typer.Option(help="Strategy config YAML.")],
    cache: Cache = Path("data_cache"),
    out: Annotated[Path, typer.Option(help="Results directory.")] = Path("results"),
) -> None:
    """Backtest one strategy config on one symbol, from the cache only. The window, r and
    starting cash come only from configs/universe.yaml (PO, DEC-30)."""
    log_path = configure_logging("run")
    sym, calendar = symbol.upper(), load_calendar()
    settings = _universe(calendar)
    underlying = _underlying(sym, settings)
    cash = settings.starting_cash
    if cash is None:
        _fail("configs/universe.yaml has no starting_cash yet: P3-09 sets it (DEC-30)")
    result = _backtest(cache, underlying, calendar, _run_config(config, settings), cash)
    path = write_result(result, out)
    _say(_describe_run(result, path))
    _say(f"Log: {log_path.as_posix()}")


def _universe(calendar: SessionCalendar) -> UniverseConfig:
    try:
        return load_universe(calendar)
    except (OSError, ValueError, yaml.YAMLError) as exc:  # no file; bad YAML; a value refused
        _fail(f"configs/universe.yaml: {exc}")


def _run_config(path: Path, settings: UniverseConfig) -> RunConfig:
    try:
        return load_run_config(path, settings)
    except (OSError, ValueError, yaml.YAMLError) as exc:  # no file; bad YAML; a rule refused
        _fail(f"{path.as_posix()}: {exc}")


def _backtest(cache: Path, underlying: Underlying, calendar: SessionCalendar,
              config: RunConfig, cash: Money) -> RunResult:  # fmt: skip
    """The run's result, or exit 1 with nothing written (DEC-49)."""
    try:
        stamp = Stamp(provenance(), DataSource.LSEG, _now())
        return run_symbol(cache, underlying, calendar, config, cash, stamp)
    except (CacheError, CalendarMismatchError, ProvenanceError, EngineError, NotBuiltError,
            ValueError) as exc:  # fmt: skip
        log.exception("run.abort", symbol=underlying.symbol, run_id=config.strategy.id)
        _fail(f"{underlying.symbol}: {exc}; nothing was written")


def _describe_run(result: RunResult, path: Path) -> str:
    manifest = result.manifest
    lines = [
        f"{manifest.symbol} {manifest.run_id}: {len(result.blotter)} trades over "
        f"{len(result.ledger)} bars and {len(result.gate_log)} weeks; final NAV "
        f"{result.ledger[-1].nav} from {result.starting_cash}.",
        f"Written to {path.as_posix()}",
    ]
    if manifest.git_dirty:
        lines.append(
            "git_dirty: true (uncommitted changes outside results/). Commit the code before a "
            "publishable run: pmcc verify rejects dirty results (DEC-50)."
        )
    return "\n".join(lines)


@app.command()
def batch(universe: Universe = Path("configs/universe.yaml")) -> None:
    """Run every symbol, strategy and variant in the universe."""
    _not_built("P5-03")


@app.command()
def calibrate(universe: Universe = Path("configs/universe.yaml")) -> None:
    """Calibrate starting capital across the universe."""
    _not_built("P3-09")


@app.command()
def export(
    out: Annotated[Path, typer.Option(help="Site data directory.")] = Path("web/public/data"),
) -> None:
    """Write site data and JSON Schema from committed results."""
    _not_built("P4-05")


@app.command()
def verify(results: Annotated[Path, typer.Argument()] = Path("results")) -> None:
    """Re-derive invariants from results and reject any that fail."""
    _not_built("P4-05")


@app.command()
def serve() -> None:
    """Serve the built site and the local data endpoints on 127.0.0.1."""
    _not_built("P7-06")
