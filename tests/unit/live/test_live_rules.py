"""The live wheel's picks from the close snapshot (L-P3, L-C3, L-T1, L-P4; LD-11, LD-13).

The fake snapshot's quotes are Black-Scholes prices at one vol, so each strike's delta is known:
the pick solves IV from each mid and must land on the strike whose true delta is nearest target.
"""

from collections.abc import Callable

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import Right
from pmcc.domain.money import Money, Price
from pmcc.live.rules import Pick, liquid, secured, select
from tests.fakes.live import RATE, snapshot, true_deltas

TARGET = 0.30


@pytest.fixture(scope="module")
def calendar() -> SessionCalendar:
    return load_calendar()


def _nearest(deltas: dict[Price, float], keep: Callable[[Price], bool], signed: float) -> Price:
    eligible = {k: d for k, d in deltas.items() if keep(k)}
    return min(eligible, key=lambda k: abs(eligible[k] - signed))


def test_l_p3_picks_the_otm_put_whose_delta_is_nearest_minus_030(
    calendar: SessionCalendar,
) -> None:
    snap = snapshot(calendar)
    deltas = true_deltas(calendar, snap, Right.PUT)

    pick = select(snap, Right.PUT, TARGET, RATE, calendar)

    assert pick is not None
    assert pick.option.strike == _nearest(deltas, lambda k: k < snap.close, -TARGET)
    assert pick.option.strike < snap.close
    assert pick.delta == pytest.approx(deltas[pick.option.strike], abs=0.02)
    assert pick.iv == pytest.approx(0.60, abs=0.03)
    assert pick.option.expiry == snap.expiry


def test_l_c3_picks_the_otm_call_whose_delta_is_nearest_030(calendar: SessionCalendar) -> None:
    snap = snapshot(calendar)
    deltas = true_deltas(calendar, snap, Right.CALL)

    pick = select(snap, Right.CALL, TARGET, RATE, calendar, floor=Price.from_dollars("150"))

    assert pick is not None
    assert pick.option.strike == _nearest(deltas, lambda k: k > snap.close, TARGET)


def test_l_c3_never_sells_below_the_cost_basis(calendar: SessionCalendar) -> None:
    snap = snapshot(calendar)
    floor = Price.from_dollars("177.5")

    pick = select(snap, Right.CALL, TARGET, RATE, calendar, floor=floor)

    assert pick is not None
    assert pick.option.strike >= floor


def test_l_c3_no_call_at_or_above_the_cost_basis_picks_nothing(
    calendar: SessionCalendar,
) -> None:
    pick = select(
        snapshot(calendar), Right.CALL, TARGET, RATE, calendar, floor=Price.from_dollars("190")
    )

    assert pick is None


def test_l_p3_only_out_of_the_money_puts_are_picked(calendar: SessionCalendar) -> None:
    # Every strike above the close: every put is in the money.
    snap = snapshot(calendar, strikes=("165.00", "167.50", "170.00"))

    assert select(snap, Right.PUT, TARGET, RATE, calendar) is None


def test_l_p3_a_contract_with_no_quote_at_the_close_is_never_picked(
    calendar: SessionCalendar,
) -> None:
    snap = snapshot(calendar)
    best = select(snap, Right.PUT, TARGET, RATE, calendar)
    assert best is not None
    unquoted = f"{best.option.strike.to_dollars():.2f}"

    pick = select(snapshot(calendar, unquoted=[unquoted]), Right.PUT, TARGET, RATE, calendar)

    assert pick is not None
    assert pick.option.strike != best.option.strike


def test_l_t1_a_spread_over_the_limit_is_not_liquid(calendar: SessionCalendar) -> None:
    tight = select(snapshot(calendar, spread=0.02), Right.PUT, TARGET, RATE, calendar)
    wide = select(snapshot(calendar, spread=0.30), Right.PUT, TARGET, RATE, calendar)

    assert tight is not None
    assert liquid(tight, 0.10)
    assert wide is not None
    assert not liquid(wide, 0.10)


@pytest.mark.parametrize(("cash", "ok"), [("15500", True), ("15499.99", False)])
def test_l_p4_cash_must_cover_the_strike_times_100(cash: str, ok: bool) -> None:
    assert secured(Money.from_dollars(cash), Price.from_dollars("155"), 1, 100) is ok


def test_l_p3_the_pick_carries_its_quote_and_a_mid_rounded_as_fills_are(
    calendar: SessionCalendar,
) -> None:
    pick = select(snapshot(calendar), Right.PUT, TARGET, RATE, calendar)

    assert isinstance(pick, Pick)
    assert pick.bid <= pick.mid <= pick.ask
