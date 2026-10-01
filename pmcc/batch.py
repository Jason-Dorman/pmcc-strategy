"""`pmcc batch` (ARCHITECTURE §11): the run matrix on every universe symbol, one process per symbol.

A symbol's job loads and prices its cache once for the runs (`Market.prepare`), runs every config
of the matrix on it, and writes each result (`{out}/{SYM}/{run_id}.json`), then the symbol's
coverage file (`{SYM}/coverage.json`): the fetch summary's counts (DEC-16), which load and price
the cache a second time as `pmcc fetch` does, and the strategies' stale-mark rate (HR-8).

- **Failure isolation:** a run that fails writes nothing and is reported; the symbol's other runs
  go on. A symbol whose cache doesn't load, whose coverage file can't be written, or whose worker
  raises or dies, is reported without stopping the others. The caller exits non-zero if anything
  failed.
- **Processes:** each symbol has its own single-worker executor, so a worker that dies (an
  out-of-memory kill) breaks only its own symbol; at most one per CPU run at once. Workers are
  spawned on every OS, never forked, so Windows and Linux run alike (DEC-58) and no worker inherits
  the parent's polars threads. A job carries everything its worker needs, so a worker reads no
  config and no git state.
- **Determinism:** each run writes its own file, whose bytes never depend on which finished first
  (INV-13).
- **Universe-level outputs** (pooled, headline, suitability) are computed last, from every
  symbol's outcome, and only when nothing failed: a pooled figure over part of the universe would
  be wrong. Their writers join at P6-01, P6-05 and P6-08 (PO, 2026-09-30), in `UNIVERSE_WRITERS`.
"""

import multiprocessing
import os
from collections.abc import Callable, Sequence
from concurrent.futures import Future, ProcessPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import final

import structlog

from pmcc.config.strategy import Detail, RunConfig
from pmcc.config.universe import Underlying
from pmcc.data import coverage as fetch_coverage
from pmcc.data.cache import CacheError
from pmcc.data.calendar import CalendarMismatchError
from pmcc.data.discovery import UnitKind
from pmcc.data.files import replace_file
from pmcc.data.load import load_symbol
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.errors import EngineError
from pmcc.domain.money import Money
from pmcc.export import canonical
from pmcc.export.analytics_models import Coverage, CoverageRow
from pmcc.export.models import RunResult
from pmcc.export.results import write_result
from pmcc.runner import Market, Stamp, run_market

log = structlog.get_logger()

COVERAGE_FILE = "coverage.json"

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

    @property
    def failed(self) -> tuple[RunOutcome, ...]:
        return tuple(r for r in self.runs if r.error is not None)

    @property
    def ok(self) -> bool:
        return self.error is None and not self.failed and self.coverage is not None


type UniverseWriter = Callable[[Sequence[SymbolOutcome], Path], Path]

UNIVERSE_WRITERS: tuple[UniverseWriter, ...] = ()
"""Each writes one universe file from every symbol's outcome and returns its path: pooled
(P6-05), headline (P6-01) and suitability (P6-08) join here."""


@final
@dataclass(frozen=True, slots=True)
class BatchOutcome:
    symbols: tuple[SymbolOutcome, ...]
    universe: tuple[Path, ...]  # the universe files written

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.symbols)

    @property
    def written(self) -> int:
        return sum(r.path is not None for s in self.symbols for r in s.runs)


def run_batch(jobs: Sequence[SymbolJob], out: Path, *,
              initializer: Callable[[], None]) -> BatchOutcome:  # fmt: skip
    """Each job in its own spawned worker process, up to one per CPU at once, then the
    universe-level outputs under `out`. `initializer` runs first in each worker and must set up
    its logging (`pmcc.cli` owns that, DEC-80): structlog's default console renderer can't encode
    a traceback on a Windows code page, and a failed run's log line would then kill the worker."""
    at_once = max(1, os.cpu_count() or 1)
    outcomes: list[SymbolOutcome] = []
    for first in range(0, len(jobs), at_once):
        outcomes += _run_together(jobs[first : first + at_once], initializer)
    universe = tuple(w(outcomes, out) for w in UNIVERSE_WRITERS) if all(
        o.ok for o in outcomes) else ()  # fmt: skip
    return BatchOutcome(tuple(outcomes), universe)


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
    """Every config of `job` on its symbol, then the symbol's coverage file."""
    symbol = job.underlying.symbol
    try:
        loaded = load_symbol(job.cache, symbol, job.calendar)
        market = Market.prepare(loaded, job.underlying.option_root, job.rate)
    except _SYMBOL_FAILURES as exc:
        log.error("batch.symbol.abort", symbol=symbol, message=str(exc))
        return SymbolOutcome(symbol, (), None, str(exc))
    ran = [_run(market, config, job) for config in job.configs]
    runs = tuple(outcome for outcome, _ in ran)
    covered = _write_coverage(job, [result for _, result in ran if result is not None])
    log.info("batch.symbol.done", symbol=symbol, runs=len(runs), failed=sum(
        r.error is not None for r in runs))  # fmt: skip
    return SymbolOutcome(symbol, runs, covered)


def _run(market: Market, config: RunConfig, job: SymbolJob) -> tuple[RunOutcome, RunResult | None]:
    run_id = config.strategy.id
    try:
        result = run_market(market, config, job.starting_cash, job.stamp)
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
        path = job.out / symbol / COVERAGE_FILE
        replace_file(path, canonical.to_bytes(coverage_file(summary, results).model_dump()))
    except _SYMBOL_FAILURES:
        log.exception("batch.coverage.abort", symbol=symbol)
        return None
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
