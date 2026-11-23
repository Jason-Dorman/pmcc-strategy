"""Synthetic inputs for the thesis tracker's tests (T2-01), on the thesis calendar's real sessions.

These are fixtures, never market evidence (THESIS-SPEC §0). The probe's fakes are in
`tests.fakes.thesis_probe`.
"""

import json
import math
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta

from pmcc.domain.clock import ET
from pmcc.export.thesis_models import Thesis
from pmcc.thesis.calendar import load_thesis_calendar, sessions_after
from pmcc.thesis.config import load_thesis_config
from pmcc.thesis.credit import CreditObservation, CreditSeries, assumed_available_at
from pmcc.thesis.fred import parse_observations
from pmcc.thesis.run import Inputs, build

CAL = load_thesis_calendar()
CONFIG = load_thesis_config()


def sessions(start: date, count: int) -> list[date]:
    """`count` sessions from `start` (a session) on."""
    return [start, *sessions_after(CAL, start, count - 1)]


def alternating(sigma: float) -> Callable[[int], float]:
    """Returns of ±`sigma` in turn, so their mean square is exactly `sigma`²."""
    return lambda i: sigma if i % 2 else -sigma


def closes(
    days: Sequence[date], returns: Callable[[int], float], start: float = 4000.0
) -> dict[date, float]:
    """Index closes whose log return on the `i`th day (from 1) is `returns(i)`."""
    out = {days[0]: start}
    level = start
    for i, day in enumerate(days[1:], start=1):
        level *= math.exp(returns(i))
        out[day] = level
    return out


def flat(days: Sequence[date], value: float) -> dict[date, float]:
    return dict.fromkeys(days, value)


def credit(days: Sequence[date], bps: Callable[[int], float]) -> CreditSeries:
    """An observation on each day, available on the spec's assumed lag (§4.4)."""
    return CreditSeries(
        [
            CreditObservation(day, bps(i), assumed_available_at(day, CAL, CONFIG.credit))
            for i, day in enumerate(days)
        ]
    )


def weekdays(start: date, end: date) -> list[date]:
    """Every weekday from `start` to `end`: a source's own observation days."""
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    return [d for d in days if d.weekday() < 5]


# --- a whole night's inputs (T3-01) ----------------------------------------------------------
# A calm year, a VIX spike with three large returns, calm again: one shock at SPIKE_SHOCK and a
# stable-credit candidate six sessions later, as `test_thesis_tracker`'s own spike.

SPIKE_DAYS = sessions(date(2014, 1, 2), 360)
SPIKE_SHOCK = 300
SPIKE_CANDIDATE = SPIKE_SHOCK + 6


def _spike_return(i: int) -> float:
    big = SPIKE_SHOCK - 1 <= i <= SPIKE_SHOCK + 1
    size = 0.03 if big else 0.006
    return size if i % 2 else -size


def _spike_vix(i: int) -> float:
    if i < SPIKE_SHOCK:
        return 13.0 + (i % 5) * 0.1
    return max(18.0, 30.0 - (i - SPIKE_SHOCK) * 0.6)


def spike_index() -> dict[date, float]:
    return closes(SPIKE_DAYS, _spike_return)


def spike_vix() -> dict[date, float]:
    return {d: _spike_vix(i) for i, d in enumerate(SPIKE_DAYS)}


def spike_fred_text(percent: float = 3.5) -> str:
    """FRED's API answer: the spread on every weekday of the spike's span."""
    days = weekdays(SPIKE_DAYS[0], SPIKE_DAYS[-1])
    rows = [{"date": d.isoformat(), "value": f"{percent:.2f}"} for d in days]
    return json.dumps({"observations": rows})


def spike_thesis() -> Thesis:
    """The spike's night as `thesis run` builds it, at 22:00 New York after its last session."""
    last = SPIKE_DAYS[-1]
    now = datetime(last.year, last.month, last.day, 22, 0, tzinfo=ET)
    index, vix = spike_index(), spike_vix()
    credit_text = parse_observations(spike_fred_text(), "BAMLH0A0HYM2")
    inputs = Inputs(index, vix, credit_text, {".SPX": 0, ".VIX": 0})
    return build(inputs, CAL, CONFIG, now)
