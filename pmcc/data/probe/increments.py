"""DEC-14: strike increments, measured the way the fetch will measure them.

Per region, one session, one daily request for the anchor and its four offsets (`discovery`).
The regions sample what the backtest needs: near the money on the next weekly and on an expired
one (the window's weeklies are all expired), and near the money and deep ITM (0.8 x spot) on the
monthly nearest 180 DTE. LDG §6.2 expects $1 near spot and $5 deep ITM on the same monthly.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import final

from pmcc.data.discovery import increment_anchor, increment_from, increment_strikes
from pmcc.data.fetch import fetch_contracts
from pmcc.data.probe.context import QUOTES, Json, Probe, dollars, over
from pmcc.data.provider import Interval
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_CENT, Price
from pmcc.domain.sessions import Session


@final
@dataclass(frozen=True, slots=True)
class RegionAsk:
    """Where to measure an increment: an expiry, the session to ask, and the region's centre."""

    name: str
    expiry: date
    session: Session
    centre: Price


def probe_increments(probe: Probe, regions: Sequence[RegionAsk]) -> tuple[Json, dict[str, int]]:
    """Each region's record, and its increment in cents."""
    records: Json = {}
    steps: dict[str, int] = {}
    for region in regions:
        records[region.name], steps[region.name] = measure(probe, region)
    return records, steps


def measure(probe: Probe, region: RegionAsk) -> tuple[Json, int]:
    anchor = increment_anchor(region.centre)
    strikes = increment_strikes(anchor)
    options = [
        OptionId(probe.root, region.expiry, Right.CALL, Price(k * UNITS_PER_CENT)) for k in strikes
    ]
    request = over([region.session], QUOTES, Interval.DAILY)
    result = fetch_contracts(probe.provider, options, request, probe.today, retry=probe.retry)
    answered = sorted(o.strike_cents for o in result.answered)
    step = increment_from(anchor, answered)
    return {
        "expiry": region.expiry.isoformat(),
        "session": region.session.day.isoformat(),
        "centre": dollars(region.centre),
        "anchor_cents": anchor,
        "asked_cents": list(strikes),
        "answered_cents": answered,
        "anchor_answered": anchor in answered,
        "step_cents": step,
        "forms_used": sorted({form.value for form in result.ric_form_used.values()}),
        "bar_dates": sorted({d.isoformat() for d in result.history.rows["bar_start"].to_list()}),
    }, step
