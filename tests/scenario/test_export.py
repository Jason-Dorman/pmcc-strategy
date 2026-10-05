"""`pmcc export` (P4-05): the site's data from results, and each run's summary and detail level
(PO, DEC-54).

The results are the baseline, the quant PMCC and ablation A3 on the synthetic `random_walk`, as
`pmcc run` writes them.
"""

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

from pmcc.config.strategy import (
    CONFIGS_DIR,
    Detail,
    RunConfig,
    Section,
    StrategyConfig,
    load_strategy,
)
from pmcc.domain import RuleId
from pmcc.domain.clock import ET
from pmcc.engine.invariants import RUNTIME_INVARIANTS
from pmcc.export import canonical
from pmcc.export.base import SCHEMA_VERSION
from pmcc.export.manifest import GitState, Provenance
from pmcc.export.models import BlotterRow, DataSource, RunResult
from pmcc.export.results import write_result
from pmcc.export.schema import SCHEMAS
from pmcc.export.site import ExportError, check_export_dir, export_site, rule_changes
from pmcc.export.site_models import Index, Rules
from pmcc.runner import Stamp, run_loaded
from tests.fixtures.synthetic.scenarios import BUILDERS, random_walk
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario import inv13_run
from tests.scenario.harness import CASH, NO_TAKE_PROFIT, SEED, config

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
        result = run_loaded(loaded, loaded.symbol, cfg, CASH, stamp, seed=SEED)
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


def test_p6_01_every_run_carries_its_analytics_and_a_full_run_its_cycles(runs: Runs) -> None:
    """A summary run's analytics are what the robustness tables read (DEC-54); a full run also
    keeps its cycles and its leg attribution, and its Greek attribution where its page shows it
    (P6-03, P6-04)."""
    for result in runs[1].values():
        summary = result.summary
        analytics = (summary.metrics, summary.cycle_stats, summary.exit_mix, summary.skips_by_rule)
        assert None not in analytics
        assert summary.nav_close
        assert summary.weekly_returns
        report = result.config.strategy.report
        full = report.detail is Detail.FULL
        assert (result.cycles is not None) == full
        assert (result.attribution is not None) == full
        if result.attribution is not None:
            greek = Section.GREEK_ATTRIBUTION in report.sections
            assert (result.attribution.greek is not None) == greek


def test_p6_03_04_the_attribution_reconciles_with_the_runs_own_rows(runs: Runs) -> None:
    """On the synthetic market: the legs add up to the run's P&L; the long's intrinsic and
    extrinsic parts to its P&L; the series ends at the totals, a point per session; each leg's
    Greek components to its change, which is the leg's own P&L; and the residual line ends at the
    residual rows' total."""
    for run_id in ("baseline_pmcc", "quant_pmcc"):
        result = runs[1][run_id]
        assert result.attribution is not None
        assert result.summary.metrics is not None
        assert result.summary.nav_close is not None
        legs = result.attribution.leg
        short_pnl = legs.net_short_premium - legs.short_open
        assert legs.long_pnl + short_pnl + legs.assignment_stock_pnl == result.summary.metrics.pnl
        assert legs.long_intrinsic + legs.long_extrinsic == legs.long_pnl
        assert legs.net_short_premium == legs.short_credits - legs.short_buybacks
        assert [p.session for p in legs.series] == [p.session for p in result.summary.nav_close]
        assert (legs.series[-1].long_pnl, legs.series[-1].net_short_premium) == (
            legs.long_pnl, legs.net_short_premium)  # fmt: skip
    greek = runs[1]["quant_pmcc"].attribution
    assert greek is not None
    assert greek.greek is not None
    changes = {g.leg: g.change for g in greek.greek.legs}
    assert changes == {"long": greek.leg.long_pnl, "short": short_pnl}
    for leg, change in changes.items():
        dollars = [r.dollars for r in greek.greek.rows if r.leg == leg]
        assert [r.component for r in greek.greek.rows if r.leg == leg] == [
            "delta", "gamma", "theta", "vega", "residual"]  # fmt: skip
        assert sum(dollars) == pytest.approx(float(change), abs=1e-6)
    residual = sum(r.dollars for r in greek.greek.rows if r.component == "residual")
    assert greek.greek.residual[-1].cumulative == pytest.approx(residual, abs=1e-6)
    assert len(greek.greek.residual) == len(runs[1]["quant_pmcc"].ledger or ())


def test_p6_01_the_analytics_reconcile_with_the_runs_own_rows(runs: Runs) -> None:
    """On the synthetic market: the last close is the ledger's last NAV, the cycles' P&L adds up
    to the run's, a week per gate-log row, and the exit mix counts the blotter's exits."""
    for run_id in ("baseline_pmcc", "quant_pmcc"):
        result = runs[1][run_id]
        summary = result.summary
        assert result.ledger
        assert result.gate_log
        assert result.blotter
        assert result.cycles
        assert summary.metrics
        assert summary.nav_close
        assert summary.weekly_returns
        assert summary.exit_mix is not None
        assert summary.cycle_stats is not None
        final = result.ledger[-1].nav
        assert summary.nav_close[-1].nav == summary.weekly_returns[-1].nav == final
        assert summary.metrics.pnl == final - result.starting_cash
        assert sum(c.pnl for c in result.cycles) == summary.metrics.pnl
        assert [c.week_open for c in result.cycles] == [g.session for g in result.gate_log]
        assert [c.outcome for c in result.cycles] == [g.outcome.kind for g in result.gate_log]
        assert sum(summary.exit_mix.values()) == sum(map(_closes_a_leg, result.blotter))
        sold = sum(r.rule_id == "E-S1" for r in result.blotter)
        assert summary.cycle_stats.weeks_traded == sold
        assert summary.metrics.weekly_return is not None
        assert summary.metrics.weekly_return.seed == SEED


def _closes_a_leg(row: BlotterRow) -> bool:
    """An X-L sale of the long, or an X-S buyback, expiry or assignment of the short."""
    if row.instrument.kind != "call":
        return False
    return row.rule_id.startswith("X-L") or (row.rule_id.startswith("X-S") and row.side != "SELL")


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
            assert (rule.title, rule.summary, rule.condition, rule.action, rule.rationale) == (
                written.title, written.summary, written.condition, written.action,
                written.rationale)  # fmt: skip


def test_export_rules_publish_params_as_the_config_holds_them(exported: Path) -> None:
    rules = Rules.model_validate_json((exported / "rules.json").read_bytes())
    quant = next(s for s in rules.strategies if s.id == "quant_pmcc")
    by_id = {r.id: r for r in quant.rules}

    assert by_id["G-3"].params == {"max_ratio": 1.2}
    assert by_id["G-5"].params == {"min_mid": "0.1000"}


def test_p7_03_export_rules_show_each_param_as_the_rules_text_does(exported: Path) -> None:
    rules = Rules.model_validate_json((exported / "rules.json").read_bytes())
    quant = next(s for s in rules.strategies if s.id == "quant_pmcc")
    by_id = {r.id: r for r in quant.rules}

    assert by_id["G-3"].shown == {"max_ratio": "1.20"}
    assert by_id["G-5"].shown == {"min_mid": "$0.10"}
    assert by_id["E-T1"].shown == {"long_max_spread": "3%", "short_max_spread": "10%"}


def _robustness(symbol: str, **tables: list[tuple[str, str]]) -> Doc:
    """A robustness file whose tables hold the given (run ID, reference) rows."""

    def row(run_id: str, reference: str) -> Doc:
        return {"run_id": run_id, "label": run_id, "reference": reference, "pnl": 0,
                "max_drawdown": 0, "payoff_ratio": None, "weekly_return": None,
                "pnl_vs_reference": 0}  # fmt: skip

    doc: Doc = {"schema_version": SCHEMA_VERSION, "symbol": symbol, "timing_dispersion": None}
    for table in ("ablations", "friction", "timing", "grid"):
        doc[table] = [row(*r) for r in tables.get(table, [])]
    return doc


def _with_robustness(runs: Runs, tmp: Path, doc: Doc, symbol: str = "SYN") -> Path:
    results = tmp / "results"
    if not results.exists():
        shutil.copytree(runs[0], results)
    (results / symbol / "robustness.json").write_bytes(canonical.to_bytes(doc))
    return results


def test_p7_03_export_rules_name_each_runs_family_from_the_robustness_tables(
    runs: Runs, tmp_path: Path
) -> None:
    ablations = [("quant_pmcc", "quant_pmcc"), ("quant_pmcc--a3", "quant_pmcc")]
    results = _with_robustness(runs, tmp_path, _robustness("SYN", ablations=ablations))

    export_site(results, tmp_path / "site")

    rules = Rules.model_validate_json((tmp_path / "site" / "rules.json").read_bytes())
    families = {s.id: s.family for s in rules.strategies}
    assert families == {
        "baseline_pmcc": "strategy",
        "quant_pmcc": "strategy",
        "quant_pmcc--a3": "ablation",
    }


def test_p7_03_export_rules_leave_a_variant_no_table_holds_without_a_family(
    exported: Path,
) -> None:
    rules = Rules.model_validate_json((exported / "rules.json").read_bytes())

    families = {s.id: s.family for s in rules.strategies}
    assert families == {
        "baseline_pmcc": "strategy",
        "quant_pmcc": "strategy",
        "quant_pmcc--a3": None,
    }


def test_p7_03_export_refuses_a_run_two_symbols_put_in_different_tables(
    runs: Runs, tmp_path: Path
) -> None:
    results = _moved(runs, tmp_path, "AAA")
    _with_robustness(runs, tmp_path, _robustness("SYN", grid=[("quant_pmcc--a3", "quant_pmcc")]))
    as_ablation = _robustness("AAA", ablations=[("quant_pmcc--a3", "quant_pmcc")])
    _with_robustness(runs, tmp_path, as_ablation, symbol="AAA")

    with pytest.raises(ExportError, match="quant_pmcc--a3"):
        export_site(results, tmp_path / "site")


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
    coverage |= {
        "iv_priced": 0,
        "iv_failures": {},
        "stale_mark_rate": None,
        "unavailable_fields": [],
    }
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

    with pytest.raises(ExportError, match="doesn't write"):
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


# ---- the adversarial review's regressions (P4-05 review, DEC-96) --------------------------------


def _strategy(path: Path) -> StrategyConfig:
    return load_strategy(path)


def _variant(tmp: Path, body: str, parent: str = "quant_pmcc.yaml") -> StrategyConfig:
    shutil.copytree(CONFIGS_DIR, tmp / "configs", dirs_exist_ok=True)
    path = tmp / "configs" / "variant.yaml"
    head = f"id: quant_pmcc--v\nname: Variant\nextends: {parent}\n"
    path.write_text(head + body, encoding="utf-8", newline="\n")
    return load_strategy(path)


def _kinds(base: StrategyConfig, variant: StrategyConfig) -> list[tuple[str, str]]:
    return [(c.rule_id, c.change) for c in rule_changes(base.rules, variant.rules)]


QUANT = CONFIGS_DIR / "quant_pmcc.yaml"


@pytest.mark.parametrize(
    ("ablation", "changes"),
    [("a1", [("E-L2", "replaced"), ("E-L3", "replaced")]), ("a2", [("E-S3", "replaced")]),
     ("a3", [("G-3", "removed")]), ("a4", [("G-4", "removed")]), ("a5", [("X-S1", "removed")])],
)  # fmt: skip
def test_export_rules_classify_each_ablations_change(
    ablation: str, changes: list[tuple[str, str]]
) -> None:
    variant = _strategy(CONFIGS_DIR / "ablations" / f"{ablation}.yaml")

    assert _kinds(_strategy(QUANT), variant) == changes


def test_export_rules_classify_a_params_change(tmp_path: Path) -> None:
    variant = _variant(tmp_path, "overrides:\n  E-S3: {params: {k: 1.25}}\n")

    assert _kinds(_strategy(QUANT), variant) == [("E-S3", "params")]


def test_export_rules_classify_a_text_only_change(tmp_path: Path) -> None:
    quant = _strategy(QUANT)
    rule = quant.rule(RuleId("G-5")).model_dump(mode="json")
    rule["rationale"] = "Another rationale."
    rule.pop("id")
    body = "overrides:\n  G-5:\n    replace: " + json.dumps(rule, ensure_ascii=False) + "\n"

    assert _kinds(quant, _variant(tmp_path, body)) == [("G-5", "text")]


def test_export_rules_classify_an_added_rule(tmp_path: Path) -> None:
    g3 = _strategy(QUANT).rule(RuleId("G-3")).model_dump(mode="json")
    body = "rules:\n  - " + json.dumps(g3, ensure_ascii=False) + "\n"
    variant = _variant(tmp_path, body, parent="baseline_pmcc.yaml")

    assert _kinds(_strategy(CONFIGS_DIR / "baseline_pmcc.yaml"), variant) == [("G-3", "added")]


def test_export_rules_publish_each_strategys_fill_model_name_and_detail(
    runs: Runs, exported: Path
) -> None:
    rules = Rules.model_validate_json((exported / "rules.json").read_bytes())

    for strategy in rules.strategies:
        config = runs[1][strategy.id].config.strategy
        assert (strategy.name, strategy.detail) == (config.name, config.report.detail)
        assert strategy.spread_capture == config.fill_model.spread_capture
        assert strategy.fee_per_contract == config.fill_model.fee_per_contract.to_dollars()
        assert strategy.strategy_id == strategy.id.split("--")[0]


def test_export_index_records_each_runs_config_hash_and_commit(runs: Runs, exported: Path) -> None:
    index = Index.model_validate_json((exported / "index.json").read_bytes())

    for run in index.symbols[0].runs:
        manifest = runs[1][run.run_id].manifest
        assert (run.config_hash, run.git_sha) == (manifest.config_hash, manifest.git_sha)


def _moved(runs: Runs, tmp: Path, symbol: str, **changes: object) -> Path:
    """The results plus quant's run under another symbol, with `changes` to its result."""
    results = tmp / "results"
    shutil.copytree(runs[0], results)
    other = runs[1]["quant_pmcc"]
    manifest = other.manifest.model_copy(update={"symbol": symbol})
    write_result(other.model_copy(update={"manifest": manifest, **changes}), results)
    return results


def _elsewhere(runs: Runs, tmp: Path, config: RunConfig) -> Path:
    """The results plus quant's run under ABC on `config`, its manifest hashing it."""
    other = runs[1]["quant_pmcc"]
    manifest = other.manifest.model_copy(
        update={"symbol": "ABC", "config_hash": config.config_hash()}
    )
    results = tmp / "results"
    shutil.copytree(runs[0], results)
    write_result(other.model_copy(update={"config": config, "manifest": manifest}), results)
    return results


def test_export_refuses_one_run_id_on_two_configs(runs: Runs, tmp_path: Path) -> None:
    config = runs[1]["quant_pmcc"].config
    renamed = config.strategy.model_copy(update={"name": "Renamed"})

    results = _elsewhere(runs, tmp_path, config.model_copy(update={"strategy": renamed}))

    with pytest.raises(ExportError, match="on another config"):
        export_site(results, tmp_path / "site")


def test_export_refuses_runs_over_another_window(runs: Runs, tmp_path: Path) -> None:
    config = runs[1]["quant_pmcc"].config
    window = config.window.model_copy(update={"start": config.window.start - timedelta(days=7)})

    results = _elsewhere(runs, tmp_path, config.model_copy(update={"window": window}))

    with pytest.raises(ExportError, match="another window, r or starting cash"):
        export_site(results, tmp_path / "site")


def test_export_lists_symbols_in_order_and_one_with_only_analytics(
    runs: Runs, tmp_path: Path
) -> None:
    results = _moved(runs, tmp_path, "AAA")
    (results / "QQQ").mkdir()
    coverage: Doc = {"schema_version": SCHEMA_VERSION, "symbol": "QQQ", "rows": []}
    coverage |= {
        "iv_priced": 0,
        "iv_failures": {},
        "stale_mark_rate": None,
        "unavailable_fields": [],
    }
    (results / "QQQ" / "coverage.json").write_bytes(canonical.to_bytes(coverage))

    export_site(results, tmp_path / "site")

    index = Index.model_validate_json((tmp_path / "site" / "index.json").read_bytes())
    assert [s.symbol for s in index.symbols] == ["AAA", "QQQ", "SYN"]
    assert (index.symbols[1].runs, index.symbols[1].files) == (
        (),
        {"coverage": "QQQ/coverage.json"},
    )


def test_export_copies_the_universe_files(runs: Runs, tmp_path: Path) -> None:
    results = tmp_path / "results"
    shutil.copytree(runs[0], results)
    (results / "universe").mkdir()
    pooled: Doc = {
        "schema_version": SCHEMA_VERSION,
        "symbols": [],
        "strategies": [],
        "quant_beat_baseline": [],
    }
    (results / "universe" / "pooled.json").write_bytes(canonical.to_bytes(pooled))

    export_site(results, tmp_path / "site")

    copied = tmp_path / "site" / "universe" / "pooled.json"
    assert copied.read_bytes() == (results / "universe" / "pooled.json").read_bytes()


@pytest.mark.parametrize("marker", ["schema/index.schema.json", "index.json"])
def test_export_never_clears_a_directory_holding_anything_else(
    runs: Runs, tmp_path: Path, marker: str
) -> None:
    """A marker an export writes is not enough: one foreign file and nothing is touched."""
    out = tmp_path / "project"
    (out / Path(marker).parent).mkdir(parents=True, exist_ok=True)
    (out / marker).write_text("{}\n", encoding="utf-8")
    (out / "src").mkdir()
    (out / "src" / "code.py").write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(ExportError, match="doesn't write"):
        export_site(runs[0], out)

    assert (out / "src" / "code.py").read_text(encoding="utf-8") == "x = 1\n"


def test_export_refuses_an_out_that_is_a_file(runs: Runs, tmp_path: Path) -> None:
    (tmp_path / "out").write_text("not a directory\n", encoding="utf-8")

    with pytest.raises(ExportError, match="is a file"):
        export_site(runs[0], tmp_path / "out")


def test_export_the_directory_check_allows_only_what_an_export_writes(tmp_path: Path) -> None:
    for name in ("index.json", "rules.json", "schema/run_result.schema.json",
                 "NVDA/quant_pmcc.json", "NVDA/coverage.json", "universe/pooled.json"):  # fmt: skip
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("{}\n", encoding="utf-8")
    check_export_dir(tmp_path)

    (tmp_path / "schema" / "notes.txt").write_text("x\n", encoding="utf-8")
    with pytest.raises(ExportError, match=r"schema/notes.txt"):
        check_export_dir(tmp_path)


def test_dec_54_the_summary_counts_every_flag_on_a_bar(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    """friday_unquoted_at_check without X-S1 has a bar flagged exit_pending and stale_short."""
    build = BUILDERS["friday_unquoted_at_check"]
    spec = build()
    loaded = synthetic.get("friday_unquoted_at_check", build).symbol
    cfg = config(tmp_path, NO_TAKE_PROFIT, spec.window_start, spec.window_end)
    stamp = Stamp(inv13_run.PROVENANCE, DataSource.SYNTHETIC, WHEN)
    result = run_loaded(loaded, loaded.symbol, cfg, CASH, stamp, seed=SEED)
    assert result.ledger is not None
    assert any(len(bar.flags) == 2 for bar in result.ledger)

    counted: dict[str, int] = {}
    for bar in result.ledger:
        for flag in bar.flags:
            counted[flag] = counted.get(flag, 0) + 1

    assert result.summary.flag_counts == counted
