"""`pmcc export` (P4-05): the site's data from results, and each run's summary and detail level
(PO, DEC-54).

The results are the baseline, the quant PMCC and ablation A3 on the synthetic `random_walk`, as
`pmcc run` writes them.
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest

from pmcc.config.strategy import Detail, Section
from pmcc.domain.clock import ET
from pmcc.engine.invariants import RUNTIME_INVARIANTS
from pmcc.export import canonical
from pmcc.export.base import SCHEMA_VERSION
from pmcc.export.manifest import GitState, Provenance
from pmcc.export.models import DataSource, RunResult
from pmcc.export.results import write_result
from pmcc.export.schema import SCHEMAS
from pmcc.export.site import ExportError, export_site
from pmcc.export.site_models import Index, Rules
from pmcc.runner import Stamp, run_loaded
from tests.fixtures.synthetic.scenarios import random_walk
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario import inv13_run
from tests.scenario.harness import CASH, config

WHEN = datetime(2026, 9, 30, 9, tzinfo=ET)
RUNS = ("baseline_pmcc", "quant_pmcc", "ablations/a3")

type Doc = dict[str, Any]
type Runs = tuple[Path, dict[str, RunResult]]


def _write(synthetic: SyntheticMarkets, tmp: Path, out: Path, provenance: Provenance,
           strategies: tuple[str, ...] = RUNS) -> dict[str, RunResult]:  # fmt: skip
    spec = random_walk()
    loaded = synthetic.get("random_walk", random_walk).symbol
    stamp = Stamp(provenance, DataSource.SYNTHETIC, WHEN)
    written: dict[str, RunResult] = {}
    for strategy in strategies:
        cfg = config(tmp, "", spec.window_start, spec.window_end, strategy=strategy)
        result = run_loaded(loaded, loaded.symbol, cfg, CASH, stamp)
        write_result(result, out)
        written[result.manifest.run_id] = result
    return written


@pytest.fixture(scope="module")
def runs(synthetic: SyntheticMarkets, tmp_path_factory: pytest.TempPathFactory) -> Runs:
    tmp = tmp_path_factory.mktemp("export")
    out = tmp / "results"
    return out, _write(synthetic, tmp, out, inv13_run.PROVENANCE)


@pytest.fixture(scope="module")
def exported(runs: Runs,
             tmp_path_factory: pytest.TempPathFactory) -> Path:  # fmt: skip
    site = tmp_path_factory.mktemp("site") / "data"
    export_site(runs[0], site)
    return site


# ---- each run's detail and summary (DEC-54) -----------------------------------------------------


def test_dec_54_a_strategy_keeps_its_rows_and_an_ablation_only_its_summary(
    runs: Runs,
) -> None:
    written = runs[1]
    for run_id in ("baseline_pmcc", "quant_pmcc"):
        result = written[run_id]
        assert result.blotter
        assert result.ledger
        assert result.gate_log
    ablation = written["quant_pmcc--a3"]
    assert (ablation.blotter, ablation.ledger, ablation.gate_log) == (None, None, None)
    assert (ablation.cycles, ablation.attribution) == (None, None)


def test_dec_54_every_summary_records_the_invariants_the_run_held(
    runs: Runs,
) -> None:
    for result in runs[1].values():
        checks = result.summary.invariants
        assert [c.id for c in checks] == list(RUNTIME_INVARIANTS)
        assert all(c.held for c in checks)


def test_dec_54_the_summary_counts_the_ledgers_flags(
    runs: Runs,
) -> None:
    result = runs[1]["baseline_pmcc"]
    assert result.ledger is not None
    counted: dict[str, int] = {}
    for bar in result.ledger:
        for flag in bar.flags:
            counted[flag] = counted.get(flag, 0) + 1

    assert result.summary.flag_counts == counted


def test_dec_54_the_analytics_wait_for_p6(runs: Runs) -> None:
    for result in runs[1].values():
        summary = result.summary
        assert (summary.metrics, summary.cycle_stats, summary.exit_mix) == (None, None, None)
        assert (summary.skips_by_rule, summary.nav_close, summary.weekly_returns) == (None,) * 3


def test_dec_54_a_summary_file_is_a_fraction_of_a_full_one(
    runs: Runs,
) -> None:
    out = runs[0]
    full = (out / "SYN" / "quant_pmcc.json").stat().st_size
    summary = (out / "SYN" / "quant_pmcc--a3.json").stat().st_size

    assert summary * 3 < full  # four weeks here; over NVDA's 26 the ratio is about 1:20


# ---- the export directory -----------------------------------------------------------------------


def test_export_copies_every_results_file_byte_for_byte(runs: Runs, exported: Path) -> None:
    for path in sorted(runs[0].glob("*/*.json")):
        assert (exported / path.relative_to(runs[0])).read_bytes() == path.read_bytes()


def test_export_writes_a_schema_per_model(exported: Path) -> None:
    written = sorted(p.name for p in (exported / "schema").iterdir())

    assert written == sorted(f"{name}.schema.json" for name in SCHEMAS)


def test_export_writes_index_and_rules_as_canonical_json(exported: Path) -> None:
    for name in ("index.json", "rules.json"):
        raw = (exported / name).read_bytes()
        assert canonical.to_bytes(canonical.loads(raw)) == raw


def test_export_index_lists_every_run_with_its_detail_and_sections(exported: Path) -> None:
    index = Index.model_validate_json((exported / "index.json").read_bytes())

    assert index.schema_version == SCHEMA_VERSION
    assert [s.symbol for s in index.symbols] == ["SYN"]
    runs = {r.run_id: r for r in index.symbols[0].runs}
    assert list(runs) == ["baseline_pmcc", "quant_pmcc", "quant_pmcc--a3"]
    assert (runs["baseline_pmcc"].detail, runs["baseline_pmcc"].sections) == (Detail.FULL, ())
    assert runs["quant_pmcc"].sections == (Section.GATE_LOG, Section.GREEK_ATTRIBUTION)
    assert (runs["quant_pmcc--a3"].detail, runs["quant_pmcc--a3"].strategy_id) == (
        Detail.SUMMARY, "quant_pmcc")  # fmt: skip
    assert runs["quant_pmcc"].path == "SYN/quant_pmcc.json"
    assert all(r.data_source is DataSource.SYNTHETIC for r in runs.values())


def test_export_index_states_the_window_r_and_starting_cash(runs: Runs, exported: Path) -> None:
    index = Index.model_validate_json((exported / "index.json").read_bytes())
    any_run = runs[1]["baseline_pmcc"]

    assert index.window == any_run.config.window
    assert index.risk_free_rate == any_run.config.risk_free_rate
    assert index.starting_cash == any_run.starting_cash
    assert (index.symbols[0].files, index.universe) == ({}, {})


def test_export_rules_render_each_run_ids_config(runs: Runs, exported: Path) -> None:
    rules = Rules.model_validate_json((exported / "rules.json").read_bytes())

    assert [s.id for s in rules.strategies] == ["baseline_pmcc", "quant_pmcc", "quant_pmcc--a3"]
    for strategy in rules.strategies:
        result = runs[1][strategy.id]
        assert [r.id for r in strategy.rules] == list(result.rule_text)
        for rule in strategy.rules:
            written = result.rule_text[rule.id]
            assert (rule.condition, rule.action, rule.rationale) == (
                written.condition, written.action, written.rationale)  # fmt: skip


def test_export_rules_publish_params_as_the_config_holds_them(exported: Path) -> None:
    rules = Rules.model_validate_json((exported / "rules.json").read_bytes())
    quant = next(s for s in rules.strategies if s.id == "quant_pmcc")
    by_id = {r.id: r for r in quant.rules}

    assert by_id["G-3"].params == {"max_ratio": 1.2}
    assert by_id["G-5"].params == {"min_mid": "0.1000"}


def test_export_rules_list_a_variants_changes_against_its_strategy(exported: Path) -> None:
    rules = Rules.model_validate_json((exported / "rules.json").read_bytes())
    by_id = {s.id: s for s in rules.strategies}

    assert [(c.rule_id, c.change) for c in by_id["quant_pmcc--a3"].changes] == [("G-3", "removed")]
    assert by_id["quant_pmcc"].changes == ()
    assert by_id["baseline_pmcc"].changes == ()


def test_export_includes_the_analytics_files_once_written(runs: Runs, tmp_path: Path) -> None:
    results = tmp_path / "results"
    shutil.copytree(runs[0], results)
    (results / "universe").mkdir()
    headline: Doc = {"schema_version": SCHEMA_VERSION, "rows": []}
    (results / "universe" / "headline.json").write_bytes(canonical.to_bytes(headline))
    coverage: Doc = {"schema_version": SCHEMA_VERSION, "symbol": "SYN", "rows": []}
    coverage |= {"iv_failures": {}, "stale_mark_rate": None, "unavailable_fields": []}
    (results / "SYN" / "coverage.json").write_bytes(canonical.to_bytes(coverage))

    export_site(results, tmp_path / "site")

    index = Index.model_validate_json((tmp_path / "site" / "index.json").read_bytes())
    assert index.universe == {"headline": "universe/headline.json"}
    assert index.symbols[0].files == {"coverage": "SYN/coverage.json"}
    assert (tmp_path / "site" / "SYN" / "coverage.json").is_file()


def test_export_replaces_an_earlier_export_whole(runs: Runs, tmp_path: Path) -> None:
    site = tmp_path / "site"
    export_site(runs[0], site)
    (site / "OLD").mkdir()
    (site / "OLD" / "baseline_pmcc.json").write_text("{}\n", encoding="utf-8")

    export_site(runs[0], site)

    assert not (site / "OLD").exists()


def test_export_refuses_to_clear_a_directory_it_didnt_write(runs: Runs, tmp_path: Path) -> None:
    (tmp_path / "mine.txt").write_text("keep me\n", encoding="utf-8")

    with pytest.raises(ExportError, match="didn't write"):
        export_site(runs[0], tmp_path)

    assert (tmp_path / "mine.txt").is_file()


# ---- what export refuses ------------------------------------------------------------------------


def test_export_refuses_results_that_fail_verification_and_writes_nothing(
    runs: Runs, tmp_path: Path
) -> None:
    results = tmp_path / "results"
    shutil.copytree(runs[0], results)
    path = results / "SYN" / "baseline_pmcc.json"
    doc = cast(Doc, canonical.loads(path.read_bytes()))
    doc["ledger"][0]["nav"] = canonical.Number("1.0000")
    path.write_bytes(canonical.to_bytes(doc))

    with pytest.raises(ExportError, match="INV-02"):
        export_site(results, tmp_path / "site")

    assert not (tmp_path / "site").exists()


def test_export_allows_a_dirty_tree_and_names_its_runs_unpublishable(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    dirty = Provenance(GitState("0" * 40, dirty=True), "1" * 64, "0.0.0")
    _write(synthetic, tmp_path, tmp_path / "results", dirty, ("baseline_pmcc",))

    done = export_site(tmp_path / "results", tmp_path / "site")

    assert done.unpublishable == ("SYN/baseline_pmcc.json",)
    assert (done.runs, done.symbols, done.files) == (1, 1, 1)


def test_export_refuses_a_variant_without_its_strategy(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    _write(synthetic, tmp_path, tmp_path / "results", inv13_run.PROVENANCE, ("ablations/a3",))

    with pytest.raises(ExportError, match="without its strategy quant_pmcc"):
        export_site(tmp_path / "results", tmp_path / "site")


def test_export_refuses_runs_over_different_starting_cash(runs: Runs, tmp_path: Path) -> None:
    results = tmp_path / "results"
    shutil.copytree(runs[0], results)
    (results / "ABC").mkdir()
    # Another symbol's run at another starting cash: rows that still hold every invariant.
    other = runs[1]["quant_pmcc--a3"]
    manifest = other.manifest.model_copy(update={"symbol": "ABC"})
    moved = other.model_copy(update={"manifest": manifest, "starting_cash": CASH.to_dollars() * 2})
    write_result(moved, results)

    with pytest.raises(ExportError, match="another window, r or starting cash"):
        export_site(results, tmp_path / "site")


def test_export_refuses_an_empty_results_directory(tmp_path: Path) -> None:
    (tmp_path / "results").mkdir()

    with pytest.raises(ExportError, match="no runs"):
        export_site(tmp_path / "results", tmp_path / "site")
