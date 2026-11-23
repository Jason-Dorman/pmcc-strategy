"""The thesis's workflow (T3-02; TD-09): its own nightly run of `thesis run`, committing only the
tracker's file, after which CI redeploys the site."""

from pathlib import Path
from typing import Any

import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "thesis.yml"
SECRETS = ("LSEG_APP_KEY", "LSEG_USERNAME", "LSEG_PASSWORD", "FRED_API_KEY")
RUN = "Run the thesis's tracker"
COMMIT = "Commit the tracker"


def _workflow() -> dict[Any, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _job() -> dict[str, Any]:
    (job,) = _workflow()["jobs"].values()
    return job


def _step(name: str) -> dict[str, Any]:
    return next(s for s in _job()["steps"] if s.get("name") == name)


def test_td_09_thesis_runs_nightly_at_04_17_utc_and_by_hand() -> None:
    triggers = _workflow()[True]  # PyYAML reads the bare key `on` as True

    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert triggers["schedule"] == [{"cron": "17 4 * * *"}]
    assert set(triggers["workflow_dispatch"]["inputs"]) == {"plan_only"}


def test_td_09_the_input_reaches_the_command_through_the_environment_only() -> None:
    step = _step(RUN)

    assert "${{" not in step["run"]
    assert step["env"]["PLAN_ONLY"] == "${{ inputs.plan_only }}"
    assert 'uv run --frozen thesis run "${args[@]}"' in step["run"]


def test_td_09_thesis_runs_only_on_main_one_at_a_time_and_may_only_write() -> None:
    assert _job()["if"] == "github.ref == 'refs/heads/main'"
    assert _workflow()["concurrency"] == {"group": "thesis", "cancel-in-progress": False}
    assert _workflow()["permissions"] == {"contents": "write"}


def test_td_09_only_the_run_sees_the_secrets() -> None:
    for step in _job()["steps"]:
        env = step.get("env", {})
        has = {s for s in SECRETS if s in env}
        assert has == (set(SECRETS) if step.get("name") == RUN else set())


def test_td_09_the_bot_commits_only_the_trackers_file_after_a_pull() -> None:
    lines = [line.strip() for line in _step(COMMIT)["run"].splitlines()]

    assert "git add -- live/thesis/thesis.json" in lines
    assert 'git config user.name "github-actions[bot]"' in lines
    assert "if git pull --rebase origin main && git push origin HEAD:main; then" in lines
    assert [line for line in lines if line.startswith("git add")] == [
        "git add -- live/thesis/thesis.json"
    ]


def test_td_09_a_failed_run_or_a_plan_commits_nothing_and_stays_red() -> None:
    assert _step(COMMIT)["if"] == "${{ !inputs.plan_only }}"
    assert "continue-on-error" not in _step(RUN)


def test_td_09_ci_redeploys_after_the_thesis_run() -> None:
    ci = yaml.safe_load((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"))
    assert _workflow()["name"] in ci[True]["workflow_run"]["workflows"]


def test_td_09_thesis_asks_lseg_only_through_thesis_run() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    for command in ("pmcc fetch", "pmcc probe", "pmcc live", "pmcc vol", "thesis probe"):
        assert command not in text
