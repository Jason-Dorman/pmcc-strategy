"""The fetch estimate (P1-08): assumed steps from the probe report, strikes, requests, minutes."""

import json
import math
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.data.cache import SymbolCache
from pmcc.data.discovery import Region, UnitKind
from pmcc.data.estimate import (
    RE_ASK_FACTOR,
    REQUESTS_PER_MINUTE,
    STEP_ASKS,
    AssumedSteps,
    NoProbeReportError,
    assumed_steps,
    describe,
    estimate,
    latest_probe_report,
)
from pmcc.data.fetch import Retry
from pmcc.data.pull import Target, prepare, pull_units
from pmcc.domain.clock import ET
from tests.fakes.market import FakeMarket

CAL = load_calendar()
NOW = datetime(2026, 9, 27, 12, tzinfo=ET)
WINDOW = (date(2026, 9, 14), date(2026, 9, 18))
TARGET = Target("NVDA", "NVDA.O", "NVDA")
NO_WAIT = Retry(sleep=lambda _: None)
STEPS = AssumedSteps(
    Path("probes/NVDA_20260927.json"), {Region.NEAR_MONEY: 100, Region.DEEP_ITM: 500}
)


def record(step: int, anchor_answered: bool = True) -> dict[str, Any]:
    return {"step_cents": step, "anchor_answered": anchor_answered}


def write_report(path: Path, increments: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"symbol": "NVDA", "increments": increments}), encoding="utf-8")
    return path


REPORT = {
    "weekly_near_money": record(250),
    "weekly_near_money_expired": record(250),
    "monthly_near_money": record(500),
    "monthly_deep_itm": record(500),
}


# --- Assumed steps ----------------------------------------------------------------------------


def test_estimate_steps_are_the_finest_the_probe_measured_per_region(tmp_path: Path) -> None:
    report = {
        **REPORT,
        "weekly_near_money_expired": record(100),
        "monthly_near_money": record(250),
    }
    path = write_report(tmp_path / "NVDA_20260927.json", report)

    steps = assumed_steps(path)

    assert steps.steps == {Region.NEAR_MONEY: 100, Region.DEEP_ITM: 250}
    assert steps.source == path


def test_estimate_steps_skip_a_record_whose_anchor_did_not_answer(tmp_path: Path) -> None:
    # AMD's near-money monthly (DEC-14): no strike answered, so its $10 measures nothing.
    report = {**REPORT, "monthly_deep_itm": record(1_000), "monthly_near_money": record(50, False)}
    path = write_report(tmp_path / "NVDA_20260927.json", report)

    assert assumed_steps(path).steps[Region.DEEP_ITM] == 1_000


def test_estimate_steps_refuse_a_region_the_probe_did_not_measure(tmp_path: Path) -> None:
    report = {
        **REPORT,
        "weekly_near_money": record(100, False),
        "weekly_near_money_expired": record(100, False),
    }
    path = write_report(tmp_path / "NVDA_20260927.json", report)

    with pytest.raises(NoProbeReportError, match="near_money"):
        assumed_steps(path)


def test_estimate_reads_the_symbols_newest_probe_report(tmp_path: Path) -> None:
    for name in ("NVDA_20260926.json", "NVDA_20260927.json", "NVDAX_20260930.json"):
        write_report(tmp_path / name, REPORT)
    (tmp_path / "NVDA_notes.json").write_text("{}", encoding="utf-8")

    assert latest_probe_report(tmp_path, "NVDA").name == "NVDA_20260927.json"


def test_estimate_needs_a_probe_report(tmp_path: Path) -> None:
    write_report(tmp_path / "QQQ_20260927.json", REPORT)

    with pytest.raises(NoProbeReportError, match="pmcc probe --symbol NVDA"):
        latest_probe_report(tmp_path, "NVDA")


# --- The estimate -----------------------------------------------------------------------------


def _market() -> FakeMarket:
    return FakeMarket(CAL, NOW.date(), hourly_from=date(2026, 3, 1))


def _prepared(cache: SymbolCache) -> Any:
    return prepare(_market(), cache, CAL, TARGET, WINDOW, lambda: NOW, retry=NO_WAIT)


def test_estimate_counts_each_pending_units_strikes_on_the_assumed_steps(tmp_path: Path) -> None:
    prepared = _prepared(SymbolCache(tmp_path, "NVDA"))

    est = estimate(prepared, STEPS)

    assert [u.name for u in est.units] == [u.name for u in prepared.pending]
    for got, unit in zip(est.units, prepared.pending, strict=True):
        ladders = {k for b in unit.bands for k in b.ladder(STEPS.steps[b.region])}
        assert got.strikes == len(ladders)  # overlapping bands count a strike once
        assert got.requests == len(ladders) + STEP_ASKS * len(unit.bands)
    assert est.requests == sum(u.requests for u in est.units)
    assert est.minutes == math.ceil(est.requests / REQUESTS_PER_MINUTE)
    assert STEP_ASKS == 5


def test_estimate_leaves_out_cached_units(tmp_path: Path) -> None:
    cache = SymbolCache(tmp_path, "NVDA")
    first = _prepared(cache)
    partial = replace(first, pending=first.pending[:3])
    pull_units(_market(), cache, partial, STEPS.steps, lambda: NOW, retry=NO_WAIT)

    again = _prepared(cache)
    est = estimate(again, STEPS)

    assert [u.name for u in est.units] == [u.name for u in first.pending[3:]]
    assert again.cached == 4  # the stock and three chain units


def test_estimate_describes_units_requests_and_its_assumptions(tmp_path: Path) -> None:
    est = estimate(_prepared(SymbolCache(tmp_path, "NVDA")), STEPS)

    text = describe(est)

    assert "probes/NVDA_20260927.json" in text
    assert "near the money $1.00, deep ITM $5.00" in text
    assert est.requests_high == RE_ASK_FACTOR * est.requests
    assert RE_ASK_FACTOR == 3
    assert est.minutes_high == math.ceil(3 * est.requests / REQUESTS_PER_MINUTE)
    assert (
        f"Estimate: {est.requests:,} to {est.requests_high:,} RIC requests, about "
        f"{est.minutes} to {est.minutes_high} min" in text
    )
    assert "stock tape fetched now" in text
    planned = len(est.prepared.plan.units)
    assert f"Units: {planned} planned, 0 cached, {planned} to write" in text  # the stock too
    assert text.isascii()  # Git Bash prints the estimate in cp1252 on Windows (DEC-58)


def test_estimate_prints_each_kinds_units_strikes_and_requests(tmp_path: Path) -> None:
    est = estimate(_prepared(SymbolCache(tmp_path, "NVDA")), STEPS)

    rows = {line[:26].strip(): line[26:].split() for line in describe(est).splitlines()[4:7]}

    expected: dict[str, list[str]] = {}
    for kind in (UnitKind.WEEKLY_CALLS, UnitKind.MONTHLY_CALLS, UnitKind.PUTS):
        units = [u for u in est.units if u.kind is kind]
        strikes, requests = sum(u.strikes for u in units), sum(u.requests for u in units)
        expected[kind.value] = [str(len(units)), f"{strikes:,}", f"{requests:,}"]
    assert rows == expected
    assert len({tuple(v[1:]) for v in expected.values()}) == 3  # the kinds' figures differ


def test_estimate_refuses_a_report_that_stopped_before_its_increments(tmp_path: Path) -> None:
    path = tmp_path / "NVDA_20260928.json"
    path.write_text(json.dumps({"symbol": "NVDA", "stopped": "a never-listed RIC answered"}))

    with pytest.raises(NoProbeReportError, match="stopped early"):
        assumed_steps(path)


@pytest.mark.parametrize("body", ["{not json", "[]", '{"increments": null}'])
def test_estimate_refuses_a_report_it_cannot_read(tmp_path: Path, body: str) -> None:
    path = tmp_path / "NVDA_20260928.json"
    path.write_text(body, encoding="utf-8")

    with pytest.raises(NoProbeReportError, match="NVDA_20260928"):
        assumed_steps(path)
