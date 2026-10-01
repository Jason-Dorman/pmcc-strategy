"""Running the engine on a scenario market (TEST-STRATEGY §5).

`run` builds a shipped strategy from its YAML: the baseline unless it names another config under
`configs/` by its path without `.yaml` (`quant_pmcc`, `ablations/a3`). Any `overrides` are applied
through the real loader (`extends` + `overrides`, DEC-53), and it runs over the scenario's window.
The engine checks INV-01 to INV-10 on every bar and every event, and raises if one fails, so every
scenario that returns has held them all (P3-07's done-when).
"""

import shutil
from collections.abc import Callable
from datetime import date, datetime, time
from pathlib import Path

from pmcc.accounting.events import Event
from pmcc.config.strategy import CONFIGS_DIR, RunConfig, load_strategy
from pmcc.config.universe import Window, read_universe_file
from pmcc.domain.clock import ET
from pmcc.domain.instruments import Side
from pmcc.domain.money import Money
from pmcc.engine.loop import RunOutput, run_backtest
from pmcc.strategy.registry import build_strategy
from tests.fixtures.synthetic.market import SyntheticSpec
from tests.fixtures.synthetic.store import SyntheticMarkets

BASELINE, QUANT = "baseline_pmcc", "quant_pmcc"
NO_TAKE_PROFIT = "X-S1: {remove: true}"  # A5's config: hold to the Friday check
CASH = Money.from_dollars(10_000)


def config(tmp: Path, overrides: str, start: date, end: date, fill_model: str = "",
           strategy: str = BASELINE) -> RunConfig:  # fmt: skip
    """The shipped `strategy`, with `overrides` (YAML keyed by rule ID) and a `fill_model` patch,
    from `start` to `end`."""
    path = CONFIGS_DIR / f"{strategy}.yaml"
    if overrides or fill_model:
        copied = (
            tmp / "configs"
        )  # the whole tree, so an ablation's `extends: ../quant_pmcc.yaml` resolves
        shutil.copytree(CONFIGS_DIR, copied, dirs_exist_ok=True)
        path = copied / "variant.yaml"
        run_id = f"{Path(strategy).name}--test"
        # A test variant keeps every row, whatever its parent reports (DEC-54).
        lines = [f"id: {run_id}", "name: Test", f"extends: {strategy}.yaml",
                 "report: {detail: full}"]  # fmt: skip
        if overrides:
            lines += ["overrides:", *(f"  {line}" for line in overrides.splitlines())]
        if fill_model:
            lines.append(f"fill_model: {fill_model}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return RunConfig(strategy=load_strategy(path), window=Window(start=start, end=end),
                     risk_free_rate=read_universe_file().risk_free_rate)  # fmt: skip


def run(synthetic: SyntheticMarkets, tmp: Path, name: str, build: Callable[[], SyntheticSpec], *,
        overrides: str = "", cash: Money = CASH, end: date | None = None,
        fill_model: str = "", strategy: str = BASELINE) -> RunOutput:  # fmt: skip
    loaded = synthetic.get(name, build)
    spec = loaded.market.spec
    cfg = config(tmp, overrides, spec.window_start, end or spec.window_end, fill_model, strategy)
    return run_backtest(loaded.data, cfg, build_strategy(cfg.strategy), cash)


def at(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=ET)


def rows(out: RunOutput, rule: str, side: Side | None = None) -> list[Event]:
    return [e for e in out.blotter if e.rule_id == rule and (side is None or e.side is side)]


def only(out: RunOutput, rule: str, side: Side | None = None) -> Event:
    found = rows(out, rule, side)
    assert len(found) == 1, f"expected one {rule} {side} row, got {found}"
    return found[0]
