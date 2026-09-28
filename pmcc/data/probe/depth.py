"""DEC-07: how far back LSEG keeps hourly bars: stock, expired weeklies and long-dated calls.

The probe samples weeks 1 to 18 months back (the holiday table starts in 2025). In each week it
asks, hourly over that week's sessions:

- the stock's TRDPRC_1;
- the weekly call at the $10 strike nearest the close before the week (near the money), expiring
  on the week-final session;
- the call on the monthly nearest 180 DTE at the $10 strike nearest 0.8 x that close (a long leg).

Options are asked in the forms `forms_to_ask` gives them (DEC-45). A leg reaches back to a sampled
week when it has bars there (a valid mid, for an option) and in every more recent sampled week. The
window's start is the PO's call at P1-05 (DEC-07); this is the evidence.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import final

import polars as pl

from pmcc.data.discovery import increment_anchor, nearest_monthly
from pmcc.data.fetch import fetch_contracts, fetch_rics
from pmcc.data.probe.context import (
    QUOTES,
    Json,
    Probe,
    over,
    price,
    session_bar_ends,
    valid_mid,
    wide,
)
from pmcc.data.probe.identifiers import DailyTape
from pmcc.data.provider import Interval
from pmcc.data.ric import build_ric, forms_to_ask
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_CENT, Price
from pmcc.domain.sessions import Session

LOOKBACK_MONTHS = (1, 2, 3, 4, 6, 9, 10, 11, 12, 15, 18)
DEEP_ITM_MONEYNESS = 0.8
LEGS = ("stock", "weekly_call", "long_call")
_MONTH_DAYS = 30.44


@final
@dataclass(frozen=True, slots=True)
class Sample:
    """One sampled week: its record, and which legs had bars there."""

    week_open: date | None
    record: Json
    found: dict[str, bool] = field(default_factory=dict[str, bool])


def probe_depth(probe: Probe, stock_ric: str, tape: DailyTape) -> Json:
    samples = [sample(probe, stock_ric, tape, months) for months in LOOKBACK_MONTHS]
    return {
        "samples": [s.record for s in samples],
        "back_to": {leg: reaches_back_to(samples, leg) for leg in LEGS},
    }


def reaches_back_to(samples: Sequence[Sample], leg: str) -> str | None:
    """The oldest sampled week the leg has bars in, with every more recent sample having them."""
    oldest: str | None = None
    for s in samples:  # most recent first
        if s.week_open is None or not s.found.get(leg, False):
            break
        oldest = s.week_open.isoformat()
    return oldest


def sample(probe: Probe, stock_ric: str, tape: DailyTape, months: int) -> Sample:
    target = probe.today - timedelta(days=round(months * _MONTH_DAYS))
    base: Json = {"months_back": months}
    if target - timedelta(days=7) < probe.calendar.first_day:
        return Sample(None, {**base, "skipped": "before the holiday table's first day"})
    week = probe.calendar.week_sessions(target)
    close = tape.close_on_or_before(week[0].day - timedelta(days=1)) if week else None
    if close is None:
        return Sample(None, {**base, "skipped": "no session, or no daily close before the week"})
    ends = session_bar_ends(week)
    weekly = OptionId(probe.root, week[-1].day, Right.CALL, _anchored(close))
    long_expiry = nearest_monthly(probe.calendar, week[0].day)
    long = OptionId(probe.root, long_expiry, Right.CALL, _anchored(close * DEEP_ITM_MONEYNESS))
    legs = {
        "stock": _stock(probe, stock_ric, week, ends),
        "weekly_call": _contract(probe, weekly, week, ends),
        "long_call": _contract(probe, long, week, ends),
    }
    record: Json = {
        **base,
        "week_open": week[0].day.isoformat(),
        "week_final": week[-1].day.isoformat(),
        "close_before": close,
        **{leg: r for leg, (r, _) in legs.items()},
    }
    return Sample(week[0].day, record, {leg: has for leg, (_, has) in legs.items()})


def _anchored(value: float) -> Price:
    return Price(increment_anchor(price(value)) * UNITS_PER_CENT)


def _stock(probe: Probe, ric: str, week: Sequence[Session], ends: pl.Series) -> tuple[Json, bool]:
    asked = over(week, ("TRDPRC_1",), Interval.HOURLY)
    rows = fetch_rics(probe.provider, [ric], asked, retry=probe.retry).series(ric)
    bars = wide(rows).filter(pl.col("end").is_in(ends.implode())).height
    return {"ric": ric, "session_bars": bars, "of": ends.len()}, bars > 0


def _contract(
    probe: Probe, option: OptionId, week: Sequence[Session], ends: pl.Series
) -> tuple[Json, bool]:
    forms = forms_to_ask(option.expiry, probe.today)
    asked = over(week, QUOTES, Interval.HOURLY)
    result = fetch_contracts(probe.provider, [option], asked, probe.today, retry=probe.retry)
    quotes = wide(result.history.rows).filter(pl.col("end").is_in(ends.implode()))
    valid = quotes.filter(valid_mid(quotes)).height
    ric = result.answered.get(option)
    return {
        "ric": ric or build_ric(option, forms[0]),
        "answered": ric is not None,
        "form": None if ric is None else result.ric_form_used[ric].value,
        "forms_asked": [f.value for f in forms],
        "valid_mid_bars": valid,
        "of": ends.len(),
    }, valid > 0
