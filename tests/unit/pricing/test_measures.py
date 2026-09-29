"""The measures the rules read (P2-03): spot and close (DEC-23), ATM strike, ATM IV and EM
(DEC-25), RV20 (DEC-26), all as the PO settled them on 2026-09-28."""

import math
from datetime import date, datetime, time

import numpy as np
import pytest

from pmcc.config.calendar import load_calendar
from pmcc.domain.clock import ET
from pmcc.domain.money import Price
from pmcc.domain.quotes import Quote
from pmcc.pricing.chain import price_quotes
from pmcc.pricing.measures import (
    RV_RETURNS,
    atm_iv,
    atm_strike,
    expected_move,
    itm_at_expiry,
    realized_vol,
    rv20,
    session_close,
)

CAL = load_calendar()


def _p(dollars: float) -> Price:
    return Price.from_dollars(dollars)


def _q(bid: float, ask: float) -> Quote:
    return Quote(_p(bid), _p(ask))


def _et(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=ET)


# ---- DEC-25: ATM strike


def test_dec_25_atm_strike_is_the_listed_strike_nearest_spot() -> None:
    strikes = [_p(95), _p(100), _p(105)]

    assert atm_strike(strikes, _p(101.20)) == _p(100)
    assert atm_strike(strikes, _p(103)) == _p(105)


def test_dec_25_atm_strike_tie_takes_the_lower_strike() -> None:
    assert atm_strike([_p(105), _p(100)], _p(102.50)) == _p(100)


def test_dec_25_atm_strike_ties_are_exact_in_price_units() -> None:
    # $0.0001 off the midpoint is no tie.
    assert atm_strike([_p(100), _p(105)], _p(102.5001)) == _p(105)


def test_dec_25_atm_strike_with_no_listed_strikes_is_unavailable() -> None:
    assert atm_strike([], _p(100)) is None


# ---- DEC-25: expected move


def test_dec_25_em_is_the_atm_call_mid_plus_the_atm_put_mid() -> None:
    assert expected_move(_q(2.00, 2.10), _q(1.80, 1.90)) == _p(3.90)


def test_dec_25_em_adds_the_rounded_mids() -> None:
    # Each mid rounds half-even to $0.0001 as a fill would (DEC-44): 1.00005 -> 1.0000,
    # 1.00015 -> 1.0002.
    assert expected_move(_q(1.0000, 1.0001), _q(1.0001, 1.0002)) == _p(2.0002)


def test_dec_25_em_rounds_each_mid_not_the_straddle() -> None:
    # 1.00005 -> 1.0000 and 2.00005 -> 2.0000, so EM is 3.0000; rounding the straddle's 3.0001
    # exactly would give 3.0001.
    assert expected_move(_q(1.0000, 1.0001), _q(2.0000, 2.0001)) == _p(3.0000)


@pytest.mark.parametrize(
    ("call", "put"),
    [(_q(2.00, 2.10), None), (None, _q(1.80, 1.90)), (None, None)],
    ids=["no put quote", "no call quote", "neither"],
)
def test_dec_25_em_is_unavailable_without_both_quotes(
    call: Quote | None, put: Quote | None
) -> None:
    assert expected_move(call, put) is None


# ---- DEC-25: ATM IV is the ATM call's


def test_dec_25_atm_iv_is_the_iv_of_the_atm_call() -> None:
    calls = price_quotes(
        strike=np.array([_p(95).units, _p(100).units], dtype=np.int64),
        bid=np.array([_p(5.60).units, _p(2.00).units], dtype=np.int64),
        ask=np.array([_p(5.80).units, _p(2.10).units], dtype=np.int64),
        valid=np.array([True, True]),
        spot=float(_p(100).units),
        years=7 / 365,
        rate=0.0371,
        is_call=True,
    )

    iv = atm_iv(calls, _p(100))

    assert iv is not None
    assert iv == pytest.approx(float(calls.iv[1]))
    assert iv != pytest.approx(float(calls.iv[0]))


def test_dec_25_atm_iv_is_unavailable_when_the_atm_call_has_no_quote() -> None:
    calls = price_quotes(
        strike=np.array([_p(100).units], dtype=np.int64),
        bid=np.array([0], dtype=np.int64),
        ask=np.array([_p(2.10).units], dtype=np.int64),
        valid=np.array([False]),
        spot=float(_p(100).units),
        years=7 / 365,
        rate=0.0371,
        is_call=True,
    )

    assert atm_iv(calls, _p(100)) is None


def test_dec_25_atm_iv_is_unavailable_when_the_atm_strike_isnt_on_the_bar() -> None:
    calls = price_quotes(
        strike=np.array([_p(95).units], dtype=np.int64),
        bid=np.array([_p(5.60).units], dtype=np.int64),
        ask=np.array([_p(5.80).units], dtype=np.int64),
        valid=np.array([True]),
        spot=float(_p(100).units),
        years=7 / 365,
        rate=0.0371,
        is_call=True,
    )

    assert atm_iv(calls, _p(100)) is None


def test_dec_25_atm_iv_is_unavailable_when_the_atm_calls_iv_fails() -> None:
    # A $0.01 mid on a $95 call with spot at $100 is under the floor.
    calls = price_quotes(
        strike=np.array([_p(95).units], dtype=np.int64),
        bid=np.array([_p(0.01).units], dtype=np.int64),
        ask=np.array([_p(0.01).units], dtype=np.int64),
        valid=np.array([True]),
        spot=float(_p(100).units),
        years=7 / 365,
        rate=0.0371,
        is_call=True,
    )

    assert atm_iv(calls, _p(95)) is None


# ---- DEC-23: spot, close, ITM at expiry


def test_dec_23_session_close_is_the_close_bars_last_trade() -> None:
    day = date(2026, 9, 25)
    trades = {_et(day, 15): _p(180), _et(day, 16): _p(181.25), _et(day, 17): _p(182)}

    assert session_close(CAL.session(day), trades) == _p(181.25)


def test_dec_23_a_half_days_close_is_its_1300_bar() -> None:
    day = date(2026, 11, 27)
    trades = {_et(day, 13): _p(150), _et(day, 14): _p(151)}

    assert session_close(CAL.session(day), trades) == _p(150)


def test_dec_23_session_close_is_unavailable_without_a_close_bar_trade() -> None:
    day = date(2026, 9, 25)

    assert session_close(CAL.session(day), {_et(day, 15): _p(180)}) is None


def test_dec_23_itm_at_expiry_needs_the_close_above_the_strike() -> None:
    assert itm_at_expiry(_p(100.01), _p(100))
    assert not itm_at_expiry(_p(99.99), _p(100))


def test_dec_23_a_close_on_the_strike_is_otm() -> None:
    assert not itm_at_expiry(_p(100), _p(100))


# ---- DEC-26: RV20


def test_dec_26_realized_vol_is_the_sample_stdev_of_log_returns_annualized() -> None:
    closes = [_p(100), _p(102), _p(99), _p(101)]
    logs = np.diff(np.log([100.0, 102.0, 99.0, 101.0]))

    assert realized_vol(closes) == pytest.approx(float(np.std(logs, ddof=1)) * math.sqrt(252))


def _daily_closes(first: date, sessions: int, *, today: date) -> dict[datetime, Price]:
    """Close-bar trades for `sessions` sessions from `first`, plus wild bars on `today`."""
    trades: dict[datetime, Price] = {}
    for i, s in enumerate(CAL.sessions(first, today)[:sessions]):
        trades[s.close_bar_end] = _p(100 * math.exp(0.01 * math.sin(i)))
        trades[_et(s.day, 12)] = _p(1)  # a mid-session bar is never a close
    session = CAL.session(today)
    for end in session.bar_ends():
        trades[end] = _p(500)
    return trades


def test_dec_26_rv20_uses_the_21_closes_before_the_current_session() -> None:
    today = date(2026, 9, 25)
    prior = CAL.sessions_before(today, RV_RETURNS + 1)
    trades = _daily_closes(date(2026, 8, 3), 60, today=today)
    closes = [trades[s.close_bar_end] for s in prior]

    got = rv20(CAL, _et(today, 16), trades)

    assert RV_RETURNS == 20
    assert got == pytest.approx(realized_vol(closes))


def test_dec_26_rv20_ignores_the_current_sessions_bars_even_at_its_close() -> None:
    today = date(2026, 9, 25)
    trades = _daily_closes(date(2026, 8, 3), 60, today=today)
    calm = {t: p for t, p in trades.items() if t.date() != today}

    at_open = rv20(CAL, _et(today, 10), trades)

    assert at_open == rv20(CAL, _et(today, 16), trades)
    assert at_open == rv20(CAL, _et(today, 10), calm)


def test_dec_26_rv20_is_unavailable_when_a_close_is_missing() -> None:
    today = date(2026, 9, 25)
    trades = _daily_closes(date(2026, 8, 3), 60, today=today)
    del trades[CAL.sessions_before(today, 5)[0].close_bar_end]

    assert rv20(CAL, _et(today, 10), trades) is None


def test_dec_26_rv20_is_unavailable_before_21_closes_exist() -> None:
    today = date(2026, 9, 25)
    trades = _daily_closes(CAL.sessions_before(today, RV_RETURNS)[0].day, 60, today=today)

    assert rv20(CAL, _et(today, 10), trades) is None


def test_dec_26_rv20_takes_a_half_days_close_from_its_1300_bar() -> None:
    today = date(2026, 12, 29)  # the 21 sessions before it include Nov 27 and Dec 24
    prior = CAL.sessions_before(today, RV_RETURNS + 1)
    assert any(s.is_half_day for s in prior)
    trades = _daily_closes(date(2026, 10, 1), 80, today=today)

    got = rv20(CAL, _et(today, 10), trades)

    assert got == pytest.approx(realized_vol([trades[s.close_bar_end] for s in prior]))
