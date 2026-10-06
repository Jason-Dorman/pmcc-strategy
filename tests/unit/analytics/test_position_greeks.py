"""Position Greeks (PO, DEC-120), worked by hand on small runs (`tests/fakes/legs.py`). Dollar
units from DEC-24's: δ × 100 × contracts in shares, Γ × 100 × contracts in shares per $1, θ ÷ 365 ×
100 × contracts in $ a calendar day, vega × contracts in $ a vol point; the short's negated."""

from datetime import date

import pytest

from pmcc.accounting.ledger import LegGreeks
from pmcc.analytics.position_greeks import position_greeks
from pmcc.export.analytics_models import PositionGreekRow, PositionGreeks
from tests.fakes.legs import Held, Tick, greeks, tape
from tests.fakes.records import FRI_1, LONG, W1, at, short_call

SHORT = short_call(FRI_1)
LONG_G = greeks(0.40, 0.80, 0.01, -36.5, 40.0)  # θ −$10.00 a day, vega +$40.00 a vol point
SHORT_G = greeks(0.50, 0.30, 0.05, -365.0, 8.0)  # θ +$100.00 a day once negated


def _row(result: PositionGreeks, component: str) -> PositionGreekRow:
    return next(r for r in result.rows if r.component == component)


def _diagonal() -> PositionGreeks:
    """10:00 the long alone; 11:00 and 12:00 the long and the short; 13:00 nothing."""
    ticks = [
        Tick(at(W1, 10), "100", Held(LONG, "25", LONG_G)),
        Tick(at(W1, 11), "100", Held(LONG, "25", LONG_G), Held(SHORT, "1", SHORT_G)),
        Tick(at(W1, 12), "101", Held(LONG, "25", LONG_G),
             Held(SHORT, "1", greeks(0.50, 0.40, 0.06, -438.0, 7.0))),
        Tick(at(W1, 13), "101"),
    ]  # fmt: skip
    return position_greeks(tape(ticks, []))


def test_dec_120_each_bar_nets_the_legs_in_dollar_units() -> None:
    result = _diagonal()
    alone, both = result.series[0], result.series[1]

    assert (alone.delta, alone.gamma, alone.theta, alone.vega) == pytest.approx((80, 1, -10, 40))
    assert alone.short_open is False
    assert (both.delta, both.gamma, both.theta, both.vega) == pytest.approx(
        (80 - 30, 1 - 5, -10 + 100, 40 - 8)
    )
    assert both.short_open is True


def test_dec_120_a_bar_holding_nothing_has_no_greeks() -> None:
    flat = _diagonal().series[3]

    assert (flat.delta, flat.gamma, flat.theta, flat.vega) == (None, None, None, None)
    assert flat.short_open is False


def test_dec_120_the_table_averages_bars_with_both_legs_held() -> None:
    """11:00 and 12:00 only: the short's θ is +100 then +120, its δ −30 then −40."""
    result = _diagonal()

    theta = _row(result, "theta")
    assert (theta.long, theta.short, theta.net) == pytest.approx((-10, 110, 100))
    assert theta.bars == 2
    delta = _row(result, "delta")
    assert (delta.long, delta.short, delta.net) == pytest.approx((80, -35, 45))


def test_dec_120_each_greek_counts_the_bars_with_the_textbook_pmccs_sign() -> None:
    """+δ, −Γ, +θ, +vega: at 11:00 net Γ is 1 − 5 = −4, at 12:00 1 − 6 = −5."""
    result = _diagonal()

    assert [(r.component, r.expected_sign) for r in result.rows] == [
        ("delta", 1), ("gamma", -1), ("theta", 1), ("vega", 1),
    ]  # fmt: skip
    assert _row(result, "gamma").share_with_sign == pytest.approx(1.0)
    assert _row(result, "vega").share_with_sign == pytest.approx(1.0)


def test_dec_120_a_greek_unknown_on_a_held_leg_leaves_that_greek_out() -> None:
    """The short's vega is unknown at 11:00: the bar's net vega is null and the table's vega counts
    only 12:00, while its δ still counts both bars."""
    unknown = LegGreeks(0.50, 0.30, 0.05, -365.0, None)
    ticks = [
        Tick(at(W1, 11), "100", Held(LONG, "25", LONG_G), Held(SHORT, "1", unknown)),
        Tick(at(W1, 12), "100", Held(LONG, "25", LONG_G), Held(SHORT, "1", SHORT_G)),
    ]
    result = position_greeks(tape(ticks, []))

    assert result.series[0].vega is None
    assert result.series[0].delta == pytest.approx(50)
    assert _row(result, "vega").bars == 1
    assert _row(result, "delta").bars == 2


def test_dec_120_assigned_stock_adds_its_shares_to_net_delta() -> None:
    """After X-S5 the long and −100 shares: net δ 80 − 100 = −20; the stock has no Γ, θ or vega."""
    ticks = [Tick(at(FRI_1, 16), "108", Held(LONG, "30", LONG_G), stock=(-100, "108"))]
    point = position_greeks(tape(ticks, [])).series[0]

    assert (point.delta, point.gamma, point.theta, point.vega) == pytest.approx((-20, 1, -10, 40))


def test_dec_120_contracts_scale_every_greek() -> None:
    ticks = [Tick(at(W1, 11), "100", Held(LONG, "50", LONG_G, qty=2),
                  Held(SHORT, "2", SHORT_G, qty=2))]  # fmt: skip
    point = position_greeks(tape(ticks, [])).series[0]

    assert (point.delta, point.theta, point.vega) == pytest.approx((100, 180, 64))


def test_dec_120_no_bar_with_both_legs_leaves_the_tables_means_null() -> None:
    ticks = [Tick(at(date(2026, 9, 14), 10), "100", Held(LONG, "25", LONG_G))]
    result = position_greeks(tape(ticks, []))

    for row in result.rows:
        assert (row.long, row.short, row.net, row.share_with_sign, row.bars) == (
            None, None, None, None, 0,
        )  # fmt: skip
