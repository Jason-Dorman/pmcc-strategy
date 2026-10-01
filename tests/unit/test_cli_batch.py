"""`pmcc batch` (P5-03): the 24-run matrix on every universe symbol, one spawned process per symbol,
each symbol's coverage file, failure isolation, and the universe-level stage (ARCHITECTURE §11).

Two synthetic symbols, SYN and TWO, are the `random_walk` market under two names, cached in a
temporary directory. A test universe in the working directory stands in for configs/universe.yaml,
as in `test_cli_run.py`; provenance is fixed and clean, so `pmcc verify` can check what the batch
wrote. Workers are real processes: they get everything through their job, never a monkeypatch.
"""

import dataclasses
import os
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pmcc import batch, cli
from pmcc.batch import SymbolJob, SymbolOutcome, run_batch, run_job, stale_mark_rate
from pmcc.cli import app
from pmcc.config.calendar import load_calendar
from pmcc.config.matrix import run_matrix
from pmcc.config.strategy import CONFIGS_DIR
from pmcc.config.universe import UNIVERSE_PATH, Underlying, Universe, read_universe_file
from pmcc.data import coverage as fetch_coverage
from pmcc.data.discovery import UnitKind
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET
from pmcc.domain.money import Money
from pmcc.export.analytics_models import Coverage
from pmcc.export.manifest import GitState, Provenance
from pmcc.export.models import DataSource, LedgerRowOut, RunResult
from pmcc.export.verify import verify
from pmcc.runner import Stamp
from tests.fixtures.synthetic.market import generate
from tests.fixtures.synthetic.scenarios import random_walk

NOW = datetime(2026, 9, 30, 9, tzinfo=ET)
SYMBOLS = ("SYN", "TWO")
RUNS = 24  # per symbol (ARCHITECTURE §11)

runner = CliRunner()


def _provenance() -> Provenance:
    return Provenance(GitState("a" * 40, False), "b" * 64, "0.0.0")


def _universe(symbols: Sequence[str] = SYMBOLS) -> str:
    """A final starting cash of $15,000 on every symbol: 2 × $5,000 rounds up to $10,000 (DEC-30),
    so the entries say $7,500."""
    spec = random_walk()
    shipped = UNIVERSE_PATH.read_text(encoding="utf-8")
    rate = shipped[shipped.index("risk_free_rate:") : shipped.index("# The universe")]
    listed = "".join(f"  - {{symbol: {s}, stock_ric: {s}.O, option_root: {s}}}\n" for s in symbols)
    entries = ", ".join(
        f"{{symbol: {s}, strategy: {t}, time: '{NOW.isoformat()}', contract: X, cost: 7500}}"
        for s in symbols for t in ("baseline_pmcc", "quant_pmcc")
    )  # fmt: skip
    return (
        f"window: {{start: {spec.window_start}, end: {spec.window_end}}}\n{rate}symbols:\n{listed}"
        "starting_cash: {value: 15000, provisional: false, cash_multiple: 2, cash_round_to: 5000, "
        f"calibration_cash: 1000000, entries: [{entries}]}}\n"
    )


@pytest.fixture(scope="module")
def market(tmp_path_factory: pytest.TempPathFactory) -> Path:
    cache = tmp_path_factory.mktemp("market")
    for symbol in SYMBOLS:
        generate(dataclasses.replace(random_walk(), symbol=symbol), cache)
    return cache


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)  # logs/ and results/ land here, the workers' too
    Path("universe.yaml").write_text(_universe(), encoding="utf-8", newline="\n")

    def stand_in(_calendar: SessionCalendar) -> Universe:
        return read_universe_file(Path("universe.yaml"))

    monkeypatch.setattr(cli, "load_universe", stand_in)
    monkeypatch.setattr(cli, "provenance", _provenance)
    monkeypatch.setattr(cli, "_now", lambda: NOW)
    return tmp_path


def _batch(cache: Path, *extra: str) -> tuple[int, str]:
    result = runner.invoke(app, ["batch", "--cache", str(cache), *extra])
    return result.exit_code, result.output


def _runs(symbol: str, out: str = "results") -> list[str]:
    return sorted(p.stem for p in Path(out, symbol).glob("*.json") if p.stem != "coverage")


# ---- the CLI, through the process pool --------------------------------------------------------


def test_p5_03_batch_writes_every_run_and_coverage_for_each_symbol(
    workdir: Path, market: Path
) -> None:
    """As the justfile runs it, `--universe configs/universe.yaml`, written under `--out`."""
    code, output = _batch(market, "--universe", str(UNIVERSE_PATH), "--out", "elsewhere")

    assert code == 0, output
    assert not Path("results").exists()  # --out is where it writes
    universe = read_universe_file(Path("universe.yaml"))
    matrix = sorted(c.strategy.id for c in run_matrix(universe))
    for symbol in SYMBOLS:
        assert _runs(symbol, "elsewhere") == matrix
        assert f"{symbol}: {RUNS} of {RUNS} runs written" in output
        coverage = Coverage.model_validate_json(
            Path("elsewhere", symbol, "coverage.json").read_bytes()
        )
        assert coverage.symbol == symbol
        assert {r.kind for r in coverage.rows} >= {"stock", "puts"}
    assert len(matrix) * len(SYMBOLS) == 48
    assert ("48 runs written for 2 symbol(s); 0 run(s) and 0 symbol(s) failed; 0 coverage "
            "file(s) not written.") in output  # fmt: skip
    assert "Universe files: none yet (P6)" in output
    assert sorted(p.name for p in Path("logs").glob("batch_*_worker*.jsonl"))  # workers log apart
    verified = verify(Path("elsewhere"))  # schema, canonical bytes, a clean tree, the invariants
    assert verified.problems == ()
    assert (verified.runs, verified.files) == (48, 50)

    # A run in the batch is the run `pmcc run` makes (both stamp the same clock here).
    config = (CONFIGS_DIR / "quant_pmcc.yaml").as_posix()
    single = runner.invoke(app, ["run", "--symbol", "SYN", "--config", config,
                                 "--cache", str(market), "--out", "single"])  # fmt: skip
    assert single.exit_code == 0, single.output
    assert Path("single/SYN/quant_pmcc.json").read_bytes() == Path(
        "elsewhere/SYN/quant_pmcc.json").read_bytes()  # fmt: skip


def test_p5_03_batch_exits_non_zero_when_a_symbol_fails_and_writes_the_rest(
    workdir: Path, market: Path
) -> None:
    """GONE has no cache: it is reported, and SYN and TWO are still written in full."""
    Path("universe.yaml").write_text(_universe((*SYMBOLS, "GONE")), encoding="utf-8")

    code, output = _batch(market)

    assert code == 1
    assert "GONE: FAILED:" in output
    assert "48 runs written for 3 symbol(s); 0 run(s) and 1 symbol(s) failed;" in output
    for symbol in SYMBOLS:
        assert len(_runs(symbol)) == RUNS
    assert not Path("results/GONE").exists()


def test_p5_03_batch_refuses_another_universe_file(workdir: Path, market: Path) -> None:
    code, output = _batch(market, "--universe", "universe.yaml")

    assert code == 1
    assert "the universe is always configs/universe.yaml" in output
    assert not Path("results").exists()


def test_p5_03_batch_refuses_a_universe_without_starting_cash(workdir: Path, market: Path) -> None:
    text = _universe()
    Path("universe.yaml").write_text(text[: text.index("starting_cash")], encoding="utf-8")

    code, output = _batch(market)

    assert code == 1
    assert "run pmcc calibrate" in output


# ---- one symbol's job, in this process ----------------------------------------------------------


def _job(market: Path, out: Path, symbol: str = "SYN", rate: float | None = None) -> SymbolJob:
    universe = read_universe_file(Path("universe.yaml"))
    configs = run_matrix(universe)
    stamp = Stamp(_provenance(), DataSource.LSEG, NOW)
    underlying = Underlying(symbol=symbol, stock_ric=f"{symbol}.O", option_root=symbol)
    return SymbolJob(market, underlying, load_calendar(), rate or universe.risk_free_rate.value,
                     configs, Money.from_dollars(15_000), stamp, out)  # fmt: skip


def test_p5_03_a_failed_run_writes_nothing_and_the_rest_go_on(workdir: Path, market: Path) -> None:
    """Priced at another r, every config refuses the market (runner.run_output): each run fails
    alone, and the symbol's coverage is still written."""
    job = _job(market, Path("out"))
    rate = job.configs[3].risk_free_rate.model_copy(update={"value": 0.05})
    bad = job.configs[3].model_copy(update={"risk_free_rate": rate})
    job = dataclasses.replace(job, configs=(*job.configs[:3], bad, *job.configs[4:]))

    outcome = run_job(job)

    assert [r.run_id for r in outcome.failed] == [bad.strategy.id]
    assert "priced at" in (outcome.failed[0].error or "")
    assert not Path("out/SYN", f"{bad.strategy.id}.json").exists()
    assert len([r for r in outcome.runs if r.path is not None]) == RUNS - 1
    assert outcome.coverage == Path("out/SYN/coverage.json")
    assert not outcome.ok


def test_p5_03_a_symbol_without_a_cache_is_reported_not_raised(workdir: Path, market: Path) -> None:
    outcome = run_job(_job(market, Path("out"), symbol="GONE"))

    assert (outcome.runs, outcome.coverage) == ((), None)
    assert outcome.error
    assert not outcome.ok


def test_p5_03_a_coverage_file_not_written_fails_the_symbol(workdir: Path, market: Path) -> None:
    """A directory where the file goes stands in for a file locked on Windows."""
    Path("out/SYN/coverage.json").mkdir(parents=True)

    outcome = run_job(_job(market, Path("out")))

    assert len([r for r in outcome.runs if r.path is not None]) == RUNS
    assert (outcome.coverage, outcome.ok) == (None, False)


def test_hr_8_coverage_file_maps_the_fetch_summary_field_by_field(
    workdir: Path, market: Path
) -> None:
    job = _job(market, Path("out"))
    run_job(job)
    coverage = Coverage.model_validate_json(Path("out/SYN/coverage.json").read_bytes())
    summary = fetch_coverage.coverage(market, "SYN", job.calendar, job.rate)

    expected = [(k.value, t.requested, t.answered, t.unanswered, round(t.share or 0, 6))
                for k in UnitKind if (t := summary.by_kind.get(k)) is not None]  # fmt: skip
    rows = [(r.kind, r.requested, r.answered, r.unanswered, r.mid_availability or 0)
            for r in coverage.rows]  # fmt: skip
    assert rows == expected
    assert coverage.iv_priced == summary.iv.priced
    assert coverage.iv_failures == {c.name.lower(): n for c, n in summary.iv.failed.items()}
    assert sum(coverage.iv_failures.values()) > 0
    fields = sorted({f for u in summary.units for f in u.fields_missing})
    assert list(coverage.unavailable_fields) == fields


def test_hr_8_coverage_file_counts_the_cache_and_the_strategies_stale_marks(
    workdir: Path, market: Path
) -> None:
    outcome = run_job(_job(market, Path("out")))

    assert outcome.ok
    raw = Path("out/SYN/coverage.json").read_bytes()
    coverage = Coverage.model_validate_json(raw)
    assert coverage.rows[0].kind == "stock"
    assert all(r.requested == r.answered + r.unanswered for r in coverage.rows)
    assert set(coverage.iv_failures) == {"below_floor", "above_cap", "no_convergence", "no_spot"}
    assert coverage.iv_priced >= sum(coverage.iv_failures.values())
    full = [RunResult.model_validate_json(Path("out/SYN", f"{s}.json").read_bytes())
            for s in ("baseline_pmcc", "quant_pmcc")]  # fmt: skip
    assert coverage.stale_mark_rate == round(stale_mark_rate(full) or 0, 6)  # 6 dp (DEC-50)
    assert verify(Path("out")).problems == ()


def test_hr_8_stale_mark_rate_counts_held_marks_over_full_runs_only(
    workdir: Path, market: Path
) -> None:
    """One stale mark among every held position's marks; a summary run, with no ledger, adds
    nothing."""
    run_job(_job(market, Path("out")))
    full = RunResult.model_validate_json(Path("out/SYN/baseline_pmcc.json").read_bytes())
    summary = RunResult.model_validate_json(Path("out/SYN/quant_pmcc--a1.json").read_bytes())
    assert full.ledger is not None
    rows = [_stale(row, False) for row in full.ledger]
    first = next(i for i, r in enumerate(rows) if r.long is not None)
    rows[first] = _stale(rows[first], True)
    marked = full.model_copy(update={"ledger": tuple(rows)})
    held = sum(p is not None for r in rows for p in (r.long, r.short, r.stock))

    assert held > len([r for r in rows if r.long is not None])  # shorts are held too
    assert stale_mark_rate([marked, summary]) == pytest.approx(1 / held)
    assert stale_mark_rate([marked, marked]) == pytest.approx(1 / held)
    assert stale_mark_rate([summary]) is None
    assert stale_mark_rate([]) is None


def _stale(row: LedgerRowOut, stale: bool) -> LedgerRowOut:
    """`row` with every held position's mark `stale` (the long's only, when `stale`)."""
    if stale:
        assert row.long is not None
        return row.model_copy(update={"long": row.long.model_copy(update={"stale": True})})
    update = {name: None if (p := getattr(row, name)) is None else p.model_copy(
        update={"stale": False}) for name in ("long", "short", "stock")}  # fmt: skip
    return row.model_copy(update=update)


# ---- the universe-level stage -------------------------------------------------------------------


def test_p5_03_universe_writers_run_last_and_only_when_nothing_failed(
    workdir: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: list[tuple[str, ...]] = []

    def writer(outcomes: Sequence[SymbolOutcome], out: Path) -> Path:
        seen.append(tuple(o.symbol for o in outcomes))
        assert all(len(_runs(o.symbol)) == RUNS for o in outcomes)  # every run is written first
        path = out / "universe" / "test.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
        return path

    monkeypatch.setattr(batch, "UNIVERSE_WRITERS", (writer,))
    jobs = [_job(market, Path("results"), symbol=s) for s in SYMBOLS]

    done = run_batch(jobs, Path("results"), initializer=cli.worker_logging)
    assert done.ok
    assert seen == [SYMBOLS]
    assert done.universe == (Path("results/universe/test.json"),)

    # Every kind of failure at once, each isolated: a failed run, a worker that raises something
    # unexpected, and a worker that dies (as an out-of-memory kill would).
    good = _job(market, Path("isolated"), symbol="SYN")
    rate = good.configs[3].risk_free_rate.model_copy(update={"value": 0.05})
    bad = good.configs[3].model_copy(update={"risk_free_rate": rate})
    failing = _job(market, Path("isolated"), symbol="TWO")
    failing = dataclasses.replace(failing, configs=(*good.configs[:3], bad, *good.configs[4:]))
    raising = dataclasses.replace(_job(market, Path("raised"), symbol="SYN"),
                                  calendar=None)  # type: ignore[arg-type]  # fmt: skip
    dying = dataclasses.replace(_job(market, Path("died"), symbol="TWO"),
                                starting_cash=_DiesWhenUnpickled())  # type: ignore[arg-type]  # fmt: skip

    broken = run_batch([good, failing, raising, dying], Path("isolated"),
                       initializer=cli.worker_logging)  # fmt: skip

    assert not broken.ok
    assert broken.universe == ()
    assert seen == [SYMBOLS]  # not run again
    ok, one_failed, raised, died = broken.symbols
    assert ok.ok
    assert _runs("SYN", "isolated") == sorted(c.strategy.id for c in good.configs)
    assert [r.run_id for r in one_failed.failed] == [bad.strategy.id]
    assert len(_runs("TWO", "isolated")) == RUNS - 1
    assert "its worker failed: AttributeError" in (raised.error or "")
    assert "its worker failed: BrokenProcessPool" in (died.error or "")
    assert broken.written == 2 * RUNS - 1


class _DiesWhenUnpickled:
    """Kills the worker process that unpickles it: a stand-in for an out-of-memory kill."""

    def __reduce__(self) -> tuple[object, tuple[int]]:
        return os._exit, (3,)
