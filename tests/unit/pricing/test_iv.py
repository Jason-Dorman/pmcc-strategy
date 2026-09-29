"""The vectorized IV solver (P2-02; ARCHITECTURE §7): Newton with a bisection fallback.

The reference is a scalar `scipy.optimize.brentq` solve on the same bracket. "Solvable" means
the reference finds a root there and the mid pins the vol down: vega at the root is at least
1e-3 * max(1, mid), so the solver's price tolerance (1e-9 * max(1, mid)) is under 1e-6 of vol.
Where the mid barely moves with vol, many vols price it equally well; those lanes are checked on
price instead.
"""

import math

import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from scipy.optimize import brentq

from pmcc.pricing import iv as iv_module
from pmcc.pricing.black_scholes import greeks, price
from pmcc.pricing.iv import MAX_VOL, MIN_VOL, PRICE_TOL, IvCode, implied_vol


def _mid(s: float, k: float, t: float, r: float, vol: float, is_call: bool) -> float:
    return float(price(s, k, t, r, vol, is_call).item())


def _solve(mid: float, s: float, k: float, t: float, r: float, is_call: bool) -> tuple[float, int]:
    got = implied_vol(mid, s, k, t, r, is_call)
    return float(got.vol.item()), int(got.code.item())


def _reference(mid: float, s: float, k: float, t: float, r: float, is_call: bool) -> float | None:
    def gap(vol: float) -> float:
        return _mid(s, k, t, r, vol, is_call) - mid

    if gap(MIN_VOL) > 0 or gap(MAX_VOL) < 0:
        return None
    return brentq(gap, MIN_VOL, MAX_VOL, xtol=1e-15, rtol=1e-15, maxiter=500)


spots = st.floats(5.0, 1000.0)
moneyness = st.floats(0.5, 1.6)
years = st.floats(1 / (365 * 24), 1.0)
rates = st.floats(0.0, 0.08)
vols = st.floats(0.02, 3.0)


@given(spots, moneyness, years, rates, vols, st.booleans())
def test_iv_matches_the_brentq_reference_where_solvable(
    s: float, m: float, t: float, r: float, vol: float, is_call: bool
) -> None:
    k = s * m
    mid = _mid(s, k, t, r, vol, is_call)
    assume(mid > 0)  # a quote is never free; a vol this low can price a far option at 0.0
    ref = _reference(mid, s, k, t, r, is_call)
    assume(ref is not None)
    assert ref is not None
    assume(float(greeks(s, k, t, r, ref, is_call).vega.item()) >= 1e-3 * max(1.0, mid))

    got, code = _solve(mid, s, k, t, r, is_call)

    assert code == IvCode.OK
    assert abs(got - ref) < 1e-6


@given(spots, moneyness, years, rates, vols, st.booleans())
def test_iv_a_solved_vol_reprices_the_mid(
    s: float, m: float, t: float, r: float, vol: float, is_call: bool
) -> None:
    k = s * m
    mid = _mid(s, k, t, r, vol, is_call)
    assume(mid > 0)  # a quote is never free; a vol this low can price a far option at 0.0

    got, code = _solve(mid, s, k, t, r, is_call)

    if code == IvCode.OK:
        assert MIN_VOL <= got <= MAX_VOL
        assert abs(_mid(s, k, t, r, got, is_call) - mid) < PRICE_TOL * max(1.0, mid)
    else:
        assert math.isnan(got)
        assert _reference(mid, s, k, t, r, is_call) is None


@given(st.lists(st.tuples(spots, moneyness, years, vols, st.booleans()), min_size=1, max_size=40))
def test_iv_solves_each_lane_as_if_alone(
    lanes: list[tuple[float, float, float, float, bool]],
) -> None:
    s = np.array([lane[0] for lane in lanes])
    k = s * np.array([lane[1] for lane in lanes])
    t = np.array([lane[2] for lane in lanes])
    call = np.array([lane[4] for lane in lanes])
    mid = price(s, k, t, 0.03, np.array([lane[3] for lane in lanes]), call)

    together = implied_vol(mid, s, k, t, 0.03, call)

    for i in range(len(lanes)):
        alone = implied_vol(float(mid[i]), float(s[i]), float(k[i]), float(t[i]), 0.03,
                            bool(call[i]))  # fmt: skip
        assert together.code[i] == alone.code.item()
        np.testing.assert_array_equal(together.vol[i], alone.vol.item())


@pytest.mark.parametrize(
    ("start", "k"),
    [(MIN_VOL, 160.0), (MAX_VOL, 160.0), (0.2, 60.0)],
    ids=["flat vega at the floor", "step below the bracket", "step past the bracket's top"],
)
def test_iv_bisects_where_newton_cant_step(
    monkeypatch: pytest.MonkeyPatch, start: float, k: float
) -> None:
    # From these starts Newton alone fails: a far out-of-the-money call's vega at the bracket's
    # floor is under 1e-8, and elsewhere its step leaves the bracket. Only the fallback reaches
    # the root.
    def fixed_start(_lanes: object) -> np.ndarray:
        return np.array([start])  # one lane

    monkeypatch.setattr(iv_module, "_start", fixed_start)
    s, t, r = 100.0, 0.25, 0.03
    mid = _mid(s, k, t, r, 0.6, True)

    got, code = _solve(mid, s, k, t, r, True)

    assert code == IvCode.OK
    assert got == pytest.approx(0.6, abs=1e-6)


def test_iv_keeps_the_broadcast_shape() -> None:
    mid = np.array([[5.0, 6.0], [7.0, 8.0]])

    got = implied_vol(mid, 100.0, 100.0, 0.5, 0.03, True)

    assert got.vol.shape == (2, 2)
    assert got.code.shape == (2, 2)
    assert (got.code == IvCode.OK).all()


# ---- failure codes (ARCHITECTURE §7)


def test_iv_no_quote_when_the_mid_is_missing_or_not_positive() -> None:
    got = implied_vol(np.array([math.nan, 0.0, -1.0]), 100.0, 100.0, 0.5, 0.03, True)

    assert list(got.code) == [IvCode.NO_QUOTE] * 3
    assert np.isnan(got.vol).all()


def test_iv_no_spot_when_the_underlying_has_no_price() -> None:
    got = implied_vol(5.0, np.array([math.nan, 0.0]), 100.0, 0.5, 0.03, True)

    assert list(got.code) == [IvCode.NO_SPOT] * 2


@pytest.mark.parametrize("t", [0.0, -0.01, math.nan])
def test_iv_expired_when_no_time_is_left(t: float) -> None:
    assert _solve(5.0, 100.0, 100.0, t, 0.03, True) == (pytest.approx(math.nan, nan_ok=True),
                                                        IvCode.EXPIRED)  # fmt: skip


def test_iv_below_floor_just_under_a_calls_discounted_intrinsic() -> None:
    s, k, t, r = 180.0, 100.0, 0.5, 0.0371
    floor = s - k * math.exp(-r * t)

    assert _solve(floor - 1e-4, s, k, t, r, True)[1] == IvCode.BELOW_FLOOR
    assert _solve(floor, s, k, t, r, True)[1] == IvCode.OK  # on the floor: vol near zero solves


def test_iv_below_floor_just_under_a_puts_discounted_intrinsic() -> None:
    s, k, t, r = 100.0, 180.0, 0.5, 0.0371
    floor = k * math.exp(-r * t) - s

    assert _solve(floor - 1e-4, s, k, t, r, False)[1] == IvCode.BELOW_FLOOR
    assert _solve(floor, s, k, t, r, False)[1] == IvCode.OK


def test_iv_above_cap_at_or_over_spot_for_a_call() -> None:
    assert _solve(100.0, 100.0, 90.0, 0.5, 0.03, True)[1] == IvCode.ABOVE_CAP
    assert _solve(100.0 - 1e-4, 100.0, 90.0, 0.5, 0.03, True)[1] != IvCode.ABOVE_CAP


def test_iv_above_cap_at_or_over_the_discounted_strike_for_a_put() -> None:
    cap = 90.0 * math.exp(-0.03 * 0.5)

    assert _solve(cap, 100.0, 90.0, 0.5, 0.03, False)[1] == IvCode.ABOVE_CAP
    assert _solve(cap - 1e-4, 100.0, 90.0, 0.5, 0.03, False)[1] != IvCode.ABOVE_CAP


def test_iv_no_convergence_when_no_vol_in_the_bracket_prices_the_mid() -> None:
    # Under the cap, but dearer than a 500% vol makes it.
    too_dear = _mid(100.0, 100.0, 0.5, 0.03, MAX_VOL, True) + 0.5

    assert too_dear < 100.0
    assert _solve(too_dear, 100.0, 100.0, 0.5, 0.03, True)[1] == IvCode.NO_CONVERGENCE


def test_iv_no_convergence_when_the_iterations_run_out() -> None:
    mid = _mid(100.0, 130.0, 0.1, 0.03, 0.4, True)

    got = implied_vol(mid, 100.0, 130.0, 0.1, 0.03, True, max_iterations=1)

    assert got.code.item() == IvCode.NO_CONVERGENCE
    assert math.isnan(float(got.vol.item()))


def test_iv_expired_outranks_the_other_codes() -> None:
    got = implied_vol(math.nan, math.nan, 100.0, 0.0, 0.03, True)

    assert got.code.item() == IvCode.EXPIRED


def test_iv_no_quote_outranks_no_spot() -> None:
    # So a bar counts as an IV failure only when the contract itself had a valid quote.
    assert implied_vol(math.nan, math.nan, 100.0, 0.5, 0.03, True).code.item() == IvCode.NO_QUOTE
