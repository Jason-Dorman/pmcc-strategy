"""The wheel's selection rules at their boundaries (W2-02), on a hand-built view."""

from datetime import date, datetime

import pytest

from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.wheel.rules import finishes_itm, passes_trigger, select_call, select_put
from tests.fakes.view import ROOT, Row, StubView

EXPIRY = date(2026, 9, 4)
NOW = datetime(2026, 8, 31, 10, tzinfo=ET)
D = Price.from_dollars


def _view(right: Right, rows: list[Row], spot: str = "100") -> StubView:
    return StubView(NOW, D(spot), {(EXPIRY, right): rows})


def test_w_p3_picks_the_otm_put_nearest_minus_030() -> None:
    rows = [Row(96, "0.50", "0.52", -0.20), Row(98, "1.00", "1.04", -0.31),
            Row(99, "1.50", "1.56", -0.38), Row(101, "2.50", "2.60", -0.55)]  # fmt: skip
    pick = select_put(_view(Right.PUT, rows), EXPIRY, 0.30)
    assert pick is not None
    assert pick.option == OptionId(ROOT, EXPIRY, Right.PUT, D(98))
    assert pick.quote.mid == D("1.02")


def test_w_p3_never_picks_a_put_at_or_above_spot() -> None:
    rows = [Row(100, "2.00", "2.10", -0.30), Row(97, "0.80", "0.82", -0.10)]
    pick = select_put(_view(Right.PUT, rows), EXPIRY, 0.30)
    assert pick is not None
    assert pick.option.strike == D(97)


def test_w_p3_a_tie_goes_to_the_lower_strike() -> None:
    rows = [Row(97, "0.80", "0.82", -0.25), Row(98, "1.00", "1.04", -0.35)]
    pick = select_put(_view(Right.PUT, rows), EXPIRY, 0.30)
    assert pick is not None
    assert pick.option.strike == D(97)


def test_w_p3_skips_a_put_with_no_quote_or_no_delta() -> None:
    rows = [Row(98, None, None, -0.30), Row(97, "0.80", "0.82"), Row(96, "0.50", "0.52", -0.15)]
    pick = select_put(_view(Right.PUT, rows), EXPIRY, 0.30)
    assert pick is not None
    assert pick.option.strike == D(96)


def test_w_p3_no_spot_no_pick() -> None:
    view = StubView(NOW, None, {(EXPIRY, Right.PUT): [Row(98, "1.00", "1.04", -0.30)]})
    assert select_put(view, EXPIRY, 0.30) is None


def test_w_c3_floors_the_call_at_the_cost_basis() -> None:
    rows = [Row(102, "1.00", "1.04", 0.30), Row(104, "0.50", "0.52", 0.18),
            Row(106, "0.20", "0.22", 0.08)]  # fmt: skip
    view = _view(Right.CALL, rows)
    low = select_call(view, EXPIRY, 0.30, D("101.50"))
    assert low is not None
    assert low.option.strike == D(102)
    pick = select_call(view, EXPIRY, 0.30, D("103.20"))
    assert pick is not None
    assert pick.option.strike == D(104)
    assert pick.values["basis_floor"] == "103.2000"


def test_w_c3_a_strike_exactly_at_the_basis_qualifies() -> None:
    view = _view(Right.CALL, [Row(104, "0.50", "0.52", 0.18)])
    pick = select_call(view, EXPIRY, 0.30, D(104))
    assert pick is not None


def test_w_c3_none_at_or_above_the_basis_is_no_pick() -> None:
    view = _view(Right.CALL, [Row(102, "1.00", "1.04", 0.30)])
    assert select_call(view, EXPIRY, 0.30, D("102.01")) is None


def test_w_c3_never_picks_a_call_at_or_below_spot() -> None:
    # A cost basis below spot (after a rally) must not let an ITM or ATM call through.
    rows = [Row(98, "2.50", "2.60", 0.30), Row(100, "1.50", "1.56", 0.30),
            Row(102, "0.60", "0.62", 0.12)]  # fmt: skip
    pick = select_call(_view(Right.CALL, rows), EXPIRY, 0.30, D(90))
    assert pick is not None
    assert pick.option.strike == D(102)


def test_w_c3_a_tie_goes_to_the_higher_strike() -> None:
    rows = [Row(102, "1.00", "1.04", 0.35), Row(103, "0.80", "0.82", 0.25)]
    pick = select_call(_view(Right.CALL, rows), EXPIRY, 0.30, D(90))
    assert pick is not None
    assert pick.option.strike == D(103)


@pytest.mark.parametrize(
    ("bid", "ask", "passes"), [("0.95", "1.05", True), ("0.94", "1.05", False)]
)
def test_w_t1_passes_at_exactly_the_spread_limit(bid: str, ask: str, passes: bool) -> None:
    pick = select_put(_view(Right.PUT, [Row(98, bid, ask, -0.30)]), EXPIRY, 0.30)
    assert pick is not None
    assert passes_trigger(pick, 0.10) is passes


@pytest.mark.parametrize(
    ("right", "close", "itm"),
    [(Right.PUT, "97.99", True), (Right.PUT, "98", False), (Right.PUT, "98.01", False),
     (Right.CALL, "98.01", True), (Right.CALL, "98", False), (Right.CALL, "97.99", False)],
)  # fmt: skip
def test_wd_15_itm_is_strictly_through_the_strike(right: Right, close: str, itm: bool) -> None:
    assert finishes_itm(OptionId(ROOT, EXPIRY, right, D(98)), D(close)) is itm
