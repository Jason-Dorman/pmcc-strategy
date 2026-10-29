"""`pmcc verify` and `pmcc export` on the wheel's results (W2-03, W3-01).

Verify passes a wheel result as `pmcc wheel` writes it, and fails a hand-corrupted copy on each
invariant it re-derives from the rows (`wheel_rederive`), on each reported number it re-derives
(Trade P&L, the S&P 500's return, the verdicts, the baseline PMCC's figures) and on each file
check. Each corruption edits one value, keeping the file canonical and valid against its schema,
so only the check it targets can catch it. Export publishes the wheel's results beside the PMCC's,
listed in the index under their symbol (W4-01).

The result is `winv10_run.full_wheel`'s, beside the baseline PMCC run on the same market, which
its benchmarks were loaded from as `pmcc wheel` loads them, so the results directory holds both
kinds, as `results/NVDA/` will.
"""

import shutil
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest

from pmcc.export import canonical
from pmcc.export.canonical import Number
from pmcc.export.models import RunResult
from pmcc.export.results import write_result
from pmcc.export.site import ExportError, export_site
from pmcc.export.site_models import Index
from pmcc.export.verify import kind_of, verify
from pmcc.export.wheel_models import WheelResult
from tests.scenario import winv10_run

WHEEL = "SYN/wheel.json"
PMCC = "SYN/baseline_pmcc.json"

type Doc = dict[str, Any]


@pytest.fixture(scope="module")
def results(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tmp = tmp_path_factory.mktemp("verify_wheel")
    out = tmp / "results"
    winv10_run.generate_market(tmp / "cache")
    sp500 = winv10_run.write_benchmarks(tmp / "cache", out, tmp / "work")
    benchmarks = winv10_run.loaded_benchmarks(out, sp500)
    write_result(winv10_run.result(tmp / "cache", benchmarks=benchmarks), out)
    return out


def _copy(results: Path, tmp: Path) -> Path:
    copied = tmp / "results"
    shutil.copytree(results, copied)
    return copied


def _edit(root: Path, change: Callable[[Doc], None]) -> None:
    path = root / WHEEL
    doc = cast(Doc, canonical.loads(path.read_bytes()))
    change(doc)
    path.write_bytes(canonical.to_bytes(doc))


def _checks(root: Path) -> set[str]:
    return {p.check for p in verify(root).problems}


def _add(value: str, amount: str) -> Number:
    return Number(f"{Decimal(value) + Decimal(amount):.4f}")


def _row(doc: Doc, rule: str, side: str) -> Doc:
    return next(r for r in doc["blotter"] if r["rule_id"] == rule and r["side"] == side)


def _quiet_bar(doc: Doc, leg: str) -> Doc:
    """A ledger bar holding `leg` ("put" or "call") on which nothing was booked."""
    booked = {r["time"] for r in doc["blotter"]}
    return next(b for b in doc["ledger"] if b[leg] is not None and b["time"] not in booked)


# ---- passing ------------------------------------------------------------------------------------


def test_w2_03_verify_passes_wheel_results_as_pmcc_wheel_writes_them(results: Path) -> None:
    verified = verify(results)

    assert verified.problems == ()
    assert (verified.runs, verified.files) == (2, 2)


@pytest.mark.parametrize(
    ("path", "kind"),
    [("SYN/wheel.json", WheelResult), ("SYN/wheel--sc025.json", WheelResult),
     ("SYN/baseline_pmcc.json", RunResult), ("SYN/wheelie.json", RunResult)],
)  # fmt: skip
def test_w2_03_a_wheel_run_is_known_by_its_run_id(path: str, kind: type) -> None:
    assert kind_of(Path(path)) is kind


# ---- each invariant -----------------------------------------------------------------------------


def _put_ric(doc: Doc) -> None:
    _quiet_bar(doc, "put")["put"]["instrument"]["ric"] = "SYNX.U"


def _sale_cash(doc: Doc) -> None:
    row = _row(doc, "W-P1", "SELL")
    row["cash_delta"] = _add(row["cash_delta"], "0.01")


def _nav(doc: Doc) -> None:
    bar = _quiet_bar(doc, "put")
    bar["nav"] = _add(bar["nav"], "0.01")


def _fill_off_mid(doc: Doc) -> None:
    row = _row(doc, "W-C1", "SELL")
    row["audit"]["bid"] = Number(str(int(row["audit"]["bid"]) - 100))


def _false_assignment(doc: Doc) -> None:
    _row(doc, "W-P1", "SELL")["audit"]["assignment"] = True


def _reserved(doc: Doc) -> None:
    bar = _quiet_bar(doc, "put")
    bar["reserved"] = _add(bar["reserved"], "0.01")


def _state(doc: Doc) -> None:
    _quiet_bar(doc, "put")["state"] = "cash"


def _expiry(doc: Doc) -> None:
    bar = _quiet_bar(doc, "call")
    bar["call"]["instrument"]["expiry"] = "2026-09-01"


def _gate_rule(doc: Doc) -> None:
    doc["gate_log"][0]["outcome"]["rule_id"] = "W-T9"


def _trade_pnl(doc: Doc) -> None:
    row = _row(doc, "W-X1", "EXPIRE")
    row["trade_pnl"] = _add(row["trade_pnl"], "0.01")


def _opening_pnl(doc: Doc) -> None:
    _row(doc, "W-P1", "SELL")["trade_pnl"] = Number("1.0000")


def _verdict_flipped(doc: Doc) -> None:
    claim = doc["summary"]["thesis"][1]
    claim["met"] = not claim["met"]


def _verdict_number(doc: Doc) -> None:
    doc["summary"]["thesis"][2]["benchmark"] = Number("-0.5")


def _sp500_return(doc: Doc) -> None:
    doc["summary"]["benchmarks"]["sp500"]["end_close"] = Number("7000.0000")


def _baseline_sharpe(doc: Doc) -> None:
    doc["summary"]["benchmarks"]["baseline_pmcc"]["config_hash"] = "3" * 64


CORRUPTIONS: list[tuple[Callable[[Doc], None], set[str]]] = [
    (_put_ric, {"positions"}), (_sale_cash, {"WINV-01", "trade_pnl"}), (_nav, {"WINV-02"}),
    (_fill_off_mid, {"WINV-03"}),
    (_false_assignment, {"WINV-03"}), (_reserved, {"WINV-05"}), (_state, {"WINV-07"}),
    (_expiry, {"WINV-08"}), (_gate_rule, {"WINV-09"}), (_trade_pnl, {"trade_pnl"}),
    (_opening_pnl, {"trade_pnl"}), (_verdict_flipped, {"thesis"}), (_verdict_number, {"thesis"}),
    (_sp500_return, {"benchmarks"}), (_baseline_sharpe, {"benchmarks"}),
]  # fmt: skip


@pytest.mark.parametrize(("corrupt", "checks"), CORRUPTIONS)
def test_w2_03_verify_fails_a_wheel_result_corrupted_against_one_invariant(
    results: Path, tmp_path: Path, corrupt: Callable[[Doc], None], checks: set[str]
) -> None:
    root = _copy(results, tmp_path)
    _edit(root, corrupt)

    assert _checks(root) == checks


def test_winv_06_an_uncovered_call_is_found(results: Path, tmp_path: Path) -> None:
    """Two contracts on 100 shares: the positions and NAV disagree too, but WINV-06 names it."""
    root = _copy(results, tmp_path)

    def two_calls(doc: Doc) -> None:
        _quiet_bar(doc, "call")["call"]["qty"] = 2

    _edit(root, two_calls)

    assert "WINV-06" in _checks(root)


def test_winv_05_cash_short_of_the_put_is_found(results: Path, tmp_path: Path) -> None:
    """Cash below the put's strike × 100: the cash walk and NAV disagree too, but WINV-05 says the
    put isn't secured."""
    root = _copy(results, tmp_path)

    def spent(doc: Doc) -> None:
        bar = _quiet_bar(doc, "put")
        bar["cash"] = _add(bar["reserved"], "-0.01")

    _edit(root, spent)

    problems = verify(root).problems
    assert any(p.check == "WINV-05" and "doesn't secure" in p.message for p in problems)


# ---- the file checks ----------------------------------------------------------------------------


def _held_false(doc: Doc) -> None:
    doc["summary"]["invariants"][0]["held"] = False


def _pmcc_invariants(doc: Doc) -> None:
    doc["summary"]["invariants"][0]["id"] = "WINV-04"


def _config_hash(doc: Doc) -> None:
    doc["config"]["wheel"]["name"] = "Wheel!"


def _rule_text(doc: Doc) -> None:
    doc["rule_text"]["W-P3"]["summary"] = "Something else."


def _git_dirty(doc: Doc) -> None:
    doc["manifest"]["git_dirty"] = True


def _bad_state(doc: Doc) -> None:
    doc["ledger"][0]["state"] = "margin"


@pytest.mark.parametrize(
    ("corrupt", "check"),
    [(_held_false, "summary"), (_pmcc_invariants, "summary"), (_config_hash, "config_hash"),
     (_rule_text, "rule_text"), (_git_dirty, "git_dirty"), (_bad_state, "schema")],
)  # fmt: skip
def test_w2_03_verify_fails_a_wheel_file_check(
    results: Path, tmp_path: Path, corrupt: Callable[[Doc], None], check: str
) -> None:
    root = _copy(results, tmp_path)
    _edit(root, corrupt)

    assert _checks(root) == {check}


def test_w2_03_verify_refuses_a_wheel_result_under_another_run_id(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)
    (root / WHEEL).rename(root / "SYN" / "wheel--other.json")

    assert [(p.path, p.check) for p in verify(root).problems] == [
        ("SYN/wheel--other.json", "manifest")
    ]


# ---- export -------------------------------------------------------------------------------------


def test_w4_01_export_publishes_the_wheels_results_beside_the_pmccs(
    results: Path, tmp_path: Path
) -> None:
    site = tmp_path / "data"

    exported = export_site(results, site)

    assert (exported.runs, exported.files) == (2, 2)
    assert (site / PMCC).read_bytes() == (results / PMCC).read_bytes()
    assert (site / WHEEL).read_bytes() == (results / WHEEL).read_bytes()
    index = Index.model_validate_json((site / "index.json").read_bytes())
    (symbol,) = index.symbols
    assert [r.run_id for r in symbol.runs] == ["baseline_pmcc"]
    (wheel,) = symbol.wheel
    result = WheelResult.model_validate_json((results / WHEEL).read_bytes())
    assert (wheel.run_id, wheel.path, wheel.name) == ("wheel", WHEEL, result.config.wheel.name)
    assert wheel.spread_capture == result.config.wheel.fill_model.spread_capture
    assert wheel.config_hash == result.manifest.config_hash
    # the wheel's own starting cash, apart from the PMCC runs' shared one (WD-10)
    assert wheel.starting_cash == result.starting_cash
    assert symbol.starting_cash == RunResult.model_validate_json(
        (results / PMCC).read_bytes()).starting_cash  # fmt: skip


def test_w4_01_export_refuses_a_wheel_run_over_another_window(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)
    wheel = WheelResult.model_validate_json((root / WHEEL).read_bytes())
    window = wheel.config.window.model_copy(update={"end": date(2026, 9, 18)})
    config = wheel.config.model_copy(update={"window": window})
    manifest = wheel.manifest.model_copy(update={"config_hash": config.config_hash()})
    write_result(wheel.model_copy(update={"config": config, "manifest": manifest}), root)

    with pytest.raises(ExportError, match="another window or r"):
        export_site(root, tmp_path / "data")


def test_w2_03_export_still_refuses_a_wheel_result_that_fails_verification(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)
    _edit(root, _nav)

    with pytest.raises(ExportError, match="WINV-02"):
        export_site(root, tmp_path / "data")


def test_w3_01_verify_needs_the_baseline_pmcc_beside_a_wheel_result(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)
    (root / PMCC).unlink()

    problems = verify(root).problems

    assert [(p.path, p.check) for p in problems] == [(WHEEL, "benchmarks")]
    assert "isn't beside it" in problems[0].message


def test_w3_01_verify_finds_a_baseline_re_run_since_the_wheel(
    results: Path, tmp_path: Path
) -> None:
    root = _copy(results, tmp_path)
    path = root / PMCC
    doc = cast(Doc, canonical.loads(path.read_bytes()))
    doc["summary"]["metrics"]["sharpe_annualized"] = Number("9.9")
    path.write_bytes(canonical.to_bytes(doc))

    assert (WHEEL, "benchmarks") in {(p.path, p.check) for p in verify(root).problems}
