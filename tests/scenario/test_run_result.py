"""A run's result file (P3-08): rows that mirror the engine, the manifest, and INV-13.

INV-13: re-running a config on cached data gives byte-identical results once the manifest's
`run_timestamp` and `git_sha` are dropped (PO, DEC-50).
"""

import hashlib
import json
import os
import subprocess
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import numpy as np
import pytest
from pydantic import ValidationError

from pmcc.config.calendar import load_calendar
from pmcc.config.strategy import RunConfig
from pmcc.data.cache import CacheError
from pmcc.data.load import SymbolData, load_symbol
from pmcc.data.ric import occ_symbol, parse_ric
from pmcc.domain.clock import ET
from pmcc.engine.loop import RunOutput
from pmcc.export import canonical
from pmcc.export.manifest import Provenance, provenance
from pmcc.export.models import DataSource, GateOut, RunResult
from pmcc.export.results import result_path, to_bytes, write_result
from pmcc.runner import Market, Stamp, run_loaded, run_market
from tests.fakes.git_repo import make_repo
from tests.fixtures.synthetic.scenarios import BUILDERS, random_walk
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario import inv13_run
from tests.scenario.harness import CASH, NO_TAKE_PROFIT, config, run

REPO_ROOT = Path(__file__).resolve().parents[2]
WHEN = datetime(2026, 9, 30, 9, tzinfo=ET)
PROVENANCE = inv13_run.PROVENANCE
FRICTION = "{spread_capture: 0.5, fee_per_contract: 0.65}"  # limit ≠ fill, and fees


def _stamp(provenance: Provenance = PROVENANCE, when: datetime = WHEN) -> Stamp:
    return Stamp(provenance, DataSource.SYNTHETIC, when)


def _walk(synthetic: SyntheticMarkets) -> SymbolData:
    return synthetic.get("random_walk", random_walk).symbol


def _cfg(tmp: Path, overrides: str = "", fill_model: str = "") -> RunConfig:
    spec = random_walk()
    tmp.mkdir(parents=True, exist_ok=True)
    return config(tmp, overrides, spec.window_start, spec.window_end, fill_model)


def _result(synthetic: SyntheticMarkets, cfg: RunConfig, stamp: Stamp | None = None) -> RunResult:
    loaded = _walk(synthetic)
    return run_loaded(loaded, loaded.symbol, cfg, CASH, stamp or _stamp())


Pair = tuple[RunOutput, RunResult]


def _pair(synthetic: SyntheticMarkets, tmp: Path, name: str, overrides: str = "",
          fill_model: str = "") -> Pair:  # fmt: skip
    """The engine's output and the result, for the same market and config."""
    build = BUILDERS.get(name, random_walk)
    tmp.mkdir(parents=True, exist_ok=True)
    engine = run(synthetic, tmp, name, build, overrides=overrides, fill_model=fill_model)
    loaded = synthetic.get(name, build).symbol
    spec = build()
    cfg = config(tmp, overrides, spec.window_start, spec.window_end, fill_model)
    return engine, run_loaded(loaded, loaded.symbol, cfg, CASH, _stamp())


@pytest.fixture(scope="module")
def walk(synthetic: SyntheticMarkets, tmp_path_factory: pytest.TempPathFactory) -> Pair:
    return _pair(synthetic, tmp_path_factory.mktemp("cfg"), "random_walk")


@pytest.fixture(scope="module")
def result(walk: Pair) -> RunResult:
    return walk[1]


@pytest.fixture(scope="module")
def pairs(synthetic: SyntheticMarkets, tmp_path_factory: pytest.TempPathFactory) -> list[Pair]:
    """Markets that between them reach every row shape: fees and limit ≠ fill, the X-S5 stock
    sale and cover with stock ledger rows, and two-flag ledger rows."""
    tmp = tmp_path_factory.mktemp("pairs")
    return [
        _pair(synthetic, tmp / "walk", "random_walk"),
        _pair(synthetic, tmp / "friction", "random_walk", fill_model=FRICTION),
        _pair(synthetic, tmp / "surge", "late_friday_surge", overrides=NO_TAKE_PROFIT),
        _pair(synthetic, tmp / "unquoted", "friday_unquoted_at_check", overrides=NO_TAKE_PROFIT),
    ]


# ---- the rows mirror the engine's output --------------------------------------------------------


def test_run_result_blotter_mirrors_the_engine(pairs: list[Pair]) -> None:
    for engine, result in pairs:
        assert len(result.blotter) == len(engine.blotter) >= 3
        for row, event in zip(result.blotter, engine.blotter, strict=True):
            assert (row.time, row.side, row.qty, row.rule_id, row.notes) == (
                event.time, event.side.value, event.qty, event.rule_id, event.notes)  # fmt: skip
            assert row.cash_delta == event.cash_delta.to_dollars()
            assert row.fee == event.fee.to_dollars()
            assert row.fill == (None if event.fill is None else event.fill.to_dollars())
            assert row.limit == (None if event.limit is None else event.limit.to_dollars())
            assert row.audit == dict(event.audit)


def test_run_result_rows_reach_every_shape(pairs: list[Pair]) -> None:
    """The mirror tests above and below would pass vacuously without these."""
    rows = [row for _engine, result in pairs for row in result.blotter]
    bars = [bar for _engine, result in pairs for bar in result.ledger]
    assert any(r.limit is not None and r.fill is not None and r.limit != r.fill for r in rows)
    assert any(r.fee > 0 for r in rows)
    assert {r.side for r in rows if r.instrument.kind == "stock"} == {"SELL", "BUY"}
    assert any(b.stock is not None and b.stock.shares < 0 for b in bars)
    assert any(len(b.flags) >= 2 for b in bars)


def test_run_result_ledger_mirrors_the_engine(pairs: list[Pair]) -> None:
    for engine, result in pairs:
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
            assert (row.stock is None) == (bar.stock is None)
            if row.stock is not None and bar.stock is not None:
                assert (row.stock.shares, row.stock.mark, row.stock.stale) == (
                    bar.stock.shares, bar.stock.mark.to_dollars(), bar.stock.stale)  # fmt: skip


def test_run_result_ledger_flags_are_sorted(pairs: list[Pair]) -> None:
    for _engine, result in pairs:
        assert all(list(bar.flags) == sorted(bar.flags) for bar in result.ledger)


def test_run_result_gate_log_mirrors_the_engine(pairs: list[Pair]) -> None:
    for engine, result in pairs:
        assert len(result.gate_log) == len(engine.gate_log) > 0
        for row, week in zip(result.gate_log, engine.gate_log, strict=True):
            assert (row.session, row.decision_time, row.notes) == (
                week.session, week.decision_time, week.notes)  # fmt: skip
            assert (row.outcome.kind, row.outcome.rule_id) == (week.outcome, week.rule_id)
            assert row.selected == (None if week.selected is None else dict(week.selected))
            assert [(g.rule_id, g.status, g.values, g.reason) for g in row.gates] == [
                (g.rule_id, g.status.value, dict(g.values), g.reason)
                for g in week.gates]  # fmt: skip


def test_run_result_names_each_option_by_the_ric_its_cache_answered(
    synthetic: SyntheticMarkets, result: RunResult
) -> None:
    """Exactly the chain frame's RIC, the expired `^` form included, not one rebuilt from the
    contract (DEC-92)."""
    chains = _walk(synthetic).chains
    named = [r.instrument for r in result.blotter if r.instrument.kind == "call"]
    named += [b.long.instrument for b in result.ledger if b.long is not None]

    assert named
    assert any("^" in n.ric for n in named)
    for n in named:
        option = parse_ric(n.ric).option
        frame = chains[(option.expiry, option.right)]
        assert frame.filter(frame["strike_cents"] == option.strike_cents)[
            "ric"
        ].unique().to_list() == [n.ric]
        assert n.occ == occ_symbol(option)
        assert (n.expiry, n.strike) == (option.expiry, option.strike.to_dollars())


def test_run_result_starting_cash_and_rule_text(result: RunResult) -> None:
    assert result.starting_cash == Decimal("10000.0000")
    rules = result.config.strategy.rules
    assert list(result.rule_text) == [r.id for r in rules]
    for rule in rules:
        text = rule.text()
        written = result.rule_text[rule.id]
        assert (written.condition, written.action, written.rationale) == (
            text.condition, text.action, text.rationale)  # fmt: skip


def test_run_result_short_stock_is_named_by_the_tape_ric(pairs: list[Pair]) -> None:
    _engine, surge = pairs[2]
    stock_rows = [r.instrument for r in surge.blotter if r.instrument.kind == "stock"]
    held = [r.stock.instrument for r in surge.ledger if r.stock is not None]

    assert stock_rows
    assert held
    for named in (*stock_rows, *held):
        assert (named.ric, named.occ, named.expiry, named.strike) == ("SYN.O", None, None, None)


@pytest.mark.parametrize(
    "value", [Decimal("1.0000"), np.float64(0.5), np.int64(3), np.bool_(True), date(2026, 1, 2)]
)
def test_run_result_value_maps_refuse_anything_but_json_scalars(value: object) -> None:
    """Strict mode alone reads these as floats (DEC-92)."""
    with pytest.raises(ValidationError, match="isn't a JSON scalar"):
        GateOut(rule_id="G-3", status="fired", values={"x": value}, reason="")


# ---- the manifest -------------------------------------------------------------------------------


def test_run_result_manifest_records_what_produced_the_run(
    synthetic: SyntheticMarkets, result: RunResult
) -> None:
    manifest = result.manifest

    assert (manifest.run_id, manifest.strategy_id, manifest.symbol) == (
        "baseline_pmcc", "baseline_pmcc", "SYN")  # fmt: skip
    assert manifest.config_hash == result.config.config_hash()
    assert manifest.data_manifest_hash == _walk(synthetic).data_manifest_hash
    assert (manifest.git_sha, manifest.git_dirty) == ("0" * 40, False)
    assert (manifest.lock_hash, manifest.pmcc_version) == ("1" * 64, "0.0.0")
    assert (manifest.run_timestamp, manifest.data_source) == (WHEN, DataSource.SYNTHETIC)


def test_run_result_a_variants_strategy_is_its_base(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    manifest = _result(synthetic, _cfg(tmp_path, NO_TAKE_PROFIT)).manifest

    assert (manifest.run_id, manifest.strategy_id) == ("baseline_pmcc--test", "baseline_pmcc")


def _rehash(raw: bytes) -> tuple[str, str]:
    written = cast(dict[str, Any], json.loads(raw))
    config_json = json.dumps(written["config"], sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False)  # fmt: skip
    return hashlib.sha256(config_json.encode()).hexdigest(), written["manifest"]["config_hash"]


def test_run_result_file_config_hashes_to_the_manifests_config_hash(result: RunResult) -> None:
    found, recorded = _rehash(to_bytes(result))

    assert found == recorded


def test_dec_92_a_config_float_past_six_places_is_published_exactly(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    cfg = _cfg(
        tmp_path,
        "E-T1: {params: {short_max_spread: 0.1234567}}\nX-S3: {params: {em_buffer: 0.2500001}}",
    )

    raw = to_bytes(_result(synthetic, cfg))

    found, recorded = _rehash(raw)
    assert found == recorded == cfg.config_hash()
    assert b'"short_max_spread":0.1234567' in raw
    assert b'"em_buffer":0.2500001' in raw


def test_dec_50_a_dirty_tree_records_git_dirty_true(
    synthetic: SyntheticMarkets, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(tmp_path, monkeypatch)
    (repo / "pmcc" / "rules.py").write_text("X = 2\n", encoding="utf-8")

    found = _result(synthetic, _cfg(tmp_path), _stamp(provenance(repo)))
    path = write_result(found, tmp_path / "results")

    manifest = cast(dict[str, Any], json.loads(path.read_bytes()))["manifest"]
    assert manifest["git_dirty"] is True


def test_dec_50_a_clean_tree_records_git_dirty_false(
    synthetic: SyntheticMarkets, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = make_repo(tmp_path, monkeypatch)

    found = _result(synthetic, _cfg(tmp_path), _stamp(provenance(repo)))
    path = write_result(found, tmp_path / "results")

    manifest = cast(dict[str, Any], json.loads(path.read_bytes()))["manifest"]
    assert manifest["git_dirty"] is False


# ---- the market: priced once, and it must cover the window --------------------------------------


def test_dec_92_one_prepared_market_serves_several_runs(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    loaded = _walk(synthetic)
    base, variant = _cfg(tmp_path / "a"), _cfg(tmp_path / "b", NO_TAKE_PROFIT)
    market = Market.prepare(loaded, loaded.symbol, base.risk_free_rate.value)

    for cfg in (base, variant, base):
        alone = run_loaded(loaded, loaded.symbol, cfg, CASH, _stamp())
        assert to_bytes(run_market(market, cfg, CASH, _stamp())) == to_bytes(alone)


def test_dec_92_a_market_priced_at_another_rate_is_refused(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    loaded = _walk(synthetic)
    cfg = _cfg(tmp_path)
    market = Market.prepare(loaded, loaded.symbol, cfg.risk_free_rate.value + 0.01)

    with pytest.raises(ValueError, match="priced at"):
        run_market(market, cfg, CASH, _stamp())


@pytest.mark.parametrize(
    ("start", "end"),
    [(date(2026, 3, 30), date(2026, 9, 25)),  # the universe window: the cache starts in July
     (date(2026, 3, 30), date(2026, 6, 26)),  # no data at all
     (date(2026, 8, 31), date(2026, 10, 2))],  # ends after the cache
)  # fmt: skip
def test_dec_92_a_window_the_cache_doesnt_cover_is_refused(
    synthetic: SyntheticMarkets, tmp_path: Path, start: date, end: date
) -> None:
    loaded = _walk(synthetic)
    cfg = config(tmp_path, "", start, end)

    with pytest.raises(CacheError, match="no stock bars on"):
        run_loaded(loaded, loaded.symbol, cfg, CASH, _stamp())


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
    cfg = _cfg(tmp_path)

    assert to_bytes(_result(synthetic, cfg)) == to_bytes(_result(synthetic, cfg))


def _start(cache: Path, out: Path, hour: int, sha: str, seed: str) -> subprocess.Popen[bytes]:
    module = "tests.scenario.inv13_run"
    command = [sys.executable, "-m", module, str(cache), str(out), str(hour), sha]
    env = {**os.environ, "PYTHONHASHSEED": seed}
    return subprocess.Popen(command, cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)  # fmt: skip


def test_inv_13_two_runs_are_byte_identical_once_the_volatile_values_are_dropped(
    tmp_path: Path,
) -> None:
    """Two fresh processes, one cached market each case: different run times, commits and hash
    seeds. Seeds 2 and 6 put `exit_pending` and `stale_short` in opposite set orders, so an
    unsorted flags tuple would differ here."""
    cache = tmp_path / "cache"
    inv13_run.generate_all(cache)
    runs = [
        _start(cache, tmp_path / out, hour, sha, seed)
        for out, hour, sha, seed in (("a", 9, "a" * 40, "2"), ("b", 11, "b" * 40, "6"))
    ]
    for proc in runs:
        output, _ = proc.communicate(timeout=300)
        assert proc.returncode == 0, output.decode(errors="replace")

    for name in inv13_run.CASES:
        first, second = (next((tmp_path / d / name).rglob("*.json")).read_bytes() for d in "ab")
        assert first != second  # the run time and commit differ...
        assert canonical.drop_volatile(first) == canonical.drop_volatile(second)  # ...only
    two_flags = next((tmp_path / "a" / "friday_unquoted_at_check").rglob("*.json"))
    multi = cast(dict[str, Any], json.loads(two_flags.read_bytes()))
    assert any(len(bar["flags"]) >= 2 for bar in multi["ledger"])


def test_inv_13_the_subprocess_entry_is_the_in_process_run(tmp_path: Path) -> None:
    """INV-13's processes run exactly what `run_loaded` runs here: it compares real runs."""
    cache = tmp_path / "cache"
    inv13_run.generate_all(cache)
    paths = inv13_run.main(cache, tmp_path / "out", 9)

    for path, name in zip(paths, inv13_run.CASES, strict=True):
        loaded = load_symbol(cache / name, "SYN", load_calendar())
        cfg = inv13_run.config(name, tmp_path / "again")
        again = run_loaded(loaded, "SYN", cfg, CASH, _stamp())
        assert path.read_bytes() == to_bytes(again)
