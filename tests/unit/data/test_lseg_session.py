"""`lseg_session`: open a Workspace session, prove it opened, always close it (LDG §4.2).

`ld.open_session()` doesn't raise when the handshake fails, so every later request would look
like "no data". The session is checked before anything is requested.
"""

import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from pmcc.data.lseg import CONFIG_PATH, LsegProvider, lseg_session
from pmcc.data.provider import Interval, ProviderOutageError, TransientError
from tests.fakes.lseg import FakeLseg, OpenState

RIC = "NVDA.O"


@pytest.fixture
def config(tmp_path: Path) -> Path:
    path = tmp_path / "lseg-data.config.json"
    path.write_text("{}", encoding="utf-8")  # a placeholder: the fake never reads it
    return path


def _history(provider: LsegProvider) -> None:
    provider.history([RIC], ["TRDPRC_1"], date(2026, 9, 14), date(2026, 9, 15), Interval.HOURLY)


def test_lseg_session_yields_a_provider_once_the_session_reports_opened(config: Path) -> None:
    fake = FakeLseg(listed={RIC: {"TRDPRC_1": [1.0, 2.0, 3.0]}})

    with lseg_session(fake, config) as provider:
        _history(provider)

    assert fake.state is OpenState.Closed
    assert fake.closes == 1
    assert [r.session_open for r in fake.requests] == [True]


@pytest.mark.parametrize("state", [OpenState.Closed, OpenState.Pending])
def test_lseg_session_not_opened_after_open_raises_before_any_request(
    config: Path, state: OpenState
) -> None:
    fake = FakeLseg(opens_to=state)

    with pytest.raises(ProviderOutageError, match="did not open"), lseg_session(fake, config):
        pytest.fail("the body must not run on a session that isn't Opened")

    assert fake.requests == []
    assert fake.closes == 1


def test_lseg_session_open_that_raises_is_an_outage(config: Path) -> None:
    fake = FakeLseg(open_error=NameError("Cannot open session desktop.workspace"))

    with (
        pytest.raises(ProviderOutageError, match="Cannot open session"),
        lseg_session(fake, config),
    ):
        pytest.fail("the body must not run")

    assert fake.requests == []
    assert fake.closes == 1


def test_lseg_session_missing_config_raises_before_opening(tmp_path: Path) -> None:
    fake = FakeLseg()

    with (
        pytest.raises(ProviderOutageError, match=r"lseg-data\.config\.json"),
        lseg_session(fake, tmp_path / "lseg-data.config.json"),
    ):
        pytest.fail("the body must not run")

    assert fake.opened_with == []
    assert fake.requests == []


def test_lseg_session_passes_the_config_path_not_the_working_directory(config: Path) -> None:
    fake = FakeLseg()

    with lseg_session(fake, config):
        pass

    assert fake.opened_with == [str(config)]


def test_lseg_session_config_path_is_at_the_repo_root() -> None:
    assert CONFIG_PATH.name == "lseg-data.config.json"
    assert (CONFIG_PATH.parent / "pyproject.toml").is_file()


def test_lseg_session_closes_when_the_body_raises(config: Path) -> None:
    fake = FakeLseg()

    with pytest.raises(RuntimeError, match="boom"), lseg_session(fake, config):
        raise RuntimeError("boom")

    assert fake.closes == 1


def test_lseg_session_closed_mid_pull_raises_before_the_next_request(config: Path) -> None:
    fake = FakeLseg(listed={RIC: {"TRDPRC_1": [1.0, 2.0, 3.0]}})

    with lseg_session(fake, config) as provider:
        _history(provider)
        fake.close_session()
        with pytest.raises(ProviderOutageError, match="not open"):
            _history(provider)

    assert len(fake.requests) == 1


def test_lseg_session_workspace_that_dies_keeps_saying_opened(config: Path) -> None:
    # lseg-data's desktop session never leaves Opened on its own (DEC-83): a dead Workspace
    # shows up only as failing requests, which the fetch retries and then calls an outage.
    fake = FakeLseg(listed={RIC: {"TRDPRC_1": [1.0, 2.0, 3.0]}}, dies_after=1)

    with lseg_session(fake, config) as provider:
        _history(provider)
        with pytest.raises(TransientError, match="connection"):
            _history(provider)
        assert fake.state is OpenState.Opened


def test_lseg_session_importing_the_adapter_does_not_load_lseg_data() -> None:
    # A fresh interpreter, since this suite's own imports would hide the answer.
    code = "import sys, pmcc.data.lseg; print('lseg.data' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)

    assert out.stdout.strip() == "False"
