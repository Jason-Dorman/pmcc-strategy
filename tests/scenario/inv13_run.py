"""INV-13's runs, written to a results directory, for its test to start in a fresh process:
`python -m tests.scenario.inv13_run CACHE OUT HOUR SHA`.

Two processes with different `PYTHONHASHSEED`s must write the same bytes once the manifest's
volatile values are dropped, so no set or dict order can leak into a result. Two markets:
`random_walk`, the general market, and `friday_unquoted_at_check` without X-S1, whose ledger has
rows with two flags (`exit_pending`, `stale_short`), the one array a result builds from a set.
The test's seeds put those two flags in opposite set orders.
"""

import sys
from collections.abc import Callable
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
from tests.fixtures.synthetic.market import SyntheticSpec, generate
from tests.fixtures.synthetic.scenarios import BUILDERS, random_walk

PROVENANCE = Provenance(GitState("0" * 40, dirty=False), "1" * 64, "0.0.0")
CASH = Money.from_dollars(10_000)
SEED = 535  # the bootstrap seed configs/universe.yaml ships (DEC-61)
NO_TAKE_PROFIT = "baseline_pmcc--a5"  # the baseline without X-S1, as the scenario tests run it

# name -> (builder, strategy file under configs/ or `NO_TAKE_PROFIT`)
CASES: dict[str, tuple[Callable[[], SyntheticSpec], str]] = {
    "random_walk": (random_walk, "baseline_pmcc"),
    "friday_unquoted_at_check": (BUILDERS["friday_unquoted_at_check"], NO_TAKE_PROFIT),
}


def generate_all(cache: Path) -> None:
    """Each case's market, cached under `cache/{name}/`."""
    for name, (build, _strategy) in CASES.items():
        generate(build(), cache / name)


def config(name: str, work: Path) -> RunConfig:
    build, strategy = CASES[name]
    spec = build()
    return RunConfig(strategy=load_strategy(_strategy_file(strategy, work)),
                     window=Window(start=spec.window_start, end=spec.window_end),
                     risk_free_rate=read_universe_file().risk_free_rate)  # fmt: skip


def _strategy_file(strategy: str, work: Path) -> Path:
    if strategy != NO_TAKE_PROFIT:
        return CONFIGS_DIR / f"{strategy}.yaml"
    work.mkdir(parents=True, exist_ok=True)
    for name in ("_shared.yaml", "baseline_pmcc.yaml"):
        (work / name).write_bytes((CONFIGS_DIR / name).read_bytes())
    path = work / "a5.yaml"
    lines = [f"id: {NO_TAKE_PROFIT}", "name: No take-profit", "extends: baseline_pmcc.yaml",
             "report: {detail: full}", "overrides:", "  X-S1: {remove: true}"]  # fmt: skip
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def main(cache: Path, out: Path, hour: int, sha: str = PROVENANCE.git.sha) -> list[Path]:
    """Each case's result under `out/{name}/`, run at `hour` from commit `sha`."""
    provenance = Provenance(GitState(sha, dirty=False), PROVENANCE.lock_hash, "0.0.0")
    stamp = Stamp(provenance, DataSource.SYNTHETIC, datetime(2026, 9, 30, hour, tzinfo=ET))
    written: list[Path] = []
    for name, (build, _strategy) in CASES.items():
        symbol = build().symbol
        loaded = load_symbol(cache / name, symbol, load_calendar())
        result = run_loaded(loaded, symbol, config(name, out / "configs"), CASH, stamp, seed=SEED)
        written.append(write_result(result, out / name))
    return written


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
