"""`pmcc batch` (ARCHITECTURE §11): the run matrix on every universe symbol, one process per symbol.

A symbol's job loads and prices its cache once for the runs (`Market.prepare`), runs every config
of the matrix on it, and writes each result (`{out}/{SYM}/{run_id}.json`), then the symbol's files:
- `{SYM}/coverage.json`: the fetch summary's counts (DEC-16), which load and price the cache a
  second time as `pmcc fetch` does, and the strategies' stale-mark rate (HR-8);
- `{SYM}/robustness.json`: the ablation, friction, timing and grid tables from the runs' summaries
  (P6-06), written only when every run succeeded, since a table missing a row would mislead;
- `{SYM}/fill_check.json`: every trade print against its bar's mid, with the fits (P6-07, DEC-64),
  from the cache the runs loaded;
- the symbol's suitability-screen row (P6-08, DEC-66): quant's picks and G-3 read at each week's
  first week-open bar on the market the runs priced, handed back in its outcome, not written.

- **Failure isolation:** a run that fails writes nothing and is reported; the symbol's other runs
  go on. A symbol whose cache doesn't load, whose coverage or robustness file can't be written,
  or whose worker raises or dies, is reported without stopping the others (a fill check that
  can't be written, or a screen that can't be read, too); so is a universe file
  that fails. The caller exits non-zero if anything failed.
- **Processes:** each symbol has its own single-worker executor, so a worker that dies (an
  out-of-memory kill) breaks only its own symbol; at most one per CPU run at once. Workers are
  spawned on every OS, never forked, so Windows and Linux run alike (DEC-58) and no worker inherits
  the parent's polars threads. A job carries everything its worker needs, so a worker reads no
  config and no git state.
- **Determinism:** each run writes its own file, whose bytes never depend on which finished first
  (INV-13).
- **Universe-level outputs** are computed last, from every symbol's strategy runs, and only when
  nothing failed: a pooled figure over part of the universe would be wrong. `UNIVERSE_WRITERS`
  writes `universe/headline.json` (P6-01), `universe/pooled.json` (P6-05, its bootstrap seeded as
  every run's is), `universe/pooled_fill_check.json` (P6-07) and `universe/suitability.json`
  from each symbol's screen row (P6-08). A writer that fails is reported, and fails the batch.
"""

import multiprocessing
import os
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Future, ProcessPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import final

import structlog
from pydantic import BaseModel

from pmcc.analytics.fillcheck import fill_check, pooled_fill_check
from pmcc.analytics.robustness import robustness
from pmcc.analytics.scores import RunScore
from pmcc.analytics.suitability import (
    Screen,
    read_week,
    sample_bars,
    suitability,
    suitability_row,
)
from pmcc.analytics.universe import QUANT, headline, pooled
from pmcc.config.matrix import Family
from pmcc.config.strategy import Detail, RunConfig
from pmcc.config.universe import Underlying, Window
from pmcc.data import coverage as fetch_coverage
from pmcc.data.cache import CacheError, SymbolCache
from pmcc.data.calendar import CalendarMismatchError
from pmcc.data.discovery import UnitKind
from pmcc.data.files import replace_file
from pmcc.data.fillcheck import fill_pairs
from pmcc.data.load import SymbolData, load_symbol
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.errors import EngineError
from pmcc.domain.money import Money
from pmcc.export import canonical
from pmcc.export.analytics_models import Coverage, CoverageRow, FillCheck, SuitabilityRow
from pmcc.export.models import RunResult
from pmcc.export.results import write_result
from pmcc.export.verify import UNIVERSE_DIR
from pmcc.runner import Market, Stamp, run_market
from pmcc.strategy.registry import build_strategy

log = structlog.get_logger()

COVERAGE_FILE, ROBUSTNESS_FILE = "coverage.json", "robustness.json"
FILL_CHECK_FILE = "fill_check.json"
HEADLINE_FILE, POOLED_FILE = "headline.json", "pooled.json"
POOLED_FILL_CHECK_FILE, SUITABILITY_FILE = "pooled_fill_check.json", "suitability.json"

# The failures a run or a symbol is reported for; anything else is a bug, and kills the worker.
_RUN_FAILURES = (CacheError, EngineError, ValueError, OSError)
_SYMBOL_FAILURES = (CacheError, CalendarMismatchError, ValueError, OSError)


@final
@dataclass(frozen=True, slots=True)
class SymbolJob:
    """One symbol's share of the batch: everything its worker needs."""

    cache: Path
    underlying: Underlying
    calendar: SessionCalendar
    rate: float  # the universe's r, which every config runs at
    configs: tuple[RunConfig, ...]
    starting_cash: Money
    stamp: Stamp
    out: Path
    families: Mapping[str, Family]  # each run ID's robustness table (P6-06)
    seed: int  # the bootstrap's (DEC-61)
    window: Window  # every config's, which the fill check's pairs lie in (P6-07)


@final
@dataclass(frozen=True, slots=True)
class RunOutcome:
    run_id: str
    path: Path | None  # the result written, or None if the run failed
    error: str | None = None


@final
@dataclass(frozen=True, slots=True)
class SymbolOutcome:
    symbol: str
    runs: tuple[RunOutcome, ...]
    coverage: Path | None  # None if it wasn't written: a failure too
    error: str | None = None  # the symbol itself failed: its cache didn't load, or its worker died
    robustness: Path | None = None  # None if any run failed, or it couldn't be written
    fill_check: Path | None = None  # None if it couldn't be written
    suitability: SuitabilityRow | None = None  # None if the screen couldn't be read

    @property
    def failed(self) -> tuple[RunOutcome, ...]:
        return tuple(r for r in self.runs if r.error is not None)

    @property
    def ok(self) -> bool:
        files = (self.coverage, self.robustness, self.fill_check)
        screened = self.suitability is not None
        return self.error is None and not self.failed and None not in files and screened


@final
@dataclass(frozen=True, slots=True)
class UniverseStage:
    """What a universe writer reads: every symbol's outcome, where to write, the bootstrap seed."""

    outcomes: Sequence[SymbolOutcome]
    out: Path
    seed: int

    def strategy_scores(self) -> dict[str, list[RunScore]]:
        """Each symbol's strategy runs, read back from their files (never a variant)."""
        return {o.symbol: [RunScore.of(RunResult.model_validate_json(r.path.read_bytes()))
                           for r in o.runs if r.path is not None and "--" not in r.run_id]
                for o in self.outcomes}  # fmt: skip

    def fill_checks(self) -> list[FillCheck]:
        """Each symbol's fill check, read back from its file."""
        return [FillCheck.model_validate_json(o.fill_check.read_bytes())
                for o in self.outcomes if o.fill_check is not None]  # fmt: skip

    def suitability_rows(self) -> list[SuitabilityRow]:
        """Each symbol's screen row, as its worker read it."""
        return [o.suitability for o in self.outcomes if o.suitability is not None]


type UniverseWriter = Callable[[UniverseStage], Path]


def write_headline(stage: UniverseStage) -> Path:
    """`universe/headline.json`: symbol × strategy (P6-01)."""
    return _write(stage.out / UNIVERSE_DIR / HEADLINE_FILE, headline(stage.strategy_scores()))


def write_pooled(stage: UniverseStage) -> Path:
    """`universe/pooled.json`: each strategy over every symbol (P6-05, DEC-61)."""
    path = stage.out / UNIVERSE_DIR / POOLED_FILE
    return _write(path, pooled(stage.strategy_scores(), stage.seed))


def write_pooled_fill_check(stage: UniverseStage) -> Path:
    """`universe/pooled_fill_check.json`: each group's fit over every symbol (P6-07, DEC-64)."""
    path = stage.out / UNIVERSE_DIR / POOLED_FILL_CHECK_FILE
    return _write(path, pooled_fill_check(stage.fill_checks()))


def write_suitability(stage: UniverseStage) -> Path:
    """`universe/suitability.json`: each symbol's screen row (P6-08, DEC-66)."""
    path = stage.out / UNIVERSE_DIR / SUITABILITY_FILE
    return _write(path, suitability(stage.suitability_rows()))


UNIVERSE_WRITERS: tuple[UniverseWriter, ...] = (write_headline, write_pooled,
                                                write_pooled_fill_check,
                                                write_suitability)  # fmt: skip
"""Each writes one universe file and returns its path. The screen reads each symbol's priced
market, which only its worker holds, so the worker hands its row back in its outcome (DEC-104)."""


@final
@dataclass(frozen=True, slots=True)
class BatchOutcome:
    symbols: tuple[SymbolOutcome, ...]
    universe: tuple[Path, ...]  # the universe files written
    universe_errors: tuple[str, ...] = ()  # a universe file that failed

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.symbols) and not self.universe_errors

    @property
    def written(self) -> int:
        return sum(r.path is not None for s in self.symbols for r in s.runs)


def run_batch(jobs: Sequence[SymbolJob], out: Path, *, seed: int,
              initializer: Callable[[], None]) -> BatchOutcome:  # fmt: skip
    """Each job in its own spawned worker process, up to one per CPU at once, then the
    universe-level outputs under `out`, their bootstrap seeded with `seed`. `initializer` runs
    first in each worker and must set up its logging (`pmcc.cli` owns that, DEC-80): structlog's
    default console renderer can't encode a traceback on a Windows code page, and a failed run's
    log line would then kill the worker."""
    at_once = max(1, os.cpu_count() or 1)
    outcomes: list[SymbolOutcome] = []
    for first in range(0, len(jobs), at_once):
        outcomes += _run_together(jobs[first : first + at_once], initializer)
    if not all(o.ok for o in outcomes):
        return BatchOutcome(tuple(outcomes), ())
    written, errors = write_universe(UniverseStage(tuple(outcomes), out, seed))
    return BatchOutcome(tuple(outcomes), written, errors)


def write_universe(stage: UniverseStage) -> tuple[tuple[Path, ...], tuple[str, ...]]:
    """Every universe file; one that fails is reported and the rest still written."""
    written: list[Path] = []
    errors: list[str] = []
    for writer in UNIVERSE_WRITERS:
        try:
            written.append(writer(stage))
        except (ValueError, OSError) as exc:
            log.exception("batch.universe.abort", writer=writer.__name__)
            errors.append(f"{writer.__name__}: {exc}")
    return tuple(written), tuple(errors)


def _run_together(jobs: Sequence[SymbolJob],
                  initializer: Callable[[], None]) -> list[SymbolOutcome]:  # fmt: skip
    """`jobs` at once, each in its own single-worker executor, so one dying worker can't break
    another's (a shared pool would fail every job with BrokenProcessPool)."""
    context = multiprocessing.get_context("spawn")
    with ExitStack() as stack:
        futures = [
            stack.enter_context(
                ProcessPoolExecutor(1, mp_context=context, initializer=initializer)
            ).submit(run_job, job)
            for job in jobs
        ]
        return [_outcome(job, f) for job, f in zip(jobs, futures, strict=True)]


def _outcome(job: SymbolJob, future: "Future[SymbolOutcome]") -> SymbolOutcome:
    """The job's outcome, or its symbol reported failed if its worker raised or died."""
    try:
        return future.result()
    except Exception as exc:  # isolation: one symbol's crash must not stop the batch
        symbol = job.underlying.symbol
        log.error("batch.symbol.abort", symbol=symbol, message=repr(exc))
        where = (job.out / symbol).as_posix()
        return SymbolOutcome(symbol, (), None, f"its worker failed: {exc!r}. Runs it finished "
                             f"before that may already be written under {where}/; rerun the "
                             "batch")  # fmt: skip


def run_job(job: SymbolJob) -> SymbolOutcome:
    """Every config of `job` on its symbol, then the symbol's coverage, robustness and fill-check
    files and its suitability-screen row."""
    symbol = job.underlying.symbol
    try:
        loaded = load_symbol(job.cache, symbol, job.calendar)
        market = Market.prepare(loaded, job.underlying.option_root, job.rate)
    except _SYMBOL_FAILURES as exc:
        log.error("batch.symbol.abort", symbol=symbol, message=str(exc))
        return SymbolOutcome(symbol, (), None, str(exc))
    ran = [_run(market, config, job) for config in job.configs]
    runs = tuple(outcome for outcome, _ in ran)
    results = [result for _, result in ran if result is not None]
    covered = _write_coverage(job, results)
    robust = _write_robustness(job, results) if len(results) == len(runs) else None
    checked = _write_fill_check(job, loaded)
    screened = _screen(job, market)
    log.info("batch.symbol.done", symbol=symbol, runs=len(runs), failed=sum(
        r.error is not None for r in runs))  # fmt: skip
    return SymbolOutcome(symbol, runs, covered, robustness=robust, fill_check=checked,
                         suitability=screened)  # fmt: skip


def _run(market: Market, config: RunConfig, job: SymbolJob) -> tuple[RunOutcome, RunResult | None]:
    run_id = config.strategy.id
    try:
        result = run_market(market, config, job.starting_cash, job.stamp, seed=job.seed)
        path = write_result(result, job.out)
    except _RUN_FAILURES as exc:
        log.exception("run.abort", symbol=job.underlying.symbol, run_id=run_id)
        return RunOutcome(run_id, None, str(exc)), None
    return RunOutcome(run_id, path), result


def _write_coverage(job: SymbolJob, results: Sequence[RunResult]) -> Path | None:
    """`{SYM}/coverage.json`, or None (logged) if the cache can't be summarized."""
    symbol = job.underlying.symbol
    try:
        summary = fetch_coverage.coverage(job.cache, symbol, job.calendar, job.rate)
        return _write(job.out / symbol / COVERAGE_FILE, coverage_file(summary, results))
    except _SYMBOL_FAILURES:
        log.exception("batch.coverage.abort", symbol=symbol)
        return None


def _write_robustness(job: SymbolJob, results: Sequence[RunResult]) -> Path | None:
    """`{SYM}/robustness.json` from every run's summary, or None (logged) if it can't be built."""
    symbol = job.underlying.symbol
    try:
        tables = robustness(symbol, [RunScore.of(r) for r in results], job.families)
        return _write(job.out / symbol / ROBUSTNESS_FILE, tables)
    except (ValueError, OSError):
        log.exception("batch.robustness.abort", symbol=symbol)
        return None


def _write_fill_check(job: SymbolJob, loaded: SymbolData) -> Path | None:
    """`{SYM}/fill_check.json` from the loaded cache, or None (logged) if it can't be written."""
    symbol = job.underlying.symbol
    try:
        units = SymbolCache(job.cache, symbol).units()
        groups = fill_pairs(loaded, units, (job.window.start, job.window.end))
        return _write(job.out / symbol / FILL_CHECK_FILE, fill_check(symbol, groups))
    except _SYMBOL_FAILURES:
        log.exception("batch.fill_check.abort", symbol=symbol)
        return None


def _screen(job: SymbolJob, market: Market) -> SuitabilityRow | None:
    """The symbol's suitability-screen row from quant's rules (P6-08, DEC-66), or None (logged)
    if it can't be read."""
    symbol = job.underlying.symbol
    try:
        quant = next((c for c in job.configs if c.strategy.id == QUANT), None)
        if quant is None:
            raise ValueError(f"the suitability screen reads {QUANT}'s rules; the matrix lacks it")
        screen = Screen.of(build_strategy(quant.strategy))
        bars = sample_bars(job.calendar, job.window.start, job.window.end)
        readings = [read_week(market.data.view(end), screen) for end in bars]
        return suitability_row(symbol, readings, screen)
    except (*_RUN_FAILURES, CalendarMismatchError):
        log.exception("batch.suitability.abort", symbol=symbol)
        return None


def _write(path: Path, model: BaseModel) -> Path:
    """`model` as canonical JSON at `path`, replacing it whole."""
    replace_file(path, canonical.to_bytes(model.model_dump()))
    return path


def coverage_file(summary: fetch_coverage.Coverage, results: Sequence[RunResult]) -> Coverage:
    """The coverage file from the fetch summary (DEC-16) and the full-detail runs' ledgers."""
    rows = tuple(
        CoverageRow(
            kind=kind.value,
            requested=t.requested,
            answered=t.answered,
            unanswered=t.unanswered,
            mid_availability=t.share,
        )
        for kind in UnitKind
        if (t := summary.by_kind.get(kind)) is not None
    )
    iv = summary.iv
    return Coverage(
        symbol=summary.symbol,
        rows=rows,
        iv_priced=iv.priced,
        iv_failures={code.name.lower(): n for code, n in iv.failed.items()},
        stale_mark_rate=stale_mark_rate(results),
        unavailable_fields=tuple(sorted({f for u in summary.units for f in u.fields_missing})),
    )


def stale_mark_rate(results: Sequence[RunResult]) -> float | None:
    """The share of held positions' marks carried stale, over every bar of the full-detail runs'
    ledgers; None if nothing was held."""
    marks = stale = 0
    for result in results:
        if result.config.strategy.report.detail is not Detail.FULL:
            continue
        for row in result.ledger or ():
            held = [p for p in (row.long, row.short, row.stock) if p is not None]
            marks += len(held)
            stale += sum(p.stale for p in held)
    return stale / marks if marks else None
