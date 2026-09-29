"""Black-Scholes prices and Greeks with q = 0, vectorized (Spec › Greeks and pricing).

Units (PO, DEC-24): T in years (ACT/365, `pricing.expiry`); δ per $1 of spot; Γ per $1²; θ per
year of calendar time, as the value changes while T shrinks; vega per 1.00 of volatility.
The formulas are ARCHITECTURE §7's.

Every argument broadcasts, so one call prices a whole chain snapshot. `price` and `greeks` refuse
inputs outside the model's domain. `price_vega` doesn't check: it is the IV solver's inner loop,
and the solver hands it only lanes it has already checked.
"""

from dataclasses import dataclass
from typing import final

import numpy as np
import numpy.typing as npt
from scipy.special import ndtr

type FloatArray = npt.NDArray[np.float64]
type BoolArray = npt.NDArray[np.bool_]
type Floats = float | FloatArray
type Rights = bool | BoolArray

_INV_SQRT_2PI = 1.0 / np.sqrt(2.0 * np.pi)


@final
@dataclass(frozen=True, slots=True)
class Greeks:
    """Delta, gamma, theta and vega, each shaped like the broadcast inputs (DEC-24 units)."""

    delta: FloatArray
    gamma: FloatArray
    theta: FloatArray
    vega: FloatArray


def price(spot: Floats, strike: Floats, years: Floats, rate: Floats, vol: Floats,
          is_call: Rights) -> FloatArray:  # fmt: skip
    """The call price where `is_call`, else the put price."""
    s, k, t, r, v = _checked(spot, strike, years, rate, vol)
    return price_vega(s, k, t, r, v, np.asarray(is_call, dtype=np.bool_))[0]


def greeks(spot: Floats, strike: Floats, years: Floats, rate: Floats, vol: Floats,
           is_call: Rights) -> Greeks:  # fmt: skip
    s, k, t, r, v = _checked(spot, strike, years, rate, vol)
    call = np.asarray(is_call, dtype=np.bool_)
    root_t = np.sqrt(t)
    d1, d2 = _d1_d2(s, k, t, r, v)
    pdf = _pdf(d1)
    discounted = k * np.exp(-r * t)
    decay = -s * pdf * v / (2.0 * root_t)
    return Greeks(
        delta=np.where(call, _cdf(d1), _cdf(d1) - 1.0),
        gamma=pdf / (s * v * root_t),
        theta=np.where(call, decay - r * discounted * _cdf(d2), decay + r * discounted * _cdf(-d2)),
        vega=s * pdf * root_t,
    )


def price_vega(spot: FloatArray, strike: FloatArray, years: FloatArray, rate: FloatArray,
               vol: FloatArray, is_call: BoolArray) -> tuple[FloatArray, FloatArray]:  # fmt: skip
    """Price and vega, unchecked: every spot, strike, T and vol must be finite and positive."""
    d1, d2 = _d1_d2(spot, strike, years, rate, vol)
    discounted = strike * np.exp(-rate * years)
    call = spot * _cdf(d1) - discounted * _cdf(d2)
    put = discounted * _cdf(-d2) - spot * _cdf(-d1)
    return np.where(is_call, call, put), spot * _pdf(d1) * np.sqrt(years)


def _d1_d2(s: FloatArray, k: FloatArray, t: FloatArray, r: FloatArray,
           v: FloatArray) -> tuple[FloatArray, FloatArray]:  # fmt: skip
    spread = v * np.sqrt(t)
    d1 = (np.log(s / k) + (r + 0.5 * v * v) * t) / spread
    return d1, d1 - spread


def _cdf(x: FloatArray) -> FloatArray:
    return np.asarray(ndtr(x), dtype=np.float64)


def _pdf(x: FloatArray) -> FloatArray:
    return _INV_SQRT_2PI * np.exp(-0.5 * x * x)


def _checked(spot: Floats, strike: Floats, years: Floats, rate: Floats,
             vol: Floats) -> tuple[FloatArray, ...]:  # fmt: skip
    named = {"spot": spot, "strike": strike, "years": years, "rate": rate, "vol": vol}
    arrays = {name: np.asarray(value, dtype=np.float64) for name, value in named.items()}
    for name, values in arrays.items():
        if not np.isfinite(values).all():
            raise ValueError(f"{name} must be finite")
        if name != "rate" and not (values > 0).all():
            raise ValueError(f"{name} must be positive")
    return tuple(arrays.values())
