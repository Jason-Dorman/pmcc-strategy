"""One `random_walk` run written to a results directory, for INV-13's test to start in a fresh
process: `python -m tests.scenario.inv13_run CACHE OUT HOUR`.

Two processes with different `PYTHONHASHSEED`s must write the same bytes, once the run timestamp
(`HOUR`) is dropped, so no set or dict order can leak into a result.
"""

import sys
from datetime import datetime
from pathlib import Path

from pmcc.config.calendar import load_calendar
from pmcc.config.strategy import CONFIGS_DIR, RunConfig, load_strategy
from pmcc.config.universe import Window, read_universe_file
from pmcc.data.load import load_symbol
from pmcc.domain.clock import ET
from pmcc.domain.money import Money
from pmcc.export.manifest import GitState, Provenance
from pmcc.export.models import DataSource
from pmcc.export.results import write_result
from pmcc.runner import Stamp, run_loaded
from tests.fixtures.synthetic.scenarios import random_walk

PROVENANCE = Provenance(GitState("0" * 40, dirty=False), "1" * 64, "0.0.0")
CASH = Money.from_dollars(10_000)


def config() -> RunConfig:
    spec = random_walk()
    return RunConfig(strategy=load_strategy(CONFIGS_DIR / "baseline_pmcc.yaml"),
                     window=Window(start=spec.window_start, end=spec.window_end),
                     risk_free_rate=read_universe_file().risk_free_rate)  # fmt: skip


def main(cache: Path, out: Path, hour: int) -> Path:
    symbol = random_walk().symbol
    loaded = load_symbol(cache, symbol, load_calendar())
    stamp = Stamp(PROVENANCE, DataSource.SYNTHETIC, datetime(2026, 9, 30, hour, tzinfo=ET))
    return write_result(run_loaded(loaded, symbol, config(), CASH, stamp), out)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]))
