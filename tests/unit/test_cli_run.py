"""`pmcc run` (P3-08): one config on one symbol's cache, written to `results/{SYM}/{run_id}.json`.

The market is the synthetic `random_walk`, cached in the working directory. Its window is four
weeks, shorter than a universe may be, so the universe is read without the calendar's ten-week
check. Provenance is fixed, so no test depends on this checkout's git state.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from pmcc import cli
from pmcc.cli import app
from pmcc.config.strategy import CONFIGS_DIR
from pmcc.config.universe import UNIVERSE_PATH, read_universe_file
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET
from pmcc.domain.errors import EngineError
from pmcc.export.manifest import GitState, Provenance
from tests.fixtures.synthetic.market import generate
from tests.fixtures.synthetic.scenarios import random_walk

NOW = datetime(2026, 9, 30, 9, tzinfo=ET)
BASELINE = (CONFIGS_DIR / "baseline_pmcc.yaml").as_posix()
RESULT = Path("results/SYN/baseline_pmcc.json")

runner = CliRunner()


def _provenance(dirty: bool = False) -> Provenance:
    return Provenance(GitState("a" * 40, dirty), "b" * 64, "0.0.0")


def _universe(cash: str = "starting_cash: 10000\n") -> str:
    spec = random_walk()
    shipped = UNIVERSE_PATH.read_text(encoding="utf-8")
    rate = shipped[shipped.index("risk_free_rate:") : shipped.index("# The universe")]
    return (
        f"window: {{start: {spec.window_start}, end: {spec.window_end}}}\n{rate}"
        "symbols:\n  - {symbol: SYN, stock_ric: SYN.O, option_root: SYN}\n"
        f"{cash}"
    )


@pytest.fixture(scope="module")
def market(tmp_path_factory: pytest.TempPathFactory) -> Path:
    cache = tmp_path_factory.mktemp("market")
    generate(random_walk(), cache)
    return cache


@pytest.fixture
def workdir(tmp_path: Path, market: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The working directory: the cached market, a universe file, a fixed clock and provenance."""
    monkeypatch.chdir(tmp_path)  # logs/ and results/ land here
    Path("universe.yaml").write_text(_universe(), encoding="utf-8", newline="\n")

    def short_window_universe(_calendar: SessionCalendar, path: Path) -> object:
        return read_universe_file(path)

    monkeypatch.setattr(cli, "load_universe", short_window_universe)
    monkeypatch.setattr(cli, "provenance", _provenance)
    monkeypatch.setattr(cli, "_now", lambda: NOW)
    return tmp_path


def _run(cache: Path, symbol: str = "syn", config: str = BASELINE) -> tuple[int, str]:
    base = ["run", "--symbol", symbol, "--config", config, "--universe", "universe.yaml"]
    result = runner.invoke(app, [*base, "--cache", str(cache)])
    return result.exit_code, result.output


def _manifest(path: Path = RESULT) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_bytes()))["manifest"]


def test_cli_run_writes_the_result_under_symbol_and_run_id(workdir: Path, market: Path) -> None:
    code, output = _run(market)

    assert code == 0, output
    manifest = _manifest()
    assert (manifest["symbol"], manifest["run_id"], manifest["data_source"]) == (
        "SYN", "baseline_pmcc", "lseg")  # fmt: skip
    assert manifest["run_timestamp"] == NOW.isoformat()
    assert "SYN baseline_pmcc:" in output
    assert "Written to results/SYN/baseline_pmcc.json" in output
    assert "Log: logs/run_" in output
    assert "git_dirty: true" not in output


def test_cli_run_takes_starting_cash_from_the_universe(workdir: Path, market: Path) -> None:
    Path("universe.yaml").write_text(_universe("starting_cash: 25000\n"), encoding="utf-8")

    code, output = _run(market)

    assert code == 0, output
    assert b'"starting_cash":25000.0000' in RESULT.read_bytes()


def test_dec_50_cli_run_on_a_dirty_tree_records_it_and_says_to_commit(
    workdir: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "provenance", lambda: _provenance(dirty=True))

    code, output = _run(market)

    assert code == 0, output
    assert _manifest()["git_dirty"] is True
    assert "git_dirty: true" in output
    assert "pmcc verify rejects dirty results" in output


def test_dec_30_cli_run_without_starting_cash_stops_naming_p3_09(
    workdir: Path, market: Path
) -> None:
    Path("universe.yaml").write_text(_universe(cash=""), encoding="utf-8")

    code, output = _run(market)

    assert code == 1
    assert "no starting_cash" in output
    assert "P3-09" in output
    assert not Path("results").exists()


def test_dec_30_cli_run_on_the_shipped_universe_stops_naming_p3_09(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["run", "--symbol", "NVDA", "--config", BASELINE,
                                 "--universe", str(UNIVERSE_PATH)])  # fmt: skip

    assert result.exit_code == 1
    assert "P3-09" in result.output
    assert not Path("results").exists()


def test_cli_run_refuses_a_symbol_outside_the_universe(workdir: Path, market: Path) -> None:
    code, output = _run(market, symbol="NVDA")

    assert code == 1
    assert "isn't in configs/universe.yaml" in output


@pytest.mark.usefixtures("workdir")
def test_cli_run_without_a_cache_fails_loudly_and_writes_nothing(tmp_path: Path) -> None:
    code, output = _run(tmp_path / "empty_cache")

    assert code == 1
    assert "nothing was written" in output
    assert not Path("results").exists()


@pytest.mark.usefixtures("workdir")
@pytest.mark.parametrize(
    ("config", "said"),
    [("missing.yaml", "no config file"), ("broken.yaml", "broken.yaml")],
)
def test_cli_run_a_bad_config_fails_loudly(market: Path, config: str, said: str) -> None:
    Path("broken.yaml").write_text("id: [unclosed\n", encoding="utf-8")

    code, output = _run(market, config=config)

    assert code == 1
    assert said in output
    assert not Path("results").exists()


def test_cli_run_an_engine_error_writes_nothing(
    workdir: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_args: object) -> object:
        raise EngineError("NAV doesn't reconcile")

    monkeypatch.setattr(cli, "run_symbol", fail)

    code, output = _run(market)

    assert code == 1
    assert "NAV doesn't reconcile; nothing was written" in output
    assert not Path("results").exists()


def test_cli_run_replaces_an_earlier_result(workdir: Path, market: Path) -> None:
    RESULT.parent.mkdir(parents=True)
    RESULT.write_text("an earlier run\n", encoding="utf-8")

    code, output = _run(market)

    assert code == 0, output
    assert _manifest()["run_id"] == "baseline_pmcc"
