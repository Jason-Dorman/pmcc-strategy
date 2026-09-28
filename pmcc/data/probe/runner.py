"""`pmcc probe`: every P1-04 check for one symbol, as one JSON report (ARCHITECTURE §6.2).

Order matters. The stock RIC comes first (every later check needs it), then the daily tape (spot,
splits, the calendar check), then the DEC-83 error answers. A never-listed RIC must come back with a
no-data code. If it answers with bars or an unreadable answer, the report stops there, says why, and
the command exits non-zero; if it fails any other way, that failure is asked again like any fetch
and persists as an outage. An outage at any point propagates and nothing is written (LDG §4.3): a
dead or signed-out Workspace shows up only as transient failures (DEC-83), never as an answer.
"""

import json
import math
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import cast

import numpy as np

from pmcc.data.discovery import TRADING_DAYS, increment_anchor, nearest_monthly
from pmcc.data.fetch import Retry
from pmcc.data.files import write_new
from pmcc.data.probe.bars import probe_bars
from pmcc.data.probe.context import CountingProvider, Json, Probe, price
from pmcc.data.probe.coverage import probe_coverage
from pmcc.data.probe.depth import DEEP_ITM_MONEYNESS, probe_depth
from pmcc.data.probe.edges import probe_edges
from pmcc.data.probe.errors import probe_errors
from pmcc.data.probe.fields import probe_fields
from pmcc.data.probe.identifiers import (
    DailyTape,
    ProbeStoppedError,
    daily_tape,
    resolve_stock,
    tape_checks,
)
from pmcc.data.probe.increments import RegionAsk, probe_increments
from pmcc.data.provider import HistoryProvider
from pmcc.data.ric import RicForm, build_ric
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import to_et
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_CENT, Price

VOL_SESSIONS = 60
LISTED_MIN_DAYS = 14  # the probe's listed call expires at least two weeks out
_DAY = timedelta(days=1)
_WEEK = timedelta(days=7)


def run_probe(
    provider: HistoryProvider,
    symbol: str,
    calendar: SessionCalendar,
    now: datetime,
    retry: Retry = Retry(),  # noqa: B008 (frozen, so a shared default is safe)
) -> Json:
    """The report for `symbol`. `now` must be tz-aware; its ET date is the fetch date (DEC-45)."""
    counting = CountingProvider(provider)
    probe = Probe(symbol, symbol, calendar, counting, to_et(now), retry)
    last = probe.last_session
    report: Json = {
        "symbol": symbol,
        "option_root": probe.root,
        "probed_at": probe.now.isoformat(),
        "fetch_date": probe.today.isoformat(),
        "last_session": last.day.isoformat(),
    }
    stock, stock_ric = resolve_stock(probe)
    tape = daily_tape(probe, stock_ric)
    report["identifiers"] = {"stock": stock, **tape_checks(probe, tape)}
    spot = tape.close_on_or_before(last.day)
    if spot is None:
        raise ProbeStoppedError(f"{stock_ric} has no daily close on or before {last.day}")
    listed = listed_call(probe, spot)
    expired = calendar.weekly_expiries(last.day - 3 * _WEEK, last.day - _WEEK)[-1]
    errors = probe_errors(probe, listed, expired)
    report["errors"] = errors
    if errors["never_listed_is_no_data"] is not True:
        stop = "a never-listed RIC answered with something other than a no-data code: see errors"
        return {**report, "stopped": stop, "requests": counting.calls}
    report.update(_quotes(probe, stock_ric, tape, spot, listed, expired))
    return {**report, "stopped": None, "requests": counting.calls}


def _quotes(
    probe: Probe, stock_ric: str, tape: DailyTape, spot: float, listed: OptionId, expired: date
) -> Json:
    """The checks that read quotes: DEC-06, 47, 13, 14, 08/09 and 07."""
    listed_ric = build_ric(listed, RicForm.LIVE)
    long_expiry = nearest_monthly(probe.calendar, probe.last_session.day)
    increments, steps = probe_increments(probe, regions(probe, tape, spot, long_expiry, expired))
    deep_step = steps["monthly_deep_itm"]
    return {
        "bars": probe_bars(probe, stock_ric, listed_ric),
        "edges": probe_edges(probe, stock_ric),
        "fields": probe_fields(probe, stock_ric, listed_ric),
        "increments": increments,
        "coverage": probe_coverage(
            probe, stock_ric, spot, realized_vol(tape), long_expiry, deep_step
        ),
        "depth": probe_depth(probe, stock_ric, tape),
    }


def listed_call(probe: Probe, spot: float) -> OptionId:
    """A liquid, live call: the next monthly at least two weeks out, at the $10 strike near spot."""
    today = probe.today
    expiry = probe.calendar.monthly_expiries(today + LISTED_MIN_DAYS * _DAY, today + 70 * _DAY)[0]
    strike = Price(increment_anchor(price(spot)) * UNITS_PER_CENT)
    return OptionId(probe.root, expiry, Right.CALL, strike)


def regions(
    probe: Probe, tape: DailyTape, spot: float, long_expiry: date, expired: date
) -> list[RegionAsk]:
    """Where increments are measured (DEC-14)."""
    last = probe.last_session
    this_final = probe.calendar.week_final(last.day).day
    next_weekly = (
        this_final if this_final > last.day else probe.calendar.week_final(last.day + _WEEK).day
    )
    expired_open = probe.calendar.week_open(expired)
    expired_centre = tape.close_on_or_before(expired_open.day - _DAY) or spot
    return [
        RegionAsk("weekly_near_money", next_weekly, last, price(spot)),
        RegionAsk("weekly_near_money_expired", expired, expired_open, price(expired_centre)),
        RegionAsk("monthly_near_money", long_expiry, last, price(spot)),
        RegionAsk("monthly_deep_itm", long_expiry, last, price(spot * DEEP_ITM_MONEYNESS)),
    ]


def realized_vol(tape: DailyTape, sessions: int = VOL_SESSIONS) -> float:
    """Annualized close-to-close volatility over the last `sessions` daily returns."""
    closes = tape.frame.drop_nulls("TRDPRC_1")["TRDPRC_1"].to_numpy()[-(sessions + 1) :]
    if closes.size < 3:
        raise ProbeStoppedError(f"too few daily closes for a volatility ({closes.size})")
    return float(np.std(np.diff(np.log(closes)), ddof=1)) * math.sqrt(TRADING_DAYS)


def probe_path(out_dir: Path, symbol: str, day: date) -> Path:
    """`data_cache/probes/{SYM}_{YYYYMMDD}.json` (ARCHITECTURE §6.4)."""
    return out_dir / f"{symbol}_{day:%Y%m%d}.json"


def write_report(report: Json, path: Path) -> None:
    """Write the report whole or not at all, and never over an existing one (LDG §5)."""
    if path.exists():
        raise FileExistsError(
            f"{path} exists; a probe report is never overwritten. Rename it first."
        )
    text = json.dumps(_finite(report), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    write_new(path, text.encode("utf-8"))


def _finite(value: object) -> object:
    """NaN and infinities as null, so the report is valid JSON."""
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): _finite(v) for k, v in cast("dict[object, object]", value).items()}
    if isinstance(value, list | tuple):
        return [_finite(v) for v in cast("Sequence[object]", value)]
    return value
