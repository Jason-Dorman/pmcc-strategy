"""The CI workflow's python job (ARCHITECTURE §14, §15; DEC-58, DEC-77)."""

from pathlib import Path
from typing import Any

import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "ci.yml"


def _workflow() -> dict[Any, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _python_job() -> dict[str, Any]:
    return _workflow()["jobs"]["python"]


def _run_lines() -> list[str]:
    return [step["run"] for step in _python_job()["steps"] if "run" in step]


def _step_running(command: str) -> dict[str, Any]:
    return next(step for step in _python_job()["steps"] if command in step.get("run", ""))


def test_ci_triggers_on_push_and_pull_request() -> None:
    # PyYAML reads the bare key `on` as True.
    triggers = _workflow()[True]
    assert {"push", "pull_request"} <= set(triggers)


def test_ci_python_job_runs_on_ubuntu() -> None:
    assert _python_job()["runs-on"].startswith("ubuntu")


def test_ci_python_job_installs_from_the_lockfile() -> None:
    assert any("uv sync --frozen" in run for run in _run_lines())


def test_ci_python_job_runs_every_pre_commit_hook() -> None:
    assert any("pre-commit run --all-files" in run for run in _run_lines())


def test_ci_python_job_runs_pytest_with_the_ci_profile() -> None:
    step = _step_running("pytest")
    assert step["env"]["HYPOTHESIS_PROFILE"] == "ci"


def test_ci_python_job_rejects_tracked_credentials() -> None:
    assert any("git ls-files" in run and "lseg-data.config.json" in run for run in _run_lines())


def test_ci_python_job_verifies_the_committed_results_after_the_tests() -> None:
    """DEC-51, DEC-79: the invariants re-derived from committed results, with no cache."""
    runs = _run_lines()
    verify = next(i for i, run in enumerate(runs) if "pmcc verify results/" in run)
    assert verify > next(i for i, run in enumerate(runs) if "pytest" in run)


def test_ci_never_contacts_lseg() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pmcc fetch" not in text
    assert "pmcc probe" not in text
