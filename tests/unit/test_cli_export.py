"""`pmcc verify` and `pmcc export` (P4-05) on synthetic results, as `pmcc run` writes them."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest
from typer.testing import CliRunner

from pmcc.cli import app
from pmcc.domain.clock import ET
from pmcc.export import canonical
from pmcc.export.manifest import GitState, Provenance
from pmcc.export.models import DataSource
from pmcc.export.results import write_result
from pmcc.export.schema import SCHEMAS
from pmcc.runner import Stamp, run_loaded
from tests.fixtures.synthetic.scenarios import random_walk
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario.harness import CASH, config

WHEN = datetime(2026, 9, 30, 9, tzinfo=ET)
CLEAN = Provenance(GitState("0" * 40, dirty=False), "1" * 64, "0.0.0")

runner = CliRunner()


def _results(synthetic: SyntheticMarkets, tmp: Path, provenance: Provenance = CLEAN) -> Path:
    spec = random_walk()
    loaded = synthetic.get("random_walk", random_walk).symbol
    cfg = config(tmp, "", spec.window_start, spec.window_end)
    out = tmp / "results"
    write_result(run_loaded(loaded, loaded.symbol, cfg, CASH,
                            Stamp(provenance, DataSource.SYNTHETIC, WHEN)), out)  # fmt: skip
    return out


@pytest.fixture(scope="module")
def results(synthetic: SyntheticMarkets, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _results(synthetic, tmp_path_factory.mktemp("cli_export"))


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)  # logs/ lands here
    return tmp_path


def _invoke(*args: str) -> tuple[int, str]:
    done = runner.invoke(app, list(args))
    return done.exit_code, done.output


def _break_nav(results: Path, tmp: Path) -> Path:
    copied = tmp / "broken"
    shutil.copytree(results, copied)
    path = copied / "SYN" / "baseline_pmcc.json"
    doc = cast(dict[str, Any], canonical.loads(path.read_bytes()))
    doc["ledger"][0]["nav"] = canonical.Number("1.0000")
    path.write_bytes(canonical.to_bytes(doc))
    return copied


# ---- pmcc verify --------------------------------------------------------------------------------


@pytest.mark.usefixtures("workdir")
def test_cli_verify_passes_results_as_written(results: Path) -> None:
    code, output = _invoke("verify", str(results))

    assert code == 0, output
    assert "Verified 1 files (1 runs): every check passed." in output


def test_cli_verify_prints_each_problem_and_exits_1(workdir: Path, results: Path) -> None:
    code, output = _invoke("verify", str(_break_nav(results, workdir)))

    assert code == 1
    assert "SYN/baseline_pmcc.json: INV-02: NAV at " in output
    assert "problem(s) in 1 files (1 runs)." in output


@pytest.mark.usefixtures("workdir")
def test_dec_50_cli_verify_refuses_dirty_results(synthetic: SyntheticMarkets,
                                                 tmp_path: Path) -> None:  # fmt: skip
    dirty = _results(synthetic, tmp_path / "d", Provenance(GitState("0" * 40, True), "1" * 64, "0"))

    code, output = _invoke("verify", str(dirty))

    assert code == 1
    assert "git_dirty: it ran on a dirty tree" in output


def test_cli_verify_needs_a_results_directory(workdir: Path) -> None:
    code, output = _invoke("verify", str(workdir / "missing"))

    assert code == 1
    assert "isn't a directory of results" in output


# ---- pmcc export --------------------------------------------------------------------------------


def test_cli_export_writes_the_site_data(workdir: Path, results: Path) -> None:
    code, output = _invoke("export", "--results", str(results), "--out", "site")

    assert code == 0, output
    assert "Exported 1 runs for 1 symbol(s), 1 results files, to site" in output
    assert "Not publishable" not in output
    for name in ("index.json", "rules.json", "SYN/baseline_pmcc.json"):
        assert (workdir / "site" / name).is_file()


def test_cli_export_names_runs_from_a_dirty_tree(synthetic: SyntheticMarkets,
                                                  workdir: Path) -> None:  # fmt: skip
    dirty = _results(synthetic, workdir / "d", Provenance(GitState("0" * 40, True), "1" * 64, "0"))

    code, output = _invoke("export", "--results", str(dirty), "--out", "site")

    assert code == 0, output
    assert "Not publishable, from a dirty tree" in output
    assert "SYN/baseline_pmcc.json" in output


def test_cli_export_refuses_results_that_fail_verification(workdir: Path, results: Path) -> None:
    code, output = _invoke("export", "--results", str(_break_nav(results, workdir)), "--out",
                           "site")  # fmt: skip

    assert code == 1
    assert "INV-02" in output
    assert "Nothing was exported." in output
    assert not (workdir / "site").exists()


def test_cli_export_schema_only_needs_no_results(workdir: Path) -> None:
    code, output = _invoke("export", "--schema-only", "--results", "missing", "--out", "site")

    assert code == 0, output
    assert f"{len(SCHEMAS)} schemas written to site/schema" in output
    assert sorted(p.name for p in (workdir / "site").iterdir()) == ["schema"]
