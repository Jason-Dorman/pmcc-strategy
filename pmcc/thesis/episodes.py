"""Shock episodes and their one candidate each (THESIS-SPEC §5.3, §5.4).

- **Shock at t:** VIX_t at or above the 80th percentile of the 252 sessions before t (t
  excluded; linear interpolation between order statistics, TD-16), and VIX_t / VIX_(t-5) at or
  above 1.25, on a warm session (§5.1's 252 valid returns). Missing inputs leave the test unknown
  (`None`), never false: a data-quality outcome.
- **Episode:** the first shock opens a fixed search window, the 10 sessions after it. Shocks
  inside it are ignored and never move its end; the next episode can open only after it.
- **Candidate:** the first window session with RV5 < RV20, RV5 <= RV5 three sessions earlier,
  and a forecast gap of at least 0.03, chosen without credit (§5.4). If a session before any
  qualifying one can't be tested, the episode is `INCOMPLETE_CANDIDATE_SEARCH`: a later
  observable session is not necessarily the first. A window running past the data, with no
  candidate yet, is `SEARCHING`; so is one the calendar's end cuts short.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import final

from pmcc.domain.calendar import SessionCalendar
from pmcc.thesis.calendar import sessions_within
from pmcc.thesis.config import NormalizationConfig, ShockConfig, ThesisConfig
from pmcc.thesis.features import FeatureRow


class CandidateStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    NO_CANDIDATE = "NO_CANDIDATE"
    INCOMPLETE_CANDIDATE_SEARCH = "INCOMPLETE_CANDIDATE_SEARCH"
    SEARCHING = "SEARCHING"


@final
@dataclass(frozen=True, slots=True)
class Episode:
    episode_id: str
    shock_day: date
    window: tuple[date, ...]  # the search sessions, s+1 .. s+10
    status: CandidateStatus
    candidate_day: date | None
    note: str  # why it is incomplete or still searching; empty otherwise

    @property
    def window_end(self) -> date:
        """The window's last session; the shock's own day if the calendar ends at the shock."""
        return self.window[-1] if self.window else self.shock_day


def percentile(values: Sequence[float], p: float) -> float:
    """The `p` quantile by linear interpolation between order statistics (numpy's default)."""
    ordered = sorted(values)
    h = (len(ordered) - 1) * p
    lo = int(h)
    if lo + 1 >= len(ordered):
        return ordered[-1]
    return ordered[lo] + (h - lo) * (ordered[lo + 1] - ordered[lo])


def shock_flags(rows: Sequence[FeatureRow], config: ShockConfig) -> tuple[bool | None, ...]:
    """Each row's shock test: True, False, or None when it can't be decided."""
    return tuple(_shock(rows, i, config) for i in range(len(rows)))


def _shock(rows: Sequence[FeatureRow], i: int, config: ShockConfig) -> bool | None:
    lookback, back = config.percentile_lookback_sessions, config.ratio_lookback_sessions
    vix = rows[i].vix_points
    if not rows[i].warm or vix is None or i < max(lookback, back):
        return None
    before = [row.vix_points for row in rows[i - lookback : i]]
    earlier = rows[i - back].vix_points
    if earlier is None or any(v is None for v in before):
        return None
    level = percentile([v for v in before if v is not None], config.percentile_threshold)
    return vix >= level and vix / earlier >= config.minimum_vix_ratio


def find_episodes(
    rows: Sequence[FeatureRow], calendar: SessionCalendar, config: ThesisConfig
) -> tuple[Episode, ...]:
    """Every episode the rows hold, in order, with its candidate decided from its window."""
    flags = shock_flags(rows, config.shock)
    by_day = {row.day: (i, row) for i, row in enumerate(rows)}
    episodes: list[Episode] = []
    for row, flag in zip(rows, flags, strict=True):
        if flag and (not episodes or row.day > episodes[-1].window_end):
            window = sessions_within(calendar, row.day, config.shock.search_sessions_after_shock)
            episodes.append(_episode(row.day, window, rows, by_day, config))
    return tuple(episodes)


def _episode(
    shock: date,
    window: tuple[date, ...],
    rows: Sequence[FeatureRow],
    by_day: dict[date, tuple[int, FeatureRow]],
    config: ThesisConfig,
) -> Episode:
    episode_id = f"{config.model_version}:{shock.isoformat()}"
    for day in window:
        found = by_day.get(day)
        if found is None:
            note = f"the window runs past the data at {day}"
            return Episode(episode_id, shock, window, CandidateStatus.SEARCHING, None, note)
        verdict = qualifies(rows, found[0], config.normalization)
        if verdict is None:
            note = f"{day} could not be tested: a feature is missing"
            status = CandidateStatus.INCOMPLETE_CANDIDATE_SEARCH
            return Episode(episode_id, shock, window, status, None, note)
        if verdict:
            return Episode(episode_id, shock, window, CandidateStatus.CANDIDATE, day, "")
    if len(window) < config.shock.search_sessions_after_shock:
        note = "the window runs past the calendar's last day"
        return Episode(episode_id, shock, window, CandidateStatus.SEARCHING, None, note)
    return Episode(episode_id, shock, window, CandidateStatus.NO_CANDIDATE, None, "")


@final
@dataclass(frozen=True, slots=True)
class Checks:
    """§5.4's three tests at one session, each None when an input is missing."""

    swings_below_long: bool | None  # RV5 < RV20
    swings_not_rising: bool | None  # RV5 <= RV5 three sessions earlier
    gap_ok: bool | None  # the forecast gap at or above its minimum
    earlier_rv_short: float | None  # RV5 three sessions earlier

    @property
    def passed(self) -> bool | None:
        """All three, or None when any couldn't be tested."""
        tests = (self.swings_below_long, self.swings_not_rising, self.gap_ok)
        return None if None in tests else all(tests)


def checks(rows: Sequence[FeatureRow], i: int, config: NormalizationConfig) -> Checks:
    back = i - config.falling_rv_comparison_sessions
    row = rows[i]
    earlier = rows[back].rv_short if back >= 0 else None
    short, long_, gap = row.rv_short, row.rv_long, row.forecast_gap_vol
    return Checks(
        swings_below_long=None if short is None or long_ is None else short < long_,
        swings_not_rising=None if short is None or earlier is None else short <= earlier,
        gap_ok=None if gap is None else gap >= config.minimum_forecast_gap_decimal,
        earlier_rv_short=earlier,
    )


def qualifies(rows: Sequence[FeatureRow], i: int, config: NormalizationConfig) -> bool | None:
    """§5.4's three tests at row `i`: True, False, or None when an input is missing."""
    return checks(rows, i, config).passed
