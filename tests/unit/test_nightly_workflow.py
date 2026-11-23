"""The live wheel's nightly workflow (L3-01; Spec › Nightly job; LD-05, LD-06, LD-14, LD-27)."""

from pathlib import Path
from typing import Any

import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
WORKFLOW = WORKFLOWS / "nightly.yml"
SECRETS = ("LSEG_APP_KEY", "LSEG_USERNAME", "LSEG_PASSWORD")
BOT_FILES = ("open_orders.json", "mkt/open_orders.json", "live/runs.jsonl")


def _workflow() -> dict[Any, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _job() -> dict[str, Any]:
    (job,) = _workflow()["jobs"].values()
    return job


def _steps() -> list[dict[str, Any]]:
    return _job()["steps"]


def _step(name: str) -> dict[str, Any]:
    return next(s for s in _steps() if s.get("name") == name)


def _commit_lines() -> list[str]:
    run = _step("Commit the orders and the run log")["run"]
    return [line.strip() for line in run.splitlines()]


def test_ld_31_nightly_runs_at_03_17_utc_and_by_hand() -> None:
    # PyYAML reads the bare key `on` as True. Off the top of the hour, GitHub's busiest (LD-31).
    triggers = _workflow()[True]

    assert set(triggers) == {"schedule", "workflow_dispatch"}
    assert triggers["schedule"] == [{"cron": "17 3 * * *"}]


def test_l3_01_nightly_runs_only_on_main_one_at_a_time() -> None:
    assert _job()["if"] == "github.ref == 'refs/heads/main'"
    assert _workflow()["concurrency"] == {"group": "nightly", "cancel-in-progress": False}


def test_ld_06_nightly_may_write_the_repo_and_nothing_else() -> None:
    assert _workflow()["permissions"] == {"contents": "write"}
    assert "permissions" not in _job()


def test_ld_05_nightly_installs_from_the_lockfile() -> None:
    assert any(s.get("run") == "uv sync --frozen" for s in _steps())


def test_l3_01_nightly_runs_one_night_of_the_live_wheel_on_nvda_for_real() -> None:
    step = _step("Run tonight's live wheel")

    assert step["run"] == "uv run --frozen pmcc live --symbol NVDA"
    assert "continue-on-error" not in step


def test_linv_09_only_the_live_step_sees_the_secrets() -> None:
    with_secrets = [s for s in _steps() if "secrets." in str(s)]

    assert with_secrets == [_step("Run tonight's live wheel")]
    assert with_secrets[0]["env"] == {name: f"${{{{ secrets.{name} }}}}" for name in SECRETS}


def test_ld_06_the_bot_commits_only_the_orders_and_the_run_log() -> None:
    adds = [line for line in _commit_lines() if line.startswith("git add")]

    assert adds == ["git add -- " + " ".join(BOT_FILES)]
    assert not any("git add -A" in line or "git add ." in line for line in _commit_lines())


def test_ld_06_the_commit_is_the_actions_bots() -> None:
    lines = _commit_lines()

    assert 'git config user.name "github-actions[bot]"' in lines
    assert 'git config user.email "41898282+github-actions[bot]@users.noreply.github.com"' in lines


def test_ld_06_the_bot_pulls_before_it_pushes_to_main_three_tries() -> None:
    lines = _commit_lines()
    attempt = next(line for line in lines if "git push" in line)

    assert attempt.index("git pull --rebase origin main") < attempt.index(
        "git push origin HEAD:main"
    )
    assert "for attempt in 1 2 3; do" in lines
    assert "git rebase --abort 2>/dev/null || true" in lines
    assert 'if [ "$attempt" -lt 3 ]; then' in lines
    assert lines[-1] == "exit 1"


def test_ld_14_a_failed_night_commits_its_row_alone() -> None:
    commit = _step("Commit the orders and the run log")
    lines = _commit_lines()
    restore = lines.index("git checkout -- open_orders.json mkt/open_orders.json")

    assert commit["if"] == "${{ !cancelled() && steps.live.outcome != 'skipped' }}"
    assert commit["env"] == {"LIVE_OUTCOME": "${{ steps.live.outcome }}"}
    assert lines[restore - 2] == 'if [ "$LIVE_OUTCOME" != "success" ]; then'
    assert restore < next(i for i, line in enumerate(lines) if line.startswith("git add"))


def test_ld_14_a_failed_night_stays_red() -> None:
    assert _step("Run tonight's live wheel")["id"] == "live"
    assert "continue-on-error" not in _job()
    assert not any("continue-on-error" in step for step in _steps())


def _ci() -> dict[Any, Any]:
    return yaml.safe_load((WORKFLOWS / "ci.yml").read_text(encoding="utf-8"))


def test_ld_06_ci_runs_when_the_nightly_completes() -> None:
    assert _ci()[True]["workflow_run"] == {
        # and the volatility workflow's (LD-34), and the thesis's tracker's (TD-09)
        "workflows": [_workflow()["name"], "vol", "thesis"],
        "types": ["completed"],
        "branches": ["main"],
    }


def test_ld_27_ci_after_the_nightly_never_cancels_another_run() -> None:
    assert _ci()["concurrency"] == {
        "group": "ci-${{ github.ref }}",
        "cancel-in-progress": "${{ github.event_name != 'workflow_run' }}",
    }


def test_ld_05_nightly_asks_lseg_only_through_pmcc_live() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")

    for command in ("pmcc fetch", "pmcc probe", "pmcc live-probe", "--dry-run"):
        assert command not in text
