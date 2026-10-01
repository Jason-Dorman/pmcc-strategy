"""`pmcc verify` (P4-05): it passes results as the pipeline writes them, and fails a hand-corrupted
copy on each invariant it re-derives from a full result's rows (DEC-51), and on each file check.

The results are synthetic runs written by the real writer: `random_walk` under the baseline (full
detail), `late_friday_surge` without X-S1 (X-S5's short stock, so INV-08's stock branch), and
`random_walk` as a summary run (DEC-54). Each corruption edits one value of a copy, keeping it
canonical and valid against the schema, so only the check it targets can catch it.
"""

import json
import shutil
from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from pmcc.config.strategy import Detail, Report, RunConfig
from pmcc.domain.clock import ET
from pmcc.engine.invariants import RUNTIME_INVARIANTS
from pmcc.export import canonical
from pmcc.export.base import SCHEMA_VERSION
from pmcc.export.canonical import Number
from pmcc.export.models import DataSource
from pmcc.export.results import write_result
from pmcc.export.verify import verify
from pmcc.runner import Stamp, run_loaded
from tests.fixtures.synthetic.scenarios import BUILDERS, random_walk
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario import inv13_run
from tests.scenario.harness import CASH, NO_TAKE_PROFIT, config

WALK = "SYN/baseline_pmcc.json"
SURGE = "SYN/baseline_pmcc--test.json"
SUMMARY = "SYN/baseline_pmcc--sum.json"
WHEN = datetime(2026, 9, 30, 9, tzinfo=ET)

type Doc = dict[str, Any]


def _summary(cfg: RunConfig) -> RunConfig:
    strategy = cfg.strategy.model_copy(
        update={"id": "baseline_pmcc--sum", "report": Report(detail=Detail.SUMMARY)}
    )
    return cfg.model_copy(update={"strategy": strategy})


@pytest.fixture(scope="module")
def results(synthetic: SyntheticMarkets, tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp = tmp_path_factory.mktemp("verify")
    out = tmp / "results"
    stamp = Stamp(inv13_run.PROVENANCE, DataSource.SYNTHETIC, WHEN)
    walk, surge = random_walk(), BUILDERS["late_friday_surge"]()
    base = config(tmp / "walk", "", walk.window_start, walk.window_end)
    no_tp = config(tmp / "surge", NO_TAKE_PROFIT, surge.window_start, surge.window_end)
    for name, build, cfg in (("random_walk", random_walk, base),
                             ("late_friday_surge", BUILDERS["late_friday_surge"], no_tp),
                             ("random_walk", random_walk, _summary(base))):  # fmt: skip
        loaded = synthetic.get(name, build).symbol
        write_result(run_loaded(loaded, loaded.symbol, cfg, CASH, stamp), out)
    return out


def _copy(results: Path, tmp: Path) -> Path:
    copied = tmp / "results"
    shutil.copytree(results, copied)
    return copied


def _edit(root: Path, name: str, change: Callable[[Doc], None]) -> None:
    path = root / name
    doc = cast(Doc, canonical.loads(path.read_bytes()))
    change(doc)
    path.write_bytes(canonical.to_bytes(doc))


def _checks(root: Path) -> set[str]:
    return {p.check for p in verify(root).problems}


def _add(value: str, amount: str) -> Number:
    """A canonical dollar number moved by `amount`."""
    return Number(f"{Decimal(value) + Decimal(amount):.4f}")


# ---- where to corrupt ---------------------------------------------------------------------------


def _entry(doc: Doc, rule: str) -> Doc:
    return next(r for r in doc["blotter"] if r["rule_id"] == rule)


def _entry_times(doc: Doc) -> set[str]:
    return {r["time"] for r in doc["blotter"]}


def _quiet_short_bar(doc: Doc) -> Doc:
    """A ledger bar holding a short on which nothing was booked."""
    booked = _entry_times(doc)
    return next(b for b in doc["ledger"] if b["short"] is not None and b["time"] not in booked)


# ---- passing ------------------------------------------------------------------------------------


def test_verify_passes_results_as_the_pipeline_writes_them(results: Path) -> None:
    verified = verify(results)

    assert verified.problems == ()
    assert (verified.runs, verified.files) == (3, 3)


def test_verify_the_results_reach_what_the_checks_read(results: Path) -> None:
    """The corruption tests would pass vacuously without these."""
    walk = cast(Doc, canonical.loads((results / WALK).read_bytes()))
    surge = cast(Doc, canonical.loads((results / SURGE).read_bytes()))
    summary = cast(Doc, canonical.loads((results / SUMMARY).read_bytes()))

    assert {"E-L1", "E-S1"} <= {r["rule_id"] for r in walk["blotter"]}
    assert _quiet_short_bar(walk)
    assert any(b["stock"] is not None for b in surge["ledger"])
    assert summary["blotter"] is None
    assert summary["ledger"] is None
    assert [c["id"] for c in summary["summary"]["invariants"]] == list(RUNTIME_INVARIANTS)


def test_verify_accepts_the_analytics_files_where_they_belong(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)
    (root / "universe").mkdir()
    pooled: Doc = {"schema_version": SCHEMA_VERSION, "strategies": [], "quant_beat_baseline": []}
    (root / "universe" / "pooled.json").write_bytes(canonical.to_bytes(pooled))
    (root / "SYN" / "fill_check.json").write_bytes(
        canonical.to_bytes({"schema_version": SCHEMA_VERSION, "symbol": "SYN", "groups": []})
    )

    verified = verify(root)

    assert verified.problems == ()
    assert (verified.runs, verified.files) == (3, 5)


# ---- one corruption per re-derivable invariant --------------------------------------------------


def _inv_01(doc: Doc) -> None:
    last = doc["ledger"][-1]  # cash and NAV moved together: NAV still reconciles
    last["cash"], last["nav"] = _add(last["cash"], "1"), _add(last["nav"], "1")


def _inv_02(doc: Doc) -> None:
    bar = doc["ledger"][len(doc["ledger"]) // 2]
    bar["nav"] = _add(bar["nav"], "0.0001")


def _inv_03(doc: Doc) -> None:
    audit = _entry(doc, "E-L1")["audit"]
    audit["bid"] = Number(str(int(audit["bid"]) - 100))  # the Limit is no longer its mid


def _inv_05(doc: Doc) -> None:
    bar = _quiet_short_bar(doc)
    bar["long"]["instrument"]["strike"] = _add(bar["short"]["instrument"]["strike"], "1")


def _inv_06(doc: Doc) -> None:
    _entry(doc, "E-S1")["audit"]["e_s5_satisfied"] = False


def _inv_07(doc: Doc) -> None:
    bar = _quiet_short_bar(doc)
    day = date.fromisoformat(bar["time"][:10]) - timedelta(days=1)
    bar["short"]["instrument"]["expiry"] = day.isoformat()


def _inv_08(doc: Doc) -> None:
    _entry(doc, "E-L1")["audit"]["funds_after"] = Number("-1")


def _inv_09(doc: Doc) -> None:
    doc["gate_log"][0]["outcome"]["rule_id"] = "G-4"  # the baseline has no G-4


def _inv_10(doc: Doc) -> None:
    bar = _quiet_short_bar(doc)  # a second short contract, valued into NAV so it reconciles
    bar["short"]["qty"] = Number("2")
    bar["nav"] = _add(bar["nav"], f"-{Decimal(bar['short']['mark']) * 100}")


@pytest.mark.parametrize(
    ("invariant", "corrupt"),
    [("INV-01", _inv_01), ("INV-02", _inv_02), ("INV-03", _inv_03), ("INV-05", _inv_05),
     ("INV-06", _inv_06), ("INV-07", _inv_07), ("INV-08", _inv_08), ("INV-09", _inv_09),
     ("INV-10", _inv_10)],
)  # fmt: skip
def test_verify_fails_a_copy_corrupted_against_one_invariant(
    results: Path, tmp_path: Path, invariant: str, corrupt: Callable[[Doc], None]
) -> None:
    root = _copy(results, tmp_path)
    _edit(root, WALK, corrupt)

    problems = verify(root).problems

    # A leg resized in the ledger alone is also one no row booked.
    also: set[str] = {"positions"} if invariant == "INV-10" else set()
    assert {p.check for p in problems} == {invariant} | also
    assert {p.path for p in problems} == {WALK}


def test_verify_the_corruptions_cover_every_invariant_it_rederives() -> None:
    covered = {"INV-01", "INV-02", "INV-03", "INV-05", "INV-06", "INV-07", "INV-08", "INV-09",
               "INV-10"}  # fmt: skip
    assert covered == set(RUNTIME_INVARIANTS)


def test_inv_01_a_rows_cash_delta_must_follow_from_its_fill(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)

    def corrupt(doc: Doc) -> None:
        row = doc["blotter"][-1]  # the last row: no later entry reads its cash
        row["cash_delta"] = _add(row["cash_delta"], "0.0100")

    _edit(root, WALK, corrupt)

    messages = [p.message for p in verify(root).problems]
    assert any("doesn't follow from its fill" in m for m in messages)
    assert _checks(root) == {"INV-01"}


def test_inv_08_funds_after_must_follow_from_cash_and_the_short(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)

    def corrupt(doc: Doc) -> None:
        audit = _entry(doc, "E-S1")["audit"]
        audit["funds_after"] = Number(str(int(audit["funds_after"]) + 1))  # still ≥ 0

    _edit(root, WALK, corrupt)

    assert _checks(root) == {"INV-08"}


def test_verify_counts_the_rest_of_a_widespread_finding(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)

    def corrupt(doc: Doc) -> None:
        for bar in doc["ledger"]:
            bar["nav"] = _add(bar["nav"], "0.0001")

    _edit(root, WALK, corrupt)

    bars = len(cast(Doc, canonical.loads((root / WALK).read_bytes()))["ledger"])
    messages = [p.message for p in verify(root).problems]
    assert len(messages) == 4
    assert messages[-1] == f"and {bars - 3} more"


# ---- the file checks ----------------------------------------------------------------------------


def _git_dirty(doc: Doc) -> None:
    doc["manifest"]["git_dirty"] = True


def _config_hash(doc: Doc) -> None:
    doc["manifest"]["config_hash"] = "0" * 64


def _rule_text(doc: Doc) -> None:
    doc["rule_text"]["G-2"]["rationale"] = "A rationale nobody rendered."


def _held_false(doc: Doc) -> None:
    doc["summary"]["invariants"][0]["held"] = False


def _one_missing(doc: Doc) -> None:
    doc["summary"]["invariants"].pop()


def _missing_summary(doc: Doc) -> None:
    del doc["summary"]


def _summary_with_rows(doc: Doc) -> None:
    doc["blotter"] = []


@pytest.mark.parametrize(
    ("name", "corrupt", "check"),
    [(WALK, _git_dirty, "git_dirty"), (WALK, _config_hash, "config_hash"),
     (WALK, _rule_text, "rule_text"), (WALK, _held_false, "summary"),
     (SUMMARY, _held_false, "summary"), (SUMMARY, _one_missing, "summary"),
     (WALK, _missing_summary, "schema"), (SUMMARY, _summary_with_rows, "schema")],
)  # fmt: skip
def test_verify_fails_a_file_check(results: Path, tmp_path: Path, name: str,
                                   corrupt: Callable[[Doc], None], check: str) -> None:  # fmt: skip
    root = _copy(results, tmp_path)
    _edit(root, name, corrupt)

    assert _checks(root) == {check}


def test_dec_50_verify_refuses_a_file_not_written_canonically(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)
    path = root / WALK
    path.write_bytes(path.read_bytes().replace(b"{", b"{ ", 1))  # same data, a space more

    assert _checks(root) == {"canonical"}


def test_verify_refuses_a_run_filed_under_another_symbol(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)
    (root / "ABC").mkdir()
    (root / WALK).rename(root / "ABC" / "baseline_pmcc.json")

    problems = verify(root).problems

    assert [(p.path, p.check) for p in problems] == [("ABC/baseline_pmcc.json", "manifest")]


@pytest.mark.parametrize(
    "stray",
    ["index.json", "notes.txt", "SYN/notes.txt", "SYN/deeper/baseline_pmcc.json",
     "sym-1/baseline_pmcc.json", "universe/other.json", "SYN/Baseline.json"],
)  # fmt: skip
def test_verify_refuses_a_file_the_pipeline_doesnt_write(
    results: Path, tmp_path: Path, stray: str
) -> None:
    root = _copy(results, tmp_path)
    (root / stray).parent.mkdir(parents=True, exist_ok=True)
    (root / stray).write_text("{}\n", encoding="utf-8")

    problems = verify(root).problems

    assert [(p.path, p.check) for p in problems] == [(stray, "layout")]


def test_verify_refuses_an_analytics_file_off_its_schema(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)
    (root / "SYN" / "coverage.json").write_text('{"symbol":"SYN"}\n', encoding="utf-8")

    problems = verify(root).problems

    assert [(p.path, p.check) for p in problems] == [("SYN/coverage.json", "schema")]


def test_verify_refuses_another_schema_version(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)
    _edit(root, WALK, lambda doc: doc.update(schema_version=Number(str(SCHEMA_VERSION - 1))))

    problems = verify(root).problems

    assert {p.check for p in problems} == {"schema"}
    assert "schema_version" in problems[0].message


def test_verify_needs_a_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="isn't a directory"):
        verify(tmp_path / "missing")


# ---- the adversarial review's regressions (P4-05 review, DEC-96) --------------------------------


def _row(doc: Doc, rule: str, side: str, kind: str = "call", nth: int = 0) -> Doc:
    wanted = (rule, side, kind)
    matching = [r for r in doc["blotter"]
                if (r["rule_id"], r["side"], r["instrument"]["kind"]) == wanted]  # fmt: skip
    return matching[nth]


def test_inv_08_is_rederived_on_the_bar_x_s5s_stock_is_covered(
    results: Path, tmp_path: Path
) -> None:
    """The cover buys the stock back before E-S1 sells, so no stock is held at the entry and its
    funds must follow from cash and the short, exactly."""
    doc = cast(Doc, canonical.loads((results / SURGE).read_bytes()))
    cover = _row(doc, "X-S5", "BUY", "stock")
    assert _row(doc, "E-S1", "SELL", nth=1)["time"] == cover["time"]
    root = _copy(results, tmp_path)

    def corrupt(doc: Doc) -> None:
        audit = _row(doc, "E-S1", "SELL", nth=1)["audit"]
        audit["funds_after"] = Number(str(int(audit["funds_after"]) + 5_000_000))  # still >= 0

    _edit(root, SURGE, corrupt)

    assert _checks(root) == {"INV-08"}


@pytest.mark.parametrize(
    ("change", "value"), [("e_s5_net_debit", "0.0100"), ("e_s5_strike_gap", "999.0000")]
)
def test_inv_06_compares_the_recorded_terms_with_the_rows(
    results: Path, tmp_path: Path, change: str, value: str
) -> None:
    root = _copy(results, tmp_path)
    _edit(root, WALK, lambda doc: _entry(doc, "E-S1")["audit"].update({change: value}))

    assert _checks(root) == {"INV-06"}


def test_inv_06_rederives_the_gap_from_the_strikes(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)

    def corrupt(doc: Doc) -> None:  # the short's strike down to the long's: no gap at all
        long = _entry(doc, "E-L1")["instrument"]["strike"]
        _entry(doc, "E-S1")["instrument"]["strike"] = long

    _edit(root, WALK, corrupt)

    assert _checks(root) == {"INV-06"}


def test_inv_06_08_a_short_opened_under_another_rule_is_caught(
    results: Path, tmp_path: Path
) -> None:
    """A row is judged by what it does: a sale opening the short is an entry, whatever its label."""
    root = _copy(results, tmp_path)
    _edit(root, WALK, lambda doc: _entry(doc, "E-S1").update(rule_id="E-S3"))

    assert _checks(root) == {"INV-06", "INV-08"}


def test_inv_08_a_long_opened_under_another_rule_is_caught(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)
    _edit(root, WALK, lambda doc: _entry(doc, "E-L1").update(rule_id="E-L3"))

    assert _checks(root) == {"INV-08"}


def test_inv_03_only_x_s5s_stock_sale_is_exempt(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)
    _edit(root, WALK, lambda doc: _entry(doc, "E-S1")["audit"].update(assignment=True))

    problems = verify(root).problems

    assert {p.check for p in problems} == {"INV-03"}
    assert "claims the assignment exemption" in problems[0].message


def test_inv_03_x_s5s_stock_sale_must_be_at_the_assigned_strike(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)
    sale = Number("101.0000")
    _edit(root, SURGE, lambda doc: _row(doc, "X-S5", "SELL", "stock").update(fill=sale))

    problems = [p for p in verify(root).problems if p.check == "INV-03"]

    assert len(problems) == 1
    assert "the assigned strike" in problems[0].message


def test_verify_the_ledger_must_hold_what_the_rows_booked(results: Path, tmp_path: Path) -> None:
    """ASSIGN moves no cash, so only the position walk sees it go missing."""
    root = _copy(results, tmp_path)
    _edit(root, SURGE, lambda doc: doc["blotter"].remove(_row(doc, "X-S5", "ASSIGN")))

    assert "positions" in _checks(root)


def test_verify_reports_a_row_missing_a_value_instead_of_crashing(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)
    _edit(root, WALK, lambda doc: _quiet_short_bar(doc)["short"]["instrument"].update(strike=None))

    assert "rows" in _checks(root)


def test_inv_05_the_long_must_expire_no_earlier_than_the_short(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)

    def corrupt(doc: Doc) -> None:
        bar = _quiet_short_bar(doc)
        short = date.fromisoformat(bar["short"]["instrument"]["expiry"])
        bar["long"]["instrument"]["expiry"] = (short - timedelta(days=1)).isoformat()

    _edit(root, WALK, corrupt)

    assert _checks(root) == {"INV-05"}


def test_inv_09_a_gate_row_carries_a_defined_rule(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)
    _edit(root, WALK, lambda doc: doc["gate_log"][0]["gates"][0].update(rule_id="G-4"))

    assert _checks(root) == {"INV-09"}


def test_inv_01_rows_booked_off_the_ledgers_bars_are_caught(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)
    _edit(root, WALK, lambda doc: doc["blotter"][-1].update(time="2026-09-12T03:00:00-04:00"))

    problems = [p.message for p in verify(root).problems if p.check == "INV-01"]

    assert any("have no ledger bar" in m for m in problems)


def test_verify_a_summary_must_not_record_an_invariant_twice(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)

    def corrupt(doc: Doc) -> None:
        checks = doc["summary"]["invariants"]
        checks.append(dict(checks[0]))

    _edit(root, SUMMARY, corrupt)

    assert _checks(root) == {"summary"}


def _coverage(symbol: str) -> Doc:
    return {"schema_version": SCHEMA_VERSION, "symbol": symbol, "rows": [], "iv_failures": {},
            "stale_mark_rate": None, "unavailable_fields": []}  # fmt: skip


def test_verify_an_analytics_file_must_sit_under_its_own_symbol(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)
    (root / "SYN" / "coverage.json").write_bytes(canonical.to_bytes(_coverage("ABC")))

    found = [(p.path, p.check) for p in verify(root).problems]

    assert found == [("SYN/coverage.json", "manifest")]


def test_verify_an_analytics_file_must_be_canonical(results: Path, tmp_path: Path) -> None:
    root = _copy(results, tmp_path)
    pretty = json.dumps(_coverage("SYN"), indent=2) + "\n"
    (root / "SYN" / "coverage.json").write_text(pretty, encoding="utf-8", newline="\n")

    found = [(p.path, p.check) for p in verify(root).problems]

    assert found == [("SYN/coverage.json", "canonical")]


# ---- fills with friction: spread_capture 0.5 and a fee ------------------------------------------

FRICTION = "SYN/baseline_pmcc--test.json"


@pytest.fixture(scope="module")
def friction(synthetic: SyntheticMarkets, tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp = tmp_path_factory.mktemp("friction")
    spec = random_walk()
    cfg = config(tmp, "", spec.window_start, spec.window_end,
                 "{spread_capture: 0.5, fee_per_contract: 0.65}")  # fmt: skip
    loaded = synthetic.get("random_walk", random_walk).symbol
    stamp = Stamp(inv13_run.PROVENANCE, DataSource.SYNTHETIC, WHEN)
    write_result(run_loaded(loaded, loaded.symbol, cfg, CASH, stamp), tmp / "results")
    return tmp / "results"


def test_inv_03_passes_fills_at_mid_plus_capture_times_half_spread(friction: Path) -> None:
    doc = cast(Doc, canonical.loads((friction / FRICTION).read_bytes()))
    traded = [r for r in doc["blotter"] if r["side"] in ("BUY", "SELL")]
    assert any(r["limit"] != r["fill"] for r in traded)

    assert verify(friction).problems == ()


def _limit_up(doc: Doc) -> None:  # the long's: E-S1's Limit also feeds INV-06 and INV-08
    row = _entry(doc, "E-L1")
    row["limit"] = _add(row["limit"], "0.0001")


def _other_capture(doc: Doc) -> None:
    _entry(doc, "E-S1")["audit"]["spread_capture"] = 0.25


@pytest.mark.parametrize("corrupt", [_limit_up, _other_capture], ids=["limit-only", "capture"])
def test_inv_03_with_friction_the_limit_and_capture_are_checked(
    friction: Path, tmp_path: Path, corrupt: Callable[[Doc], None]
) -> None:
    root = _copy(friction, tmp_path)
    _edit(root, FRICTION, corrupt)

    assert _checks(root) == {"INV-03"}


def test_inv_03_with_friction_a_fill_off_the_model_is_caught(
    friction: Path, tmp_path: Path
) -> None:
    root = _copy(friction, tmp_path)

    def corrupt(doc: Doc) -> None:
        row = _entry(doc, "E-S1")
        row["fill"] = _add(row["fill"], "0.0001")

    _edit(root, FRICTION, corrupt)

    assert "INV-03" in _checks(root)
