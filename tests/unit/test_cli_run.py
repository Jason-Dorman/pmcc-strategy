"""`pmcc run` (P3-08): one config on one symbol's cache, written to `results/{SYM}/{run_id}.json`.

The market is the synthetic `random_walk`, cached in a temporary directory. The universe always
comes from configs/universe.yaml (PO, DEC-30), so these tests stand a test universe in for it:
`universe.yaml` in the working directory, read without the calendar's ten-week check, since the
market's window is four weeks. Provenance is fixed, so no test depends on this checkout's git state.
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
from pmcc.config.universe import UNIVERSE_PATH, Universe, read_universe_file
from pmcc.data.calendar import CalendarMismatchError
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET
from pmcc.domain.errors import EngineError
from pmcc.export.manifest import GitState, Provenance, ProvenanceError
from tests.fixtures.synthetic.market import generate
from tests.fixtures.synthetic.scenarios import random_walk

NOW = datetime(2026, 9, 30, 9, tzinfo=ET)
BASELINE = (CONFIGS_DIR / "baseline_pmcc.yaml").as_posix()
RESULT = Path("results/SYN/baseline_pmcc.json")

runner = CliRunner()


def _provenance(dirty: bool = False) -> Provenance:
    return Provenance(GitState("a" * 40, dirty), "b" * 64, "0.0.0")


RULE = "cash_multiple: 2, cash_round_to: 5000, calibration_cash: 1000000"  # E-L4's, and $1M


def cash_block(cost: int = 5_000, *, final: bool = False) -> str:
    """A calibrated starting cash for SYN: 2 × `cost` rounded up to $5,000 (DEC-30). Provisional
    on the baseline alone; final with the quant strategy too."""
    value = -(-2 * cost // 5_000) * 5_000
    strategies = ("baseline_pmcc", "quant_pmcc") if final else ("baseline_pmcc",)
    when = NOW.isoformat()
    entries = ", ".join(
        f"{{symbol: SYN, strategy: {s}, time: '{when}', contract: X, cost: {cost}}}"
        for s in strategies
    )
    head = f"value: {value}, provisional: {str(not final).lower()}, {RULE}"
    return f"starting_cash: {{{head}, entries: [{entries}]}}\n"


def _universe(cash: str | None = None, window: str = "") -> str:
    cash = cash_block() if cash is None else cash
    spec = random_walk()
    shipped = UNIVERSE_PATH.read_text(encoding="utf-8")
    rate = shipped[shipped.index("risk_free_rate:") : shipped.index("# The universe")]
    window = window or f"{{start: {spec.window_start}, end: {spec.window_end}}}"
    return (
        f"window: {window}\n{rate}"
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
    """The working directory: a test universe standing in for the shipped one, a fixed clock and
    provenance."""
    monkeypatch.chdir(tmp_path)  # logs/ and results/ land here
    Path("universe.yaml").write_text(_universe(), encoding="utf-8", newline="\n")

    def stand_in(_calendar: SessionCalendar) -> Universe:
        return read_universe_file(Path("universe.yaml"))

    monkeypatch.setattr(cli, "load_universe", stand_in)
    monkeypatch.setattr(cli, "provenance", _provenance)
    monkeypatch.setattr(cli, "_now", lambda: NOW)
    return tmp_path


def _run(cache: Path, symbol: str = "syn", config: str = BASELINE) -> tuple[int, str]:
    args = ["run", "--symbol", symbol, "--config", config, "--cache", str(cache)]
    result = runner.invoke(app, args)
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
    Path("universe.yaml").write_text(_universe(cash_block(12_000)), encoding="utf-8")

    code, output = _run(market)

    assert code == 0, output
    assert b'"starting_cash":25000.0000' in RESULT.read_bytes()


def test_dec_30_cli_run_has_no_universe_override(workdir: Path, market: Path) -> None:
    """Starting cash comes only from configs/universe.yaml (PO, DEC-30)."""
    args = ["run", "--symbol", "SYN", "--config", BASELINE, "--cache", str(market)]
    result = runner.invoke(app, [*args, "--universe", "universe.yaml"])

    assert result.exit_code == 2  # typer: no such option
    assert not Path("results").exists()


def test_dec_50_cli_run_on_a_dirty_tree_records_it_and_says_to_commit(
    workdir: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "provenance", lambda: _provenance(dirty=True))

    code, output = _run(market)

    assert code == 0, output
    assert _manifest()["git_dirty"] is True
    assert "git_dirty: true" in output
    assert "pmcc verify rejects dirty results" in output


def test_dec_30_cli_run_without_starting_cash_stops_naming_calibrate(
    workdir: Path, market: Path
) -> None:
    Path("universe.yaml").write_text(_universe(cash=""), encoding="utf-8")

    code, output = _run(market)

    assert code == 1
    assert "configs/universe.yaml has no starting_cash yet: run pmcc calibrate" in output
    assert not Path("results").exists()


def test_dec_30_cli_run_says_when_the_starting_cash_is_provisional(
    workdir: Path, market: Path
) -> None:
    code, output = _run(market)

    assert code == 0, output
    assert "Starting cash 10000.0000 is provisional (DEC-30)" in output


def test_dec_30_cli_run_is_silent_about_a_final_starting_cash(workdir: Path, market: Path) -> None:
    Path("universe.yaml").write_text(_universe(cash_block(final=True)), encoding="utf-8")

    code, output = _run(market)

    assert code == 0, output
    assert "provisional" not in output


@pytest.mark.usefixtures("workdir")
@pytest.mark.parametrize(
    "body",
    ["window: [unclosed\n", _universe("starting_cash: 10000.00005\n"), _universe("cash: 1\n")],
    ids=["bad-yaml", "sub-unit-cash", "unknown-key"],
)
def test_cli_run_a_bad_universe_fails_loudly(market: Path, body: str) -> None:
    Path("universe.yaml").write_text(body, encoding="utf-8")

    code, output = _run(market)

    assert code == 1
    assert "configs/universe.yaml:" in output
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


def test_dec_92_cli_run_refuses_a_window_its_cache_doesnt_cover(
    workdir: Path, market: Path
) -> None:
    window = "{start: 2026-03-30, end: 2026-09-25}"  # the market starts in July
    Path("universe.yaml").write_text(_universe(window=window), encoding="utf-8")

    code, output = _run(market)

    assert code == 1
    assert "no stock bars on" in output
    assert "pmcc fetch" in output
    assert not Path("results").exists()


def _variant(params: str) -> str:
    for name in ("_shared.yaml", "baseline_pmcc.yaml"):
        Path(name).write_bytes((CONFIGS_DIR / name).read_bytes())
    lines = ["id: baseline_pmcc--bad", "name: Bad", "extends: baseline_pmcc.yaml", "overrides:",
             f"  E-T1: {{params: {params}}}"]  # fmt: skip
    Path("variant.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return "variant.yaml"


@pytest.mark.usefixtures("workdir")
@pytest.mark.parametrize(
    ("config", "said"),
    [("missing.yaml", "no config file"), ("broken.yaml", "broken.yaml"),
     ("refused", "variant.yaml")],
)  # fmt: skip
def test_cli_run_a_bad_config_fails_loudly(market: Path, config: str, said: str) -> None:
    Path("broken.yaml").write_text("id: [unclosed\n", encoding="utf-8")
    if config == "refused":
        config = _variant("{short_max_spread: 2}")  # a fraction must be below 1

    code, output = _run(market, config=config)

    assert code == 1
    assert said in output
    assert not Path("results").exists()


@pytest.mark.parametrize(
    "error",
    [EngineError("NAV doesn't reconcile"), CalendarMismatchError("a tape day isn't a session"),
     ValueError("two RICs")],
    ids=["engine", "calendar", "value"],
)  # fmt: skip
def test_cli_run_a_run_error_writes_nothing(
    workdir: Path, market: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    def fail(*_args: object) -> object:
        raise error

    monkeypatch.setattr(cli, "run_symbol", fail)

    code, output = _run(market)

    assert code == 1
    assert f"{error}; nothing was written" in output
    assert not Path("results").exists()


def test_cli_run_a_provenance_error_writes_nothing(
    workdir: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail() -> Provenance:
        raise ProvenanceError("git isn't installed; a run records its commit")

    monkeypatch.setattr(cli, "provenance", fail)

    code, output = _run(market)

    assert code == 1
    assert "git isn't installed" in output
    assert not Path("results").exists()


def test_cli_run_replaces_an_earlier_result(workdir: Path, market: Path) -> None:
    RESULT.parent.mkdir(parents=True)
    RESULT.write_text("an earlier run\n", encoding="utf-8")

    code, output = _run(market)

    assert code == 0, output
    assert _manifest()["run_id"] == "baseline_pmcc"
