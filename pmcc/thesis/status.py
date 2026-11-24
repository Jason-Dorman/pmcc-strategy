"""The tracker's statuses and its dated current state (THESIS-SPEC §9, §10; T2-02).

Pure, on a `Tracker` in memory, as of its last session with both closes (`data_through`):

- **`data_status`:** `CURRENT` when that is the last session decided at `now` (its 20:30 has
  passed, §7.1), `STALE` when it is older, `BLOCKED` when there is none. A changed build time
  over old inputs is never fresh (§10).
- **`expected_by`:** when the next session's run should have published, the day after that
  session at `update_due_time_et` (a scheduled run can start hours late, LD-27). A page read
  after it shows the tracker as stale, so a failed night is never falsely fresh (§9).
- **`signal_status`:** the latest episode's state while `data_through` is inside it (its shock
  through its window's last session): `SEARCHING`, `NO_CANDIDATE`, or its candidate's
  `ELIGIBLE` or `FILTERED_OUT`; `NO_SHOCK` otherwise. Two tracker states the spec's list lacks are
  kept as they are (PO, TD-25): `CREDIT_UNAVAILABLE` (a candidate whose credit can't be read at
  its decision) and `INCOMPLETE_CANDIDATE_SEARCH` (a window session a missing feature left
  untested). Neither is eligible, filtered out, or a confirmed absence of a candidate: their
  `assessment` is `BLOCKED`, with the day, the episode and why. Nothing stops: the tracker still
  updates and publishes.
- **`thesis_status`:** `PAUSED` while K1's rolling assessment is `FAIL`, else `PROVISIONAL`: K2
  and K3 aren't evaluated, so the thesis can't be `ACTIVE` in this milestone.
- **The current state** (§10 component 9, TD-10): `data_through`'s VIX, its 80th-percentile
  shock level over the 252 sessions before and VIX's share of those at or below it, its ratio to
  VIX five sessions earlier, the forecast vol and gap, RV5 and RV20, and credit at the decision.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import final

from pmcc.domain.calendar import SessionCalendar
from pmcc.thesis.calendar import decision_at, last_decided, sessions_after
from pmcc.thesis.config import ThesisConfig
from pmcc.thesis.credit import CreditState
from pmcc.thesis.episodes import CandidateStatus, percentile
from pmcc.thesis.evidence import ConditionStatus, Evidence
from pmcc.thesis.features import FeatureRow
from pmcc.thesis.tracker import Eligibility, TrackedEpisode, Tracker


class DataStatus(StrEnum):
    CURRENT = "CURRENT"
    STALE = "STALE"
    BLOCKED = "BLOCKED"


class SignalStatus(StrEnum):
    NO_SHOCK = "NO_SHOCK"
    SEARCHING = "SEARCHING"
    NO_CANDIDATE = "NO_CANDIDATE"
    FILTERED_OUT = "FILTERED_OUT"
    ELIGIBLE = "ELIGIBLE"
    CREDIT_UNAVAILABLE = "CREDIT_UNAVAILABLE"
    INCOMPLETE_CANDIDATE_SEARCH = "INCOMPLETE_CANDIDATE_SEARCH"


class Assessment(StrEnum):
    OK = "OK"
    BLOCKED = "BLOCKED"


class ThesisStatus(StrEnum):
    PROVISIONAL = "PROVISIONAL"
    PAUSED = "PAUSED"


@final
@dataclass(frozen=True, slots=True)
class Signal:
    day: date | None  # data_through
    status: SignalStatus
    assessment: Assessment
    episode_id: str | None
    shock_day: date | None
    candidate_day: date | None
    window_end: date | None
    reason: str  # why the assessment is blocked; empty otherwise


@final
@dataclass(frozen=True, slots=True)
class CurrentState:
    day: date
    vix_points: float | None
    shock_level_points: float | None  # the 80th percentile of the 252 sessions before
    vix_share_at_or_below: float | None  # of those 252, the share at or below today's VIX
    vix_ratio: float | None  # VIX against VIX five sessions earlier
    forecast_vol: float | None
    forecast_gap_vol: float | None
    rv_short: float | None
    rv_long: float | None
    credit: CreditState | None


_BY_ELIGIBILITY = {
    Eligibility.ELIGIBLE: SignalStatus.ELIGIBLE,
    Eligibility.FILTERED_OUT: SignalStatus.FILTERED_OUT,
    Eligibility.CREDIT_UNAVAILABLE: SignalStatus.CREDIT_UNAVAILABLE,
}
_BY_SEARCH = {
    CandidateStatus.SEARCHING: SignalStatus.SEARCHING,
    CandidateStatus.NO_CANDIDATE: SignalStatus.NO_CANDIDATE,
    CandidateStatus.INCOMPLETE_CANDIDATE_SEARCH: SignalStatus.INCOMPLETE_CANDIDATE_SEARCH,
}
_BLOCKED = frozenset({SignalStatus.CREDIT_UNAVAILABLE, SignalStatus.INCOMPLETE_CANDIDATE_SEARCH})


def data_status(
    tracker: Tracker, calendar: SessionCalendar, config: ThesisConfig, now: datetime
) -> DataStatus:
    if tracker.data_through is None:
        return DataStatus.BLOCKED
    expected = last_decided(calendar, now, config.decision_time)
    return DataStatus.CURRENT if tracker.data_through >= expected else DataStatus.STALE


def expected_by(calendar: SessionCalendar, config: ThesisConfig, now: datetime) -> datetime:
    """When the next session's run should have published: the day after that session."""
    decided = last_decided(calendar, now, config.decision_time)
    (following,) = sessions_after(calendar, decided, 1)
    return decision_at(following + timedelta(days=1), config.update_due_time)


def signal(tracker: Tracker) -> Signal:
    day = tracker.data_through
    active = _active(tracker.episodes, day)
    if day is None or active is None:
        return Signal(day, SignalStatus.NO_SHOCK, Assessment.OK, None, None, None, None, "")
    episode = active.episode
    status = (
        _BY_ELIGIBILITY[active.eligibility]
        if active.eligibility is not None
        else _BY_SEARCH[episode.status]
    )
    blocked = status in _BLOCKED
    return Signal(
        day=day,
        status=status,
        assessment=Assessment.BLOCKED if blocked else Assessment.OK,
        episode_id=episode.episode_id,
        shock_day=episode.shock_day,
        candidate_day=episode.candidate_day,
        window_end=episode.window_end,
        reason=_reason(active) if blocked else "",
    )


def _active(episodes: Sequence[TrackedEpisode], day: date | None) -> TrackedEpisode | None:
    """The latest episode, if `day` is from its shock through its window's last session."""
    if day is None or not episodes:
        return None
    latest = episodes[-1]
    return latest if latest.episode.shock_day <= day <= latest.episode.window_end else None


def _reason(active: TrackedEpisode) -> str:
    if active.eligibility is Eligibility.CREDIT_UNAVAILABLE:
        note = active.credit.note if active.credit is not None else ""
        return f"credit unavailable at {active.episode.candidate_day}'s decision: {note}".rstrip(
            ": "
        )
    return active.episode.note


def thesis_status(found: Evidence) -> ThesisStatus:
    k1 = found.conditions[0]
    return ThesisStatus.PAUSED if k1.status is ConditionStatus.FAIL else ThesisStatus.PROVISIONAL


def current_state(tracker: Tracker, config: ThesisConfig) -> CurrentState | None:
    """`data_through`'s measured state, or None without one."""
    day = tracker.data_through
    if day is None:
        return None
    rows = tracker.features
    i = next(k for k, row in enumerate(rows) if row.day == day)
    row = rows[i]
    level, share = _shock_level(rows, i, config)
    back = i - config.shock.ratio_lookback_sessions
    earlier = rows[back].vix_points if back >= 0 else None
    ratio = row.vix_points / earlier if row.vix_points is not None and earlier else None
    return CurrentState(
        day=day,
        vix_points=row.vix_points,
        shock_level_points=level,
        vix_share_at_or_below=share,
        vix_ratio=ratio,
        forecast_vol=row.forecast_vol,
        forecast_gap_vol=row.forecast_gap_vol,
        rv_short=row.rv_short,
        rv_long=row.rv_long,
        credit=tracker.credit[i],
    )


def _shock_level(
    rows: Sequence[FeatureRow], i: int, config: ThesisConfig
) -> tuple[float | None, float | None]:
    """The shock test's percentile level over the sessions before `i`, and the share of them at
    or below `i`'s VIX; None when a value is missing or the history is short (§5.3)."""
    lookback = config.shock.percentile_lookback_sessions
    vix = rows[i].vix_points
    before = [row.vix_points for row in rows[max(0, i - lookback) : i]]
    if vix is None or len(before) < lookback:
        return None, None
    values = [v for v in before if v is not None]
    if len(values) < lookback:
        return None, None
    share = sum(1 for v in values if v <= vix) / lookback
    return percentile(values, config.shock.percentile_threshold), share
