"""The tracker's evidence and statuses (T2-02): K1's sample gate (spec §14 test 12), the
preliminary cohorts and their plain-language statements (TD-23), R5's cost from the config
(TD-21), and the status fields (TD-25). Trackers are built by hand: fixtures, never market data."""

from datetime import UTC, date, datetime, time

import pytest

from pmcc.domain.clock import at_et
from pmcc.thesis.credit import CreditState, CreditStatus
from pmcc.thesis.episodes import CandidateStatus, Episode
from pmcc.thesis.evidence import (
    EVIDENCE_STATUS,
    NEITHER_GROUP,
    NO_COMPARISON,
    NOT_EVALUATED,
    ConditionStatus,
    cost_note,
    evidence,
)
from pmcc.thesis.features import FeatureRow
from pmcc.thesis.outcomes import Outcome, OutcomeStatus
from pmcc.thesis.status import (
    Assessment,
    DataStatus,
    SignalStatus,
    ThesisStatus,
    current_state,
    data_status,
    expected_by,
    signal,
    thesis_status,
)
from pmcc.thesis.tracker import Eligibility, TrackedEpisode, Tracker
from tests.fakes.thesis_tracker import CAL, CONFIG, sessions

DAYS = sessions(date(2024, 1, 2), 400)
DECIDED = datetime(2024, 1, 2, 1, 30, tzinfo=UTC)

type Spec = tuple[int, Eligibility | None, float | None]  # day index, eligibility, premium


def _row(day: date, vix: float | None) -> FeatureRow:
    return FeatureRow(
        day=day,
        index_close=4000.0,
        vix_points=vix,
        log_return=0.0,
        valid_returns=300,
        ewma_variance=1e-4,
        rv_short=0.15,
        rv_long=0.18,
        horizon_closes=21,
        implied_total_variance=None,
        forecast_total_variance=None,
        forecast_vol=0.17,
        forecast_gap_vol=0.03,
        forecast_gap_variance=None,
        warm=True,
    )


def _outcome(day: date, premium: float | None) -> Outcome:
    if premium is None:
        return Outcome(day, None, OutcomeStatus.PENDING, None, None, None, None)
    return Outcome(day, None, OutcomeStatus.MATURED, 0.002, 0.15, premium, 0.0)


def _credit(day: date, status: CreditStatus = CreditStatus.STABLE, note: str = "") -> CreditState:
    level = None if status is CreditStatus.UNAVAILABLE else 300.0
    return CreditState(day, DECIDED, status, None, level, 0.0, 0.0, None, None, None, 0, note)


def _episode(shock: int, status: CandidateStatus, candidate: int | None, note: str = "") -> Episode:
    window = tuple(DAYS[shock + 1 : shock + 11])
    day = DAYS[candidate] if candidate is not None else None
    return Episode(f"v1.0:{DAYS[shock]}", DAYS[shock], window, status, day, note)


def _tracker(
    specs: list[Spec],
    premiums: float | None = 0.001,
    through: int = 399,
    episodes: list[TrackedEpisode] | None = None,
) -> Tracker:
    """Rows to `through`; every session's outcome matured at `premiums` (None: pending), except
    each spec's candidate day, which gets its own premium and episode."""
    days = DAYS[: through + 1]
    own = {DAYS[i]: premium for i, _, premium in specs}
    outcomes = [_outcome(d, own.get(d, premiums) if d in own else premiums) for d in days]
    found = episodes if episodes is not None else [_candidate(i, e) for i, e, _ in specs]
    return Tracker(
        config_hash="test",
        data_through=days[-1],
        features=tuple(_row(d, 20.0) for d in days),
        outcomes=tuple(outcomes),
        credit=tuple(_credit(d) for d in days),
        episodes=tuple(found),
    )


def _candidate(i: int, eligibility: Eligibility | None) -> TrackedEpisode:
    episode = _episode(i - 1, CandidateStatus.CANDIDATE, i)
    return TrackedEpisode(episode, _credit(DAYS[i]), eligibility)


def _stable(count: int, premium: float, start: int = 20, step: int = 12) -> list[Spec]:
    return [(start + k * step, Eligibility.ELIGIBLE, premium) for k in range(count)]


# --- K1's sample gate (spec §14 test 12) -----------------------------------------------------


def test_t2_02_k1_below_30_is_insufficient_never_pass_even_if_positive() -> None:
    k1 = evidence(_tracker(_stable(29, 0.01)), CONFIG).conditions[0]

    assert k1.status is ConditionStatus.INSUFFICIENT_DATA
    assert k1.sample == 29
    assert k1.value == pytest.approx(0.01)  # the provisional value, still shown
    assert k1.assessed_on == DAYS[399]


def test_t2_02_k1_with_no_episodes_is_insufficient_without_a_value() -> None:
    k1 = evidence(_tracker([]), CONFIG).conditions[0]
    assert k1.status is ConditionStatus.INSUFFICIENT_DATA
    assert (k1.sample, k1.value) == (0, None)


@pytest.mark.parametrize(("premium", "status"), [(0.002, "PASS"), (0.0, "FAIL"), (-0.001, "FAIL")])
def test_t2_02_k1_at_30_passes_above_zero_and_fails_at_or_below(
    premium: float, status: str
) -> None:
    k1 = evidence(_tracker(_stable(30, premium)), CONFIG).conditions[0]
    assert k1.status is ConditionStatus(status)


def test_t2_02_k1_reads_only_the_latest_30() -> None:
    old_loss = [(8, Eligibility.ELIGIBLE, -1.0)]  # the 31st most recent: rolled out
    k1 = evidence(_tracker(old_loss + _stable(30, 0.002)), CONFIG).conditions[0]

    assert k1.sample == 31
    assert k1.value == pytest.approx(0.002)
    assert k1.status is ConditionStatus.PASS
    assert "rolling" in k1.note


def test_t2_02_k1_counts_only_matured_stable_candidates() -> None:
    specs: list[Spec] = [
        *_stable(29, 0.01),
        (380, Eligibility.ELIGIBLE, None),  # pending: counts nowhere
        (392, Eligibility.FILTERED_OUT, 0.01),
        (396, Eligibility.CREDIT_UNAVAILABLE, 0.01),
    ]
    k1 = evidence(_tracker(specs), CONFIG).conditions[0]
    assert k1.sample == 29
    assert k1.status is ConditionStatus.INSUFFICIENT_DATA


def test_t2_02_k2_and_k3_are_defined_but_not_evaluated() -> None:
    _, k2, k3 = evidence(_tracker([]), CONFIG).conditions
    for k in (k2, k3):
        assert k.status is ConditionStatus.NOT_EVALUATED
        assert (k.value, k.sample, k.assessed_on) == (None, None, None)
        assert k.note == NOT_EVALUATED
        assert k.formula
        assert k.threshold
    assert k2.minimum_sample == "30 resolved trades"
    assert k3.minimum_sample == "at least 20 completed events per disjoint cohort"


# --- the preliminary cohorts (TD-23) ---------------------------------------------------------


def test_td_23_cohorts_split_candidates_by_their_credit() -> None:
    specs: list[Spec] = [
        (20, Eligibility.ELIGIBLE, 0.004),
        (40, Eligibility.ELIGIBLE, 0.002),
        (60, Eligibility.FILTERED_OUT, -0.001),
        (80, Eligibility.CREDIT_UNAVAILABLE, 0.003),
        (100, Eligibility.ELIGIBLE, None),  # pending
    ]
    found = evidence(_tracker(specs), CONFIG).cohorts

    assert (found.candidates.count, found.stable.count, found.unstable.count) == (4, 2, 1)
    assert found.credit_unavailable.count == 1
    assert found.stable.mean_premium == pytest.approx(0.003)
    assert found.stable.median_premium == pytest.approx(0.003)
    assert (found.stable.first_day, found.stable.last_day) == (DAYS[20], DAYS[40])
    assert found.stable.mean_start_vix == pytest.approx(20.0)
    assert found.stable.mean_vol_gap == pytest.approx(0.05)  # VIX 20% against 15% realized
    assert found.stable.mean_overstatement == pytest.approx(0.25)
    assert found.all_sessions.count == 399  # every session but the pending one


def test_td_23_statements_compare_both_groups_and_say_the_sample_is_small() -> None:
    specs: list[Spec] = [(20, Eligibility.ELIGIBLE, 0.004), (60, Eligibility.FILTERED_OUT, -0.001)]
    text = evidence(_tracker(specs), CONFIG).statements

    assert "The average premium was positive in the 1 available stable-credit episode." in text
    assert "The average premium was negative in the 1 available unstable-credit episode." in text
    assert NO_COMPARISON not in text
    assert any("does not establish a reliable edge" in s for s in text)


def test_td_23_one_group_missing_makes_the_comparison_unavailable() -> None:
    text = evidence(_tracker([(20, Eligibility.ELIGIBLE, 0.004)]), CONFIG).statements
    assert NO_COMPARISON in text


def test_td_23_neither_credit_group_matured_is_said_directly() -> None:
    specs: list[Spec] = [(20, Eligibility.CREDIT_UNAVAILABLE, 0.004)]
    text = evidence(_tracker(specs), CONFIG).statements
    assert NEITHER_GROUP in text
    assert NO_COMPARISON in text
    assert any(s.startswith("1 matured candidate has no credit data at its decision") for s in text)
    one = evidence(_tracker([(20, Eligibility.ELIGIBLE, 0.004)]), CONFIG).statements
    assert NEITHER_GROUP not in one


def test_td_23_nothing_matured_is_said_directly() -> None:
    text = evidence(_tracker([], premiums=None), CONFIG).statements
    assert text[0].startswith("No session's 30-day outcome has matured yet")
    assert "No candidate episode's outcome has matured yet." in text


def test_td_23_the_validation_target_never_changes_the_status() -> None:
    specs = _stable(20, 0.01) + [(21 + k * 12, Eligibility.FILTERED_OUT, 0.01) for k in range(20)]
    found = evidence(_tracker(specs), CONFIG)

    assert (found.cohorts.stable.count, found.cohorts.unstable.count) == (20, 20)
    assert found.validation_target_per_cohort == 20
    assert found.evidence_status == EVIDENCE_STATUS


# --- R5's cost (TD-21) -----------------------------------------------------------------------


def test_td_21_r5_cost_is_reproduced_from_the_dated_sample() -> None:
    note = cost_note(CONFIG)
    fee = 2 * 2.00 / 100  # two transactions a leg, in index points

    assert note.sample_session == date(2026, 11, 20)
    assert note.puts.legs == 20
    assert note.puts.base_share == pytest.approx(0.0971 + fee / 106.225)
    assert note.puts.stressed_share == pytest.approx(1.5 * 0.0971 + 2 * fee / 106.225)
    assert note.calls.base_share == pytest.approx(0.1961 + fee / 35.55)
    assert note.calls.stressed_share == pytest.approx(1.5 * 0.1961 + 2 * fee / 35.55)
    assert "skipped" in note.spec_condor


# --- the statuses (TD-25) --------------------------------------------------------------------


def _with(episode: TrackedEpisode, through: int) -> Tracker:
    return _tracker([], through=through, episodes=[episode])


def test_td_25_no_episode_in_progress_is_no_shock() -> None:
    assert signal(_tracker([])).status is SignalStatus.NO_SHOCK
    done = TrackedEpisode(_episode(100, CandidateStatus.NO_CANDIDATE, None), None, None)
    assert signal(_with(done, 200)).status is SignalStatus.NO_SHOCK  # its window ended


@pytest.mark.parametrize(
    ("status", "candidate", "eligibility", "expected"),
    [
        (CandidateStatus.SEARCHING, None, None, SignalStatus.SEARCHING),
        (CandidateStatus.NO_CANDIDATE, None, None, SignalStatus.NO_CANDIDATE),
        (CandidateStatus.CANDIDATE, 103, Eligibility.ELIGIBLE, SignalStatus.ELIGIBLE),
        (CandidateStatus.CANDIDATE, 103, Eligibility.FILTERED_OUT, SignalStatus.FILTERED_OUT),
    ],
)
def test_td_25_an_episode_in_progress_gives_its_state(
    status: CandidateStatus,
    candidate: int | None,
    eligibility: Eligibility | None,
    expected: SignalStatus,
) -> None:
    credit = _credit(DAYS[candidate]) if candidate is not None else None
    found = signal(
        _with(TrackedEpisode(_episode(100, status, candidate), credit, eligibility), 110)
    )

    assert found.status is expected
    assert found.assessment is Assessment.OK
    assert found.episode_id == f"v1.0:{DAYS[100]}"
    assert found.reason == ""


def test_td_25_credit_unavailable_blocks_the_assessment_with_its_reason() -> None:
    credit = _credit(DAYS[103], CreditStatus.UNAVAILABLE, "the latest observation is 5 days old")
    episode = TrackedEpisode(
        _episode(100, CandidateStatus.CANDIDATE, 103), credit, Eligibility.CREDIT_UNAVAILABLE
    )
    found = signal(_with(episode, 105))

    assert found.status is SignalStatus.CREDIT_UNAVAILABLE
    assert found.assessment is Assessment.BLOCKED
    assert found.candidate_day == DAYS[103]
    assert "5 days old" in found.reason


def test_td_25_an_incomplete_search_blocks_the_assessment() -> None:
    note = f"{DAYS[102]} could not be tested: a feature is missing"
    episode = _episode(100, CandidateStatus.INCOMPLETE_CANDIDATE_SEARCH, None, note)
    found = signal(_with(TrackedEpisode(episode, None, None), 104))

    assert found.status is SignalStatus.INCOMPLETE_CANDIDATE_SEARCH
    assert found.assessment is Assessment.BLOCKED
    assert found.reason == note


def test_td_28_data_status_is_current_only_at_the_last_decided_session() -> None:
    tracker = _tracker([], through=50)

    # Through the session after it, until that one's own 20:30 decision.
    assert data_status(tracker, CAL, CONFIG, at_et(DAYS[50], time(20, 30))) is DataStatus.CURRENT
    assert data_status(tracker, CAL, CONFIG, at_et(DAYS[51], time(20, 29))) is DataStatus.CURRENT
    assert data_status(tracker, CAL, CONFIG, at_et(DAYS[51], time(20, 30))) is DataStatus.STALE


def test_td_28_the_next_file_is_due_at_noon_the_day_after_the_next_session() -> None:
    friday, monday = date(2026, 11, 20), date(2026, 11, 23)
    night = at_et(friday, time(23, 17))
    assert expected_by(CAL, CONFIG, night) == at_et(date(2026, 11, 24), time(12, 0))
    # Monday afternoon, before Monday's decision: still Monday's file that is due.
    assert expected_by(CAL, CONFIG, at_et(monday, time(15, 0))) == at_et(
        date(2026, 11, 24), time(12, 0)
    )


def test_t2_02_thesis_status_pauses_only_on_k1_failing() -> None:
    assert thesis_status(evidence(_tracker(_stable(30, -0.001)), CONFIG)) is ThesisStatus.PAUSED
    assert thesis_status(evidence(_tracker(_stable(29, -0.001)), CONFIG)) is (
        ThesisStatus.PROVISIONAL
    )


def test_t2_02_current_state_reads_the_shock_level_over_the_prior_252() -> None:
    state = current_state(_tracker([], through=300), CONFIG)

    assert state is not None
    assert state.day == DAYS[300]
    assert state.shock_level_points == pytest.approx(20.0)
    assert state.vix_share_at_or_below == pytest.approx(1.0)
    assert state.vix_ratio == pytest.approx(1.0)
    assert state.credit is not None


def test_t2_02_current_state_without_252_prior_sessions_has_no_level() -> None:
    state = current_state(_tracker([], through=100), CONFIG)
    assert state is not None
    assert (state.shock_level_points, state.vix_share_at_or_below) == (None, None)
