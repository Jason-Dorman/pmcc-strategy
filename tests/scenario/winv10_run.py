"""The wheel's result on a synthetic market, written by the real pipeline (W2-03), and WINV-10's
runs, for its test to start in a fresh process: `python -m tests.scenario.winv10_run CACHE OUT HOUR
SHA`.

`full_wheel` is five weeks in which every rule that books or skips fires: week 1 is flat at $100,
so the put expires (W-X1); week 2 falls to $92 by Friday's close, so the put is assigned (W-X2);
week 3 stays at $92, so far below the cost basis that no call there has a quote (a W-C3 skip);
week 4 sits at $95, so the call is floored at the basis and expires (W-X3); week 5 rallies to $110
and the shares are called away (W-X4). Its cache is generated as `pmcc fetch` and `pmcc fetch
--wheel` would leave it: stock and calls in the symbol's cache, puts in the wheel part (WD-11), so
the result is loaded through `load_wheel_market`, as `pmcc wheel` loads it.

Its benchmarks (W3-01) are `BENCHMARKS`, fixed numbers, unless a test passes others:
`write_benchmarks` runs the baseline PMCC on the same market and writes it with an S&P 500 file
for its window, so `load_benchmarks` reads them as `pmcc wheel` does.

Two processes with different `PYTHONHASHSEED`s must write the same bytes once the manifest's
volatile values are dropped (WINV-10).
"""

import shutil
import sys
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from pmcc.config.calendar import load_calendar
from pmcc.config.universe import Underlying, Window, read_universe_file
from pmcc.data.cache import WHEEL_PART
from pmcc.data.load import load_symbol
from pmcc.domain.clock import ET
from pmcc.export.manifest import GitState, Provenance
from pmcc.export.models import DataSource
from pmcc.export.results import write_result
from pmcc.export.wheel_models import Benchmarks, IndexBenchmarkOut, PmccBenchmark, WheelResult
from pmcc.runner import Stamp, run_loaded
from pmcc.wheel.benchmarks import load_benchmarks
from pmcc.wheel.config import WheelRunConfig, load_wheel
from pmcc.wheel.result import run_wheel_symbol
from tests.fixtures.synthetic.market import IvSurface, SpotPath, SyntheticSpec, generate, knot
from tests.scenario.harness import CASH, SEED
from tests.scenario.harness import config as pmcc_config

PROVENANCE = Provenance(GitState("0" * 40, dirty=False), "1" * 64, "0.0.0")
SYMBOL = "SYN"
UNDERLYING = Underlying(symbol=SYMBOL, stock_ric=f"{SYMBOL}.O", option_root=SYMBOL)
WEEKS = ((date(2026, 8, 31), date(2026, 9, 4)), (date(2026, 9, 8), date(2026, 9, 11)),
         (date(2026, 9, 14), date(2026, 9, 18)), (date(2026, 9, 21), date(2026, 9, 25)),
         (date(2026, 9, 28), date(2026, 10, 2)))  # fmt: skip
"""Each week's first and last session; week 2 opens on Tuesday, after Labor Day."""
BEFORE = date(2026, 8, 28)  # the last close before the window
BENCHMARKS = Benchmarks(
    baseline_pmcc=PmccBenchmark(run_id="baseline_pmcc", config_hash="2" * 64,
                                starting_cash=Decimal("10000"), return_on_starting_cash=0.05,
                                sharpe_annualized=1.5, max_drawdown_pct=0.1),
    sp500=IndexBenchmarkOut(series="SP500", start=BEFORE, start_close=Decimal("6000"),
                            end=WEEKS[-1][1], end_close=Decimal("6060"), price_return=0.01,
                            source="synthetic"),
)  # fmt: skip


def full_wheel() -> SyntheticSpec:
    (w1, f1), (w2, f2), (w3, f3), (w4, f4), (w5, f5) = WEEKS
    path = SpotPath((knot(w1, 10, 100.0), knot(f1, 16, 100.0), knot(w2, 10, 100.0),
                     knot(f2, 16, 92.0), knot(w3, 10, 92.0), knot(f3, 16, 92.0),
                     knot(w4, 10, 95.0), knot(f4, 16, 95.0), knot(w5, 10, 96.0),
                     knot(f5, 16, 110.0)))  # fmt: skip
    base = SyntheticSpec(w1, f5, spot=100.0, iv=IvSurface(weekly=0.40, monthly=0.20))
    return replace(base, path=path)


def generate_market(cache: Path) -> None:
    """`full_wheel` under `cache`, its puts copied into the wheel part (the wheel never reads the
    cache's own)."""
    generate(full_wheel(), cache)
    part = cache / SYMBOL / WHEEL_PART / "chains"
    part.mkdir(parents=True)
    for path in (cache / SYMBOL / "chains").glob("*_P.*"):
        shutil.copy(path, part / path.name)


def config() -> WheelRunConfig:
    spec = full_wheel()
    return WheelRunConfig(wheel=load_wheel(),
                          window=Window(start=spec.window_start, end=spec.window_end),
                          risk_free_rate=read_universe_file().risk_free_rate)  # fmt: skip


def stamp(hour: int = 9, provenance: Provenance = PROVENANCE) -> Stamp:
    return Stamp(provenance, DataSource.SYNTHETIC, datetime(2026, 9, 30, hour, tzinfo=ET))


def result(cache: Path, run: Stamp | None = None,
           benchmarks: Benchmarks = BENCHMARKS) -> WheelResult:  # fmt: skip
    return run_wheel_symbol(cache, UNDERLYING, load_calendar(), config(), run or stamp(),
                            benchmarks)  # fmt: skip


def write_benchmarks(cache: Path, results: Path, work: Path) -> Path:
    """The baseline PMCC on `cache`'s market, written under `results`, and an S&P 500 file for the
    window in `work`; returns that file's path."""
    spec = full_wheel()
    loaded = load_symbol(cache, SYMBOL, load_calendar())
    baseline = pmcc_config(work, "", spec.window_start, spec.window_end)
    write_result(run_loaded(loaded, SYMBOL, baseline, CASH, stamp(), seed=SEED), results)
    work.mkdir(parents=True, exist_ok=True)
    path = work / "benchmarks.yaml"
    path.write_text(
        f"sp500:\n  series: SP500\n  start: {{day: {BEFORE}, close: '6000.00'}}\n"
        f"  end: {{day: {spec.window_end}, close: '6060.00'}}\n  source: synthetic\n",
        encoding="utf-8", newline="\n",
    )  # fmt: skip
    return path


def loaded_benchmarks(results: Path, path: Path) -> Benchmarks:
    return load_benchmarks(results, SYMBOL, load_calendar(), config(), path)


def main(cache: Path, out: Path, hour: int, sha: str = PROVENANCE.git.sha) -> Path:
    """The result under `out`, run at `hour` from commit `sha`."""
    provenance = Provenance(GitState(sha, dirty=False), PROVENANCE.lock_hash, "0.0.0")
    return write_result(result(cache, stamp(hour, provenance)), out)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
