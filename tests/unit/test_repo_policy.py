"""What the repository commits: DEC-05's raw-cache policy and the hooks that guard the cache."""

import re
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
PRE_COMMIT = ROOT / ".pre-commit-config.yaml"


def _ignored(path: str) -> bool:
    # --no-index checks the patterns alone, so a tracked or missing file answers the same way.
    done = subprocess.run(["git", "check-ignore", "--no-index", "-q", path], cwd=ROOT, check=False)
    assert done.returncode in (0, 1), f"git check-ignore failed on {path}"
    return done.returncode == 0


def _hooks(hook_id: str) -> list[dict[str, Any]]:
    config = yaml.safe_load(PRE_COMMIT.read_text(encoding="utf-8"))
    return [hook for repo in config["repos"] for hook in repo["hooks"] if hook["id"] == hook_id]


def _applies(hook: dict[str, Any], path: str) -> bool:
    # pre-commit matches `files` and `exclude` with re.search.
    return bool(re.search(hook.get("files", ""), path)) and not (
        "exclude" in hook and re.search(hook["exclude"], path)
    )


@pytest.mark.parametrize(
    "path",
    [
        "data_cache/NVDA/stock.parquet",
        "data_cache/NVDA/stock.sidecar.json",
        "data_cache/NVDA/manifest.json",
        "data_cache/NVDA/chains/2026-09-18_C.parquet",
    ],
)
def test_dec_05_nvdas_raw_cache_is_committed(path: str) -> None:
    assert not _ignored(path)


@pytest.mark.parametrize(
    "path",
    [
        "data_cache/TSLA/manifest.json",
        "data_cache/QQQ/chains/2026-09-18_C.parquet",
        "data_cache/probes/NVDA_20260927.json",
        "data_cache/NVDA.moved/stock.parquet",
    ],
)
def test_dec_05_other_symbols_and_probe_reports_stay_local(path: str) -> None:
    assert _ignored(path)


@pytest.mark.parametrize("path", ["logs/run_20260930T151254Z.jsonl", "lseg-data.config.json"])
def test_dec_05_logs_and_credentials_stay_local(path: str) -> None:
    assert _ignored(path)


def test_dec_05_results_are_committed() -> None:
    assert not _ignored("results/NVDA/baseline_pmcc.json")


def test_dec_05_no_hook_rewrites_the_cache() -> None:
    (fixer,) = _hooks("end-of-file-fixer")
    assert not _applies(fixer, "data_cache/NVDA/manifest.json")
    assert _applies(fixer, "docs/DECISIONS.md")


def test_dec_05_the_cache_has_its_own_large_file_limit() -> None:
    manifest = "data_cache/NVDA/manifest.json"
    applying = [hook for hook in _hooks("check-added-large-files") if _applies(hook, manifest)]
    assert len(applying) == 1
    assert applying[0]["args"] == ["--maxkb=2048"]
    assert not any(_applies(hook, "pmcc/cli.py") for hook in applying)
