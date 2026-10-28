"""Writing a run's result: canonical JSON at `{out}/{symbol}/{run_id}.json` (ARCHITECTURE §12).

A result is regenerated, never edited: a re-run replaces its file whole, and a run that fails
writes nothing (DEC-49). The PMCC's runs and the wheel's (W2-03) are written the same way.
"""

from pathlib import Path

from pmcc.data.files import replace_file
from pmcc.export import canonical
from pmcc.export.models import RunResult
from pmcc.export.wheel_models import WheelResult

type Result = RunResult | WheelResult


def result_path(out: Path, symbol: str, run_id: str) -> Path:
    return out / symbol / f"{run_id}.json"


def to_bytes(result: Result) -> bytes:
    """The result as canonical JSON (DEC-50). The config is its JSON dump, whose floats print
    unrounded, as its hash covers them, so the file's config always hashes to
    `manifest.config_hash` (DEC-92)."""
    data = result.model_dump(mode="python")
    data["config"] = canonical.verbatim_floats(result.config.model_dump(mode="json"))
    return canonical.to_bytes(data)


def write_result(result: Result, out: Path) -> Path:
    """Write `result` under `out`, replacing an earlier run's file whole; return its path."""
    path = result_path(out, result.manifest.symbol, result.manifest.run_id)
    replace_file(path, to_bytes(result))
    return path
