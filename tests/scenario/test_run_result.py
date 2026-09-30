"""A run's result file (P3-08): rows that mirror the engine, the manifest, and INV-13.

INV-13: re-running a config on cached data gives byte-identical results once
`manifest.run_timestamp` is dropped (PO, DEC-50).
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.config.strategy import RunConfig
from pmcc.data.load import load_symbol
from pmcc.data.ric import occ_symbol, parse_ric
from pmcc.domain.clock import ET
from pmcc.engine.loop import RunOutput
from pmcc.export import canonical
from pmcc.export.manifest import Provenance, provenance
from pmcc.export.models import DataSource, RunResult
from pmcc.export.results import result_path, to_bytes, write_result
from pmcc.runner import Stamp, run_loaded
from tests.fakes.git_repo import make_repo
from tests.fixtures.synthetic.market import generate
from tests.fixtures.synthetic.scenarios import BUILDERS, random_walk
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario import inv13_run
from tests.scenario.harness import CASH, NO_TAKE_PROFIT, config, run

REPO_ROOT = Path(__file__).resolve().parents[2]
WHEN = datetime(2026, 9, 30, 9, tzinfo=ET)
PROVENANCE = inv13_run.PROVENANCE


def _stamp(provenance: Provenance = PROVENANCE, when: datetime = WHEN) -> Stamp:
    return Stamp(provenance, DataSource.SYNTHETIC, when)


def _result(synthetic: SyntheticMarkets, cfg: RunConfig, stamp: Stamp | None = None) -> RunResult:
    loaded = synthetic.get("random_walk", random_walk).symbol
    return run_loaded(loaded, loaded.symbol, cfg, CASH, stamp or _stamp())


@pytest.fixture(scope="module")
def engine(synthetic: SyntheticMarkets, tmp_path_factory: pytest.TempPathFactory) -> RunOutput:
    return run(synthetic, tmp_path_factory.mktemp("cfg"), "random_walk", random_walk)


@pytest.fixture(scope="module")
def result(synthetic: SyntheticMarkets, tmp_path_factory: pytest.TempPathFactory) -> RunResult:
    spec = random_walk()
    cfg = config(tmp_path_factory.mktemp("cfg"), "", spec.window_start, spec.window_end)
    return _result(synthetic, cfg)


# ---- the rows mirror the engine's output --------------------------------------------------------


def test_run_result_blotter_mirrors_the_engine(engine: RunOutput, result: RunResult) -> None:
    assert len(engine.blotter) >= 3  # the long, a short, and more
    assert len(result.blotter) == len(engine.blotter)
    for row, event in zip(result.blotter, engine.blotter, strict=True):
        assert (row.time, row.side, row.qty, row.rule_id, row.notes) == (
            event.time, event.side.value, event.qty, event.rule_id, event.notes)  # fmt: skip
        assert row.cash_delta == event.cash_delta.to_dollars()
        assert row.fee == event.fee.to_dollars()
        assert row.fill == (None if event.fill is None else event.fill.to_dollars())
        assert row.limit == (None if event.limit is None else event.limit.to_dollars())
        assert row.audit == dict(event.audit)


def test_run_result_names_each_option_by_the_ric_its_cache_answered(result: RunResult) -> None:
    options = [r.instrument for r in result.blotter if r.instrument.kind == "call"]

    assert options
    for named in options:
        option = parse_ric(named.ric).option
        assert named.occ == occ_symbol(option)
        assert (named.expiry, named.strike) == (option.expiry, option.strike.to_dollars())


def test_run_result_ledger_mirrors_the_engine(engine: RunOutput, result: RunResult) -> None:
    assert len(result.ledger) == len(engine.ledger) > 0
    for row, bar in zip(result.ledger, engine.ledger, strict=True):
        assert row.time == bar.time
        assert (row.cash, row.nav, row.im, row.mm) == tuple(
            m.to_dollars() for m in (bar.cash, bar.nav, bar.im, bar.mm))  # fmt: skip
        assert (row.available_funds, row.excess_equity) == (
            bar.available_funds.to_dollars(), bar.excess_equity.to_dollars())  # fmt: skip
        assert row.flags == bar.flags
        for leg, held in ((row.long, bar.long), (row.short, bar.short)):
            assert (leg is None) == (held is None)
            if leg is not None and held is not None:
                assert parse_ric(leg.instrument.ric).option == held.option
                assert (leg.qty, leg.mark, leg.stale, leg.delta) == (
                    held.qty, held.mark.to_dollars(), held.stale, held.delta)  # fmt: skip


def test_run_result_gate_log_mirrors_the_engine(engine: RunOutput, result: RunResult) -> None:
    assert len(result.gate_log) == len(engine.gate_log) == 4  # one row per week
    for row, week in zip(result.gate_log, engine.gate_log, strict=True):
        assert (row.session, row.decision_time, row.notes) == (
            week.session, week.decision_time, week.notes)  # fmt: skip
        assert (row.outcome.kind, row.outcome.rule_id) == (week.outcome, week.rule_id)
        assert row.selected == (None if week.selected is None else dict(week.selected))
        assert [(g.rule_id, g.status, g.values) for g in row.gates] == [
            (g.rule_id, g.status.value, dict(g.values)) for g in week.gates]  # fmt: skip


def test_run_result_starting_cash_and_rule_text(result: RunResult) -> None:
    assert result.starting_cash == Decimal("10000.0000")
    rules = result.config.strategy.rules
    assert list(result.rule_text) == [r.id for r in rules]
    for rule in rules:
        text = rule.text()
        assert result.rule_text[rule.id].condition == text.condition
        assert result.rule_text[rule.id].rationale == text.rationale


def test_run_result_short_stock_is_named_by_the_tape_ric(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    build = BUILDERS["late_friday_surge"]
    loaded = synthetic.get("late_friday_surge", build).symbol
    spec = build()
    cfg = config(tmp_path, NO_TAKE_PROFIT, spec.window_start, spec.window_end)
    found = run_loaded(loaded, loaded.symbol, cfg, CASH, _stamp())

    stock_rows = [r.instrument for r in found.blotter if r.instrument.kind == "stock"]
    held = [r.stock.instrument for r in found.ledger if r.stock is not None]
    assert stock_rows
    assert held
    for named in (*stock_rows, *held):
        assert (named.ric, named.occ, named.expiry, named.strike) == ("SYN.O", None, None, None)


# ---- the manifest -------------------------------------------------------------------------------


def test_run_result_manifest_records_what_produced_the_run(
    synthetic: SyntheticMarkets, result: RunResult
) -> None:
    manifest = result.manifest
    loaded = synthetic.get("random_walk", random_walk).symbol

    assert (manifest.run_id, manifest.strategy_id, manifest.symbol) == (
        "baseline_pmcc", "baseline_pmcc", "SYN")  # fmt: skip
    assert manifest.config_hash == result.config.config_hash()
    assert manifest.data_manifest_hash == loaded.data_manifest_hash
    assert (manifest.git_sha, manifest.git_dirty) == ("0" * 40, False)
    assert (manifest.lock_hash, manifest.pmcc_version) == ("1" * 64, "0.0.0")
    assert (manifest.run_timestamp, manifest.data_source) == (WHEN, DataSource.SYNTHETIC)


def test_run_result_a_variants_strategy_is_its_base(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    spec = random_walk()
    cfg = config(tmp_path, NO_TAKE_PROFIT, spec.window_start, spec.window_end)

    manifest = _result(synthetic, cfg).manifest

    assert (manifest.run_id, manifest.strategy_id) == ("baseline_pmcc--test", "baseline_pmcc")


def test_run_result_file_config_hashes_to_the_manifests_config_hash(result: RunResult) -> None:
    written = cast(dict[str, Any], json.loads(to_bytes(result)))
    config_json = json.dumps(written["config"], sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False)  # fmt: skip

    assert hashlib.sha256(config_json.encode()).hexdigest() == written["manifest"]["config_hash"]


def test_dec_50_a_dirty_tree_records_git_dirty_true(
    synthetic: SyntheticMarkets, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(tmp_path, monkeypatch)
    (repo / "pmcc" / "rules.py").write_text("X = 2\n", encoding="utf-8")
    spec = random_walk()
    cfg = config(tmp_path, "", spec.window_start, spec.window_end)

    path = write_result(_result(synthetic, cfg, _stamp(provenance(repo))), tmp_path / "results")

    manifest = cast(dict[str, Any], json.loads(path.read_bytes()))["manifest"]
    assert manifest["git_dirty"] is True


def test_dec_50_a_clean_tree_records_git_dirty_false(
    synthetic: SyntheticMarkets, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(tmp_path, monkeypatch)
    spec = random_walk()
    cfg = config(tmp_path, "", spec.window_start, spec.window_end)

    path = write_result(_result(synthetic, cfg, _stamp(provenance(repo))), tmp_path / "results")

    manifest = cast(dict[str, Any], json.loads(path.read_bytes()))["manifest"]
    assert manifest["git_dirty"] is False


# ---- the file -----------------------------------------------------------------------------------


def test_run_result_file_is_canonical_json(result: RunResult) -> None:
    raw = to_bytes(result)

    assert raw.endswith(b"}\n")
    assert raw.count(b"\n") == 1
    assert b"\r" not in raw
    assert canonical.to_bytes(canonical.loads(raw)) == raw  # re-dumping changes nothing


def test_run_result_file_prints_money_to_four_places(result: RunResult) -> None:
    raw = to_bytes(result)

    assert b'"starting_cash":10000.0000' in raw
    assert b'"fee":0.0000' in raw


def test_run_result_writes_to_symbol_and_run_id_replacing_an_earlier_file(
    result: RunResult, tmp_path: Path
) -> None:
    stale = result_path(tmp_path, "SYN", "baseline_pmcc")
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"an earlier run, longer than nothing at all " * 10_000)

    path = write_result(result, tmp_path)

    assert path == tmp_path / "SYN" / "baseline_pmcc.json"
    assert path.read_bytes() == to_bytes(result)
    assert [p.name for p in path.parent.iterdir()] == ["baseline_pmcc.json"]  # no temp file left


def test_run_result_models_refuse_unknown_fields(result: RunResult) -> None:
    data = result.model_dump()
    data["extra"] = 1

    with pytest.raises(ValueError, match="extra"):
        RunResult.model_validate(data)


# ---- INV-13 -------------------------------------------------------------------------------------


def test_inv_13_the_same_run_twice_in_one_process_writes_identical_bytes(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    spec = random_walk()
    cfg = config(tmp_path, "", spec.window_start, spec.window_end)

    assert to_bytes(_result(synthetic, cfg)) == to_bytes(_result(synthetic, cfg))


def _start(cache: Path, out: Path, hour: int, seed: str) -> subprocess.Popen[bytes]:
    command = [sys.executable, "-m", "tests.scenario.inv13_run", str(cache), str(out), str(hour)]
    env = {**os.environ, "PYTHONHASHSEED": seed}
    return subprocess.Popen(command, cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)  # fmt: skip


def test_inv_13_two_runs_are_byte_identical_once_run_timestamp_is_dropped(tmp_path: Path) -> None:
    """Two fresh processes, different hash seeds and run timestamps, one cached market."""
    cache = tmp_path / "cache"
    generate(random_walk(), cache)
    runs = [
        _start(cache, tmp_path / out, hour, seed)
        for out, hour, seed in (("a", 9, "1"), ("b", 11, "2"))
    ]
    for proc in runs:
        output, _ = proc.communicate(timeout=300)
        assert proc.returncode == 0, output.decode(errors="replace")

    first, second = (result_path(tmp_path / d, "SYN", "baseline_pmcc").read_bytes() for d in "ab")
    assert first != second  # the timestamps differ...
    assert canonical.drop_run_timestamp(first) == canonical.drop_run_timestamp(second)  # ...only


def test_inv_13_the_subprocess_entry_is_the_in_process_run(tmp_path: Path) -> None:
    """INV-13's processes run exactly what `run_loaded` runs here: it compares a real run."""
    cache = tmp_path / "cache"
    generate(random_walk(), cache)
    path = inv13_run.main(cache, tmp_path / "out", 9)
    loaded = load_symbol(cache, "SYN", load_calendar())
    again = run_loaded(loaded, "SYN", inv13_run.config(), CASH, _stamp())

    assert path.read_bytes() == to_bytes(again)
