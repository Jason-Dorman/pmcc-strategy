"""`pmcc wheel` (W2-03): the wheel on one symbol's cache, written to `results/{SYM}/wheel.json`.

The market is `winv10_run.full_wheel`, cached as `pmcc fetch` and `pmcc fetch --wheel` leave a
symbol (puts in the wheel part); the baseline PMCC's result on it sits in the working directory's
`results/`, as `pmcc batch` leaves it, with an S&P 500 file for its window (W3-01). As in
`test_cli_run`, a test universe in the working directory stands in for configs/universe.yaml, and
the clock and provenance are fixed.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from pmcc import cli
from pmcc.cli import app
from pmcc.config.universe import UNIVERSE_PATH, Universe, read_universe_file
from pmcc.data.cache import WHEEL_PART
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET
from pmcc.domain.errors import EngineError
from pmcc.export.manifest import GitState, Provenance, ProvenanceError
from pmcc.export.verify import verify
from pmcc.wheel.config import FRICTION_DIR, WHEEL_PATH
from tests.scenario import winv10_run

NOW = datetime(2026, 10, 5, 9, tzinfo=ET)
RESULT = Path("results/SYN/wheel.json")

runner = CliRunner()


def _provenance(dirty: bool = False) -> Provenance:
    return Provenance(GitState("a" * 40, dirty), "b" * 64, "0.0.0")


def _universe(symbols: tuple[str, ...] = ("SYN",)) -> str:
    """The shipped r, the market's window and `symbols`; no starting cash, which the wheel's
    config holds (WD-10)."""
    spec = winv10_run.full_wheel()
    shipped = UNIVERSE_PATH.read_text(encoding="utf-8")
    rate = shipped[shipped.index("risk_free_rate:") : shipped.index("# The universe")]
    listed = "".join(f"  - {{symbol: {s}, stock_ric: {s}.O, option_root: {s}}}\n" for s in symbols)
    return (
        f"window: {{start: {spec.window_start}, end: {spec.window_end}}}\n{rate}symbols:\n{listed}"
    )


@pytest.fixture(scope="module")
def market(tmp_path_factory: pytest.TempPathFactory) -> Path:
    cache = tmp_path_factory.mktemp("wheel_market")
    winv10_run.generate_market(cache)
    return cache


@pytest.fixture(scope="module")
def benchmarks(market: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """`results/` holding the baseline PMCC, and the S&P 500 file, under one directory."""
    root = tmp_path_factory.mktemp("benchmarks")
    winv10_run.write_benchmarks(market, root / "results", root)
    return root


@pytest.fixture
def workdir(tmp_path: Path, benchmarks: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)  # logs/ and results/ land here
    Path("universe.yaml").write_text(_universe(), encoding="utf-8", newline="\n")
    shutil.copytree(benchmarks / "results", "results")
    shutil.copy(benchmarks / "benchmarks.yaml", "benchmarks.yaml")

    def stand_in(_calendar: SessionCalendar) -> Universe:
        return read_universe_file(Path("universe.yaml"))

    monkeypatch.setattr(cli, "load_universe", stand_in)
    monkeypatch.setattr(cli, "provenance", _provenance)
    monkeypatch.setattr(cli, "_now", lambda: NOW)
    return tmp_path


def _wheel(cache: Path, *args: str, symbol: str = "syn") -> tuple[int, str]:
    args = ("--benchmarks", "benchmarks.yaml", *args)
    result = runner.invoke(app, ["wheel", "--symbol", symbol, "--cache", str(cache), *args])
    return result.exit_code, result.output


def _doc(path: Path = RESULT) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_bytes()))


def test_w2_03_cli_wheel_writes_the_result_under_symbol_and_run_id(
    workdir: Path, market: Path
) -> None:
    code, output = _wheel(market)

    assert code == 0, output
    manifest = _doc()["manifest"]
    assert (manifest["symbol"], manifest["run_id"], manifest["data_source"]) == (
        "SYN", "wheel", "lseg")  # fmt: skip
    assert manifest["run_timestamp"] == NOW.isoformat()
    assert "SYN wheel: 10 trades over 168 bars and 5 weeks; final NAV" in output
    assert "Written to results/SYN/wheel.json" in output
    assert "Log: logs/wheel_" in output
    assert "git_dirty: true" not in output
    assert verify(Path("results")).problems == ()


def test_wd_10_cli_wheel_takes_its_starting_cash_from_the_wheel_config(
    workdir: Path, market: Path
) -> None:
    code, output = _wheel(market)

    assert code == 0, output
    assert _doc()["starting_cash"] == 25000.0
    assert _doc()["config"]["window"] == {"start": "2026-08-31", "end": "2026-10-02"}


def test_w2_03_cli_wheel_runs_another_wheel_config_under_its_own_id(
    workdir: Path, market: Path
) -> None:
    variant = Path("wheel--sc050.yaml")
    text = WHEEL_PATH.read_text(encoding="utf-8")
    text = text.replace("id: wheel\n", "id: wheel--sc050\n").replace(
        "spread_capture: 0.0", "spread_capture: 0.5")  # fmt: skip
    variant.write_text(text, encoding="utf-8", newline="\n")

    code, output = _wheel(market, "--config", str(variant))

    assert code == 0, output
    written = Path("results/SYN/wheel--sc050.json")
    assert _doc(written)["config"]["wheel"]["fill_model"]["spread_capture"] == 0.5
    assert not RESULT.exists()
    assert verify(Path("results")).problems == ()


def test_dec_50_cli_wheel_on_a_dirty_tree_records_it_and_says_to_commit(
    workdir: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "provenance", lambda: _provenance(dirty=True))

    code, output = _wheel(market)

    assert code == 0, output
    assert _doc()["manifest"]["git_dirty"] is True
    assert "pmcc verify rejects dirty results" in output


def test_w2_03_cli_wheel_without_the_wheels_puts_fails_and_writes_nothing(
    workdir: Path, market: Path, tmp_path: Path
) -> None:
    cache = tmp_path / "no_part"
    shutil.copytree(market, cache, ignore=shutil.ignore_patterns(WHEEL_PART))

    code, output = _wheel(cache)

    assert code == 1
    assert "pmcc fetch --wheel" in output
    assert "nothing was written" in output
    assert not RESULT.exists()


def test_w2_03_cli_wheel_refuses_a_symbol_outside_the_universe(workdir: Path, market: Path) -> None:
    code, output = _wheel(market, symbol="ABC")

    assert code == 1
    assert "ABC isn't in configs/universe.yaml" in output
    assert not RESULT.exists()


@pytest.mark.parametrize(
    ("body", "said"),
    [("id: wheel\nname: Wheel\n", "rules"), ("{not yaml", "")],
)
def test_w2_03_cli_wheel_a_bad_config_fails_loudly(
    workdir: Path, market: Path, body: str, said: str
) -> None:
    Path("bad.yaml").write_text(body, encoding="utf-8")

    code, output = _wheel(market, "--config", "bad.yaml")

    assert code == 1
    assert "bad.yaml" in output
    assert said in output
    assert not RESULT.exists()


def test_w2_03_cli_wheel_a_run_error_writes_nothing(
    workdir: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def broken(*_args: object) -> None:
        raise EngineError("WINV-05: the put isn't cash-secured")

    monkeypatch.setattr(cli, "run_wheel_symbol", broken)

    code, output = _wheel(market)

    assert code == 1
    assert "WINV-05" in output
    assert "nothing was written" in output
    assert not RESULT.exists()


def test_w2_03_cli_wheel_a_provenance_error_writes_nothing(
    workdir: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_git() -> Provenance:
        raise ProvenanceError("git isn't installed; a run records its commit")

    monkeypatch.setattr(cli, "provenance", no_git)

    code, output = _wheel(market)

    assert code == 1
    assert "git isn't installed" in output
    assert not RESULT.exists()


def test_w2_03_cli_wheel_replaces_an_earlier_result(workdir: Path, market: Path) -> None:
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text("stale\n", encoding="utf-8")

    code, output = _wheel(market)

    assert code == 0, output
    assert _doc()["manifest"]["run_id"] == "wheel"


def test_w3_01_cli_wheel_states_each_thesis_claims_verdict(workdir: Path, market: Path) -> None:
    code, output = _wheel(market)

    assert code == 0, output
    claims = _doc()["summary"]["thesis"]
    for claim in claims:
        met = "met" if claim["met"] else "not met"
        assert f"Claim {claim['claim']} ({claim['test']}): {met}" in output
    assert [c["met"] for c in claims] == [True, False, True]


def test_w3_01_cli_wheel_without_the_baseline_pmcc_fails_naming_the_batch(
    workdir: Path, market: Path
) -> None:
    Path("results/SYN/baseline_pmcc.json").unlink()

    code, output = _wheel(market)

    assert code == 1
    assert "baseline_pmcc.json is missing: run pmcc batch first" in output
    assert not RESULT.exists()


def test_w3_01_cli_wheel_refuses_an_sp500_file_off_the_window(workdir: Path, market: Path) -> None:
    text = Path("benchmarks.yaml").read_text(encoding="utf-8")
    Path("benchmarks.yaml").write_text(text.replace("2026-08-28", "2026-08-27"), encoding="utf-8")

    code, output = _wheel(market)

    assert code == 1
    assert "the last close before the window is 2026-08-28" in output
    assert not RESULT.exists()


def test_w3_02_cli_wheel_runs_a_shipped_friction_variant(workdir: Path, market: Path) -> None:
    code, output = _wheel(market, "--config", str(FRICTION_DIR / "sc025.yaml"))

    assert code == 0, output
    written = _doc(Path("results/SYN/wheel--sc025.json"))
    assert written["config"]["wheel"]["fill_model"]["spread_capture"] == 0.25
    assert written["manifest"]["strategy_id"] == "wheel"
    assert verify(Path("results")).problems == ()
