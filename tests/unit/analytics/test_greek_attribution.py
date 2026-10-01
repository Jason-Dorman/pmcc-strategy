"""Greek attribution (P6-04; PO, DEC-63, DEC-76), worked by hand on small runs
(`tests/fakes/legs.py`). DEC-24 units: θ per year, vega per 1.00 of vol, Δt in elapsed years (an
hour is 1/8,760). No fees here unless a test says so."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from pmcc.analytics.greek_attribution import greek_attribution
from pmcc.domain.clock import ET
from pmcc.domain.instruments import Side
from pmcc.domain.money import Money
from pmcc.export.analytics_models import GreekAttribution, GreekLeg, GreekRow
from tests.fakes.legs import Held, Tick, greeks, tape, with_iv
from tests.fakes.records import FRI_1, LONG, STOCK, W1, Records, at, short_call, trade

NO_FEE = Money.zero()
HOUR = 1 / 8760
SHORT = short_call(FRI_1)
G0 = greeks(0.50, 0.80, 0.01, -10.0, 30.0)
G1 = greeks(0.52, 0.82, 0.01, -11.0, 29.0)


def _long_run() -> Records:
    """The $80 long, bought at its $40.00 mid at 10:00 (spot 100), marked $42.22 at 11:00 (spot
    102), sold at $43.00 at 12:00 (spot 103) at an IV of 0.51.

    - 11:00, G0's Greeks: δ 0.80 × 2 = 1.60; ½ × 0.01 × 2² = 0.02; −10 × 1/8,760; 30 × (0.52 −
      0.50) = 0.60; × 100: 160, 2, −0.114155, 60. Actual 222, residual +0.114155.
    - 12:00, G1's: 0.82 × 1; ½ × 0.01 × 1; −11/8,760; 29 × (0.51 − 0.52) = −0.29; × 100: 82, 0.5,
      −0.125571, −29. Actual 78, residual +24.625571.
    """
    ticks = [
        Tick(at(W1, 10), "100", Held(LONG, "40", G0)),
        Tick(at(W1, 11), "102", Held(LONG, "42.22", G1)),
        Tick(at(W1, 12), "103"),
    ]
    blotter = [
        with_iv(trade(at(W1, 10), Side.BUY, LONG, "40.00", "E-L1", NO_FEE), 0.50),
        with_iv(trade(at(W1, 12), Side.SELL, LONG, "43.00", "X-L1", NO_FEE), 0.51),
    ]
    return tape(ticks, blotter)


def _row(result: GreekAttribution, leg: str, component: str) -> GreekRow:
    return next(r for r in result.rows if (r.leg, r.component) == (leg, component))


def _dollars(result: GreekAttribution, leg: str) -> dict[str, float]:
    return {r.component: r.dollars for r in result.rows if r.leg == leg}


def test_dec_63_each_held_bar_is_priced_with_the_previous_bars_greeks() -> None:
    result = greek_attribution(_long_run())

    assert _dollars(result, "long") == pytest.approx({
        "delta": 160 + 82, "gamma": 2 + 0.5, "theta": -100 * 21 * HOUR, "vega": 60 - 29,
        "residual": 300 - (242 + 2.5 - 100 * 21 * HOUR + 31),
    })  # fmt: skip


def test_dec_63_a_legs_components_add_up_to_its_change_and_their_shares_to_one() -> None:
    result = greek_attribution(_long_run())
    long = [r for r in result.rows if r.leg == "long"]

    assert result.legs[0] == GreekLeg(leg="long", change=Decimal(300), bars_held=2,
                                      bars_unattributed=0)  # fmt: skip
    assert sum(r.dollars for r in long) == pytest.approx(300)
    assert sum(r.share_of_change or 0 for r in long) == pytest.approx(1)
    assert _row(result, "long", "delta").share_of_change == pytest.approx(242 / 300)


def test_dec_63_a_closed_legs_iv_at_the_bar_is_its_fills() -> None:
    """The 12:00 vega term is 29 × (0.51 − 0.52) × 100 = −29, from the sale's `fill_iv`."""
    vega = _dollars(greek_attribution(_long_run()), "long")["vega"]

    assert vega == pytest.approx(60 - 29)


def test_dec_63_each_leg_closed_on_one_bar_takes_its_own_fills_iv() -> None:
    """At 11:00 (spot 101) X-L1 sells the long at IV 0.51, then X-S1 buys the short back at IV
    0.45, as the engine books them (the long check before the short's exits).

    - Long, G0: 0.80 × 1, ½ × 0.01 × 1, −10/8,760, 30 × (0.51 − 0.50); × 100: 80, 0.5,
      −0.114155, 30. Actual 100.
    - Short (IV 0.40, δ 0.30, Γ 0.02, θ −40, vega 10): its buyback is a BUY, and its own IV is
      0.45, not the long's 0.51. −100 × (0.30, 0.01, −40/8,760, 10 × 0.05) = −30, −1,
      +0.456621, −50. Actual −30.
    """
    short_greeks = greeks(0.40, 0.30, 0.02, -40.0, 10.0)
    ticks = [
        Tick(at(W1, 10), "100", Held(LONG, "40", G0), Held(SHORT, "2.00", short_greeks)),
        Tick(at(W1, 11), "101"),
    ]
    blotter = [
        with_iv(trade(at(W1, 10), Side.BUY, LONG, "40.00", "E-L1", NO_FEE), 0.50),
        with_iv(trade(at(W1, 10), Side.SELL, SHORT, "2.00", "E-S1", NO_FEE), 0.40),
        with_iv(trade(at(W1, 11), Side.SELL, LONG, "41.00", "X-L1", NO_FEE), 0.51),
        with_iv(trade(at(W1, 11), Side.BUY, SHORT, "2.30", "X-S1", NO_FEE), 0.45),
    ]
    result = greek_attribution(tape(ticks, blotter))

    assert [(g.bars_held, g.bars_unattributed) for g in result.legs] == [(1, 0), (1, 0)]
    assert _dollars(result, "long") == pytest.approx({
        "delta": 80, "gamma": 0.5, "theta": -1000 * HOUR, "vega": 30,
        "residual": 100 - 80 - 0.5 + 1000 * HOUR - 30,
    })  # fmt: skip
    assert _dollars(result, "short") == pytest.approx({
        "delta": -30, "gamma": -1, "theta": 4000 * HOUR, "vega": -50,
        "residual": -30 + 30 + 1 - 4000 * HOUR + 50,
    })  # fmt: skip


def test_dec_63_an_assignments_stock_stays_out_of_both_legs() -> None:
    """The $105 short (marked $1.00) is assigned at Friday's close, spot 108: its $1.00 liability
    goes with no cash, so the short's change is +100 there, residual whole (no fill IV), and its
    run total is the credit, +100. The stock sold at $105 (+10,500) and covered Monday at $108.50
    (−10,850) is neither leg's: the long, marked $30 throughout, changes by 0."""
    short_greeks = greeks(0.40, 0.30, 0.02, -40.0, 10.0)
    ticks = [
        Tick(at(FRI_1, 15), "104", Held(LONG, "30", G0), Held(SHORT, "1.00", short_greeks)),
        Tick(at(FRI_1, 16), "108", Held(LONG, "30", G0), stock=(-100, "108")),
        Tick(at(date(2026, 9, 21), 10), "108.50", Held(LONG, "30", G0)),
    ]
    blotter = [
        trade(at(FRI_1, 15), Side.BUY, LONG, "30.00", "E-L1", NO_FEE),
        trade(at(FRI_1, 15), Side.SELL, SHORT, "1.00", "E-S1", NO_FEE),
        trade(at(FRI_1, 16), Side.ASSIGN, SHORT, None, "X-S5"),
        trade(at(FRI_1, 16), Side.SELL, STOCK, "105", "X-S5"),
        trade(at(date(2026, 9, 21), 10), Side.BUY, STOCK, "108.50", "X-S5"),
    ]
    result = greek_attribution(tape(ticks, blotter))

    assert [g.change for g in result.legs] == [Decimal(0), Decimal(100)]
    assert (result.legs[1].bars_held, result.legs[1].bars_unattributed) == (1, 1)
    assert _dollars(result, "short")["residual"] == 100


def test_dec_63_the_terms_scale_with_the_contracts_held() -> None:
    """Two contracts of `_long_run`'s first bar: every term and the change double (δ 320, Γ 4,
    θ −0.228311, vega 120; actual 444)."""
    ticks = [
        Tick(at(W1, 10), "100", Held(LONG, "40", G0, qty=2)),
        Tick(at(W1, 11), "102", Held(LONG, "42.22", G1, qty=2)),
    ]
    blotter = [trade(at(W1, 10), Side.BUY, LONG, "40.00", "E-L1", NO_FEE, contracts=2)]
    result = greek_attribution(tape(ticks, blotter))

    assert result.legs[0].change == Decimal(444)
    assert _dollars(result, "long") == pytest.approx({
        "delta": 320, "gamma": 4, "theta": -2000 * HOUR, "vega": 120,
        "residual": 444 - 320 - 4 + 2000 * HOUR - 120,
    })  # fmt: skip


def test_dec_76_the_residual_line_runs_bar_by_bar_over_both_legs() -> None:
    result = greek_attribution(_long_run())

    assert [p.time for p in result.residual] == [at(W1, 10), at(W1, 11), at(W1, 12)]
    assert [p.cumulative for p in result.residual] == pytest.approx(
        [0, 100 * HOUR * 10, 100 * HOUR * 21 + 24.5])  # fmt: skip


def test_dec_76_a_leg_never_held_has_no_change_and_no_share() -> None:
    result = greek_attribution(_long_run())

    assert result.legs[1] == GreekLeg(leg="short", change=Decimal(0), bars_held=0,
                                      bars_unattributed=0)  # fmt: skip
    assert [r.component for r in result.rows if r.leg == "short"] == [
        "delta", "gamma", "theta", "vega", "residual"]  # fmt: skip
    assert all(r.share_of_change is None for r in result.rows if r.leg == "short")


def test_dec_63_the_short_legs_terms_carry_the_positions_sign() -> None:
    """Sold at $2.00 (spot 100; IV 0.40, δ 0.30, Γ 0.02, θ −40, vega 10), marked $2.40 an hour later
    (spot 101, IV 0.41): −100 × (0.30, 0.01, −40/8,760, 0.10) = −30, −1, +0.456621, −10; the
    short lost 40, so the residual is +0.543379."""
    ticks = [
        Tick(at(W1, 10), "100", short=Held(SHORT, "2.00", greeks(0.40, 0.30, 0.02, -40.0, 10.0))),
        Tick(at(W1, 11), "101", short=Held(SHORT, "2.40", greeks(0.41, 0.31, 0.02, -41.0, 10.0))),
    ]
    blotter = [with_iv(trade(at(W1, 10), Side.SELL, SHORT, "2.00", "E-S1", NO_FEE), 0.40)]
    result = greek_attribution(tape(ticks, blotter))

    assert result.legs[1].change == Decimal(-40)
    assert _dollars(result, "short") == pytest.approx({
        "delta": -30, "gamma": -1, "theta": 4000 * HOUR, "vega": -10,
        "residual": -40 + 30 + 1 - 4000 * HOUR + 10,
    })  # fmt: skip


def test_dec_63_a_stale_mark_makes_both_its_bars_residual_and_counts_them() -> None:
    """11:00 carries 10:00's $40 mark, stale: 10:00 → 11:00 ends stale and 11:00 → 12:00 starts
    stale, so both are residual whole (0, then 300)."""
    ticks = [
        Tick(at(W1, 10), "100", Held(LONG, "40", G0)),
        Tick(at(W1, 11), "102", Held(LONG, "40", stale=True)),
        Tick(at(W1, 12), "103", Held(LONG, "43", G1)),
    ]
    blotter = [trade(at(W1, 10), Side.BUY, LONG, "40.00", "E-L1", NO_FEE)]
    result = greek_attribution(tape(ticks, blotter))

    assert result.legs[0].bars_unattributed == 2
    assert _dollars(result, "long") == {"delta": 0, "gamma": 0, "theta": 0, "vega": 0,
                                        "residual": 300}  # fmt: skip


def test_dec_63_a_failed_iv_makes_the_bar_residual_even_with_dec_27s_greeks() -> None:
    """Under its floor the long has DEC-27's Greeks (δ 1, Γ = vega = 0) but no IV: 10:00 → 11:00 is
    residual whole; 11:00 → 12:00 is priced (δ 0.82 × 1 × 100 = 82, …)."""
    floor = greeks(None, 1.0, 0.0, -3.0, 0.0)
    ticks = [
        Tick(at(W1, 10), "100", Held(LONG, "20", floor)),
        Tick(at(W1, 11), "102", Held(LONG, "22", G1)),
        Tick(at(W1, 12), "103", Held(LONG, "23", G1)),
    ]
    blotter = [trade(at(W1, 10), Side.BUY, LONG, "20.00", "E-L1", NO_FEE)]
    result = greek_attribution(tape(ticks, blotter))

    assert (result.legs[0].bars_held, result.legs[0].bars_unattributed) == (2, 1)
    assert _dollars(result, "long")["delta"] == pytest.approx(82)


def test_dec_63_a_bar_without_a_spot_is_residual() -> None:
    ticks = [
        Tick(at(W1, 10), "100", Held(LONG, "40", G0)),
        Tick(at(W1, 11), None, Held(LONG, "42", G1)),
    ]
    blotter = [trade(at(W1, 10), Side.BUY, LONG, "40.00", "E-L1", NO_FEE)]
    result = greek_attribution(tape(ticks, blotter))

    assert result.legs[0].bars_unattributed == 1
    assert _dollars(result, "long")["residual"] == 200


def test_dec_63_an_expiry_has_no_iv_so_its_bar_is_residual() -> None:
    """X-S4 at Friday's close: the short leaves at $0 with no fill IV (T is 0), so the bar's
    change, the $0.10 liability gone (+10), is residual whole."""
    ticks = [
        Tick(at(FRI_1, 15), "100", short=Held(SHORT, "0.10", greeks(0.9, 0.02, 0.01, -50.0, 1.0))),
        Tick(at(FRI_1, 16), "100"),
    ]
    blotter = [
        trade(at(FRI_1, 15), Side.SELL, SHORT, "0.10", "E-S1", NO_FEE),
        trade(at(FRI_1, 16), Side.EXPIRE, SHORT, "0", "X-S4"),
    ]
    result = greek_attribution(tape(ticks, blotter))

    assert result.legs[1].bars_unattributed == 1
    assert _dollars(result, "short")["residual"] == 10


def test_dec_24_theta_runs_on_elapsed_time_across_a_clock_change() -> None:
    """Fri Oct 30 16:00 to Mon Nov 2 10:00 ET is 66 hours on the wall clock but 67 elapsed (the
    clocks go back on Nov 1): θ −8.76 a year is −0.001 an hour, so −0.067 × 100 = −6.7."""
    friday, monday = datetime(2026, 10, 30, 16, tzinfo=ET), datetime(2026, 11, 2, 10, tzinfo=ET)
    g = greeks(0.5, 0.0, 0.0, -8.76, 0.0)
    ticks = [Tick(friday, "100", Held(LONG, "40", g)), Tick(monday, "100", Held(LONG, "40", g))]
    blotter = [trade(friday, Side.BUY, LONG, "40.00", "E-L1", NO_FEE)]

    assert _dollars(greek_attribution(tape(ticks, blotter)), "long")["theta"] == pytest.approx(-6.7)


def test_p6_04_an_entrys_friction_and_fee_fall_in_the_residual_on_no_held_bar() -> None:
    """Bought at $40.10 against a $40.00 mid, with a $0.65 fee: the bar's change is 4,000 −
    4,010.65 = −10.65, all residual, and the long wasn't held when the bar began."""
    ticks = [Tick(at(W1, 10), "100", Held(LONG, "40", G0))]
    result = greek_attribution(tape(ticks, [trade(at(W1, 10), Side.BUY, LONG, "40.10", "E-L1")]))

    assert result.legs[0] == GreekLeg(leg="long", change=Decimal("-10.65"), bars_held=0,
                                      bars_unattributed=0)  # fmt: skip
    assert _dollars(result, "long")["residual"] == pytest.approx(-10.65)


def test_p6_04_a_reentered_long_on_the_same_bar_is_priced_on_the_one_sold() -> None:
    """X-L2 at 11:00 sells the $80 long at $43.00 (IV 0.51) and buys another at $50.00 marked
    $50: the bar's change is 4,300 − 4,222 (the sale) + 5,000 − 5,000 (the new long) = 78, and the
    prediction is the $80's, as in `_long_run`'s last bar (82, 0.5, −11/8,760 × 100, −29)."""
    other = short_call(date(2027, 3, 19))  # any second contract on the long side
    ticks = [
        Tick(at(W1, 11), "102", Held(LONG, "42.22", G1)),
        Tick(at(W1, 12), "103", Held(other, "50", G0)),
    ]
    blotter = [
        with_iv(trade(at(W1, 11), Side.BUY, LONG, "42.22", "E-L1", NO_FEE), 0.52),
        with_iv(trade(at(W1, 12), Side.SELL, LONG, "43.00", "X-L2", NO_FEE), 0.51),
        with_iv(trade(at(W1, 12), Side.BUY, other, "50.00", "E-L1", NO_FEE), 0.50),
    ]
    result = greek_attribution(tape(ticks, blotter))

    assert result.legs[0].change == Decimal(78)
    assert _dollars(result, "long") == pytest.approx({
        "delta": 82, "gamma": 0.5, "theta": -1100 * HOUR, "vega": -29,
        "residual": 78 - 82 - 0.5 + 1100 * HOUR + 29,
    })  # fmt: skip
