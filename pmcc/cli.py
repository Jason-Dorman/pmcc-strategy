"""The `pmcc` command line. A command not built yet is a stub naming its backlog item."""

import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, NoReturn

import structlog
import typer
import yaml

from pmcc.batch import BatchOutcome, SymbolJob, SymbolOutcome, run_batch
from pmcc.calibration import Calibration, CalibrationError
from pmcc.calibration import calibrate as calibrate_cash
from pmcc.config.calendar import load_calendar
from pmcc.config.capital import (
    CALIBRATED_STRATEGIES,
    StartingCash,
    SymbolCash,
    render_block,
    with_block,
)
from pmcc.config.matrix import Family, run_families, run_matrix
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
from pmcc.export.site import Exported, ExportError, check_export_dir, export_site
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
    universe = _universe(calendar)
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
    """Backtest one strategy config on one symbol, from the cache only. The window, r and the
    symbol's starting cash come only from configs/universe.yaml (PO, DEC-30)."""
    log_path = configure_logging("run")
    sym, calendar = symbol.upper(), load_calendar()
    settings = _universe(calendar)
    underlying = _underlying(sym, settings)
    cash = settings.cash_of(sym)
    if cash is None:
        _fail(f"configs/universe.yaml has no starting cash for {sym} yet: run pmcc calibrate "
              f"--symbol {sym} (DEC-30)")  # fmt: skip
    result = _backtest(
        cache,
        underlying,
        calendar,
        _run_config(config, settings),
        cash.value,
        settings.bootstrap.seed,
    )
    path = write_result(result, out)
    _say(_describe_run(result, path))
    if cash.provisional:
        _say(f"{sym}'s starting cash {cash.value.to_dollars()} is provisional (DEC-30): calibrate "
             f"it under both strategies for the final value, then repeat its runs.")  # fmt: skip
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
              config: RunConfig, cash: Money, seed: int) -> RunResult:  # fmt: skip
    """The run's result, or exit 1 with nothing written (DEC-49)."""
    try:
        stamp = Stamp(provenance(), DataSource.LSEG, _now())
        return run_symbol(cache, underlying, calendar, config, cash, stamp, seed=seed)
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
def batch(
    universe: Annotated[
        Path | None, typer.Option(help="Universe YAML: only ever configs/universe.yaml (DEC-30).")
    ] = None,
    cache: Cache = Path("data_cache"),
    out: Annotated[Path, typer.Option(help="Results directory.")] = Path("results"),
) -> None:
    """Run every symbol, strategy and variant in the universe: the 24-run matrix per symbol
    (ARCHITECTURE §11), one process per symbol, then each symbol's coverage, robustness and
    fill-check files and its suitability screen, then the universe's headline, pooled, pooled
    fill-check and suitability files. Exits 1 if any run, symbol file, screen, symbol or universe
    file failed; the rest are still written."""
    log_path = configure_logging("batch")
    if universe is not None and universe.resolve() != UNIVERSE_PATH.resolve():
        _fail(f"{universe.as_posix()}: the universe is always configs/universe.yaml, so every run "
              "takes its starting cash from there (DEC-30)")  # fmt: skip
    calendar = load_calendar()
    settings = _universe(calendar)
    cash = _every_symbols_cash(settings)
    configs, families = _matrix(settings)
    stamp, seed = _stamp(), settings.bootstrap.seed
    jobs = [SymbolJob(cache, u, calendar, settings.risk_free_rate.value, configs,
                      cash[u.symbol].value, stamp, out, families, seed, settings.window)
            for u in settings.symbols]  # fmt: skip
    outcome = run_batch(jobs, out, seed=seed, initializer=worker_logging)
    log.info("batch.done", symbols=len(outcome.symbols), runs=outcome.written,
             ok=outcome.ok, universe=len(outcome.universe))  # fmt: skip
    _say(describe_batch(outcome, out, len(configs)))
    if stamp.provenance.git.dirty:
        _say("git_dirty: true (uncommitted changes outside results/). Commit the code before a "
             "publishable batch: pmcc verify rejects dirty results (DEC-50).")  # fmt: skip
    for c in cash.values():
        if c.provisional:
            _say(f"{c.symbol}'s starting cash {c.value.to_dollars()} is provisional (DEC-30).")
    _say(f"Log: {log_path.as_posix()} (each worker logs beside it)")
    if not outcome.ok:
        raise typer.Exit(code=1)


def _every_symbols_cash(settings: UniverseConfig) -> dict[str, SymbolCash]:
    """Each universe symbol's starting cash; exit 1 if any isn't calibrated yet (DEC-30)."""
    cash = {u.symbol: settings.cash_of(u.symbol) for u in settings.symbols}
    uncalibrated = [s for s, c in cash.items() if c is None]
    if uncalibrated:
        _fail(f"configs/universe.yaml has no starting cash for {', '.join(uncalibrated)} yet: "
              "run pmcc calibrate (DEC-30)")  # fmt: skip
    return {s: c for s, c in cash.items() if c is not None}


def _matrix(settings: UniverseConfig) -> tuple[tuple[RunConfig, ...], dict[str, Family]]:
    try:
        return run_matrix(settings), run_families()
    except (OSError, ValueError, yaml.YAMLError) as exc:  # a config missing, unreadable or refused
        _fail(f"the run matrix: {exc}")


def _stamp() -> Stamp:
    try:
        return Stamp(provenance(), DataSource.LSEG, _now())
    except ProvenanceError as exc:
        _fail(f"{exc}; nothing was run")


def worker_logging() -> None:
    """Each batch worker logs to its own file beside the batch's (pmcc.log is the CLI's, DEC-80)."""
    configure_logging("batch", suffix=f"_worker{os.getpid()}")


def describe_batch(outcome: BatchOutcome, out: Path, matrix: int) -> str:
    lines = [_describe_symbol(s, out, matrix) for s in outcome.symbols]
    universe = ", ".join(p.as_posix() for p in outcome.universe) or "none"
    lines.append(f"Universe files: {universe}")
    lines += [f"  FAILED universe file {e}" for e in outcome.universe_errors]
    failed = sum(len(s.failed) for s in outcome.symbols)
    broken = sum(s.error is not None for s in outcome.symbols)
    uncovered = sum(s.error is None and s.coverage is None for s in outcome.symbols)
    untabled = sum(s.error is None and s.robustness is None for s in outcome.symbols)
    unchecked = sum(s.error is None and s.fill_check is None for s in outcome.symbols)
    unscreened = sum(s.error is None and s.suitability is None for s in outcome.symbols)
    lines.append(f"{outcome.written} runs written for {len(outcome.symbols)} symbol(s); "
                 f"{failed} run(s) and {broken} symbol(s) failed; {uncovered} coverage, "
                 f"{untabled} robustness and {unchecked} fill-check file(s) not written; "
                 f"{unscreened} suitability screen(s) not read; "
                 f"{len(outcome.universe_errors)} universe file(s) failed.")  # fmt: skip
    return "\n".join(lines)


def _describe_symbol(symbol: SymbolOutcome, out: Path, matrix: int) -> str:
    if symbol.error is not None:
        return f"{symbol.symbol}: FAILED: {symbol.error}"
    written = len(symbol.runs) - len(symbol.failed)
    coverage, robustness, checked = (
        _written(p) for p in (symbol.coverage, symbol.robustness, symbol.fill_check)
    )
    screen = "read" if symbol.suitability is not None else "NOT read: FAILED (see the log)"
    lines = [f"{symbol.symbol}: {written} of {matrix} runs written to "
             f"{(out / symbol.symbol).as_posix()}/; coverage.json {coverage}; "
             f"robustness.json {robustness}; fill_check.json {checked}; "
             f"suitability screen {screen}"]  # fmt: skip
    lines += [f"  FAILED {r.run_id}: {r.error}" for r in symbol.failed]
    return "\n".join(lines)


def _written(path: Path | None) -> str:
    return "written" if path is not None else "NOT written: FAILED (see the log)"


_SYMBOLS_HELP = ("A symbol to calibrate; repeat for more. Default: every symbol without a final "
                 "value (with --check: every calibrated symbol).")  # fmt: skip
Symbols = Annotated[list[str] | None, typer.Option("--symbol", help=_SYMBOLS_HELP)]
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
    """Calibrate each symbol's starting cash (Spec › E-L4) and write it, with its basis, into
    configs/universe.yaml. A symbol's value is provisional until it is calibrated under both
    strategies; a final one is never replaced, and other symbols' values are kept (DEC-30)."""
    log_path = configure_logging("calibrate")
    calendar = load_calendar()
    settings = _universe(calendar)
    symbols = _to_calibrate([s.upper() for s in symbol or []], settings, check=check)
    paths = config or [CONFIGS_DIR / f"{s}.yaml" for s in CALIBRATED_STRATEGIES]
    configs = [_run_config(p, settings) for p in paths]
    markets = {s: _market(cache, _underlying(s, settings), calendar, settings) for s in symbols}
    calibration = _calibrated(markets, configs, settings)
    _say(_describe_cash(calibration))
    if check:
        _check_matches(settings, calibration.cash)
    else:
        _write_cash(_merged(settings, calibration.cash), calendar)
    _say(f"Log: {log_path.as_posix()}")


def _to_calibrate(asked: list[str], settings: UniverseConfig, *, check: bool) -> list[str]:
    """The symbols to calibrate: those asked for, or by default every symbol without a final
    value (to write) or every calibrated one (to check). A final value is never rewritten."""
    current = settings.starting_cash
    if check:
        symbols = asked or ([] if current is None else [c.symbol for c in current.symbols])
        if not symbols:
            _fail("configs/universe.yaml has no starting cash to check: run pmcc calibrate")
        return symbols
    final = [u.symbol for u in settings.symbols if _is_final(settings.cash_of(u.symbol))]
    symbols = asked or [u.symbol for u in settings.symbols if u.symbol not in final]
    refused = [s for s in symbols if s in final]
    if refused or not symbols:
        _fail(f"{', '.join(refused or final)}: a final starting cash is never replaced. Remove "
              "its entry from configs/universe.yaml by hand to calibrate it again "
              "(DEC-30).")  # fmt: skip
    return symbols


def _is_final(cash: SymbolCash | None) -> bool:
    return cash is not None and not cash.provisional


def _merged(settings: UniverseConfig, new: StartingCash) -> StartingCash:
    """`new`'s symbols written over the file's, every other symbol's value kept."""
    try:
        return _over(settings, new)
    except ValueError as exc:
        _fail(f"{exc}; configs/universe.yaml is unchanged")


def _over(settings: UniverseConfig, new: StartingCash) -> StartingCash:
    """Raises `ValueError` if the file's block was calibrated under another E-L4 rule."""
    current = settings.starting_cash
    return new if current is None else current.merged(new, [u.symbol for u in settings.symbols])


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
    lines: list[str] = []
    for cash in calibration.cash.symbols:
        state = "provisional" if cash.provisional else "final"
        lines.append(f"{cash.symbol}: starting cash {cash.value.to_dollars()} ({state}), from:")
        lines += [
            f"  {e.strategy}: {e.contract} at {e.time.isoformat()}, {e.cost.to_dollars()}"
            for e in cash.entries
        ]
    lines.append("Available funds at each symbol's starting cash (reported, not refused; DEC-30):")
    lines += [
        f"  {f.symbol} {f.strategy}: lowest {f.lowest.to_dollars()} at {f.lowest_at.isoformat()}; "
        f"{f.negative_bars} bar(s) below zero"
        for f in calibration.funds
    ]
    return "\n".join(lines)


def _check_matches(settings: UniverseConfig, new: StartingCash) -> None:
    """Byte for byte: the file must be exactly what `pmcc calibrate` would write (DEC-93)."""
    try:
        text = UNIVERSE_PATH.read_text(encoding="utf-8")
        same = with_block(text, render_block(_over(settings, new))) == text
    except (OSError, ValueError, yaml.YAMLError):  # unreadable, set by hand, or another rule
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
        try:
            check_export_dir(out)  # never plant files in a directory export doesn't own
        except ExportError as exc:
            _fail(f"{exc}\nNothing was written.")
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
