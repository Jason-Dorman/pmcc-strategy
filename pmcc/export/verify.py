"""`pmcc verify results/`: check committed results without the cache or credentials (ARCHITECTURE
§12, DEC-51). CI runs it on every push (DEC-79).

Every file under the results directory must be one the pipeline writes, where it writes it:
`{SYM}/{run_id}.json`, `{SYM}/{robustness,fill_check,coverage}.json` or
`universe/{pooled,headline,suitability}.json`. Each must validate against its model, which is the
JSON Schema `pmcc export` publishes, since both come from the same pydantic model.

A run's file must also:
- be canonical JSON, byte for byte as `pmcc run` writes it (DEC-50);
- sit at its manifest's symbol and run ID;
- come from a clean tree (`git_dirty: false`, PO, DEC-50) and hash its config to
  `manifest.config_hash`;
- render its rule text from its config, and record every runtime invariant as held;
- if it is full detail, hold the invariants re-derived from its rows (`rederive`).
"""

import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import final

from pydantic import BaseModel, ValidationError

from pmcc.engine.invariants import RUNTIME_INVARIANTS
from pmcc.export import canonical
from pmcc.export.analytics_models import SYMBOL_FILES, UNIVERSE_FILES
from pmcc.export.models import RunResult
from pmcc.export.rederive import rederive
from pmcc.export.results import to_bytes

UNIVERSE_DIR = "universe"
SYMBOL_DIR = re.compile(r"[A-Z][A-Z0-9]*")
RUN_FILE = re.compile(r"[a-z][a-z0-9_]*(--[a-z0-9]+)*\.json")
_SHOWN = 3  # findings of one kind printed per file before the rest are counted


@final
@dataclass(frozen=True, slots=True)
class Problem:
    path: str  # relative to the results directory, with forward slashes
    check: str  # "layout", "schema", "canonical", "manifest", "git_dirty", "config_hash",
    # "rule_text", "summary", or an invariant ("INV-01")
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.check}: {self.message}"


@final
@dataclass(frozen=True, slots=True)
class Verified:
    runs: int
    files: int  # every file read, runs included
    problems: tuple[Problem, ...]


def verify(root: Path) -> Verified:
    """Check every file under `root`. Raises `FileNotFoundError` if `root` isn't a directory."""
    if not root.is_dir():
        raise FileNotFoundError(f"{root} isn't a directory of results")
    runs = files = 0
    problems: list[Problem] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        files += 1
        name = path.relative_to(root).as_posix()
        kind = kind_of(path.relative_to(root))
        if kind is None:
            problems.append(Problem(name, "layout", "isn't a file the pipeline writes here"))
        elif kind is RunResult:
            runs += 1
            problems += _check_run(path, name)
        else:
            problems += _check_other(path, name, kind)
    return Verified(runs, files, tuple(problems))


def kind_of(relative: Path) -> type[BaseModel] | None:
    """The model a file at `relative` must hold, or None if nothing belongs there."""
    if len(relative.parts) != 2 or relative.suffix != ".json":
        return None
    folder, stem = relative.parts[0], relative.stem
    if folder == UNIVERSE_DIR:
        return UNIVERSE_FILES.get(stem)
    if not SYMBOL_DIR.fullmatch(folder):
        return None
    if stem in SYMBOL_FILES:
        return SYMBOL_FILES[stem]
    return RunResult if RUN_FILE.fullmatch(relative.name) else None


def _check_other(path: Path, name: str, kind: type[BaseModel]) -> list[Problem]:
    """An analytics file: its schema, canonical bytes, and a symbol file under its own symbol."""
    raw = path.read_bytes()
    try:
        model = kind.model_validate_json(raw)
    except ValidationError as e:
        return [Problem(name, "schema", _describe(e))]
    problems: list[Problem] = []
    if canonical.to_bytes(canonical.loads(raw)) != raw:
        problems.append(Problem(name, "canonical", "isn't canonical JSON (DEC-50)"))
    symbol = getattr(model, "symbol", None)
    if symbol is not None and symbol != path.parent.name:
        problems.append(
            Problem(name, "manifest", f"holds {symbol}'s data under {path.parent.name}/")
        )
    return problems


def _check_run(path: Path, name: str) -> list[Problem]:
    raw = path.read_bytes()
    try:
        result = RunResult.model_validate_json(raw)
    except ValidationError as e:
        return [Problem(name, "schema", _describe(e))]
    found = [Problem(name, check, message) for check, message in _run_checks(result, raw, path)]
    return found + _shown(name, [(f.invariant, f.message) for f in rederive(result)])


def _run_checks(result: RunResult, raw: bytes, path: Path) -> Iterator[tuple[str, str]]:
    manifest, config = result.manifest, result.config
    if to_bytes(result) != raw:
        yield "canonical", "isn't canonical JSON as pmcc run writes it (DEC-50)"
    where = (path.parent.name, path.stem)
    if where != (manifest.symbol, manifest.run_id) or manifest.run_id != config.strategy.id:
        yield "manifest", (f"its manifest names {manifest.symbol}/{manifest.run_id}, run from "
                           f"{config.strategy.id}")  # fmt: skip
    if manifest.git_dirty:
        yield "git_dirty", "it ran on a dirty tree; commit the code and run it again (DEC-50)"
    if config.config_hash() != manifest.config_hash:
        yield "config_hash", "its config doesn't hash to manifest.config_hash"
    rendered = {str(r.id): asdict(r.text()) for r in config.strategy.rules}
    if {k: v.model_dump() for k, v in result.rule_text.items()} != rendered:
        yield "rule_text", "its rule text isn't rendered from its config (DEC-52)"
    held = {c.id for c in result.summary.invariants if c.held}
    recorded = [c.id for c in result.summary.invariants]
    if held != set(RUNTIME_INVARIANTS) or len(recorded) != len(held):
        yield "summary", (f"it records invariants {recorded} as held {sorted(held)}; every run "
                          f"holds {list(RUNTIME_INVARIANTS)}")  # fmt: skip


def _shown(name: str, findings: list[tuple[str, str]]) -> list[Problem]:
    """The first few findings of each invariant, then how many more."""
    by_check: dict[str, list[str]] = {}
    for check, message in findings:
        by_check.setdefault(check, []).append(message)
    problems: list[Problem] = []
    for check, messages in by_check.items():
        problems += [Problem(name, check, m) for m in messages[:_SHOWN]]
        if len(messages) > _SHOWN:
            problems.append(Problem(name, check, f"and {len(messages) - _SHOWN} more"))
    return problems


def _describe(error: ValidationError) -> str:
    first = error.errors()[:_SHOWN]
    parts = [f"{'.'.join(map(str, e['loc'])) or '(file)'}: {e['msg']}" for e in first]
    more = error.error_count() - len(first)
    return "; ".join(parts) + (f"; and {more} more" if more else "")
