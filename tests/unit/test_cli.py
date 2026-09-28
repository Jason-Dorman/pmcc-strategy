"""The `pmcc` command surface (ARCHITECTURE §3.1, Spec › CLI)."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, datetime
from functools import partial
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pmcc import cli
from pmcc.cli import app
from pmcc.config.calendar import load_calendar
from pmcc.data.fetch import Retry
from pmcc.data.probe import run_probe
from pmcc.data.provider import Interval
from pmcc.domain.clock import ET
from tests.fakes.market import FakeMarket

COMMANDS = ["fetch", "probe", "run", "batch", "calibrate", "export", "verify", "serve"]
NOW = datetime(2026, 9, 27, 12, tzinfo=ET)

runner = CliRunner()


def test_cli_help_lists_every_command() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command in COMMANDS:
        assert command in result.output


@pytest.mark.parametrize(
    ("args", "item"),
    [
        (["fetch", "--symbol", "NVDA", "--start", "2026-07-06", "--end", "2026-09-18"], "P1-08"),
        (["run", "--symbol", "NVDA", "--config", "configs/quant_pmcc.yaml"], "P3-08"),
        (["batch", "--universe", "configs/universe.yaml"], "P5-03"),
        (["calibrate"], "P3-09"),
        (["export", "--out", "web/public/data/"], "P4-05"),
        (["verify", "results/"], "P4-05"),
        (["serve"], "P7-06"),
    ],
)
def test_cli_stub_fails_loudly_naming_its_backlog_item(args: list[str], item: str) -> None:
    result = runner.invoke(app, args)

    assert result.exit_code == 1
    assert item in result.output


# --- pmcc probe (P1-04) -----------------------------------------------------------------------


@pytest.fixture
def market(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FakeMarket:
    """A fake market behind `lseg_session`, at a fixed `now`, working in `tmp_path`."""
    fake = FakeMarket(load_calendar(), NOW.date(), hourly_from=date(2026, 3, 1))

    @contextmanager
    def session() -> Generator[FakeMarket]:
        yield fake

    monkeypatch.chdir(tmp_path)  # logs/ and the report land here
    monkeypatch.setattr(cli, "lseg_session", session)
    monkeypatch.setattr(cli, "_now", lambda: NOW)
    monkeypatch.setattr(cli, "run_probe", partial(run_probe, retry=Retry(sleep=lambda _: None)))
    return fake


def _probe() -> tuple[int, str]:
    result = runner.invoke(app, ["probe", "--symbol", "nvda", "--out", "probes"])
    return result.exit_code, result.output


def test_cli_probe_writes_one_report_per_symbol_and_date(market: FakeMarket) -> None:
    code, output = _probe()

    assert code == 0, output
    assert Path("probes/NVDA_20260927.json").is_file()
    assert f"{market.calls} requests" in output


def test_cli_probe_refuses_to_overwrite_a_report_before_asking_anything(
    market: FakeMarket,
) -> None:
    _probe()
    calls = market.calls

    code, output = _probe()

    assert code == 1
    assert "never overwritten" in output
    assert market.calls == calls


@pytest.mark.parametrize("served", [5, 12])  # in the daily tape; in the DEC-83 asks
def test_cli_probe_dead_workspace_writes_nothing(market: FakeMarket, served: int) -> None:
    market.dies_after = served

    code, output = _probe()

    assert code == 1
    assert "wrote nothing" in output
    assert not Path("probes").exists()


def test_cli_probe_stopped_early_writes_its_report_and_fails(market: FakeMarket) -> None:
    market.odd_strikes_answer = {Interval.HOURLY}  # a never-listed RIC answers

    code, output = _probe()

    assert code == 1
    assert "stopped early" in output
    assert Path("probes/NVDA_20260927.json").is_file()
