"""Synthetic inputs for the thesis tracker's tests (T2-01), on the thesis calendar's real sessions.

These are fixtures, never market evidence (THESIS-SPEC §0). The probe's fakes are in
`tests.fakes.thesis_probe`.
"""

import math
from collections.abc import Callable, Sequence
from datetime import date, timedelta

from pmcc.thesis.calendar import load_thesis_calendar, sessions_after
from pmcc.thesis.config import load_thesis_config
from pmcc.thesis.credit import CreditObservation, CreditSeries, assumed_available_at

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
