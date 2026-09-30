"""`pmcc export`: the site's data, from committed results (ARCHITECTURE §12, Spec › Site and UI).

The export directory is rebuilt whole on every export:

- `schema/*.schema.json`, one per result model (`pmcc.export.schema`), which the site's
  `gen:types` turns into TypeScript (INV-14);
- every results file, copied byte for byte, once it passes `pmcc verify` (a dirty tree is allowed
  here, so a local preview works; CI's verify step keeps dirty results off the published site);
- `index.json`: what exists, per symbol, with the window, r and starting cash every run shares;
- `rules.json`: each strategy's and variant's rules, rendered from the config it ran with, and each
  variant's changes against its strategy (the Trade rules page; DEC-52).

Both are derived from the results at export time rather than committed, so neither can disagree
with the runs it describes.
"""

import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import final

from pmcc.config.kinds import SPEC_RULE_IDS
from pmcc.config.strategy import Rule
from pmcc.export import canonical
from pmcc.export.analytics_models import SYMBOL_FILES, UNIVERSE_FILES
from pmcc.export.models import RunResult
from pmcc.export.schema import write_schemas
from pmcc.export.site_models import (
    Index,
    IndexRun,
    IndexSymbol,
    RuleChange,
    RuleOut,
    Rules,
    StrategyRules,
)
from pmcc.export.verify import UNIVERSE_DIR, Problem, verify

INDEX, RULES = "index.json", "rules.json"
PUBLISHABLE_ONLY = "git_dirty"  # the one verify check a local export lets through


class ExportError(Exception):
    """Results that can't be exported, or an export directory that isn't one."""


# ---- the export ---------------------------------------------------------------------------------


@final
@dataclass(frozen=True, slots=True)
class Exported:
    runs: int
    symbols: int
    files: int  # results files copied
    unpublishable: tuple[str, ...]  # runs from a dirty tree: fine to preview, refused by verify


@final
@dataclass(frozen=True, slots=True)
class _Loaded:
    path: str  # relative to the results directory
    result: RunResult


def export_site(results: Path, out: Path) -> Exported:
    """Rebuild `out` from `results`. Raises `ExportError`, before touching `out`, if a results
    file fails verification (a dirty tree aside) or the runs don't share one window, r and
    starting cash."""
    verified = verify(results)
    refused = [p for p in verified.problems if p.check != PUBLISHABLE_ONLY]
    if refused:
        raise ExportError(_problems(refused))
    runs = _runs(results)
    if not runs:
        raise ExportError(f"{results} holds no runs to export")
    index, rules = build_index(runs, _extras(results)), build_rules(runs)
    _clear(out)
    write_schemas(out)
    copied = _copy(results, out)
    (out / INDEX).write_bytes(canonical.to_bytes(index.model_dump()))
    (out / RULES).write_bytes(canonical.to_bytes(rules.model_dump()))
    dirty = sorted({p.path for p in verified.problems if p.check == PUBLISHABLE_ONLY})
    return Exported(len(runs), len(index.symbols), copied, tuple(dirty))


def build_index(runs: Sequence[_Loaded], extras: Sequence[str]) -> Index:
    first = runs[0].result
    for run in runs:
        _check_shared(first, run)
    symbols = sorted({run.result.manifest.symbol for run in runs})
    return Index(
        pmcc_version=version("pmcc"),
        window=first.config.window,
        risk_free_rate=first.config.risk_free_rate,
        starting_cash=first.starting_cash,
        symbols=tuple(_symbol(s, runs, extras) for s in symbols),
        universe=_files_in(UNIVERSE_DIR, extras),
    )


def _files_in(folder: str, extras: Sequence[str]) -> dict[str, str]:
    """The analytics files in `folder`, by name."""
    return {Path(p).stem: p for p in extras if Path(p).parent.name == folder}


def _check_shared(first: RunResult, run: _Loaded) -> None:
    shared = (first.config.window, first.config.risk_free_rate, first.starting_cash)
    mine = (run.result.config.window, run.result.config.risk_free_rate, run.result.starting_cash)
    if mine != shared:
        raise ExportError(
            f"{run.path} ran over another window, r or starting cash than "
            f"{first.manifest.symbol}/{first.manifest.run_id}; re-run every result together"
        )


def _symbol(symbol: str, runs: Sequence[_Loaded], extras: Sequence[str]) -> IndexSymbol:
    mine = sorted((r for r in runs if r.result.manifest.symbol == symbol),
                  key=lambda r: r.result.manifest.run_id)  # fmt: skip
    return IndexSymbol(symbol=symbol, runs=tuple(_index_run(r) for r in mine),
                       files=_files_in(symbol, extras))  # fmt: skip


def _index_run(run: _Loaded) -> IndexRun:
    manifest, strategy = run.result.manifest, run.result.config.strategy
    return IndexRun(
        run_id=manifest.run_id,
        strategy_id=manifest.strategy_id,
        name=strategy.name,
        detail=strategy.report.detail,
        sections=strategy.report.sections,
        path=run.path,
        data_source=manifest.data_source,
        config_hash=manifest.config_hash,
        git_sha=manifest.git_sha,
    )


def build_rules(runs: Sequence[_Loaded]) -> Rules:
    """One entry per run ID. Every symbol runs a run ID on one config, so one serves them all."""
    by_id: dict[str, RunResult] = {}
    for run in runs:
        seen = by_id.setdefault(run.result.manifest.run_id, run.result)
        if seen.manifest.config_hash != run.result.manifest.config_hash:
            raise ExportError(
                f"{run.path} ran {seen.manifest.run_id} on another config than "
                f"{seen.manifest.symbol}'s; re-run every result together"
            )
    return Rules(strategies=tuple(_strategy_rules(by_id[i], by_id) for i in sorted(by_id)))


def _strategy_rules(result: RunResult, by_id: Mapping[str, RunResult]) -> StrategyRules:
    strategy, manifest = result.config.strategy, result.manifest
    base = by_id.get(manifest.strategy_id)
    if base is None:
        raise ExportError(
            f"{manifest.run_id} is exported without its strategy {manifest.strategy_id}, "
            "which its rule changes are shown against"
        )
    dumped = result.config.model_dump(mode="json")["strategy"]
    return StrategyRules(
        id=strategy.id,
        name=strategy.name,
        strategy_id=manifest.strategy_id,
        detail=strategy.report.detail,
        spread_capture=strategy.fill_model.spread_capture,
        fee_per_contract=strategy.fill_model.fee_per_contract.to_dollars(),
        rules=tuple(
            _rule(r, d["params"]) for r, d in zip(strategy.rules, dumped["rules"], strict=True)
        ),
        changes=() if base is result else _changes(base.config.strategy.rules, strategy.rules),
    )


def _rule(rule: Rule, params: Mapping[str, float | int | str]) -> RuleOut:
    text = rule.text()
    return RuleOut(id=str(rule.id), name=rule.name, kind=rule.kind, params=dict(params),
                   condition=text.condition, action=text.action,
                   rationale=text.rationale)  # fmt: skip


def _changes(base: Sequence[Rule], variant: Sequence[Rule]) -> tuple[RuleChange, ...]:
    theirs, mine = {r.id: r for r in base}, {r.id: r for r in variant}
    changes: list[RuleChange] = []
    for rule_id in SPEC_RULE_IDS:
        change = _change(theirs.get(rule_id), mine.get(rule_id))
        if change:
            changes.append(RuleChange(rule_id=str(rule_id), change=change))
    return tuple(changes)


def _change(base: Rule | None, variant: Rule | None) -> str:
    if base is None or variant is None:
        return "" if base is variant else ("added" if base is None else "removed")
    if base.kind != variant.kind:
        return "replaced"
    if base.params != variant.params:
        return "params"
    return "" if base == variant else "text"


# ---- files --------------------------------------------------------------------------------------


def _runs(results: Path) -> list[_Loaded]:
    """Every run file (`verify` has passed them)."""
    extras = {*SYMBOL_FILES, *UNIVERSE_FILES}
    return [
        _Loaded(p.relative_to(results).as_posix(), RunResult.model_validate_json(p.read_bytes()))
        for p in sorted(results.glob("*/*.json"))
        if p.parent.name != UNIVERSE_DIR and p.stem not in extras
    ]


def _extras(results: Path) -> list[str]:
    """The analytics files present, by their path relative to `results`."""
    found = [*results.glob(f"{UNIVERSE_DIR}/*.json"),
             *(p for p in results.glob("*/*.json") if p.stem in SYMBOL_FILES)]  # fmt: skip
    return sorted(p.relative_to(results).as_posix() for p in found)


def _clear(out: Path) -> None:
    """Empty `out` for a fresh export, refusing a directory an export didn't write."""
    if out.is_dir() and any(out.iterdir()):
        if not ((out / INDEX).is_file() or (out / "schema").is_dir()):
            raise ExportError(f"{out} holds files pmcc export didn't write; not clearing it")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)


def _copy(results: Path, out: Path) -> int:
    copied = 0
    for path in sorted(results.glob("*/*.json")):
        target = out / path.relative_to(results)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
        copied += 1
    return copied


def _problems(problems: Sequence[Problem]) -> str:
    return "results fail verification:\n" + "\n".join(f"  {p}" for p in problems)
