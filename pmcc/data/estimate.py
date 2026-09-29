"""The fetch estimate, printed before any option request (ARCHITECTURE §6.1 step 3; LDG §4.15).

A plan holds bands, not strikes, and a band's ladder depends on its strike step, which only an
option request can measure. So the estimate assumes steps from the symbol's probe report (DEC-14,
DEC-84): the finest the probes measured per region. A band can still measure finer. The same steps
stand in for a band whose step can't be measured during the fetch (PO, DEC-14). The long (deep
ITM) bands run up to the money, so their region draws on both monthly records.

Requests: the low figure is Σ strikes + 5 per band (the step asks), one form per contract. An
hourly batch holding one unlisted strike is asked again one RIC at a time (DEC-83, LDG §4.4), and a
recently expired contract can be asked in both forms (DEC-45), so the high figure is three times
the low one. Fetches on the fake market asked 2.3 to 2.5 times the low figure, and an NVDA-sized
plan 1.9 times (P1-08's review). Minutes assume LDG §4.15's pace, about 44 RIC
requests a minute.
"""

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast, final

from pmcc.data.discovery import (
    INCREMENT_OFFSETS_CENTS,
    Region,
    Unit,
    UnitKind,
    unit_kind,
)
from pmcc.data.pull import Prepared

REQUESTS_PER_MINUTE = 44  # LDG §4.15: about 1,100 RIC requests in about 25 minutes
STEP_ASKS = 1 + len(INCREMENT_OFFSETS_CENTS)  # a band's step: the anchor and its offsets
RE_ASK_FACTOR = 3  # a batch's RICs asked again alone, a second form: 1.9-2.5x measured
# The probe report's increment records (DEC-85) that measure each region.
PROBE_RECORDS: Mapping[Region, tuple[str, ...]] = {
    Region.NEAR_MONEY: ("weekly_near_money", "weekly_near_money_expired"),
    Region.DEEP_ITM: ("monthly_deep_itm", "monthly_near_money"),
}


class NoProbeReportError(Exception):
    """The symbol has no probe report to take its strike steps from."""


@final
@dataclass(frozen=True, slots=True)
class AssumedSteps:
    """Strike steps in cents per region, and the probe report they came from."""

    source: Path
    steps: Mapping[Region, int]


def latest_probe_report(probes: Path, symbol: str) -> Path:
    """The symbol's newest probe report, `{SYM}_{YYYYMMDD}.json`. Raises `NoProbeReportError`.

    A report that stopped early is still the newest: `assumed_steps` refuses it rather than fall
    back to an older one, since the stop says something about LSEG changed.
    """
    reports = sorted(probes.glob(f"{symbol}_{'[0-9]' * 8}.json"))
    if not reports:
        raise NoProbeReportError(
            f"no probe report for {symbol} in {probes}: run `pmcc probe --symbol {symbol}` first; "
            "its strike steps feed the estimate (DEC-14)"
        )
    return reports[-1]


def assumed_steps(report: Path) -> AssumedSteps:
    """The finest step the report measured per region, from records whose anchor answered.

    Raises `NoProbeReportError` for a report that can't be read, that stopped before measuring
    increments, or that has a region with no such record.
    """
    increments = _increments(report)
    steps: dict[Region, int] = {}
    for region, names in PROBE_RECORDS.items():
        measured = [
            int(increments[n]["step_cents"])
            for n in names
            if n in increments and increments[n]["anchor_answered"] is True
        ]
        if not measured:
            raise NoProbeReportError(f"{report} measured no {region.value} strike step")
        steps[region] = min(measured)
    return AssumedSteps(report, steps)


def _increments(report: Path) -> Mapping[str, Mapping[str, Any]]:
    try:
        raw: object = json.loads(report.read_bytes())
    except (OSError, ValueError) as exc:
        raise NoProbeReportError(f"{report} can't be read: {exc}") from exc
    body = cast("dict[str, Any]", raw) if isinstance(raw, dict) else {}
    increments = body.get("increments")
    if not isinstance(increments, dict):
        stopped = body.get("stopped")
        why = f"it stopped early ({stopped})" if stopped else "it has no increments"
        raise NoProbeReportError(
            f"{report} can't give strike steps: {why}. Probe {report.stem.split('_')[0]} again."
        )
    return cast("Mapping[str, Mapping[str, Any]]", increments)


@final
@dataclass(frozen=True, slots=True)
class UnitEstimate:
    """One pending unit's strikes on the assumed steps, and its RIC requests."""

    name: str
    kind: UnitKind
    bands: int
    strikes: int

    @property
    def requests(self) -> int:
        return self.strikes + STEP_ASKS * self.bands


@final
@dataclass(frozen=True, slots=True)
class Estimate:
    """What is left to fetch for one symbol, and roughly how long it takes."""

    prepared: Prepared
    steps: AssumedSteps
    units: tuple[UnitEstimate, ...]

    @property
    def requests(self) -> int:
        return sum(u.requests for u in self.units)

    @property
    def requests_high(self) -> int:
        return RE_ASK_FACTOR * self.requests

    @property
    def minutes(self) -> int:
        return math.ceil(self.requests / REQUESTS_PER_MINUTE)

    @property
    def minutes_high(self) -> int:
        return math.ceil(self.requests_high / REQUESTS_PER_MINUTE)


def estimate(prepared: Prepared, steps: AssumedSteps) -> Estimate:
    """The pending units' strikes and requests on the assumed steps."""
    return Estimate(prepared, steps, tuple(_unit(u, steps) for u in prepared.pending))


def _unit(unit: Unit, steps: AssumedSteps) -> UnitEstimate:
    strikes = {k for b in unit.bands for k in b.ladder(steps.steps[b.region])}
    kind = unit_kind(unit.right, {b.region for b in unit.bands})
    return UnitEstimate(unit.name, kind, len(unit.bands), len(strikes))


def describe(est: Estimate) -> str:
    """The estimate as printed."""
    prepared, plan = est.prepared, est.prepared.plan
    stock = "fetched now (1 RIC request)" if prepared.stock is not None else "cached"
    near, deep = (est.steps.steps[r] / 100 for r in (Region.NEAR_MONEY, Region.DEEP_ITM))
    lines = [
        f"{prepared.target.symbol}: window {plan.window_start} to {plan.window_end}; "
        f"stock tape {stock}; band volatility {plan.sigma:.4f}",
        f"Strike steps assumed from {est.steps.source.as_posix()} (DEC-14): "
        f"near the money ${near:.2f}, deep ITM ${deep:.2f}",
        f"Units: {len(plan.units)} planned, {prepared.cached} cached, "
        f"{len(est.units) + (prepared.stock is not None)} to write",
        f"  {'kind':<24}{'units':>7}{'strikes':>10}{'requests':>10}",
    ]
    for kind in UnitKind:
        units = [u for u in est.units if u.kind is kind]
        if units:
            strikes, requests = sum(u.strikes for u in units), sum(u.requests for u in units)
            lines.append(f"  {kind.value:<24}{len(units):>7}{strikes:>10,}{requests:>10,}")
    lines += [
        f"Estimate: {est.requests:,} to {est.requests_high:,} RIC requests, about "
        f"{est.minutes} to {est.minutes_high} min at {REQUESTS_PER_MINUTE} a minute (LDG 4.15).",
        "The low figure asks each strike once. A batch holding an unlisted strike is asked again "
        "one RIC at a time, and a recently expired contract in both forms: expect about 2 to 2.5 "
        "times the low figure.",
    ]
    return "\n".join(lines)
