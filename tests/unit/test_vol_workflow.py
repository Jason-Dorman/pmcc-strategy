"""The volatility workflow (L4-02; PO, LD-33; LD-34): its own nightly LSEG pull, like the course's
`oi-plots.yml` beside its deploy, committing only the chart's two files."""

from pathlib import Path
from typing import Any

import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "vol.yml"
SECRETS = ("LSEG_APP_KEY", "LSEG_USERNAME", "LSEG_PASSWORD")
BOT_FILES = ("live/vol.jsonl", "live/smile.json")


def _workflow() -> dict[Any, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _job() -> dict[str, Any]:
    (job,) = _workflow()["jobs"].values()
    return job


def _step(name: str) -> dict[str, Any]:
    return next(s for s in _job()["steps"] if s.get("name") == name)


def _lines(name: str) -> list[str]:
    return [line.strip() for line in _step(name)["run"].splitlines()]


def test_ld_34_vol_runs_nightly_after_the_orders_and_by_hand() -> None:
    triggers = _workflow()[True]  # PyYAML reads the bare key `on` as True

    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert triggers["schedule"] == [{"cron": "47 3 * * *"}]  # 30 minutes after the nightly's


def test_ld_34_a_run_by_hand_can_plan_and_backfill() -> None:
    inputs = _workflow()[True]["workflow_dispatch"]["inputs"]

    assert set(inputs) == {"since", "plan_only"}
    assert inputs["plan_only"]["type"] == "boolean"
    assert inputs["since"]["required"] is False


def test_ld_34_the_inputs_reach_the_command_through_the_environment_only() -> None:
    step = _step("Pull NVDA's volatility")
    run = step["run"]

    assert "${{" not in run  # never pasted into the script
    assert step["env"]["SINCE"] == "${{ inputs.since }}"
    assert step["env"]["PLAN_ONLY"] == "${{ inputs.plan_only }}"
    assert 'uv run --frozen pmcc vol --symbol NVDA "${args[@]}"' in run


def test_ld_34_vol_runs_only_on_main_one_at_a_time() -> None:
    assert _job()["if"] == "github.ref == 'refs/heads/main'"
    assert _workflow()["concurrency"] == {"group": "vol", "cancel-in-progress": False}


def test_ld_34_vol_may_write_the_repo_and_nothing_else() -> None:
    assert _workflow()["permissions"] == {"contents": "write"}


def test_ld_34_only_the_pull_sees_the_secrets() -> None:
    for step in _job()["steps"]:
        env = step.get("env", {})
        has = {s for s in SECRETS if s in env}
        assert has == (set(SECRETS) if step.get("name") == "Pull NVDA's volatility" else set())


def test_ld_34_the_bot_commits_only_the_charts_files_after_a_pull() -> None:
    lines = _lines("Commit the chart's data")

    assert f"git add -- {' '.join(BOT_FILES)}" in lines
    assert 'git config user.name "github-actions[bot]"' in lines
    assert "if git pull --rebase origin main && git push origin HEAD:main; then" in lines
    assert "for attempt in 1 2 3; do" in lines


def test_ld_34_a_failed_pull_or_a_plan_commits_nothing_and_stays_red() -> None:
    commit = _step("Commit the chart's data")

    # Implicitly success(): it runs only after the pull succeeded, and not after a plan.
    assert commit["if"] == "${{ !inputs.plan_only }}"
    assert "continue-on-error" not in _step("Pull NVDA's volatility")


def test_ld_34_ci_redeploys_after_the_nightly_and_after_vol() -> None:
    ci = yaml.safe_load((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"))

    assert ci[True]["workflow_run"]["workflows"][:2] == ["nightly", _workflow()["name"]]


def test_ld_34_vol_asks_lseg_only_through_pmcc_vol() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for command in ("pmcc fetch", "pmcc probe", "pmcc live-probe", "pmcc live "):
        assert command not in text
