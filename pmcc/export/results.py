"""Writing a run's result: canonical JSON at `{out}/{symbol}/{run_id}.json` (ARCHITECTURE §12).

A result is regenerated, never edited: a re-run replaces its file whole, and a run that fails
writes nothing (DEC-49).
"""

from pathlib import Path

from pmcc.data.files import replace_file
from pmcc.export import canonical
from pmcc.export.models import RunResult


def result_path(out: Path, symbol: str, run_id: str) -> Path:
    return out / symbol / f"{run_id}.json"


def to_bytes(result: RunResult) -> bytes:
    """The result as canonical JSON (DEC-50)."""
    return canonical.to_bytes(result.model_dump(mode="python"))


def write_result(result: RunResult, out: Path) -> Path:
    """Write `result` under `out`, replacing an earlier run's file whole; return its path."""
    path = result_path(out, result.manifest.symbol, result.manifest.run_id)
    replace_file(path, to_bytes(result))
    return path
