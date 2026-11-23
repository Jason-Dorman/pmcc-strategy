"""`run_tracker`: the whole tracker on series in memory (THESIS-SPEC §5; TD-03).

Index and VIX closes and a credit series in; out, for every session from the first input to the
last: its features, its outcome (null until matured), and its credit state at its decision
(20:30 New York, §7.1); and every episode, each candidate's credit at the candidate's decision and
its eligibility. The candidate is fixed before credit is read (§5.4), so credit can only mark it
`ELIGIBLE`, `FILTERED_OUT` or `CREDIT_UNAVAILABLE`, never move it, and is never read again for
that episode.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import final

from pmcc.domain.calendar import SessionCalendar
from pmcc.thesis.calendar import decision_at
from pmcc.thesis.config import ThesisConfig
from pmcc.thesis.credit import CreditSeries, CreditState, CreditStatus, credit_state
from pmcc.thesis.episodes import CandidateStatus, Episode, find_episodes
from pmcc.thesis.features import FeatureRow, TrackerInputError, compute_features
from pmcc.thesis.outcomes import Outcome, compute_outcomes


class Eligibility(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    FILTERED_OUT = "FILTERED_OUT"
    CREDIT_UNAVAILABLE = "CREDIT_UNAVAILABLE"


@final
@dataclass(frozen=True, slots=True)
class TrackedEpisode:
    episode: Episode
    credit: CreditState | None  # at the candidate's decision; None without a candidate
    eligibility: Eligibility | None  # None without a candidate


@final
@dataclass(frozen=True, slots=True)
class Tracker:
    config_hash: str
    data_through: date | None  # the last session with both an index close and a VIX close
    features: tuple[FeatureRow, ...]
    outcomes: tuple[Outcome, ...]  # one per feature row, same order
    credit: tuple[CreditState, ...]  # one per feature row, same order
    episodes: tuple[TrackedEpisode, ...]


_ELIGIBILITY = {
    CreditStatus.STABLE: Eligibility.ELIGIBLE,
    CreditStatus.UNSTABLE: Eligibility.FILTERED_OUT,
    CreditStatus.UNAVAILABLE: Eligibility.CREDIT_UNAVAILABLE,
}


def run_tracker(
    index: Mapping[date, float],
    vix: Mapping[date, float],
    credit: CreditSeries,
    calendar: SessionCalendar,
    config: ThesisConfig,
) -> Tracker:
    _check_credit(credit, calendar)
    rows = compute_features(index, vix, calendar, config)
    states = tuple(_state(credit, row.day, calendar, config) for row in rows)
    by_day = {state.day: state for state in states}
    episodes = tuple(_tracked(e, by_day) for e in find_episodes(rows, calendar, config))
    both = [r.day for r in rows if r.index_close is not None and r.vix_points is not None]
    return Tracker(
        config_hash=config.config_hash(),
        data_through=both[-1] if both else None,
        features=rows,
        outcomes=compute_outcomes(rows, calendar, config.forecast.horizon_calendar_days),
        credit=states,
        episodes=episodes,
    )


def _check_credit(credit: CreditSeries, calendar: SessionCalendar) -> None:
    """Credit's business days are counted on the calendar, so every observation must be in it
    (`credit.credit_series` clips a source's points to it)."""
    outside = [
        o.observation_date
        for o in credit.observations
        if not calendar.first_day <= o.observation_date <= calendar.last_day
    ]
    if outside:
        raise TrackerInputError(
            f"credit has {len(outside)} observations outside the calendar "
            f"({calendar.first_day} to {calendar.last_day}), the first on {outside[0]}: build "
            "the series with credit_series, which clips them"
        )


def _state(
    credit: CreditSeries, day: date, calendar: SessionCalendar, config: ThesisConfig
) -> CreditState:
    return credit_state(
        credit, day, decision_at(day, config.decision_time), calendar, config.credit
    )


def _tracked(episode: Episode, credit: Mapping[date, CreditState]) -> TrackedEpisode:
    if episode.status is not CandidateStatus.CANDIDATE or episode.candidate_day is None:
        return TrackedEpisode(episode, None, None)
    state = credit[episode.candidate_day]
    return TrackedEpisode(episode, state, _ELIGIBILITY[state.status])
