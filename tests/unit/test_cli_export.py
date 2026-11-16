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
from pmcc.live.config import LIVE_PATH
from pmcc.runner import Stamp, run_loaded
from tests.fixtures.synthetic.scenarios import random_walk
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario.harness import CASH, SEED, config

WHEN = datetime(2026, 9, 30, 9, tzinfo=ET)
CLEAN = Provenance(GitState("0" * 40, dirty=False), "1" * 64, "0.0.0")

runner = CliRunner()


def _results(synthetic: SyntheticMarkets, tmp: Path, provenance: Provenance = CLEAN) -> Path:
    spec = random_walk()
    loaded = synthetic.get("random_walk", random_walk).symbol
    cfg = config(tmp, "", spec.window_start, spec.window_end)
    out = tmp / "results"
    stamp = Stamp(provenance, DataSource.SYNTHETIC, WHEN)
    write_result(run_loaded(loaded, loaded.symbol, cfg, CASH, stamp, seed=SEED), out)
    return out


@pytest.fixture(scope="module")
def results(synthetic: SyntheticMarkets, tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _results(synthetic, tmp_path_factory.mktemp("cli_export"))


@pytest.fixture
def workdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo root: logs/ lands here, and it holds the live wheel's files, which export reads
    from the root by default (L4-01): no orders, an empty run log."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "open_orders.json").write_text("[]\n", encoding="utf-8")
    (tmp_path / "live").mkdir()
    (tmp_path / "live" / "runs.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "configs").mkdir()
    shutil.copyfile(LIVE_PATH, tmp_path / "configs" / "live.yaml")
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
    for name in ("index.json", "rules.json", "live.json", "SYN/baseline_pmcc.json"):
        assert (workdir / "site" / name).is_file()


def test_l4_01_cli_export_reads_the_live_config_from_the_root_and_refuses_one_without(
    workdir: Path, results: Path
) -> None:
    (workdir / "configs" / "live.yaml").unlink()

    code, output = _invoke("export", "--results", str(results), "--out", "site")

    assert code == 1
    assert "the live wheel's page:" in output
    assert "live.yaml" in output
    assert "Nothing was exported." in output
    assert not (workdir / "site").exists()


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


def test_cli_export_schema_only_never_plants_files_in_a_foreign_directory(workdir: Path) -> None:
    """Otherwise a later export would take the directory for its own and clear it."""
    (workdir / "project").mkdir()
    (workdir / "project" / "notes.txt").write_text("keep\n", encoding="utf-8")

    code, output = _invoke("export", "--schema-only", "--out", "project")

    assert code == 1
    assert "doesn't write" in output
    assert sorted(p.name for p in (workdir / "project").iterdir()) == ["notes.txt"]
