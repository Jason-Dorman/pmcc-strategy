"""The thesis probe's workflow (T1-01; TD-04): run by hand, read-only, secrets in one step."""

from pathlib import Path
from typing import Any

import yaml

WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "thesis-probe.yml"
SECRETS = ("LSEG_APP_KEY", "LSEG_USERNAME", "LSEG_PASSWORD")


def _workflow() -> dict[Any, Any]:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _steps() -> list[dict[str, Any]]:
    return _workflow()["jobs"]["probe"]["steps"]


def test_t1_01_thesis_probe_runs_only_by_hand() -> None:
    # PyYAML reads the bare key `on` as True.
    assert set(_workflow()[True]) == {"workflow_dispatch"}


def test_t1_01_thesis_probe_can_only_read_the_repo() -> None:
    assert _workflow()["permissions"] == {"contents": "read"}
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "git push" not in text
    assert "git commit" not in text


def test_t1_01_only_the_probe_step_sees_the_secrets() -> None:
    with_secrets = [s for s in _steps() if "secrets." in str(s)]

    assert len(with_secrets) == 1
    step = with_secrets[0]
    assert "thesis probe" in step["run"]
    assert step["env"] == {name: f"${{{{ secrets.{name} }}}}" for name in SECRETS}


def test_t1_01_thesis_probe_installs_from_the_lockfile() -> None:
    assert any(s.get("run") == "uv sync --frozen" for s in _steps())


def test_t1_01_the_report_with_values_is_kept_for_one_day() -> None:
    upload = next(s for s in _steps() if s.get("uses", "").startswith("actions/upload-artifact"))

    assert upload["with"]["retention-days"] == 1
    assert upload["with"]["path"] == "data_cache/probes/thesis_*.json"
