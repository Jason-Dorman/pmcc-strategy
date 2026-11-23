"""Shock episodes and their candidates (THESIS-SPEC §5.3, §5.4), and §14's episode determinism (3).

Rows are built by hand, so each test sets exactly the VIX, RV and gap values it is about.
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import date

import pytest

from pmcc.thesis.episodes import CandidateStatus, find_episodes, percentile, shock_flags
from pmcc.thesis.features import FeatureRow
from tests.fakes.thesis_tracker import CAL, CONFIG, sessions

DAYS = sessions(date(2015, 1, 2), 330)
BASE = 300  # the first row a shock can be tested on with room either side


def _row(day: date, vix: float | None = 14.0) -> FeatureRow:
    return FeatureRow(
        day=day, index_close=4000.0, vix_points=vix, log_return=0.0, valid_returns=300,
        ewma_variance=1e-4, rv_short=0.20, rv_long=0.15, horizon_closes=21,
        implied_total_variance=0.0, forecast_total_variance=0.0, forecast_vol=0.15,
        forecast_gap_vol=0.0, forecast_gap_variance=0.0, warm=True,
    )  # fmt: skip


def _rows(vix: dict[int, float] | None = None, base: float = 14.0) -> list[FeatureRow]:
    """Rows on DAYS: VIX at `base` but at the positions `vix` sets; no session qualifies."""
    levels = vix or {}
    return [_row(d, levels.get(i, base + (i % 7) * 0.01)) for i, d in enumerate(DAYS)]


def _set(rows: list[FeatureRow], i: int, **changes: float | None) -> None:
    rows[i] = replace(rows[i], **changes)  # pyright: ignore[reportArgumentType]


def _qualify(rows: list[FeatureRow], i: int, gap: float = 0.05) -> None:
    """Make row `i` pass all three normalization tests."""
    _set(rows, i, rv_short=0.10, rv_long=0.30, forecast_gap_vol=gap)


def _episodes(rows: Sequence[FeatureRow]):
    return find_episodes(rows, CAL, CONFIG)


def test_f53_percentile_interpolates_linearly() -> None:
    assert percentile([1.0, 2.0, 3.0, 4.0, 5.0], 0.8) == pytest.approx(4.2)
    assert percentile([5.0, 1.0, 3.0], 0.5) == 3.0
    assert percentile([2.0], 0.8) == 2.0


def test_f53_shock_excludes_today_from_its_percentile() -> None:
    # The 252 sessions before t: 51 at 30 (earliest) and 201 at 10, so the 80th percentile is 26.
    # With t's own 27 included it would be 30, and t would not be a shock.
    vix = {BASE - 252 + k: 30.0 for k in range(51)}
    vix |= {BASE - 201 + k: 10.0 for k in range(201)}
    vix[BASE] = 27.0
    flags = shock_flags(_rows(vix), CONFIG.shock)
    assert flags[BASE] is True


def test_f53_shock_needs_the_level_and_the_jump() -> None:
    high_slow = {BASE - 5 + k: 20.0 + 0.8 * k for k in range(6)}  # high, up only 20% over 5
    flags = shock_flags(_rows(high_slow), CONFIG.shock)
    assert flags[BASE] is False
    low_jump = {k: 40.0 for k in range(BASE - 252, BASE - 100)} | {BASE - 5: 10.0, BASE: 13.0}
    assert shock_flags(_rows(low_jump), CONFIG.shock)[BASE] is False  # up 30%, below the 80th
    both = {BASE - 5: 14.0, BASE: 17.5}  # up exactly 25%, above the 80th
    assert shock_flags(_rows(both), CONFIG.shock)[BASE] is True


def test_f53_shock_is_unknown_without_its_inputs_or_warmup() -> None:
    rows = _rows({BASE: 25.0})
    _set(rows, BASE - 100, vix_points=None)
    assert shock_flags(rows, CONFIG.shock)[BASE] is None
    cold = _rows({BASE: 25.0})
    cold[BASE] = replace(cold[BASE], warm=False)
    assert shock_flags(cold, CONFIG.shock)[BASE] is None
    assert shock_flags(_rows(), CONFIG.shock)[100] is None  # fewer than 252 sessions before


def test_f53_shocks_inside_a_window_are_ignored_and_never_extend_it() -> None:
    rows = _rows({BASE - 20: 25.0, BASE - 16: 25.0, BASE - 9: 25.0})
    flags = shock_flags(rows, CONFIG.shock)
    assert (flags[BASE - 20], flags[BASE - 16], flags[BASE - 9]) == (True, True, True)
    episodes = _episodes(rows)
    assert [e.shock_day for e in episodes] == [DAYS[BASE - 20], DAYS[BASE - 9]]
    first = episodes[0]
    assert first.window == tuple(DAYS[BASE - 19 : BASE - 9])  # s+1 .. s+10, fixed
    assert first.status is CandidateStatus.NO_CANDIDATE


def test_f54_candidate_is_the_first_qualifying_window_session() -> None:
    rows = _rows({BASE: 25.0})
    _qualify(rows, BASE + 4)
    _qualify(rows, BASE + 7)
    (episode,) = _episodes(rows)
    assert (episode.status, episode.candidate_day) == (CandidateStatus.CANDIDATE, DAYS[BASE + 4])
    assert episode.episode_id == f"v1.0:{DAYS[BASE].isoformat()}"


def test_f54_the_shock_day_itself_is_not_searched() -> None:
    rows = _rows({BASE: 25.0})
    _qualify(rows, BASE)
    (episode,) = _episodes(rows)
    assert episode.status is CandidateStatus.NO_CANDIDATE


def test_f54_each_test_is_needed_and_its_boundary_holds() -> None:
    i = BASE + 3
    rows = _rows({BASE: 25.0})
    _set(rows, i - 3, rv_short=0.10)
    _set(rows, i, rv_short=0.10, rv_long=0.30, forecast_gap_vol=0.03)  # equal RV5, gap on the line
    assert _episodes(rows)[0].candidate_day == DAYS[i]
    for change in ({"rv_long": 0.10}, {"rv_short": 0.11}, {"forecast_gap_vol": 0.0299}):
        failing = list(rows)
        _set(failing, i, **change)
        assert _episodes(failing)[0].status is CandidateStatus.NO_CANDIDATE, change


def test_f54_a_session_that_cant_be_tested_before_a_qualifying_one_is_incomplete() -> None:
    rows = _rows({BASE: 25.0})
    _set(rows, BASE + 2, forecast_gap_vol=None)
    _qualify(rows, BASE + 5)
    (episode,) = _episodes(rows)
    assert episode.status is CandidateStatus.INCOMPLETE_CANDIDATE_SEARCH
    assert episode.candidate_day is None
    assert str(DAYS[BASE + 2]) in episode.note


def test_f54_a_window_past_the_data_is_still_searching() -> None:
    rows = _rows({BASE: 25.0})[: BASE + 4]
    (episode,) = _episodes(rows)
    assert (episode.status, episode.candidate_day) == (CandidateStatus.SEARCHING, None)
    assert len(episode.window) == 10


def _rows_ending_at_the_calendar() -> tuple[list[date], list[FeatureRow]]:
    days = [s.day for s in CAL.sessions(date(2026, 9, 1), CAL.last_day)][-330:]
    return days, [_row(d, 14.0 + (i % 7) * 0.01) for i, d in enumerate(days)]


def test_f53_a_shock_near_the_calendars_end_searches_a_window_cut_short() -> None:
    days, rows = _rows_ending_at_the_calendar()
    shock = len(days) - 4  # three sessions left in the calendar
    _set(rows, shock, vix_points=25.0)
    (episode,) = _episodes(rows)
    assert episode.shock_day == days[shock]
    assert episode.window == tuple(days[shock + 1 :])
    assert (episode.status, episode.candidate_day) == (CandidateStatus.SEARCHING, None)
    assert "calendar" in episode.note


def test_f53_a_shock_on_the_calendars_last_day_has_an_empty_window() -> None:
    days, rows = _rows_ending_at_the_calendar()
    _set(rows, len(days) - 1, vix_points=25.0)
    (episode,) = _episodes(rows)
    assert episode.window == ()
    assert episode.window_end == CAL.last_day
    assert episode.status is CandidateStatus.SEARCHING
