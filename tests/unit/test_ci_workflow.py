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


# ---- the web and deploy jobs (P4-07) ------------------------------------------------------------


def _job(name: str) -> dict[str, Any]:
    return _workflow()["jobs"][name]


def _web_runs() -> list[str]:
    return [step["run"] for step in _job("web")["steps"] if "run" in step]


def _index(runs: list[str], command: str) -> int:
    return next(i for i, run in enumerate(runs) if command in run)


def test_ci_web_job_exports_the_committed_results_before_the_site_is_checked() -> None:
    runs = _web_runs()
    export = _index(runs, "pmcc export --out web/public/data/")
    assert export < _index(runs, "npm run typecheck")
    assert export < _index(runs, "npm run build")


def test_ci_web_job_checks_then_builds_then_guards_the_site() -> None:
    runs = _web_runs()
    steps = ("npm ci", "npm run lint", "npm run typecheck", "npm run test", "npm run build",
             "npm run guard")  # fmt: skip
    order = [_index(runs, c) for c in steps]
    assert order == sorted(order)


def test_ci_web_job_installs_node_from_nvmrc() -> None:
    node = next(
        s for s in _job("web")["steps"] if s.get("uses", "").startswith("actions/setup-node")
    )
    assert node["with"]["node-version-file"] == "web/.nvmrc"


def test_ci_uploads_and_deploys_only_from_main() -> None:
    main = "github.ref == 'refs/heads/main' && github.event_name == 'push'"
    upload = next(s for s in _job("web")["steps"]
                  if s.get("uses", "").startswith("actions/upload-pages-artifact"))  # fmt: skip
    assert (upload["if"], upload["with"]["path"]) == (main, "web/dist")
    deploy = _job("deploy")
    assert deploy["if"] == main
    assert set(deploy["needs"]) == {"python", "web"}


def test_ci_only_the_deploy_job_may_write_pages() -> None:
    assert _workflow()["permissions"] == {"contents": "read"}
    assert _job("deploy")["permissions"] == {"pages": "write", "id-token": "write"}
    assert "permissions" not in _job("web")
    assert _job("deploy")["steps"][-1]["uses"].startswith("actions/deploy-pages")


def test_inv_15_ci_smoke_tests_every_route_after_the_dist_guard() -> None:
    runs = _web_runs()
    smoke = _index(runs, "npm run e2e")
    assert _index(runs, "npm run guard") < _index(runs, "playwright install") < smoke


def test_ci_uploads_the_smoke_tests_screenshots_even_when_it_fails() -> None:
    upload = next(s for s in _job("web")["steps"]
                  if s.get("uses", "").startswith("actions/upload-artifact"))  # fmt: skip
    assert (upload["if"], upload["with"]["path"]) == ("always()", "web/test-results/screenshots")
