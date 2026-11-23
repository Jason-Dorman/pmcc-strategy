"""`thesis run` (T3-01; TD-09, TD-13): the night's tracker into live/thesis/thesis.json.

It prints counts and dates but no values, plans without asking LSEG, and writes nothing on an
outage, without FRED's key, or when a source lacks what the tracker needs.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pmcc import cli
from pmcc.cli import thesis_app
from pmcc.data.provider import ProviderOutageError
from pmcc.domain.clock import ET
from pmcc.export.thesis_models import Thesis
from pmcc.thesis.probe import INDEX_RIC, VIX_RIC
from pmcc.thesis.run import THESIS_FILE
from tests.fakes.thesis_probe import ChainProvider
from tests.fakes.thesis_tracker import CAL, SPIKE_DAYS, spike_fred_text, spike_index, spike_vix

LAST = SPIKE_DAYS[-1]
NOW = datetime(LAST.year, LAST.month, LAST.day, 22, 0, tzinfo=ET)

runner = CliRunner()


@pytest.fixture
def served(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """What `_platform` yields (or raises), and every time it was opened, at a fixed `now`."""
    closes = {INDEX_RIC: spike_index(), VIX_RIC: spike_vix()}
    served: list[object] = [ChainProvider(CAL, closes, LAST, LAST)]
    opened: list[object] = []

    @contextmanager
    def platform() -> Generator[object]:
        opened.append(served[0])
        if isinstance(served[0], Exception):
            raise served[0]
        yield served[0]

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_platform", platform)
    monkeypatch.setattr(cli, "http_get", _fred)
    monkeypatch.setattr(cli, "_now", lambda: NOW)
    monkeypatch.setenv("FRED_API_KEY", "0123456789abcdef0123456789abcdef")
    served.append(opened)
    return served


def _fred(_url: str) -> str:
    return spike_fred_text()


def _run(*args: str) -> tuple[int, str]:
    result = runner.invoke(thesis_app, ["run", *args])
    return result.exit_code, result.output


def test_t3_01_run_writes_the_file_and_prints_no_values(served: list[object]) -> None:
    code, output = _run()

    assert code == 0, output
    thesis = Thesis.model_validate_json(THESIS_FILE.read_bytes())
    assert thesis.data_through == LAST.isoformat()
    assert "Thesis tracker written to live/thesis/thesis.json" in output
    assert f"data through {LAST}" in output
    assert "360 sessions, 1 episodes" in output
    for value in ("13.", "350", "3.5"):
        assert value not in output


def test_t3_01_plan_only_asks_nothing_and_writes_nothing(served: list[object]) -> None:
    code, output = _run("--plan-only")

    assert code == 0, output
    assert "1 daily request" in output
    assert served[1] == []
    assert not THESIS_FILE.exists()


@pytest.mark.parametrize(
    "failure",
    [ProviderOutageError("the LSEG session is not open"), "no FRED key", "no VIX"],
)
def test_t3_01_a_failure_writes_nothing(
    failure: object, served: list[object], monkeypatch: pytest.MonkeyPatch
) -> None:
    if isinstance(failure, Exception):
        served[0] = failure
    elif failure == "no FRED key":
        monkeypatch.delenv("FRED_API_KEY")
    else:
        served[0] = ChainProvider(CAL, {INDEX_RIC: spike_index()}, LAST, LAST)
    code, output = _run()

    assert code == 1
    assert "the thesis run stopped and wrote nothing" in output
    assert not THESIS_FILE.exists()
