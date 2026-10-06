"""A strategy's `report` block (PO, DEC-54): how much detail its results keep and which optional
sections its page shows. It is inherited through `extends` and replaced whole by a child."""

import shutil
import textwrap
from pathlib import Path

import pytest

from pmcc.config.strategy import (
    CONFIGS_DIR,
    Detail,
    RunConfig,
    Section,
    load_strategy,
)
from pmcc.config.universe import read_universe_file

ABLATIONS = sorted((CONFIGS_DIR / "ablations").glob("a*.yaml"))


@pytest.fixture
def configs(tmp_path: Path) -> Path:
    shutil.copytree(CONFIGS_DIR, tmp_path, dirs_exist_ok=True)
    return tmp_path


def _variant(configs: Path, body: str = "", parent: str = "baseline_pmcc.yaml") -> Path:
    head = f"id: baseline_pmcc--v\nname: Variant\nextends: {parent}\n"
    path = configs / "variant.yaml"
    path.write_text(head + textwrap.dedent(body), encoding="utf-8", newline="\n")
    return path


def test_dec_120_the_baseline_page_adds_the_greek_attribution_and_position_greeks() -> None:
    report = load_strategy(CONFIGS_DIR / "baseline_pmcc.yaml").report

    assert report.detail is Detail.FULL
    assert report.sections == (Section.GREEK_ATTRIBUTION, Section.POSITION_GREEKS)


def test_dec_54_the_quant_page_adds_the_gate_log_greek_attribution_and_position_greeks() -> None:
    report = load_strategy(CONFIGS_DIR / "quant_pmcc.yaml").report

    assert report.detail is Detail.FULL
    assert report.sections == (
        Section.GATE_LOG, Section.GREEK_ATTRIBUTION, Section.POSITION_GREEKS,
    )  # fmt: skip


@pytest.mark.parametrize("path", ABLATIONS, ids=lambda p: p.stem)
def test_dec_54_an_ablation_keeps_a_summary(path: Path) -> None:
    report = load_strategy(path).report

    assert (report.detail, report.sections) == (Detail.SUMMARY, ())


def test_dec_54_report_is_never_inherited(configs: Path) -> None:
    """A variant keeps a summary unless its own file says otherwise, so a sensitivity variant of
    a full strategy can't publish full detail by accident."""
    for parent in ("baseline_pmcc.yaml", "quant_pmcc.yaml"):
        report = load_strategy(_variant(configs, parent=parent)).report
        assert (report.detail, report.sections) == (Detail.SUMMARY, ())


def test_dec_54_a_variant_can_ask_for_full_detail(configs: Path) -> None:
    block = "report: {detail: full, sections: [gate_log]}\n"
    variant = load_strategy(_variant(configs, block, parent="quant_pmcc.yaml"))

    assert (variant.report.detail, variant.report.sections) == (Detail.FULL, (Section.GATE_LOG,))


def test_dec_54_a_strategy_no_file_reports_on_keeps_a_summary(configs: Path) -> None:
    text = (configs / "baseline_pmcc.yaml").read_text(encoding="utf-8")
    body = text[: text.index("report:")] + text[text.index("rules:") :]
    (configs / "baseline_pmcc.yaml").write_text(body, encoding="utf-8", newline="\n")

    report = load_strategy(configs / "baseline_pmcc.yaml").report

    assert (report.detail, report.sections) == (Detail.SUMMARY, ())


@pytest.mark.parametrize(
    ("block", "message"),
    [("{detail: summary, sections: [gate_log]}", "sections need full detail"),
     ("{detail: full, sections: [gate_log, gate_log]}", "more than once"),
     ("{detail: full, sections: [blotter]}", "sections"),
     ("{detail: everything}", "detail"),
     ("{sections: [gate_log]}", "detail"),
     ("{detail: full, colour: red}", "colour")],
)  # fmt: skip
def test_dec_54_a_bad_report_block_is_refused(configs: Path, block: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        load_strategy(_variant(configs, f"report: {block}\n"))


def test_dec_54_report_is_part_of_the_config_hash(configs: Path) -> None:
    universe = read_universe_file()

    def hashed(path: Path) -> str:
        config = RunConfig(strategy=load_strategy(path), window=universe.window,
                           risk_free_rate=universe.risk_free_rate)  # fmt: skip
        return config.config_hash()

    full = hashed(_variant(configs, "report: {detail: full}\n"))
    summary = hashed(_variant(configs))

    assert full != summary
