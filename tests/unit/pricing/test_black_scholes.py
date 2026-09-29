"""Black-Scholes prices and Greeks with q = 0 (P2-01; ARCHITECTURE §7; units per DEC-24).

The reference values were computed once with mpmath at 50 significant digits from the formulas in
ARCHITECTURE §7, and match Hull's worked example (Options, Futures and Other Derivatives, 15.6:
C = 4.7594, P = 0.8086) to its four decimals.
"""

import math
from collections.abc import Callable

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pmcc.pricing.black_scholes import greeks, price

# name: (S, K, T, r, sigma), then (price, delta, gamma, theta, vega) for the call and the put
REFERENCE = {
    "hull_15_6": (
        (42.0, 40.0, 0.5, 0.10, 0.20),
        (4.7594223928715332, 0.77913129094266894, 0.049962670405911856, -4.5590921945926265,
         8.8134150596028513),
        (0.80859937290009358, -0.22086870905733106, 0.049962670405911856, -0.75417449658977046,
         8.8134150596028513),
    ),
    "atm_one_year": (
        (100.0, 100.0, 1.0, 0.05, 0.2),
        (10.450583572185567, 0.63683065117561907, 0.018762017345846894, -6.4140275464381958,
         37.524034691693788),
        (5.5735260222569677, -0.36316934882438093, 0.018762017345846894, -1.6578804239346258,
         37.524034691693788),
    ),
    "deep_itm_long": (
        (180.0, 140.0, 0.5, 0.0371, 0.45),
        (48.053665851542851, 0.84308092828159497, 0.0041942483701001563, -17.606535214085814,
         30.576070618030139),
        (5.4806047756609163, -0.15691907171840503, 0.0041942483701001563, -12.507995780001034,
         30.576070618030139),
    ),
    "otm_weekly": (
        (180.0, 190.0, 4 / 365, 0.0371, 0.5),
        (0.7682113043349021, 0.15889395351259875, 0.025707790563594913, -105.14914496472571,
         4.5640132288245216),
        (10.690977690971726, -0.84110604648740125, 0.025707790563594913, -98.103010331781483,
         4.5640132288245216),
    ),
    "deep_otm_quarter": (
        (50.0, 80.0, 0.25, 0.03, 0.3),
        (0.0026758474066164768, 0.0013133196352262811, 0.0005762614679801241,
         -0.066719119178404888, 0.10804902524627327),
        (29.404920232937691, -0.99868668036477372, 0.0005762614679801241, 2.3153482123875273,
         0.10804902524627327),
    ),
}  # fmt: skip

TOL = 1e-8


def _one(values: np.ndarray) -> float:
    return float(values.item())


@pytest.mark.parametrize("name", REFERENCE)
@pytest.mark.parametrize("is_call", [True, False], ids=["call", "put"])
def test_bs_matches_the_reference_values(name: str, is_call: bool) -> None:
    (s, k, t, r, vol), call, put = REFERENCE[name]
    want = call if is_call else put

    got_price = _one(price(s, k, t, r, vol, is_call))
    g = greeks(s, k, t, r, vol, is_call)

    assert got_price == pytest.approx(want[0], abs=TOL)
    assert _one(g.delta) == pytest.approx(want[1], abs=TOL)
    assert _one(g.gamma) == pytest.approx(want[2], abs=TOL)
    assert _one(g.theta) == pytest.approx(want[3], abs=TOL)
    assert _one(g.vega) == pytest.approx(want[4], abs=TOL)


def test_bs_prices_a_whole_chain_at_once() -> None:
    strikes = np.array([40.0, 100.0, 140.0])
    rights = np.array([True, False, True])

    got = price(np.array([42.0, 100.0, 180.0]), strikes, np.array([0.5, 1.0, 0.5]),
                np.array([0.10, 0.05, 0.0371]), np.array([0.20, 0.2, 0.45]), rights)  # fmt: skip

    assert got == pytest.approx(
        [REFERENCE["hull_15_6"][1][0], REFERENCE["atm_one_year"][2][0],
         REFERENCE["deep_itm_long"][1][0]], abs=TOL,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("field", "value"),
    [("spot", 0.0), ("strike", -1.0), ("years", 0.0), ("vol", 0.0), ("spot", math.nan),
     ("years", math.inf)],
)  # fmt: skip
def test_bs_refuses_inputs_outside_its_domain(field: str, value: float) -> None:
    args = {"spot": 100.0, "strike": 100.0, "years": 0.5, "rate": 0.03, "vol": 0.3}
    args[field] = value

    with pytest.raises(ValueError, match=field):
        price(args["spot"], args["strike"], args["years"], args["rate"], args["vol"], True)


# Spot, strike ratio, years, rate and vol over what the backtest meets: weekly shorts to
# long-dated monthlies, from deep in the money to far out.
spots = st.floats(5.0, 1000.0)
moneyness = st.floats(0.5, 1.6)
years = st.floats(1 / 365, 1.0)
rates = st.floats(0.0, 0.08)
vols = st.floats(0.05, 2.0)


@given(spots, moneyness, years, rates, vols)
def test_bs_put_call_parity_holds(s: float, m: float, t: float, r: float, vol: float) -> None:
    k = s * m

    parity = _one(price(s, k, t, r, vol, True)) - _one(price(s, k, t, r, vol, False))

    assert parity == pytest.approx(s - k * math.exp(-r * t), abs=1e-9 * s)


def _central(f: Callable[[float], float], x: float, h: float) -> float:
    return (f(x + h) - f(x - h)) / (2 * h)


def _spot_step(s: float, t: float, vol: float) -> float:
    """A spot step small against the curve's width, S·sigma·sqrt(T), which a short, calm option
    makes narrow."""
    return 1e-3 * s * vol * math.sqrt(t)


@given(spots, moneyness, years, rates, vols, st.booleans())
def test_bs_delta_is_the_price_slope_in_spot(
    s: float, m: float, t: float, r: float, vol: float, is_call: bool
) -> None:
    k = s * m
    slope = _central(lambda x: _one(price(x, k, t, r, vol, is_call)), s, _spot_step(s, t, vol))

    assert _one(greeks(s, k, t, r, vol, is_call).delta) == pytest.approx(slope, rel=1e-5, abs=1e-7)


@given(spots, moneyness, years, rates, vols, st.booleans())
def test_bs_gamma_is_the_delta_slope_in_spot(
    s: float, m: float, t: float, r: float, vol: float, is_call: bool
) -> None:
    k = s * m
    slope = _central(
        lambda x: _one(greeks(x, k, t, r, vol, is_call).delta), s, _spot_step(s, t, vol)
    )

    assert _one(greeks(s, k, t, r, vol, is_call).gamma) == pytest.approx(
        slope, rel=1e-4, abs=1e-7 / s
    )


@given(spots, moneyness, years, rates, vols, st.booleans())
def test_bs_theta_is_the_price_change_per_year_as_expiry_nears(
    s: float, m: float, t: float, r: float, vol: float, is_call: bool
) -> None:
    k = s * m
    h = 1e-4 * t
    # theta is dV/dt as calendar time passes, so T shrinks: -dV/dT (DEC-24: per year)
    slope = -_central(lambda x: _one(price(s, k, x, r, vol, is_call)), t, h)

    assert _one(greeks(s, k, t, r, vol, is_call).theta) == pytest.approx(slope, rel=1e-4, abs=1e-4)


@given(spots, moneyness, years, rates, vols, st.booleans())
def test_bs_vega_is_the_price_change_per_unit_of_vol(
    s: float, m: float, t: float, r: float, vol: float, is_call: bool
) -> None:
    k = s * m
    # DEC-24: vega per 1.00 of volatility, so dV/dsigma with sigma in vol units
    slope = _central(lambda x: _one(price(s, k, t, r, x, is_call)), vol, 1e-5)

    assert _one(greeks(s, k, t, r, vol, is_call).vega) == pytest.approx(slope, rel=1e-5, abs=1e-6)
