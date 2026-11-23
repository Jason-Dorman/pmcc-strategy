"""Each session's features (THESIS-SPEC §5.1, §5.2), and §14's horizon-integrity test (4)."""

import math
from datetime import date

import pytest

from pmcc.thesis.features import TrackerInputError, compute_features, horizon_sessions
from pmcc.thesis.outcomes import OutcomeStatus, compute_outcomes
from tests.fakes.thesis_tracker import CAL, CONFIG, alternating, closes, flat, sessions

DAYS = sessions(date(2014, 1, 2), 320)
SIGMA = 0.01


def _rows(index: dict[date, float], vix: dict[date, float] | None = None):
    return compute_features(index, flat(DAYS, 20.0) if vix is None else vix, CAL, CONFIG)


def test_f51_return_is_the_log_of_close_over_previous_close() -> None:
    index = {DAYS[0]: 100.0, DAYS[1]: 110.0, DAYS[2]: 99.0}
    rows = compute_features(index, {}, CAL, CONFIG)
    assert [r.log_return for r in rows] == [None, math.log(1.1), math.log(0.9)]


def test_f51_ewma_starts_at_the_60th_return_with_the_mean_square() -> None:
    returns = alternating(SIGMA)
    rows = _rows(closes(DAYS, lambda i: 0.03 if i == 61 else returns(i)))
    assert all(r.ewma_variance is None for r in rows[:60])
    assert rows[60].ewma_variance == pytest.approx(SIGMA**2)
    assert rows[61].ewma_variance == pytest.approx(0.94 * SIGMA**2 + 0.06 * 0.03**2)


def test_f51_rv_is_the_annualised_root_mean_square() -> None:
    rows = _rows(closes(DAYS, lambda i: 0.02 if i >= 100 else SIGMA))
    assert rows[104].rv_short == pytest.approx(math.sqrt(252) * 0.02)
    assert rows[104].rv_long == pytest.approx(math.sqrt(252 * (5 * 0.02**2 + 15 * SIGMA**2) / 20))
    assert rows[3].rv_short is None  # only 3 returns so far


def test_f51_warm_needs_252_valid_returns() -> None:
    rows = _rows(closes(DAYS, alternating(SIGMA)))
    assert [r.warm for r in rows[251:254]] == [False, True, True]
    assert rows[252].valid_returns == 252


def test_f51_a_missing_close_breaks_two_returns_and_nothing_is_forward_filled() -> None:
    index = closes(DAYS, alternating(SIGMA))
    del index[DAYS[100]]
    rows = _rows(index)
    assert rows[100].index_close is None
    assert (rows[100].log_return, rows[101].log_return) == (None, None)
    assert (rows[100].ewma_variance, rows[101].ewma_variance) == (None, None)
    assert rows[102].ewma_variance is not None  # the recursion resumes
    assert all(rows[i].rv_short is None for i in range(100, 106))
    assert rows[106].rv_short is not None
    assert rows[110].valid_returns == 108


def test_f51_values_on_non_sessions_or_not_positive_are_refused() -> None:
    with pytest.raises(TrackerInputError, match="not a session"):
        compute_features({date(2014, 1, 4): 100.0}, {}, CAL, CONFIG)  # a Saturday
    with pytest.raises(TrackerInputError, match="above zero"):
        compute_features({DAYS[0]: 0.0}, {}, CAL, CONFIG)
    with pytest.raises(TrackerInputError, match="finite"):
        compute_features({}, {DAYS[0]: math.nan}, CAL, CONFIG)


def test_f52_horizon_counts_closes_after_t_through_30_calendar_days() -> None:
    horizon = horizon_sessions(CAL, date(2024, 11, 21), 30)
    assert horizon is not None
    assert (horizon[0], horizon[-1], len(horizon)) == (date(2024, 11, 22), date(2024, 12, 20), 20)
    assert date(2024, 11, 28) not in horizon  # Thanksgiving


def test_f52_horizon_takes_the_leap_day_and_ends_on_the_30th_day() -> None:
    horizon = horizon_sessions(CAL, date(2024, 2, 15), 30)
    assert horizon is not None
    assert date(2024, 2, 29) in horizon
    assert date(2024, 2, 19) not in horizon  # Washington's Birthday
    assert len(horizon) == 20
    to_the_30th = horizon_sessions(CAL, date(2024, 2, 16), 30)  # ends Sun Mar 17
    assert to_the_30th is not None
    assert to_the_30th[-1] == date(2024, 3, 15)


def test_f52_horizon_counts_calendar_days_across_a_dst_change() -> None:
    horizon = horizon_sessions(CAL, date(2024, 3, 1), 30)  # DST starts Mar 10
    assert horizon is not None
    assert len(horizon) == 19  # Mar 29 is Good Friday
    autumn = horizon_sessions(CAL, date(2024, 10, 18), 30)  # DST ends Nov 3
    assert autumn is not None
    assert (autumn[-1], len(autumn)) == (date(2024, 11, 15), 20)


def test_f52_horizon_past_the_calendar_is_none() -> None:
    assert horizon_sessions(CAL, date(2027, 12, 15), 30) is None


def test_f52_implied_and_forecast_share_one_convention() -> None:
    rows = _rows(closes(DAYS, alternating(SIGMA)), flat(DAYS, 25.0))
    row = rows[200]
    n = row.horizon_closes
    assert n is not None
    assert row.ewma_variance is not None
    assert row.implied_total_variance == pytest.approx(0.25**2 * 30 / 365)
    assert row.forecast_total_variance == pytest.approx(n * row.ewma_variance)
    forecast_vol = math.sqrt(n * row.ewma_variance * 365 / 30)
    assert row.forecast_vol == pytest.approx(forecast_vol)
    assert row.forecast_gap_vol == pytest.approx(0.25 - forecast_vol)
    assert row.forecast_gap_variance == pytest.approx(0.25**2 * 30 / 365 - n * row.ewma_variance)


def test_f52_realized_is_null_until_the_horizon_matures() -> None:
    t = 200
    horizon = horizon_sessions(CAL, DAYS[t], 30)
    assert horizon is not None
    last = DAYS.index(horizon[-1])
    index = closes(DAYS, alternating(SIGMA))
    before = compute_outcomes(_rows({d: index[d] for d in DAYS[:last]}), CAL, 30)[t]
    assert (before.status, before.realized_total_variance) == (OutcomeStatus.PENDING, None)
    after = compute_outcomes(_rows({d: index[d] for d in DAYS[: last + 1]}), CAL, 30)[t]
    assert after.status is OutcomeStatus.MATURED
    assert after.maturity_day == horizon[-1]
    assert after.realized_total_variance == pytest.approx(len(horizon) * SIGMA**2)


def test_f52_realized_takes_the_weekend_gap_in_mondays_return() -> None:
    gap_day = next(i for i, d in enumerate(DAYS) if i > 200 and d.weekday() == 0)
    rows = _rows(closes(DAYS, lambda i: 0.05 if i == gap_day else SIGMA))
    outcomes = compute_outcomes(rows, CAL, 30)
    t = gap_day - 1  # the Friday before: the Monday's return is in its horizon
    n = rows[t].horizon_closes
    assert n is not None
    assert outcomes[t].realized_total_variance == pytest.approx(0.05**2 + (n - 1) * SIGMA**2)
    implied = rows[t].implied_total_variance
    assert implied is not None
    assert outcomes[t].realized_variance_premium == pytest.approx(
        implied - (0.05**2 + (n - 1) * SIGMA**2)
    )


def test_f52_a_missing_return_in_the_horizon_is_incomplete_not_zero() -> None:
    index = closes(DAYS, alternating(SIGMA))
    del index[DAYS[205]]
    outcome = compute_outcomes(_rows(index), CAL, 30)[200]
    assert (outcome.status, outcome.realized_total_variance) == (OutcomeStatus.INCOMPLETE, None)


def test_f51_ewma_initialisation_counts_60_valid_returns_across_a_gap() -> None:
    # PO, TD-16: a gap during the start-up doesn't restart the count.
    index = closes(DAYS, alternating(SIGMA))
    del index[DAYS[30]]  # removes returns 30 and 31
    rows = _rows(index)
    assert rows[59].valid_returns == 57
    assert all(r.ewma_variance is None for r in rows[:62])
    assert rows[62].valid_returns == 60
    assert rows[62].ewma_variance == pytest.approx(SIGMA**2)


def test_f51_rv20_is_unavailable_while_its_window_holds_a_missing_return() -> None:
    index = closes(DAYS, alternating(SIGMA))
    del index[DAYS[100]]  # returns 100 and 101 are missing
    rows = _rows(index)
    assert all(rows[i].rv_long is None for i in range(100, 121))
    assert rows[121].rv_long == pytest.approx(math.sqrt(252) * SIGMA)


def test_f51_a_holiday_is_an_expected_gap_not_missing_data() -> None:
    # Thanksgiving 2014 (Nov 27): Friday's return is from Wednesday's close, one session.
    wednesday, friday = date(2014, 11, 26), date(2014, 11, 28)
    i = DAYS.index(friday)
    assert DAYS[i - 1] == wednesday
    index = closes(DAYS, alternating(SIGMA))
    rows = _rows(index)
    assert rows[i].log_return == pytest.approx(math.log(index[friday] / index[wednesday]))
    assert rows[i].valid_returns == i
