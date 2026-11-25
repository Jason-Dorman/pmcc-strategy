"""Two exploratory rule versions, beside the original spike-based one (PO, TD-33).

Both are read at every session, with no VIX spike and no search window before them:

- **A, pricing gap + stable credit:** the forecast gap at or above its minimum, and credit stable.
- **B, also wait for calmer markets:** A's two, and RV5 below RV20 and no higher than three sessions
  earlier. B differs from A only there.

Each condition is the tracker's own (`episodes.checks`, §5.4; `credit.credit_state`, §5.5), so no
threshold, forecast, publication lag or missing-data rule changes. Nothing of the original version
(episodes, candidates, cohorts, K1-K3) is read or written here.

- **A session's state** is met, not met or unknown. A condition known to fail makes it not met
  whatever else is missing; otherwise a missing condition makes it unknown, never not met.
- **A stretch** is an uninterrupted run of sessions on which every condition is met. Its
  observation is its first session. It is confirmed only when the session before is known not to
  meet the conditions: after an unknown session (or with none before) the run may have started
  earlier, so it is counted as unconfirmed and never as a new start.
- **Counting views**, chosen from the confirmed starts alone, over the whole history, before any
  outcome is read: every start; ten-session spacing (each retained start at least that many sessions
  after the last retained); thirty-calendar-day spacing (the same, in days). A discarded start is
  dropped, never moved to a later day of its stretch. These are ways of counting, not trades.
- **Outcomes** (§5.2, unchanged): a view's statistics read its completed outcomes only. A pending or
  incomplete one is still counted as selected.
- **K1, revised:** for each version apart, the mean variance premium over the latest 30 completed
  observations of its thirty-day selection, dates chosen first. Below 30 it is descriptive only.
"""

import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import final

from pmcc.thesis.config import ThesisConfig
from pmcc.thesis.credit import CreditState, CreditStatus
from pmcc.thesis.episodes import checks
from pmcc.thesis.evidence import Condition, ConditionStatus
from pmcc.thesis.features import FeatureRow
from pmcc.thesis.outcomes import Outcome, OutcomeStatus
from pmcc.thesis.tracker import Tracker


class VersionKey(StrEnum):
    A = "A"
    B = "B"


class Check(StrEnum):
    GAP = "gap"
    CREDIT = "credit"
    SWINGS_BELOW = "swings_below_long"
    SWINGS_NOT_RISING = "swings_not_rising"


class State(StrEnum):
    MET = "MET"
    NOT_MET = "NOT_MET"
    UNKNOWN = "UNKNOWN"


class ViewKey(StrEnum):
    ALL = "all"
    TEN_SESSION = "ten_session"
    THIRTY_DAY = "thirty_day"


NAMES = {
    VersionKey.A: "Pricing gap + stable credit",
    VersionKey.B: "Also wait for calmer markets",
}
CHECKS: dict[VersionKey, tuple[Check, ...]] = {
    VersionKey.A: (Check.GAP, Check.CREDIT),
    VersionKey.B: (Check.GAP, Check.CREDIT, Check.SWINGS_BELOW, Check.SWINGS_NOT_RISING),
}

type Verdicts = dict[Check, bool | None]


@final
@dataclass(frozen=True, slots=True)
class Stretch:
    """A run of sessions meeting a version's conditions, as indices into the tracker's rows."""

    start: int
    end: int
    confirmed: bool

    @property
    def sessions(self) -> int:
        return self.end - self.start + 1


@final
@dataclass(frozen=True, slots=True)
class Observation:
    """A confirmed stretch's first session, its outcome, and the views that retain it."""

    day: date
    stretch_end: date
    stretch_sessions: int
    ten_session: bool
    thirty_day: bool
    vix_points: float | None
    forecast_gap_vol: float | None
    outcome: OutcomeStatus
    outcome_end: date | None
    realized_vol: float | None
    vol_gap: float | None  # VIX minus the realized vol that followed, decimal; completed only
    premium: float | None  # realized_variance_premium; completed only


@final
@dataclass(frozen=True, slots=True)
class View:
    key: ViewKey
    selected: int
    completed: int
    pending: int
    incomplete: int  # a return missing, or the window past the calendar
    mean_gap: float | None
    median_gap: float | None
    worst_gap: float | None
    worst_day: date | None
    mean_premium: float | None


@final
@dataclass(frozen=True, slots=True)
class Latest:
    """A version's reading at the last session with data."""

    state: State
    checks: Verdicts
    stretch_start: date | None  # the open stretch's first session, when the state is met


@final
@dataclass(frozen=True, slots=True)
class Version:
    key: VersionKey
    name: str
    qualifying_days: int
    unknown_days: int  # within the analysis period
    unconfirmed_stretches: int
    latest: Latest | None
    views: tuple[View, View, View]
    observations: tuple[Observation, ...]
    k1: Condition


@final
@dataclass(frozen=True, slots=True)
class Comparison:
    methodology_version: str
    analysis_start: date | None  # the first session every condition of both could be read
    analysis_end: date | None
    spacing_sessions: int
    spacing_calendar_days: int
    versions: tuple[Version, Version]


def compare(tracker: Tracker, config: ThesisConfig) -> Comparison:
    rows = tracker.features
    verdicts = [
        session_verdicts(rows, i, credit, config) for i, credit in enumerate(tracker.credit)
    ]
    first = next((i for i, v in enumerate(verdicts) if None not in v.values()), None)
    rules = config.comparison
    return Comparison(
        methodology_version=rules.methodology_version,
        analysis_start=None if first is None else rows[first].day,
        analysis_end=tracker.data_through,
        spacing_sessions=rules.spacing_sessions,
        spacing_calendar_days=rules.spacing_calendar_days,
        versions=(
            _version(VersionKey.A, tracker, verdicts, first, config),
            _version(VersionKey.B, tracker, verdicts, first, config),
        ),
    )


# --- a session's state -----------------------------------------------------------------------


def session_verdicts(
    rows: Sequence[FeatureRow], i: int, credit: CreditState, config: ThesisConfig
) -> Verdicts:
    """Every condition at row `i`, by the tracker's own checks; None where an input is missing."""
    calm = checks(rows, i, config.normalization)
    known = credit.status is not CreditStatus.UNAVAILABLE
    stable = credit.status is CreditStatus.STABLE if known else None
    return {
        Check.GAP: calm.gap_ok,
        Check.CREDIT: stable,
        Check.SWINGS_BELOW: calm.swings_below_long,
        Check.SWINGS_NOT_RISING: calm.swings_not_rising,
    }


def state_of(key: VersionKey, verdicts: Verdicts) -> State:
    mine = [verdicts[c] for c in CHECKS[key]]
    if any(v is False for v in mine):
        return State.NOT_MET
    return State.UNKNOWN if any(v is None for v in mine) else State.MET


# --- stretches and views ---------------------------------------------------------------------


def stretches(states: Sequence[State]) -> tuple[Stretch, ...]:
    """Each run of met sessions; confirmed when the session before is known not to be met."""
    found: list[Stretch] = []
    for i, state in enumerate(states):
        if state is not State.MET:
            continue
        if found and found[-1].end == i - 1:
            found[-1] = Stretch(found[-1].start, i, found[-1].confirmed)
        else:
            found.append(Stretch(i, i, i > 0 and states[i - 1] is State.NOT_MET))
    return tuple(found)


def spaced(starts: Sequence[int], far_enough: Callable[[int, int], bool]) -> tuple[int, ...]:
    """The first start, then each far enough after the last one kept, in order."""
    kept: list[int] = []
    for start in starts:
        if not kept or far_enough(kept[-1], start):
            kept.append(start)
    return tuple(kept)


def _version(
    key: VersionKey,
    tracker: Tracker,
    verdicts: Sequence[Verdicts],
    first: int | None,
    config: ThesisConfig,
) -> Version:
    rows, rules = tracker.features, config.comparison
    states = [state_of(key, v) for v in verdicts]
    runs = stretches(states)
    confirmed = [s for s in runs if s.confirmed]
    starts = [s.start for s in confirmed]
    # The dates are chosen here, before any outcome is read.
    ten = frozenset(spaced(starts, lambda a, b: b - a >= rules.spacing_sessions))
    thirty = frozenset(
        spaced(starts, lambda a, b: (rows[b].day - rows[a].day).days >= rules.spacing_calendar_days)
    )
    observed = tuple(
        _observation(s, rows, tracker.outcomes[s.start], s.start in ten, s.start in thirty)
        for s in confirmed
    )
    period = states[first:] if first is not None else []
    return Version(
        key=key,
        name=NAMES[key],
        qualifying_days=sum(1 for s in states if s is State.MET),
        unknown_days=sum(1 for s in period if s is State.UNKNOWN),
        unconfirmed_stretches=len(runs) - len(confirmed),
        latest=_latest(key, tracker, verdicts, states, runs),
        views=(
            view(ViewKey.ALL, observed),
            view(ViewKey.TEN_SESSION, [o for o in observed if o.ten_session]),
            view(ViewKey.THIRTY_DAY, [o for o in observed if o.thirty_day]),
        ),
        observations=observed,
        k1=revised_k1(key, [o for o in observed if o.thirty_day], tracker.data_through, config),
    )


def _observation(
    stretch: Stretch, rows: Sequence[FeatureRow], outcome: Outcome, ten: bool, thirty: bool
) -> Observation:
    row = rows[stretch.start]
    realized, vix = outcome.realized_vol, row.vix_decimal
    matured = outcome.status is OutcomeStatus.MATURED
    gap = vix - realized if matured and vix is not None and realized is not None else None
    return Observation(
        day=row.day,
        stretch_end=rows[stretch.end].day,
        stretch_sessions=stretch.sessions,
        ten_session=ten,
        thirty_day=thirty,
        vix_points=row.vix_points,
        forecast_gap_vol=row.forecast_gap_vol,
        outcome=outcome.status,
        outcome_end=outcome.maturity_day,
        realized_vol=realized,
        vol_gap=gap,
        premium=outcome.realized_variance_premium if matured else None,
    )


def view(key: ViewKey, observed: Sequence[Observation]) -> View:
    """A counting view's statistics, over its completed outcomes only."""
    done = [(o.vol_gap, o) for o in observed if o.vol_gap is not None]
    premiums = [o.premium for _, o in done if o.premium is not None]
    worst = min(done, key=lambda pair: (pair[0], pair[1].day), default=None)
    pending = sum(1 for o in observed if o.outcome is OutcomeStatus.PENDING)
    return View(
        key=key,
        selected=len(observed),
        completed=len(done),
        pending=pending,
        incomplete=len(observed) - len(done) - pending,
        mean_gap=statistics.fmean(g for g, _ in done) if done else None,
        median_gap=statistics.median(g for g, _ in done) if done else None,
        worst_gap=None if worst is None else worst[0],
        worst_day=None if worst is None else worst[1].day,
        mean_premium=statistics.fmean(premiums) if premiums else None,
    )


def _latest(
    key: VersionKey,
    tracker: Tracker,
    verdicts: Sequence[Verdicts],
    states: Sequence[State],
    runs: Sequence[Stretch],
) -> Latest | None:
    if tracker.data_through is None:
        return None
    i = next(k for k, row in enumerate(tracker.features) if row.day == tracker.data_through)
    run = next((s for s in runs if s.start <= i <= s.end), None)
    return Latest(
        state=states[i],
        checks={c: verdicts[i][c] for c in CHECKS[key]},
        stretch_start=None if run is None else tracker.features[run.start].day,
    )


# --- K1, revised -----------------------------------------------------------------------------


def revised_k1(
    key: VersionKey, selected: Sequence[Observation], assessed: date | None, config: ThesisConfig
) -> Condition:
    """The revised first condition for one version, from its thirty-day selection."""
    window = config.comparison.kill_window_observations
    days = config.comparison.spacing_calendar_days
    done = [o.premium for o in selected if o.premium is not None]
    latest = done[-window:]
    value = statistics.fmean(latest) if latest else None
    return Condition(
        condition_id=f"K1-{key.value}",
        name="The observed variance premium disappears",
        formula=(
            f"mean realized_variance_premium over the latest {window} completed observations of "
            f"version {key.value}'s {days}-calendar-day-spaced selection, the dates selected first"
        ),
        threshold="wrong if <= 0",
        minimum_sample=f"{window} completed observations",
        required=window,
        status=_k1_status(value, len(done), window),
        value=value,
        sample=len(done),
        assessed_on=assessed,
        note="A revised observation definition (TD-33); the original version's K1 is kept apart.",
    )


def _k1_status(value: float | None, sample: int, window: int) -> ConditionStatus:
    if value is None or sample < window:
        return ConditionStatus.INSUFFICIENT_DATA
    return ConditionStatus.FAIL if value <= 0 else ConditionStatus.PASS
