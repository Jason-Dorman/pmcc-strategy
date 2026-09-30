"""The `pmcc` command line. A command not built yet is a stub naming its backlog item."""

from datetime import datetime
from pathlib import Path
from typing import Annotated, NoReturn

import structlog
import typer
import yaml

from pmcc.calibration import Calibration, CalibrationError
from pmcc.calibration import calibrate as calibrate_cash
from pmcc.config.calendar import load_calendar
from pmcc.config.capital import CALIBRATED_STRATEGIES, StartingCash, render_block, with_block
from pmcc.config.strategy import CONFIGS_DIR, RunConfig, load_run_config
from pmcc.config.universe import UNIVERSE_PATH, Underlying, load_universe
from pmcc.config.universe import Universe as UniverseConfig
from pmcc.config.yaml_file import parse_yaml
from pmcc.data import coverage, estimate
from pmcc.data.cache import CacheError, SymbolCache
from pmcc.data.calendar import CalendarMismatchError
from pmcc.data.files import replace_file
from pmcc.data.load import load_symbol
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
from pmcc.export.schema import write_schemas
from pmcc.export.site import Exported, ExportError, export_site
from pmcc.export.verify import Verified
from pmcc.export.verify import verify as verify_results
from pmcc.log import configure_logging
from pmcc.runner import Market, Stamp, run_symbol

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
        _fail("configs/universe.yaml has no starting_cash yet: run pmcc calibrate (DEC-30)")
    result = _backtest(cache, underlying, calendar, _run_config(config, settings), cash.value)
    path = write_result(result, out)
    _say(_describe_run(result, path))
    if cash.provisional:
        _say(f"Starting cash {cash.value.to_dollars()} is provisional (DEC-30): P5-01 calibrates "
             "the final value, and every run is repeated with it.")  # fmt: skip
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
    except (CacheError, CalendarMismatchError, ProvenanceError, EngineError, ValueError) as exc:
        log.exception("run.abort", symbol=underlying.symbol, run_id=config.strategy.id)
        _fail(f"{underlying.symbol}: {exc}; nothing was written")


def _describe_run(result: RunResult, path: Path) -> str:
    manifest = result.manifest
    lines = [_describe_rows(result), f"Written to {path.as_posix()}"]
    if manifest.git_dirty:
        lines.append(
            "git_dirty: true (uncommitted changes outside results/). Commit the code before a "
            "publishable run: pmcc verify rejects dirty results (DEC-50)."
        )
    return "\n".join(lines)


def _describe_rows(result: RunResult) -> str:
    manifest = result.manifest
    head = f"{manifest.symbol} {manifest.run_id}:"
    blotter, ledger, gate_log = result.blotter, result.ledger, result.gate_log
    if blotter is None or ledger is None or gate_log is None:
        return f"{head} a summary, without its rows (DEC-54)."
    return (f"{head} {len(blotter)} trades over {len(ledger)} bars and {len(gate_log)} weeks; "
            f"final NAV {ledger[-1].nav} from {result.starting_cash}.")  # fmt: skip


@app.command()
def batch(universe: Universe = Path("configs/universe.yaml")) -> None:
    """Run every symbol, strategy and variant in the universe."""
    _not_built("P5-03")


Symbols = Annotated[
    list[str] | None,
    typer.Option("--symbol", help="A symbol to calibrate on; repeat for more. Default: all."),
]
Configs = Annotated[
    list[Path] | None,
    typer.Option("--config", help="A strategy config; repeat for more. Default: both strategies."),
]


@app.command()
def calibrate(
    symbol: Symbols = None,
    config: Configs = None,
    check: Annotated[
        bool, typer.Option(help="Recompute and compare with configs/universe.yaml; write nothing.")
    ] = False,
    cache: Cache = Path("data_cache"),
) -> None:
    """Calibrate the starting cash (Spec › E-L4) and write it, with its basis, into
    configs/universe.yaml. It stays provisional until every symbol is calibrated under both
    strategies (DEC-30)."""
    log_path = configure_logging("calibrate")
    calendar = load_calendar()
    settings = _universe(calendar)
    if not check:
        _check_replaceable(settings.starting_cash)
    symbols = [s.upper() for s in symbol] if symbol else [u.symbol for u in settings.symbols]
    paths = config or [CONFIGS_DIR / f"{s}.yaml" for s in CALIBRATED_STRATEGIES]
    configs = [_run_config(p, settings) for p in paths]
    markets = {s: _market(cache, _underlying(s, settings), calendar, settings) for s in symbols}
    calibration = _calibrated(markets, configs, settings)
    cash = calibration.cash
    _say(_describe_cash(calibration))
    if check:
        _check_matches(cash)
    else:
        _write_cash(cash, calendar)
    _say(f"Log: {log_path.as_posix()}")


def _check_replaceable(current: StartingCash | None) -> None:
    if current is not None and not current.provisional:
        _fail("configs/universe.yaml holds a final starting_cash; pmcc calibrate never replaces "
              "it. Remove its block by hand to calibrate again (DEC-30).")  # fmt: skip


def _market(cache: Path, underlying: Underlying, calendar: SessionCalendar,
            settings: UniverseConfig) -> Market:  # fmt: skip
    try:
        loaded = load_symbol(cache, underlying.symbol, calendar)
    except (CacheError, CalendarMismatchError) as exc:
        _fail(f"{underlying.symbol}: {exc}")
    return Market.prepare(loaded, underlying.option_root, settings.risk_free_rate.value)


def _calibrated(markets: dict[str, Market], configs: list[RunConfig],
                settings: UniverseConfig) -> Calibration:  # fmt: skip
    try:
        return calibrate_cash(markets, configs, [u.symbol for u in settings.symbols])
    except (CalibrationError, CacheError, EngineError, ValueError) as exc:
        log.exception("calibrate.abort")
        _fail(f"calibration failed: {exc}; configs/universe.yaml is unchanged")


def _describe_cash(calibration: Calibration) -> str:
    cash = calibration.cash
    state = "provisional" if cash.provisional else "final"
    lines = [f"Starting cash {cash.value.to_dollars()} ({state}), from:"]
    lines += [
        f"  {e.symbol} {e.strategy}: {e.contract} at {e.time.isoformat()}, {e.cost.to_dollars()}"
        for e in cash.entries
    ]
    lines.append(f"Available funds at {cash.value.to_dollars()} (reported, not refused; DEC-30):")
    lines += [
        f"  {f.symbol} {f.strategy}: lowest {f.lowest.to_dollars()} at {f.lowest_at.isoformat()}; "
        f"{f.negative_bars} bar(s) below zero"
        for f in calibration.funds
    ]
    return "\n".join(lines)


def _check_matches(cash: StartingCash) -> None:
    """Byte for byte: the file must be exactly what `pmcc calibrate` would write (DEC-93)."""
    try:
        text = UNIVERSE_PATH.read_text(encoding="utf-8")
        same = with_block(text, render_block(cash)) == text
    except (OSError, ValueError, yaml.YAMLError):  # unreadable, or a block set by hand
        same = False
    if not same:
        _fail("configs/universe.yaml's starting_cash doesn't match this calibration; run pmcc "
              "calibrate to rewrite it")  # fmt: skip
    _say("configs/universe.yaml's starting_cash matches.")


def _write_cash(cash: StartingCash, calendar: SessionCalendar) -> None:
    """Write the block, after checking the whole file still loads with it."""
    try:
        text = with_block(UNIVERSE_PATH.read_text(encoding="utf-8"), render_block(cash))
        validate_universe(text, calendar)
        replace_file(UNIVERSE_PATH, text.encode("utf-8"))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        _fail(f"configs/universe.yaml: {exc}; it is unchanged")
    _say("Written to configs/universe.yaml.")


def validate_universe(text: str, calendar: SessionCalendar) -> None:
    """Raises unless `text` loads as `load_universe` would load it."""
    UniverseConfig.model_validate(parse_yaml(text)).window.check_sessions(calendar)


Results = Annotated[Path, typer.Option(help="The results directory.")]


@app.command()
def export(
    out: Annotated[Path, typer.Option(help="Site data directory.")] = Path("web/public/data"),
    results: Results = Path("results"),
    schema_only: Annotated[
        bool, typer.Option(help="Write only the JSON Schemas, which the site's types come from.")
    ] = False,
) -> None:
    """Rebuild the site's data from results: JSON Schemas, the results files, index.json and
    rules.json. Refuses results that fail pmcc verify, a dirty tree aside."""
    configure_logging("export")
    if schema_only:
        written = write_schemas(out)
        _say(f"{len(written)} schemas written to {(out / 'schema').as_posix()}")
        return
    try:
        exported = export_site(results, out)
    except (ExportError, OSError) as exc:  # OSError: no results, or --out is a file
        log.error("export.abort", message=str(exc))
        _fail(f"{exc}\nNothing was exported.")
    log.info("export.done", runs=exported.runs, symbols=exported.symbols, files=exported.files,
             unpublishable=len(exported.unpublishable))  # fmt: skip
    _say(_describe_export(exported, out))


def _describe_export(exported: Exported, out: Path) -> str:
    lines = [f"Exported {exported.runs} runs for {exported.symbols} symbol(s), {exported.files} "
             f"results files, to {out.as_posix()}"]  # fmt: skip
    if exported.unpublishable:
        lines.append(
            "Not publishable, from a dirty tree (pmcc verify refuses them; DEC-50): "
            + ", ".join(exported.unpublishable)
        )
    return "\n".join(lines)


@app.command()
def verify(results: Annotated[Path, typer.Argument()] = Path("results")) -> None:
    """Check results without the cache: layout, schema, canonical bytes, a clean tree, the config
    hash, and the invariants re-derived from each full run's rows (DEC-51)."""
    configure_logging("verify")
    try:
        verified = verify_results(results)
    except FileNotFoundError as exc:
        _fail(str(exc))
    for problem in verified.problems:
        typer.echo(str(problem), err=True)
    if verified.problems:
        log.error("verify.failed", files=verified.files, problems=len(verified.problems))
        _fail(f"{len(verified.problems)} problem(s) in {_counted(verified)}.")
    log.info("verify.done", runs=verified.runs, files=verified.files)
    _say(f"Verified {_counted(verified)}: every check passed.")


def _counted(verified: Verified) -> str:
    return f"{verified.files} files ({verified.runs} runs)"


@app.command()
def serve() -> None:
    """Serve the built site and the local data endpoints on 127.0.0.1."""
    _not_built("P7-06")
