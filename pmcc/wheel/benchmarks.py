"""The wheel's benchmarks (WD-03, WD-17; W3-01): the S&P 500 and the baseline PMCC.

The wheel is compared with the index's price return over the same window: from the last close
before the window, which the first decision could have known, to the window's last close, two
closes from `configs/benchmarks.yaml`. And with the baseline PMCC on the same symbol, from its
committed result (`results/{SYM}/baseline_pmcc.json`), which must have run over the same window
at the same r, so its return, Sharpe and drawdown are measured as the wheel's are.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pmcc.config.strategy import CONFIGS_DIR
from pmcc.config.yaml_file import read_yaml
from pmcc.domain.calendar import SessionCalendar
from pmcc.export.models import RunResult
from pmcc.export.wheel_models import Benchmarks, IndexBenchmarkOut, PmccBenchmark
from pmcc.wheel.config import WheelRunConfig

BENCHMARKS_PATH = CONFIGS_DIR / "benchmarks.yaml"


class BenchmarkError(Exception):
    """The benchmark file is malformed, or its closes don't bracket the window."""


@final
class IndexClose(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    day: date
    close: Decimal = Field(gt=0)


@final
class IndexBenchmark(BaseModel):
    """An index's close before the window and at its end, and where they came from."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    series: str = Field(min_length=1)
    start: IndexClose
    end: IndexClose
    source: str = Field(min_length=1)

    @property
    def price_return(self) -> Decimal:
        return self.end.close / self.start.close - 1


@final
class _File(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sp500: IndexBenchmark


def load_sp500(
    calendar: SessionCalendar, window_start: date, window_end: date, path: Path = BENCHMARKS_PATH
) -> IndexBenchmark:
    """The S&P 500's closes, checked against the window. Raises `BenchmarkError`."""
    try:
        sp500 = _File.model_validate(read_yaml(path)).sp500
    except (ValidationError, ValueError) as exc:
        raise BenchmarkError(f"{path}: {exc}") from exc
    before = calendar.sessions_before(window_start, 1)[0].day
    if sp500.start.day != before:
        raise BenchmarkError(
            f"{path}: the start close is {sp500.start.day}; the last close before the window is "
            f"{before}"
        )
    if sp500.end.day != window_end:
        raise BenchmarkError(
            f"{path}: the end close is {sp500.end.day}; the window ends {window_end}"
        )
    return sp500


BASELINE_PMCC = "baseline_pmcc"  # the run the wheel is compared with (WD-03)


def pmcc_benchmark(baseline: RunResult, config: WheelRunConfig) -> PmccBenchmark:
    """The baseline PMCC's numbers. Raises `BenchmarkError` for another run, window or r, or a
    result without metrics."""
    ran = baseline.config
    if baseline.manifest.run_id != BASELINE_PMCC:
        raise BenchmarkError(f"the benchmark is {BASELINE_PMCC}, not {baseline.manifest.run_id}")
    if (ran.window, ran.risk_free_rate) != (config.window, config.risk_free_rate):
        raise BenchmarkError(
            f"{BASELINE_PMCC} ran over {ran.window.start} to {ran.window.end} at r "
            f"{ran.risk_free_rate.value}; the wheel runs over {config.window.start} to "
            f"{config.window.end} at {config.risk_free_rate.value}: re-run pmcc batch"
        )
    metrics = baseline.summary.metrics
    if metrics is None:
        raise BenchmarkError(f"{BASELINE_PMCC}'s result has no metrics: re-run pmcc batch")
    return PmccBenchmark(
        run_id=BASELINE_PMCC,
        config_hash=baseline.manifest.config_hash,
        starting_cash=baseline.starting_cash,
        return_on_starting_cash=metrics.return_on_starting_nav,
        sharpe_annualized=metrics.sharpe_annualized,
        max_drawdown_pct=metrics.max_drawdown_pct,
    )


def index_benchmark(index: IndexBenchmark) -> IndexBenchmarkOut:
    return IndexBenchmarkOut(
        series=index.series,
        start=index.start.day,
        start_close=index.start.close,
        end=index.end.day,
        end_close=index.end.close,
        price_return=float(index.price_return),
        source=index.source,
    )


def load_benchmarks(
    results: Path,
    symbol: str,
    calendar: SessionCalendar,
    config: WheelRunConfig,
    path: Path = BENCHMARKS_PATH,
) -> Benchmarks:
    """The baseline PMCC's committed result for `symbol` under `results`, and the S&P 500's closes
    at `path`, both checked against `config`'s window. Raises `BenchmarkError`."""
    baseline = results / symbol / f"{BASELINE_PMCC}.json"
    try:
        result = RunResult.model_validate_json(baseline.read_bytes())
    except FileNotFoundError:
        raise BenchmarkError(f"{baseline.as_posix()} is missing: run pmcc batch first") from None
    except ValidationError as exc:
        raise BenchmarkError(f"{baseline.as_posix()}: {exc}") from exc
    sp500 = load_sp500(calendar, config.window.start, config.window.end, path)
    return Benchmarks(baseline_pmcc=pmcc_benchmark(result, config), sp500=index_benchmark(sp500))
