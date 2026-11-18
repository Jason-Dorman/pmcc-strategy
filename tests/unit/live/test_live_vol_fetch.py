"""Asking LSEG for the volatility points (L4-02; PO, LD-33; LD-34), over a fake provider that
quotes every option from Black-Scholes at a known vol."""

from datetime import date

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.data.fetch import Retry
from pmcc.data.provider import ProviderOutageError
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.money import Price
from pmcc.live.vol import VolError, rv20_through, tenor_expiry
from pmcc.live.vol_fetch import fetch_points, plan_points
from tests.fakes.vol import RATE, STOCK, VolProvider

TUESDAY = date(2026, 11, 17)
NO_WAIT = Retry(attempts=1, sleep=lambda _: None)


@pytest.fixture(scope="module")
def calendar() -> SessionCalendar:
    return load_calendar()


def _closes(calendar: SessionCalendar, last: date, count: int) -> dict[date, float]:
    days = [s.day for s in calendar.sessions_before(last, count - 1)] + [last]
    return {d: round(150 + 3 * ((i * 7) % 5) - 0.37 * i, 2) for i, d in enumerate(days)}


def _sessions(calendar: SessionCalendar, *days: date):
    return tuple(calendar.session(d) for d in days)


def test_ld_33_points_for_three_sessions_over_two_expiries(calendar: SessionCalendar) -> None:
    days = (date(2026, 11, 12), date(2026, 11, 13), date(2026, 11, 16))
    closes = _closes(calendar, days[-1], 25)
    provider = VolProvider(calendar, closes, vol=0.48)

    plan = plan_points(provider, STOCK, calendar, _sessions(calendar, *days), TUESDAY, NO_WAIT)
    points = fetch_points(provider, plan, "NVDA", calendar, RATE, NO_WAIT)

    assert [p.session for p in points] == list(days)
    assert {tenor_expiry(calendar, d) for d in days} == {date(2026, 12, 11), date(2026, 12, 18)}
    assert len(plan.groups) == 2  # one request round per expiry, not per session
    for point in points:
        close = Price.from_dollars(f"{closes[point.session]:.2f}")
        assert point.close == close
        assert point.expiry == tenor_expiry(calendar, point.session)
        assert point.strike is not None
        assert abs(point.strike.units - close.units) <= Price.from_dollars("1.25").units
        assert point.atm_iv is not None
        assert abs(point.atm_iv - 0.48) < 0.01
        prices = {d: Price.from_dollars(f"{c:.2f}") for d, c in closes.items()}
        rv = rv20_through(calendar, point.session, prices)
        assert point.rv20 == pytest.approx(rv)


def test_ld_34_the_plan_counts_its_contracts_and_requests(calendar: SessionCalendar) -> None:
    closes = _closes(calendar, TUESDAY, 25)
    provider = VolProvider(calendar, closes)

    plan = plan_points(provider, STOCK, calendar, _sessions(calendar, TUESDAY), TUESDAY, NO_WAIT)

    assert provider.asked == [(STOCK,)]  # the plan asks for the closes alone
    assert plan.contracts == 12  # six strikes within $7.50 of the close, a put and a call each
    assert plan.requests == 2  # the closes, and one batch of 12 live contracts
    assert "12 contracts" in plan.describe()


def test_ld_34_a_session_without_a_close_stops_the_run(calendar: SessionCalendar) -> None:
    closes = _closes(calendar, TUESDAY, 25)
    del closes[TUESDAY]
    provider = VolProvider(calendar, closes)

    with pytest.raises(VolError, match="2026-11-17"):
        plan_points(provider, STOCK, calendar, _sessions(calendar, TUESDAY), TUESDAY, NO_WAIT)


def test_ld_34_an_unlisted_atm_strike_falls_to_the_next_nearest(calendar: SessionCalendar) -> None:
    closes = {**_closes(calendar, TUESDAY, 25), TUESDAY: 155.10}
    provider = VolProvider(calendar, closes, unlisted=[155])

    plan = plan_points(provider, STOCK, calendar, _sessions(calendar, TUESDAY), TUESDAY, NO_WAIT)
    (point,) = fetch_points(provider, plan, "NVDA", calendar, RATE, NO_WAIT)

    assert point.strike == Price.from_dollars("157.50")


def test_ld_34_an_outage_raises_and_makes_no_points(calendar: SessionCalendar) -> None:
    provider = VolProvider(calendar, _closes(calendar, TUESDAY, 25), down=True)

    with pytest.raises(ProviderOutageError):
        plan_points(provider, STOCK, calendar, _sessions(calendar, TUESDAY), TUESDAY, NO_WAIT)
