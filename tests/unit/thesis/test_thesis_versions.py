"""The two exploratory versions (TD-33): a session's state, stretches and their confirmed starts,
the spacing boundaries, pending outcomes, the latest reading, the revised K1, and the original
version left untouched. Rows are built by hand: fixtures, never market data."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta

import pytest

from pmcc.thesis.credit import CreditState, CreditStatus
from pmcc.thesis.evidence import ConditionStatus, evidence
from pmcc.thesis.features import FeatureRow
from pmcc.thesis.outcomes import Outcome, OutcomeStatus
from pmcc.thesis.tracker import Tracker
from pmcc.thesis.versions import (
    Check,
    Comparison,
    State,
    Stretch,
    Version,
    VersionKey,
    ViewKey,
    compare,
    spaced,
    state_of,
    stretches,
)
from tests.fakes.thesis_tracker import CONFIG, sessions, spike_thesis

M, N, U = State.MET, State.NOT_MET, State.UNKNOWN
DAYS = sessions(date(2024, 1, 2), 320)
DECIDED = datetime(2024, 1, 2, 1, 30, tzinfo=UTC)
STABLE, UNSTABLE, MISSING = CreditStatus.STABLE, CreditStatus.UNSTABLE, CreditStatus.UNAVAILABLE


def _row(day: date, gap: float | None) -> FeatureRow:
    return FeatureRow(
        day=day, index_close=4000.0, vix_points=20.0, log_return=0.0, valid_returns=300,
        ewma_variance=1e-4, rv_short=0.10, rv_long=0.20, horizon_closes=21,
        implied_total_variance=None, forecast_total_variance=None, forecast_vol=0.15,
        forecast_gap_vol=gap, forecast_gap_variance=None, warm=True,
    )  # fmt: skip


def _credit(day: date, status: CreditStatus) -> CreditState:
    return CreditState(day, DECIDED, status, None, 300.0, 0.0, 0.0, None, None, None, 0, "")


def _matured(day: date, realized: float = 0.15, premium: float = 0.001) -> Outcome:
    return Outcome(day, day + timedelta(days=30), OutcomeStatus.MATURED, 0.002, realized, premium,
                   0.0)  # fmt: skip


def _tracker(
    met: set[int],
    count: int = 60,
    gaps: dict[int, float | None] | None = None,
    credit: dict[int, CreditStatus] | None = None,
    outcomes: dict[int, Outcome] | None = None,
    features: dict[int, dict[str, float | None]] | None = None,
) -> Tracker:
    """Sessions on which A's and B's conditions hold at `met`; elsewhere the gap is too small."""
    days = DAYS[:count]
    levels: dict[int, float | None] = {i: 0.05 if i in met else 0.0 for i in range(count)}
    levels |= gaps or {}
    rows = [_row(d, levels[i]) for i, d in enumerate(days)]
    for i, changes in (features or {}).items():
        rows[i] = replace(rows[i], **changes)  # pyright: ignore[reportArgumentType]
    return Tracker(
        config_hash="test",
        data_through=days[-1],
        features=tuple(rows),
        outcomes=tuple((outcomes or {}).get(i, _matured(d)) for i, d in enumerate(days)),
        credit=tuple(_credit(d, (credit or {}).get(i, STABLE)) for i, d in enumerate(days)),
        episodes=(),
    )


def _versions(tracker: Tracker) -> tuple[Version, Version]:
    return compare(tracker, CONFIG).versions


def _starts(version: Version) -> list[date]:
    return [o.day for o in version.observations]


# --- a session's state -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("gap", "credit", "expected"),
    [
        (True, True, M),
        (False, True, N),
        (True, False, N),
        (None, True, U),
        (True, None, U),
        (None, None, U),
        (False, None, N),  # known to fail, whatever is missing
        (None, False, N),
    ],
)
def test_td_33_a_missing_input_is_unknown_never_a_failed_condition(
    gap: bool | None, credit: bool | None, expected: State
) -> None:
    verdicts: dict[Check, bool | None] = {
        Check.GAP: gap, Check.CREDIT: credit, Check.SWINGS_BELOW: True,
        Check.SWINGS_NOT_RISING: True,
    }  # fmt: skip
    assert state_of(VersionKey.A, verdicts) is expected
    assert state_of(VersionKey.B, verdicts) is expected


def test_td_33_b_adds_only_the_two_calming_conditions() -> None:
    rising = {i: {"rv_short": 0.10 + i / 100} for i in range(20, 30)}
    a, b = _versions(_tracker(set(range(10, 40)), features=rising))  # pyright: ignore[reportArgumentType]
    assert a.qualifying_days == 30
    assert b.qualifying_days < a.qualifying_days
    above = {i: {"rv_short": 0.30} for i in range(10, 40)}
    _, b = _versions(_tracker(set(range(10, 40)), features=above))  # pyright: ignore[reportArgumentType]
    assert b.qualifying_days == 0


def test_td_33_the_gap_counts_at_its_minimum_exactly() -> None:
    a, _ = _versions(_tracker(set(), gaps={10: 0.03, 12: 0.0299}))
    assert _starts(a) == [DAYS[10]]


# --- stretches -------------------------------------------------------------------------------


def test_td_33_a_run_is_one_stretch_from_its_first_session() -> None:
    assert stretches([N, M, M, M, M, M, N, M]) == (Stretch(1, 5, True), Stretch(7, 7, True))
    a, _ = _versions(_tracker({10, 11, 12, 13, 14, 20}))
    assert _starts(a) == [DAYS[10], DAYS[20]]
    assert a.qualifying_days == 6
    assert a.observations[0].stretch_sessions == 5
    assert a.observations[0].stretch_end == DAYS[14]


def test_td_33_missing_data_never_manufactures_a_confirmed_start() -> None:
    assert stretches([N, M, U, M, M]) == (Stretch(1, 1, True), Stretch(3, 4, False))
    assert stretches([U, M]) == (Stretch(1, 1, False),)
    assert stretches([M]) == (Stretch(0, 0, False),)
    a, _ = _versions(_tracker({10, 11, 12, 13}, credit={11: MISSING}))
    assert _starts(a) == [DAYS[10]]
    assert (a.qualifying_days, a.unconfirmed_stretches, a.unknown_days) == (3, 1, 1)


def test_td_33_a_session_unknown_for_a_but_known_to_fail_confirms_the_next() -> None:
    # Credit is missing on 10, but the gap is known to be too small: 11 is a confirmed start.
    a, _ = _versions(_tracker({11}, credit={10: MISSING}))
    assert _starts(a) == [DAYS[11]]


def test_td_33_b_can_first_qualify_later_in_an_a_stretch() -> None:
    swings = {i: {"rv_short": 0.30} for i in range(10, 13)}
    a, b = _versions(_tracker(set(range(10, 20)), features=swings))  # pyright: ignore[reportArgumentType]
    assert _starts(a) == [DAYS[10]]
    assert _starts(b) == [DAYS[13]]


# --- the counting views ----------------------------------------------------------------------


def test_td_33_ten_session_spacing_keeps_exactly_ten_and_not_nine() -> None:
    def ten(a: int, b: int) -> bool:
        return b - a >= 10

    assert spaced([0, 9, 10, 19, 20], ten) == (0, 10, 20)
    assert spaced([0, 9, 18, 27], ten) == (0, 18)  # measured from the last kept, not the last seen
    assert spaced([], ten) == ()
    a, _ = _versions(_tracker({5, 14, 15}))  # 14 and 15 are one stretch, starting 9 after 5
    assert [o.ten_session for o in a.observations] == [True, False]  # never moved to 15
    a, _ = _versions(_tracker({5, 15}))
    assert [o.ten_session for o in a.observations] == [True, True]


def test_td_33_thirty_day_spacing_keeps_exactly_thirty_and_not_twenty_nine() -> None:
    first = DAYS.index(date(2024, 1, 9))
    at_30, at_29 = DAYS.index(date(2024, 2, 8)), DAYS.index(date(2024, 2, 7))
    assert (DAYS[at_30] - DAYS[first]).days == 30
    a, _ = _versions(_tracker({first, at_30}))
    assert [o.thirty_day for o in a.observations] == [True, True]
    a, _ = _versions(_tracker({first, at_29}))
    assert [o.thirty_day for o in a.observations] == [True, False]


def test_td_33_selection_reads_no_outcome() -> None:
    met = {5, 14, 25, 40}
    later = {i: Outcome(DAYS[i], None, OutcomeStatus.PENDING, None, None, None, None) for i in met}
    flags = [
        [(o.day, o.ten_session, o.thirty_day) for o in v.observations]
        for t in (_tracker(met), _tracker(met, outcomes=later))
        for v in _versions(t)
    ]
    assert flags[0] == flags[2]
    assert flags[1] == flags[3]


def test_td_33_pending_and_incomplete_outcomes_are_counted_but_not_averaged() -> None:
    def odd(i: int, status: OutcomeStatus) -> Outcome:
        return Outcome(DAYS[i], None, status, None, None, None, None)

    outcomes = {
        5: _matured(DAYS[5], realized=0.10, premium=0.004),  # VIX 20% less 10%: +10 points
        15: _matured(DAYS[15], realized=0.26, premium=-0.006),  # -6 points
        30: odd(30, OutcomeStatus.INCOMPLETE),
        45: odd(45, OutcomeStatus.PENDING),
    }
    a, _ = _versions(_tracker({5, 15, 30, 45}, outcomes=outcomes))
    every = a.views[0]
    assert every.key is ViewKey.ALL
    assert (every.selected, every.completed, every.pending, every.incomplete) == (4, 2, 1, 1)
    assert every.mean_gap == pytest.approx(0.02)
    assert every.median_gap == pytest.approx(0.02)
    assert (every.worst_gap, every.worst_day) == (pytest.approx(-0.06), DAYS[15])
    assert every.mean_premium == pytest.approx(-0.001)


def test_td_33_an_empty_view_has_counts_and_no_statistics() -> None:
    for version in _versions(_tracker(set())):
        for view in version.views:
            assert (view.selected, view.completed) == (0, 0)
            assert (view.mean_gap, view.worst_gap, view.worst_day) == (None, None, None)


# --- the latest reading and the period -------------------------------------------------------


def test_td_33_the_latest_reading_is_each_versions_own() -> None:
    swings = {59: {"rv_short": 0.30}}
    a, b = _versions(_tracker({58, 59}, features=swings))  # pyright: ignore[reportArgumentType]
    assert a.latest is not None
    assert b.latest is not None
    assert (a.latest.state, a.latest.stretch_start) == (M, DAYS[58])
    assert b.latest.state is N
    assert a.latest.checks == {Check.GAP: True, Check.CREDIT: True}
    assert b.latest.checks[Check.SWINGS_BELOW] is False
    a, _ = _versions(_tracker({59}, credit={59: MISSING}))
    assert a.latest is not None
    assert a.latest.state is U


def test_td_33_the_period_starts_when_every_condition_can_be_read() -> None:
    compared = compare(_tracker({20}, credit=dict.fromkeys(range(8), MISSING)), CONFIG)
    assert (compared.analysis_start, compared.analysis_end) == (DAYS[8], DAYS[59])


# --- K1, revised -----------------------------------------------------------------------------


def _monthly(count: int, premium: float) -> Tracker:
    """`count` stretches, each over thirty days after the last, completed at `premium`."""
    met = {5 + 22 * k for k in range(count)}
    days = sessions(date(2016, 1, 4), 5 + 22 * count + 10)
    base = _tracker(set(), count=1)
    rows = tuple(_row(d, 0.05 if i in met else 0.0) for i, d in enumerate(days))
    return replace(
        base,
        data_through=days[-1],
        features=rows,
        outcomes=tuple(_matured(d, premium=premium) for d in days),
        credit=tuple(_credit(d, STABLE) for d in days),
    )


@pytest.mark.parametrize(
    ("count", "premium", "status"),
    [
        (29, 0.01, ConditionStatus.INSUFFICIENT_DATA),
        (29, -0.01, ConditionStatus.INSUFFICIENT_DATA),
        (30, 0.01, ConditionStatus.PASS),
        (30, 0.0, ConditionStatus.FAIL),
        (31, -0.01, ConditionStatus.FAIL),
    ],
)
def test_td_33_revised_k1_needs_thirty_completed_spaced_observations(
    count: int, premium: float, status: ConditionStatus
) -> None:
    a, b = _versions(_monthly(count, premium))
    for version in (a, b):
        assert version.k1.status is status
        assert version.k1.sample == count
        assert version.k1.value == pytest.approx(premium)
        assert version.k1.condition_id == f"K1-{version.key.value}"


def test_td_33_revised_k1_reads_only_the_thirty_day_selection() -> None:
    a, _ = _versions(_tracker({5, 8, 11, 40}))
    assert [o.thirty_day for o in a.observations] == [True, False, False, True]
    assert a.k1.sample == 2
    assert a.views[0].completed == 4


# --- the original, untouched -----------------------------------------------------------------


def test_td_33_the_original_versions_evidence_does_not_change() -> None:
    thesis = spike_thesis()
    (episode,) = thesis.episodes
    assert episode.episode_id.startswith("v1.0:")
    assert thesis.evidence.cohorts.stable.count == 1
    assert [k.condition_id for k in thesis.evidence.conditions] == ["K1", "K2", "K3"]
    tracker = _tracker({10, 20})
    before = evidence(tracker, CONFIG)
    compared: Comparison = compare(tracker, CONFIG)
    assert evidence(tracker, CONFIG) == before
    assert compared.methodology_version != CONFIG.model_version
    assert thesis.comparison is not None
    assert [v.key for v in thesis.comparison.versions] == ["A", "B"]
