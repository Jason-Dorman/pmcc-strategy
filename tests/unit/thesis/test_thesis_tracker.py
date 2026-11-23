"""The whole tracker on a synthetic spike (THESIS-SPEC §5), and §14's tests 1 and 3.

A calm year, then a VIX spike with three large returns, then calm again: one shock, and a
candidate six sessions later, when RV5 has fallen under RV20 with VIX still well over the
forecast. Fixtures, never market evidence.
"""

from collections.abc import Callable
from datetime import date, time

import pytest

from pmcc.domain.clock import at_et
from pmcc.thesis.credit import CreditObservation, CreditSeries
from pmcc.thesis.episodes import CandidateStatus
from pmcc.thesis.features import TrackerInputError
from pmcc.thesis.outcomes import OutcomeStatus
from pmcc.thesis.tracker import Eligibility, Tracker, run_tracker
from tests.fakes.thesis_tracker import CAL, CONFIG, closes, credit, sessions, weekdays

DAYS = sessions(date(2014, 1, 2), 360)
SHOCK = 300
CANDIDATE = SHOCK + 6
SOURCE_DAYS = weekdays(date(2014, 1, 2), DAYS[-1])


def _return(i: int) -> float:
    big = SHOCK - 1 <= i <= SHOCK + 1
    size = 0.03 if big else 0.006
    return size if i % 2 else -size


def _vix(i: int) -> float:
    return 13.0 + (i % 5) * 0.1 if i < SHOCK else max(18.0, 30.0 - (i - SHOCK) * 0.6)


INDEX = closes(DAYS, _return)
VIX = {d: _vix(i) for i, d in enumerate(DAYS)}


def _credit(bps: Callable[[int], float] = lambda i: 350.0) -> CreditSeries:
    return credit(SOURCE_DAYS, bps)


def _run(
    index: dict[date, float] = INDEX,
    vix: dict[date, float] = VIX,
    series: CreditSeries | None = None,
) -> Tracker:
    return run_tracker(index, vix, _credit() if series is None else series, CAL, CONFIG)


def test_tracker_finds_the_spikes_episode_and_its_eligible_candidate() -> None:
    tracker = _run()
    (tracked,) = tracker.episodes
    assert tracked.episode.shock_day == DAYS[SHOCK]
    assert (tracked.episode.status, tracked.episode.candidate_day) == (
        CandidateStatus.CANDIDATE,
        DAYS[CANDIDATE],
    )
    assert tracked.eligibility is Eligibility.ELIGIBLE
    assert tracked.credit is not None
    assert tracked.credit.day == DAYS[CANDIDATE]
    assert tracker.data_through == DAYS[-1]
    assert len(tracker.features) == len(tracker.outcomes) == len(tracker.credit) == len(DAYS)
    assert tracker.config_hash == CONFIG.config_hash()


def test_tracker_outcomes_are_pending_at_the_end_and_matured_before_it() -> None:
    tracker = _run()
    assert tracker.outcomes[-1].status is OutcomeStatus.PENDING
    assert tracker.outcomes[CANDIDATE].status is OutcomeStatus.MATURED


def _altered_after(cut: int) -> tuple[dict[date, float], dict[date, float], CreditSeries]:
    late = DAYS[cut]
    index = {d: v * (1.5 if d > late else 1.0) for d, v in INDEX.items()}
    vix = {d: v + (25.0 if d > late else 0.0) for d, v in VIX.items()}
    series = _credit(lambda i: 900.0 if SOURCE_DAYS[i] > late else 350.0)
    return index, vix, series


@pytest.mark.parametrize("cut", [SHOCK + 3, CANDIDATE, CANDIDATE + 30])
def test_f14_1_data_after_t_changes_nothing_known_at_t(cut: int) -> None:
    base, altered = _run(), _run(*_altered_after(cut))
    late = DAYS[cut]
    assert altered.features[cut + 1] != base.features[cut + 1]  # the alteration bites
    assert altered.features[: cut + 1] == base.features[: cut + 1]
    assert altered.credit[: cut + 1] == base.credit[: cut + 1]
    settled = [
        e for e in base.episodes if (e.episode.candidate_day or e.episode.window_end) <= late
    ]
    assert settled == [e for e in altered.episodes if e in settled]
    assert [e.episode.shock_day for e in altered.episodes][: len(settled)] == [
        e.episode.shock_day for e in settled
    ]
    matured = [o for o in base.outcomes if o.maturity_day is not None and o.maturity_day <= late]
    assert matured == [o for o in altered.outcomes if o in matured]
    assert len(matured) == len(
        [o for o in altered.outcomes if o.maturity_day is not None and o.maturity_day <= late]
    )


@pytest.mark.parametrize("cut", [SHOCK + 3, CANDIDATE])
def test_f14_1_a_run_on_data_through_t_sees_the_same_features(cut: int) -> None:
    late = DAYS[cut]
    through = _run(
        {d: v for d, v in INDEX.items() if d <= late},
        {d: v for d, v in VIX.items() if d <= late},
        CreditSeries([o for o in _credit().observations if o.observation_date <= late]),
    )
    full = _run()
    assert through.features == full.features[: cut + 1]
    assert through.credit == full.credit[: cut + 1]
    (episode,) = through.episodes
    expected = CandidateStatus.SEARCHING if cut < CANDIDATE else CandidateStatus.CANDIDATE
    assert episode.episode.status is expected


def test_f14_3_credit_never_moves_the_candidate() -> None:
    stable = _run()
    rising = _run(series=_credit(lambda i: 300.0 + 3.0 * i))  # +60 bps over 20: unstable
    missing = _run(series=CreditSeries([]))
    days = {t.episodes[0].episode.candidate_day for t in (stable, rising, missing)}
    assert days == {DAYS[CANDIDATE]}
    assert [t.episodes[0].eligibility for t in (stable, rising, missing)] == [
        Eligibility.ELIGIBLE,
        Eligibility.FILTERED_OUT,
        Eligibility.CREDIT_UNAVAILABLE,
    ]
    assert rising.features == stable.features


def test_tracker_refuses_credit_outside_the_calendar_naming_it() -> None:
    days = sessions(date(2014, 1, 2), 30)
    early = CreditSeries(
        [CreditObservation(date(2013, 12, 30), 400.0, at_et(date(2014, 1, 2), time(20, 30)))]
    )
    with pytest.raises(TrackerInputError, match="2013-12-30"):
        run_tracker(closes(days, lambda _i: 0.01), {d: 15.0 for d in days}, early, CAL, CONFIG)
