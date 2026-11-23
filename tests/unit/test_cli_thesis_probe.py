"""`thesis probe` (T1-01; TD-04, TD-05, TD-13): the thesis's own command, over the headless session.

It writes one report and never overwrites it, prints counts but no values, writes nothing when the
session won't open, and fails when the index's or VIX's closes don't come back.
"""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pmcc import cli
from pmcc.cli import thesis_app
from pmcc.config.calendar import load_calendar
from pmcc.data.provider import ProviderOutageError
from pmcc.domain.clock import ET
from pmcc.thesis.fred import FredUnavailableError
from pmcc.thesis.probe import INDEX_RIC, VIX_RIC
from tests.fakes.thesis_probe import FRED_TEXT, ChainProvider, FakeFinder, daily

CAL = load_calendar()
NOW = datetime(2026, 11, 20, 22, 0, tzinfo=ET)
SESSION, EXPIRY = date(2026, 11, 20), date(2026, 12, 23)

runner = CliRunner()


def _closes(with_vix: bool = True) -> dict[str, dict[date, float]]:
    start = date(2026, 6, 1)
    index = {
        d: v for d, v in daily(start, [6500.0 + i for i in range(200)], CAL).items() if d <= SESSION
    }
    vix = {d: 18.0 for d in index}
    return {INDEX_RIC: index, VIX_RIC: vix} if with_vix else {INDEX_RIC: index}


@pytest.fixture
def served(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[object]:
    """The provider `_platform` yields (or an error it raises), at a fixed `now`, in `tmp_path`."""
    served: list[object] = [ChainProvider(CAL, _closes(), SESSION, EXPIRY, spot=6699.0)]

    @contextmanager
    def platform() -> Generator[object]:
        if isinstance(served[0], Exception):
            raise served[0]
        yield served[0]

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "_platform", platform)
    monkeypatch.setattr(cli, "lseg_discovery", FakeFinder)
    monkeypatch.setattr(cli, "http_get", _fred)
    monkeypatch.setattr(cli, "_now", lambda: NOW)
    return served


def _fred(_url: str) -> str:
    return FRED_TEXT


def _probe() -> tuple[int, str]:
    result = runner.invoke(thesis_app, ["probe", "--out", "probes"])
    return result.exit_code, result.output


def _reports() -> list[Path]:
    return sorted(Path("probes").glob("thesis_*.json")) if Path("probes").exists() else []


def test_t1_01_writes_one_report_and_prints_counts(served: list[object]) -> None:
    code, output = _probe()

    assert code == 0, output
    assert [p.name for p in _reports()] == ["thesis_20261120T220000.json"]
    assert "Closes: .SPX" in output
    assert "SPXW: expiry 2026-12-23" in output
    assert "6699" not in output


def test_t1_01_never_overwrites_a_report(served: list[object]) -> None:
    Path("probes").mkdir()
    Path("probes/thesis_20261120T220000.json").write_text("{}", encoding="utf-8")
    code, output = _probe()

    assert code == 1
    assert "never overwritten" in output
    assert Path("probes/thesis_20261120T220000.json").read_text(encoding="utf-8") == "{}"


def test_t1_01_a_session_that_wont_open_writes_nothing(served: list[object]) -> None:
    served[0] = ProviderOutageError("LSEG_PASSWORD not set")
    code, output = _probe()

    assert code == 1
    assert "wrote nothing" in output
    assert _reports() == []


def test_t1_01_fred_not_answering_writes_nothing(
    served: list[object], monkeypatch: pytest.MonkeyPatch
) -> None:
    def down(_url: str) -> str:
        raise FredUnavailableError("FRED did not answer: TimeoutError")

    monkeypatch.setattr(cli, "http_get", down)
    code, output = _probe()

    assert code == 1
    assert "wrote nothing" in output
    assert _reports() == []


def test_t1_01_missing_vix_fails_after_writing_the_report(served: list[object]) -> None:
    served[0] = ChainProvider(CAL, _closes(with_vix=False), SESSION, EXPIRY)
    code, output = _probe()

    assert code == 1
    assert "closes didn't come back" in output
    assert len(_reports()) == 1
