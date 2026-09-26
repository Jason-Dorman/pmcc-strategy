"""The `pmcc` command surface (ARCHITECTURE §3.1, Spec › CLI)."""

import pytest
from typer.testing import CliRunner

from pmcc.cli import app

COMMANDS = ["fetch", "probe", "run", "batch", "calibrate", "export", "verify", "serve"]

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
        (["probe", "--symbol", "NVDA"], "P1-04"),
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
