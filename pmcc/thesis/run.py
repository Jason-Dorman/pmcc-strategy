"""`thesis run`: pull, compute, write `live/thesis/thesis.json` (T3-01; TD-04, TD-05, TD-09).

Each night the whole tracker is re-derived from its sources, and only the derived file is kept
(TD-03, TD-09); nothing is cached:

1. **Closes** (TD-04): `.SPX` and `.VIX`, daily from 2014-01-01, over the platform session, in one
   batched request. A day the calendar has no session for is dropped and counted: VIX is computed
   on some NYSE holidays (TD-18), and the tracker runs on NYSE's sessions (§4.4). A session whose
   20:30 decision hasn't passed is left out too: LSEG serves a day's bar while it trades, and a
   session's signal is never generated before its decision (§7.1, TD-28).
2. **Credit** (TD-05, TD-19): FRED's BAMLH0A0HYM2 through its API (TD-17), percent to basis points,
   on the assumed publication lag (§4.4). LSEG isn't entitled to ICE's indexes.
3. **Compute:** `run_tracker`, the evidence and the statuses, as of the run's time.
4. **Write:** the public model as canonical JSON, to a temporary file and then into place.

An outage (LSEG's session, FRED not answering) raises before anything is written; so does a
series that comes back empty or a FRED answer that can't be read: the night's file is left as it
was, never replaced by a partial one (CLAUDE.md › LSEG access, FRED).
"""

import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import final

import polars as pl

from pmcc.data.fetch import BarRequest, fetch_rics
from pmcc.data.provider import (
    HistoryProvider,
    Interval,
    NoDataError,
    TransientError,
    UnreadableAnswerError,
)
from pmcc.domain.calendar import SessionCalendar
from pmcc.export import canonical
from pmcc.export.thesis_models import Thesis, ThesisSource
from pmcc.thesis.calendar import last_decided
from pmcc.thesis.config import ThesisConfig
from pmcc.thesis.credit import credit_series, percent_to_bps
from pmcc.thesis.evidence import evidence
from pmcc.thesis.fred import FredError, FredKey, FredSeries, GetText, fetch_series
from pmcc.thesis.probe import CLOSE, FRED_SERIES, HISTORY_START, INDEX_RIC, VIX_RIC
from pmcc.thesis.publish import Statuses, thesis_file
from pmcc.thesis.status import current_state, data_status, expected_by, signal, thesis_status
from pmcc.thesis.tracker import run_tracker
from pmcc.thesis.versions import compare

THESIS_FILE = Path("live") / "thesis" / "thesis.json"
_DAY = timedelta(days=1)


class ThesisRunError(Exception):
    """A source answered without what the tracker needs: nothing is written."""


@final
@dataclass(frozen=True, slots=True)
class Inputs:
    index: dict[date, float]
    vix: dict[date, float]
    credit: FredSeries
    dropped: Mapping[str, int]  # closes on days the calendar has no session, per RIC


def plan(now: datetime) -> str:
    """The request estimate `--plan-only` prints: small, a few seconds."""
    return (
        f"LSEG: 1 daily request for {INDEX_RIC} and {VIX_RIC}, {HISTORY_START} to {now.date()} "
        f"(about 3,300 sessions each); FRED: 1 request for {FRED_SERIES}. Nothing is cached."
    )


def pull(
    provider: HistoryProvider,
    get_text: GetText,
    key: FredKey,
    calendar: SessionCalendar,
    config: ThesisConfig,
    now: datetime,
    sleep: Callable[[float], None] = lambda seconds: time.sleep(seconds),
) -> Inputs:
    """The closes and the credit series. Raises `ThesisRunError` when one comes back without
    what the tracker needs; an outage propagates."""
    request = BarRequest((CLOSE,), HISTORY_START, now.date() + _DAY, Interval.DAILY)
    try:
        result = fetch_rics(provider, [INDEX_RIC, VIX_RIC], request)
    except (NoDataError, TransientError, UnreadableAnswerError) as exc:
        raise ThesisRunError(f"LSEG's closes: {type(exc).__name__}: {exc}") from exc
    if result.unanswered:
        raise ThesisRunError(f"LSEG returned no closes for {', '.join(result.unanswered)}")
    through = last_decided(calendar, now, config.decision_time)
    rows = result.history.rows
    index, dropped_index = on_sessions(_closes(rows, INDEX_RIC), calendar, through)
    vix, dropped_vix = on_sessions(_closes(rows, VIX_RIC), calendar, through)
    try:
        credit = fetch_series(FRED_SERIES, key, get_text, sleep=sleep)
    except FredError as exc:
        raise ThesisRunError(str(exc)) from exc
    if not credit.valued:
        raise ThesisRunError(f"FRED's {FRED_SERIES} holds no values")
    return Inputs(index, vix, credit, {INDEX_RIC: dropped_index, VIX_RIC: dropped_vix})


def _closes(rows: pl.DataFrame, ric: str) -> dict[date, float]:
    picked = rows.filter((pl.col("ric") == ric) & (pl.col("field") == CLOSE)).sort("bar_start")
    return dict(zip(picked["bar_start"].to_list(), picked["value"].to_list(), strict=True))


def on_sessions(
    closes: Mapping[date, float], calendar: SessionCalendar, through: date
) -> tuple[dict[date, float], int]:
    """The closes on the calendar's sessions up to `through`, and how many up to it fell on other
    days. A later day's bar isn't final: neither kept nor counted."""
    final = {d: v for d, v in closes.items() if d <= through}
    kept = {
        d: v
        for d, v in final.items()
        if calendar.first_day <= d <= calendar.last_day and calendar.is_session(d)
    }
    return kept, len(final) - len(kept)


def build(inputs: Inputs, calendar: SessionCalendar, config: ThesisConfig, now: datetime) -> Thesis:
    """The night's file, from its inputs, as of `now`."""
    points = [(d, percent_to_bps(v)) for d, v in inputs.credit.valued]
    credit = credit_series(points, calendar, config.credit)
    tracker = run_tracker(inputs.index, inputs.vix, credit, calendar, config)
    found = evidence(tracker, config)
    statuses = Statuses(
        data_status=data_status(tracker, calendar, config, now).value,
        expected_by=expected_by(calendar, config, now),
        thesis_status=thesis_status(found).value,
        signal=signal(tracker),
        current=current_state(tracker, config),
    )
    compared = compare(tracker, config)
    return thesis_file(tracker, found, compared, statuses, sources(inputs), calendar, config, now)


def sources(inputs: Inputs) -> tuple[ThesisSource, ...]:
    """Each series' provider, coverage and units (§10's provenance)."""
    valued = inputs.credit.valued
    return (
        _source(
            "index",
            "LSEG",
            INDEX_RIC,
            inputs.index,
            "index points",
            "S&P 500 index, daily close (TRDPRC_1)",
        ),
        _source(
            "vix",
            "LSEG",
            VIX_RIC,
            inputs.vix,
            "VIX points",
            f"Cboe VIX, daily close (TRDPRC_1); {inputs.dropped[VIX_RIC]} values on days NYSE "
            "was closed left out",
        ),
        ThesisSource(
            series="credit",
            provider="FRED, Federal Reserve Bank of St. Louis; ICE Data Indices, LLC",
            identifier=FRED_SERIES,
            first=valued[0][0].isoformat() if valued else None,
            last=valued[-1][0].isoformat() if valued else None,
            observations=len(valued),
            units="basis points",
            note=(
                "ICE BofA US High Yield Index Option-Adjusted Spread, published in percent and "
                "shown in basis points (3.52 is 352). Assumed usable two business days after its "
                "date, at 20:30 New York. FRED serves the last three years only."
            ),
        ),
    )


def _source(
    series: str, provider: str, ric: str, closes: Mapping[date, float], units: str, note: str
) -> ThesisSource:
    days = sorted(closes)
    return ThesisSource(
        series=series,
        provider=provider,
        identifier=ric,
        first=days[0].isoformat() if days else None,
        last=days[-1].isoformat() if days else None,
        observations=len(days),
        units=units,
        note=note,
    )


def write(root: Path, thesis: Thesis) -> Path:
    """`thesis` at `root/live/thesis/thesis.json`, written whole or not at all."""
    path = root / THESIS_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_bytes(canonical.to_bytes(thesis.model_dump(mode="json")))
    os.replace(temporary, path)
    return path
