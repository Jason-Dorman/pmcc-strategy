"""`pmcc batch` (P5-03): the 24-run matrix on every universe symbol, one spawned process per symbol,
each symbol's coverage, robustness (P6-06) and fill-check (P6-07) files and suitability screen
(P6-08), failure isolation, and the universe-level stage with its headline, pooled, pooled
fill-check and suitability files (P6-01, P6-05, P6-07, P6-08) (ARCHITECTURE §11).

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
from pmcc.analytics.bootstrap import mean_ci
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
from pmcc.batch import (
    BatchOutcome,
    RunOutcome,
    SymbolJob,
    SymbolOutcome,
    UniverseStage,
    run_batch,
    run_job,
    stale_mark_rate,
)
from pmcc.cli import app
from pmcc.config.calendar import load_calendar
from pmcc.config.matrix import run_families, run_matrix
from pmcc.config.strategy import CONFIGS_DIR, load_strategy
from pmcc.config.universe import UNIVERSE_PATH, Underlying, Universe, Window, read_universe_file
from pmcc.data import coverage as fetch_coverage
from pmcc.data.cache import SymbolCache
from pmcc.data.discovery import UnitKind
from pmcc.data.fillcheck import fill_pairs
from pmcc.data.load import load_symbol
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET
from pmcc.domain.money import Money
from pmcc.export import canonical
from pmcc.export.analytics_models import (
    Coverage,
    FillCheck,
    Headline,
    Metrics,
    Pooled,
    PooledFillCheck,
    Robustness,
    Suitability,
    SuitabilityRow,
)
from pmcc.export.manifest import GitState, Provenance
from pmcc.export.models import DataSource, LedgerRowOut, RunResult
from pmcc.export.verify import verify
from pmcc.runner import Market, Stamp
from pmcc.strategy.registry import build_strategy
from tests.fixtures.synthetic.market import generate
from tests.fixtures.synthetic.scenarios import random_walk

NOW = datetime(2026, 9, 30, 9, tzinfo=ET)
SYMBOLS = ("SYN", "TWO")
RUNS = 24  # per symbol (ARCHITECTURE §11)
SEED = 7  # the test universe's bootstrap seed: not the shipped 535, so a hardcoded seed fails

runner = CliRunner()


def _provenance() -> Provenance:
    return Provenance(GitState("a" * 40, False), "b" * 64, "0.0.0")


CASH = {"SYN": 15_000, "TWO": 25_000, "GONE": 15_000}  # each symbol's own (PO, DEC-30)
COSTS = {"SYN": 7_500, "TWO": 12_000, "GONE": 7_500}  # 2× each, rounded up to $5,000


def _universe(symbols: Sequence[str] = SYMBOLS, calibrated: Sequence[str] | None = None) -> str:
    """Each `calibrated` symbol's own final starting cash (default: every symbol): SYN's $7,500
    entries give $15,000 and TWO's $12,000 give $25,000 (2× each, rounded up to $5,000; DEC-30)."""
    calibrated = symbols if calibrated is None else calibrated
    spec = random_walk()
    shipped = UNIVERSE_PATH.read_text(encoding="utf-8")
    rate = shipped[shipped.index("risk_free_rate:") : shipped.index("# The universe")]
    assert "seed: 535" in rate
    rate = rate.replace("seed: 535", f"seed: {SEED}")
    listed = "".join(f"  - {{symbol: {s}, stock_ric: {s}.O, option_root: {s}}}\n" for s in symbols)

    def cash(s: str) -> str:
        entries = ", ".join(
            f"{{strategy: {t}, time: '{NOW.isoformat()}', contract: X, cost: {COSTS[s]}}}"
            for t in ("baseline_pmcc", "quant_pmcc")
        )
        return f"{{symbol: {s}, value: {CASH[s]}, provisional: false, entries: [{entries}]}}"

    block = ", ".join(cash(s) for s in symbols if s in calibrated)
    return (
        f"window: {{start: {spec.window_start}, end: {spec.window_end}}}\n{rate}symbols:\n{listed}"
        "starting_cash: {cash_multiple: 2, cash_round_to: 5000, calibration_cash: 1000000, "
        f"symbols: [{block}]}}\n"
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
    return sorted(p.stem for p in Path(out, symbol).glob("*.json")
                  if p.stem not in ("coverage", "robustness", "fill_check"))  # fmt: skip


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
        for run in Path("elsewhere", symbol).glob("*_pmcc*.json"):  # each symbol's own cash
            assert RunResult.model_validate_json(run.read_bytes()).starting_cash == CASH[symbol]
    assert len(matrix) * len(SYMBOLS) == 48
    assert ("48 runs written for 2 symbol(s); 0 run(s) and 0 symbol(s) failed; 0 coverage, "
            "0 robustness and 0 fill-check file(s) not written; 0 suitability screen(s) not "
            "read; 0 universe file(s) failed.") in output  # fmt: skip
    assert ("Universe files: elsewhere/universe/headline.json, elsewhere/universe/pooled.json, "
            "elsewhere/universe/pooled_fill_check.json, "
            "elsewhere/universe/suitability.json") in output  # fmt: skip
    assert sorted(p.name for p in Path("logs").glob("batch_*_worker*.jsonl"))  # workers log apart
    verified = verify(Path("elsewhere"))  # schema, canonical bytes, a clean tree, the invariants
    assert verified.problems == ()
    assert (verified.runs, verified.files) == (48, 58)  # + 2 each coverage, robustness and fill
    # check, and 4 universe files

    # A run in the batch is the run `pmcc run` makes (both stamp the same clock here).
    config = (CONFIGS_DIR / "quant_pmcc.yaml").as_posix()
    single = runner.invoke(app, ["run", "--symbol", "SYN", "--config", config,
                                 "--cache", str(market), "--out", "single"])  # fmt: skip
    assert single.exit_code == 0, single.output
    assert Path("single/SYN/quant_pmcc.json").read_bytes() == Path(
        "elsewhere/SYN/quant_pmcc.json").read_bytes()  # fmt: skip

    # The universe files: from both symbols' two strategies, the pooled CI over both at once.
    results = {s: {i: RunResult.model_validate_json(Path("elsewhere", s, f"{i}.json").read_bytes())
                   for i in ("baseline_pmcc", "quant_pmcc")} for s in SYMBOLS}  # fmt: skip
    head = Headline.model_validate_json(Path("elsewhere/universe/headline.json").read_bytes())
    assert [(r.symbol, r.strategy_id) for r in head.rows] == [
        (s, i) for s in SYMBOLS for i in ("baseline_pmcc", "quant_pmcc")]  # fmt: skip
    assert all(r.pnl == _metrics(results[r.symbol][r.strategy_id]).pnl for r in head.rows)
    pool = Pooled.model_validate_json(Path("elsewhere/universe/pooled.json").read_bytes())
    assert pool.symbols == SYMBOLS
    baseline = [_weekly(results[s]["baseline_pmcc"]) for s in SYMBOLS]
    expected = mean_ci([list(week) for week in zip(*baseline, strict=True)], SEED)
    assert expected is not None
    assert pool.strategies[0].weekly_return == expected.model_copy(
        update={k: round(getattr(expected, k), 6) for k in ("mean", "low", "high")}
    )  # 6 dp
    # Every CI carries the universe's seed: the workers' runs, the robustness rows, the pool.
    for symbol in SYMBOLS:
        tables = Robustness.model_validate_json(Path("elsewhere", symbol, "robustness.json")
                                                .read_bytes())  # fmt: skip
        cis = [r.weekly_return for t in (tables.ablations, tables.friction, tables.timing,
                                         tables.grid) for r in t]  # fmt: skip
        assert {ci.seed for ci in cis if ci is not None} == {SEED}
    assert {s.weekly_return.seed for s in pool.strategies if s.weekly_return} == {SEED}
    assert pool.strategies[0].total_pnl == sum(
        _metrics(results[s]["baseline_pmcc"]).pnl for s in SYMBOLS)  # fmt: skip
    # The pooled fill check fits both symbols' files' pairs together.
    checks = [FillCheck.model_validate_json(Path("elsewhere", s, "fill_check.json").read_bytes())
              for s in SYMBOLS]  # fmt: skip
    raw = Path("elsewhere/universe/pooled_fill_check.json").read_bytes()
    assert raw == canonical.to_bytes(pooled_fill_check(checks).model_dump())
    assert PooledFillCheck.model_validate_json(raw).symbols == SYMBOLS
    # Each symbol's pairs span the universe's whole window, as the CLI hands it to its job.
    window = (universe.window.start, universe.window.end)
    for symbol in SYMBOLS:
        data = load_symbol(market, symbol, load_calendar())
        groups = fill_pairs(data, SymbolCache(market, symbol).units(), window)
        assert Path("elsewhere", symbol, "fill_check.json").read_bytes() == canonical.to_bytes(
            fill_check(symbol, groups).model_dump())  # fmt: skip
    # The screen: a row per symbol, each read over the universe's whole window.
    raw = Path("elsewhere/universe/suitability.json").read_bytes()
    rows = [_screen_row(market, s, universe.window) for s in reversed(SYMBOLS)]
    assert raw == canonical.to_bytes(suitability(rows).model_dump())
    assert [r.symbol for r in Suitability.model_validate_json(raw).rows] == list(SYMBOLS)


def _metrics(result: RunResult) -> Metrics:
    assert result.summary.metrics is not None
    return result.summary.metrics


def _weekly(result: RunResult) -> list[float]:
    assert result.summary.weekly_returns is not None
    return [w.value for w in result.summary.weekly_returns]


def test_p5_03_batch_exits_non_zero_when_a_symbol_fails_and_writes_the_rest(
    workdir: Path, market: Path
) -> None:
    """GONE has no cache: it is reported, and SYN and TWO are still written in full."""
    Path("universe.yaml").write_text(_universe((*SYMBOLS, "GONE")), encoding="utf-8")

    code, output = _batch(market)

    assert code == 1
    assert "GONE: FAILED:" in output
    assert "48 runs written for 3 symbol(s); 0 run(s) and 1 symbol(s) failed;" in output
    # GONE never reached its files or its screen: it is counted as failed, not again as those.
    assert ("0 coverage, 0 robustness and 0 fill-check file(s) not written; 0 suitability "
            "screen(s) not read;") in output  # fmt: skip
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


def test_dec_30_batch_refuses_a_symbol_without_its_starting_cash(
    workdir: Path, market: Path
) -> None:
    """Each symbol's own value (PO, 2026-10-05): SYN's doesn't stand in for TWO's."""
    Path("universe.yaml").write_text(_universe(calibrated=["SYN"]), encoding="utf-8")

    code, output = _batch(market)

    assert code == 1
    assert "no starting cash for TWO yet: run pmcc calibrate" in output
    assert not Path("results").exists()


# ---- one symbol's job, in this process ----------------------------------------------------------


def _job(market: Path, out: Path, symbol: str = "SYN", rate: float | None = None) -> SymbolJob:
    universe = read_universe_file(Path("universe.yaml"))
    configs = run_matrix(universe)
    stamp = Stamp(_provenance(), DataSource.LSEG, NOW)
    underlying = Underlying(symbol=symbol, stock_ric=f"{symbol}.O", option_root=symbol)
    return SymbolJob(market, underlying, load_calendar(), rate or universe.risk_free_rate.value,
                     configs, Money.from_dollars(15_000), stamp, out, run_families(),
                     universe.bootstrap.seed, universe.window)  # fmt: skip


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
    assert outcome.robustness is None  # a table missing a row would mislead
    assert not Path("out/SYN/robustness.json").exists()
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


def test_p6_06_robustness_file_tables_every_family_from_the_runs_summaries(
    workdir: Path, market: Path
) -> None:
    """Each family against its strategy: 5 ablations, 4 friction runs, 7 timing and 6 grid, each
    table led by its reference rows; built from the result files the batch wrote."""
    job = _job(market, Path("out"))
    outcome = run_job(job)

    assert outcome.ok
    assert outcome.robustness == Path("out/SYN/robustness.json")
    raw = Path("out/SYN/robustness.json").read_bytes()
    tables = Robustness.model_validate_json(raw)
    files = [Path("out/SYN", f"{c.strategy.id}.json").read_bytes() for c in job.configs]
    scores = [RunScore.of(RunResult.model_validate_json(f)) for f in files]
    assert canonical.to_bytes(robustness("SYN", scores, run_families()).model_dump()) == raw
    assert [len(t) for t in (tables.ablations, tables.friction, tables.timing, tables.grid)] == [
        6, 6, 8, 7]  # fmt: skip
    assert [r.run_id for r in tables.friction if r.run_id == r.reference] == [
        "baseline_pmcc", "quant_pmcc"]  # fmt: skip
    assert tables.timing_dispersion is not None
    assert tables.timing_dispersion.runs == 7
    assert verify(Path("out")).problems == ()


def test_p6_07_fill_check_file_pairs_every_print_in_the_window_from_the_cache(
    workdir: Path, market: Path
) -> None:
    """The file is the cache's pairs over the universe's window, fitted, as canonical JSON."""
    job = _job(market, Path("out"))

    outcome = run_job(job)

    assert outcome.ok
    assert outcome.fill_check == Path("out/SYN/fill_check.json")
    raw = Path("out/SYN/fill_check.json").read_bytes()
    data = load_symbol(market, "SYN", job.calendar)
    groups = fill_pairs(data, SymbolCache(market, "SYN").units(),
                        (job.window.start, job.window.end))  # fmt: skip
    assert raw == canonical.to_bytes(fill_check("SYN", groups).model_dump())
    check = FillCheck.model_validate_json(raw)
    assert [(g.group, g.fit is not None) for g in check.groups] == [("shorts", True),
                                                                    ("longs", True)]  # fmt: skip
    assert verify(Path("out")).problems == ()


def test_p6_07_a_fill_check_not_written_fails_the_symbol(workdir: Path, market: Path) -> None:
    Path("out/SYN/fill_check.json").mkdir(parents=True)

    outcome = run_job(_job(market, Path("out")))

    assert outcome.coverage is not None
    assert outcome.robustness is not None
    assert (outcome.fill_check, outcome.ok) == (None, False)


def test_p6_07_batch_summary_counts_a_fill_check_not_written() -> None:
    written = Path("out/SYN/coverage.json")
    symbol = SymbolOutcome("SYN", (RunOutcome("baseline_pmcc", written),), written,
                           robustness=written, fill_check=None)  # fmt: skip

    text = cli.describe_batch(BatchOutcome((symbol,), ()), Path("out"), 1)

    assert "robustness.json written; fill_check.json NOT written: FAILED" in text
    assert "0 coverage, 0 robustness and 1 fill-check file(s) not written" in text


def _screen_row(market: Path, symbol: str, window: Window) -> SuitabilityRow:
    """The screen read here, from quant's shipped config, on the symbol's market priced at r."""
    universe = read_universe_file(Path("universe.yaml"))
    priced = Market.prepare(load_symbol(market, symbol, load_calendar()), symbol,
                            universe.risk_free_rate.value)  # fmt: skip
    screen = Screen.of(build_strategy(load_strategy(CONFIGS_DIR / "quant_pmcc.yaml")))
    bars = sample_bars(load_calendar(), window.start, window.end)
    return suitability_row(symbol, [read_week(priced.data.view(t), screen) for t in bars], screen)


def test_p6_08_screen_row_reads_quants_rules_each_week_of_the_window(
    workdir: Path, market: Path
) -> None:
    job = _job(market, Path("out"))

    outcome = run_job(job)

    assert outcome.ok
    row = outcome.suitability
    assert row == _screen_row(market, "SYN", job.window)
    assert row is not None
    assert row.weeks == len(sample_bars(job.calendar, job.window.start, job.window.end)) > 1
    assert min(row.long_weeks, row.short_weeks, row.iv_rv20_weeks, row.g3_weeks) > 0
    assert row.g3_max_ratio == 1.20


def test_p6_08_a_screen_that_cant_be_read_fails_the_symbol(workdir: Path, market: Path) -> None:
    """Without quant's config there are no rules to read with: the runs and files are written,
    but the symbol isn't ok, so the batch exits 1 and writes no universe file."""
    job = _job(market, Path("out"))
    job = dataclasses.replace(job, configs=tuple(c for c in job.configs
                                                 if c.strategy.id != "quant_pmcc"))  # fmt: skip

    outcome = run_job(job)

    assert None not in (outcome.coverage, outcome.fill_check)
    assert (outcome.suitability, outcome.ok) == (None, False)


def test_p6_08_a_bug_in_the_screen_is_raised_not_reported(
    workdir: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Anything outside the batch's failures is a bug, and kills the worker (`_RUN_FAILURES`):
    the screen doesn't swallow it as a screen not read."""

    def broken(*_: object) -> None:
        raise TypeError("a bug in the screen")

    monkeypatch.setattr(batch, "read_week", broken)

    with pytest.raises(TypeError, match="a bug in the screen"):
        run_job(_job(market, Path("out")))


def test_p6_08_batch_summary_counts_a_screen_not_read() -> None:
    written = Path("out/SYN/coverage.json")
    symbol = SymbolOutcome("SYN", (RunOutcome("baseline_pmcc", written),), written,
                           robustness=written, fill_check=written)  # fmt: skip

    text = cli.describe_batch(BatchOutcome((symbol,), ()), Path("out"), 1)

    assert not symbol.ok
    assert "fill_check.json written; suitability screen NOT read: FAILED" in text
    assert "1 suitability screen(s) not read" in text


def test_p6_06_a_robustness_file_that_cant_be_built_fails_the_symbol(
    workdir: Path, market: Path
) -> None:
    """Every run and coverage.json written, but a run outside the families: no robustness.json,
    and the symbol isn't ok, so the batch exits 1 and writes no universe file."""
    job = _job(market, Path("out"))
    families = dict(job.families)
    del families["quant_pmcc--a1"]

    outcome = run_job(dataclasses.replace(job, families=families))

    assert len([r for r in outcome.runs if r.path is not None]) == RUNS
    assert outcome.coverage == Path("out/SYN/coverage.json")
    assert outcome.robustness is None
    assert not Path("out/SYN/robustness.json").exists()
    assert not outcome.ok


def test_p6_01_a_universe_file_that_fails_is_reported_and_the_rest_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(_stage: UniverseStage) -> Path:
        raise ValueError("quant_pmcc has no metrics")

    def fine(stage: UniverseStage) -> Path:
        return stage.out / "universe" / "fine.json"

    monkeypatch.setattr(batch, "UNIVERSE_WRITERS", (broken, fine))

    written, errors = batch.write_universe(UniverseStage((), tmp_path, SEED))

    assert written == (tmp_path / "universe" / "fine.json",)
    assert errors == ("broken: quant_pmcc has no metrics",)
    assert not batch.BatchOutcome((), written, errors).ok


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

    def writer(stage: UniverseStage) -> Path:
        seen.append(tuple(o.symbol for o in stage.outcomes))
        assert all(len(_runs(o.symbol)) == RUNS for o in stage.outcomes)  # every run is written
        assert stage.seed == SEED
        path = stage.out / "universe" / "test.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
        return path

    monkeypatch.setattr(batch, "UNIVERSE_WRITERS", (writer,))
    jobs = [_job(market, Path("results"), symbol=s) for s in SYMBOLS]

    done = run_batch(jobs, Path("results"), seed=SEED, initializer=cli.worker_logging)
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

    broken = run_batch([good, failing, raising, dying], Path("isolated"), seed=SEED,
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
