"""Implied volatility from a mid, vectorized over a chain (Spec › Greeks and pricing).

Each lane is either solved or given the reason it can't be, checked in this order:

1. `EXPIRED`: no time left (T ≤ 0), which includes the expiry session's close bar.
2. `NO_QUOTE`: no mid (no valid BID/ASK).
3. `NO_SPOT`: the underlying has no price on the bar.
4. `BELOW_FLOOR`: the mid is under the no-arbitrage floor, max(0, S - K·e^(-rT)) for a call and
   max(0, K·e^(-rT) - S) for a put.
5. `ABOVE_CAP`: the mid is at or over what any vol can reach: S for a call, K·e^(-rT) for a put.
6. `NO_CONVERGENCE`: no vol in [MIN_VOL, MAX_VOL] prices the mid, or the iterations ran out.

The rest are solved by Newton's method, safeguarded: every lane keeps a bracket that holds its
root, and a lane whose Newton step would leave the bracket, or whose vega is under 1e-8, bisects
instead. A lane is done when the model price is within PRICE_TOL * max(1, mid) of the mid, or its
bracket is narrower than VOL_TOL.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import final

import numpy as np
import numpy.typing as npt

from pmcc.pricing.black_scholes import BoolArray, FloatArray, Floats, Rights, price_vega

MIN_VOL = 1e-4
MAX_VOL = 5.0
# Relative to max(1, mid). It pins vol to < 1e-6 wherever vega >= 1e-3 * max(1, mid); where the
# price barely moves with vol, the vol is looser but still reprices the mid to this (DEC-89).
PRICE_TOL = 1e-9
VOL_TOL = 1e-12
MIN_VEGA = 1e-8
MAX_ITERATIONS = 100

type CodeArray = npt.NDArray[np.int8]


class IvCode(IntEnum):
    OK = 0
    EXPIRED = 1
    NO_QUOTE = 2
    NO_SPOT = 3
    BELOW_FLOOR = 4
    ABOVE_CAP = 5
    NO_CONVERGENCE = 6


@final
@dataclass(frozen=True, slots=True)
class ImpliedVol:
    """Per lane: the vol (NaN unless solved) and its `IvCode`."""

    vol: FloatArray
    code: CodeArray


@final
@dataclass(frozen=True, slots=True)
class _Lanes:
    """The inputs, broadcast and flattened; one entry per contract."""

    mid: FloatArray
    spot: FloatArray
    strike: FloatArray
    years: FloatArray
    rate: FloatArray
    call: BoolArray

    def take(self, idx: npt.NDArray[np.intp]) -> "_Lanes":
        return _Lanes(self.mid[idx], self.spot[idx], self.strike[idx], self.years[idx],
                      self.rate[idx], self.call[idx])  # fmt: skip

    def price_vega(self, vol: FloatArray) -> tuple[FloatArray, FloatArray]:
        return price_vega(self.spot, self.strike, self.years, self.rate, vol, self.call)


def implied_vol(mid: Floats, spot: Floats, strike: Floats, years: Floats, rate: Floats,
                is_call: Rights, *,
                max_iterations: int = MAX_ITERATIONS) -> ImpliedVol:  # fmt: skip
    """The vol that prices each mid, or why there is none. Strikes must be positive."""
    arrays = np.broadcast_arrays(
        np.asarray(mid, dtype=np.float64), np.asarray(spot, dtype=np.float64),
        np.asarray(strike, dtype=np.float64), np.asarray(years, dtype=np.float64),
        np.asarray(rate, dtype=np.float64), np.asarray(is_call, dtype=np.bool_),
    )  # fmt: skip
    shape = arrays[0].shape
    lanes = _Lanes(*(np.ravel(a) for a in arrays))
    code = _screen(lanes)
    vol = np.full(code.shape, np.nan)
    todo = np.flatnonzero(code == IvCode.OK)
    solved, code[todo] = _solve(lanes.take(todo), max_iterations)
    vol[todo] = solved
    return ImpliedVol(vol.reshape(shape), code.reshape(shape))


def _screen(lanes: _Lanes) -> CodeArray:
    """Each lane's code before solving: a failure, or OK for the lanes left to solve."""
    live = lanes.years > 0
    quoted = live & np.isfinite(lanes.mid) & (lanes.mid > 0)
    priced = quoted & np.isfinite(lanes.spot) & (lanes.spot > 0)
    with np.errstate(invalid="ignore", over="ignore"):
        discounted = lanes.strike * np.exp(-lanes.rate * np.where(live, lanes.years, 0.0))
    intrinsic = np.where(lanes.call, lanes.spot - discounted, discounted - lanes.spot)
    cap = np.where(lanes.call, lanes.spot, discounted)
    conditions = [
        ~live,
        ~quoted,
        ~priced,
        lanes.mid < np.maximum(intrinsic, 0.0),
        lanes.mid >= cap,
    ]
    choices = [IvCode.EXPIRED, IvCode.NO_QUOTE, IvCode.NO_SPOT, IvCode.BELOW_FLOOR,
               IvCode.ABOVE_CAP]  # fmt: skip
    return np.select(conditions, choices, IvCode.OK).astype(np.int8)


def _solve(lanes: _Lanes, max_iterations: int) -> tuple[FloatArray, CodeArray]:
    """Safeguarded Newton on lanes that passed the screen."""
    n = lanes.mid.size
    tol = PRICE_TOL * np.maximum(1.0, lanes.mid)
    low, high = np.full(n, MIN_VOL), np.full(n, MAX_VOL)
    reachable = _in_bracket(lanes, tol)
    vol = np.clip(_start(lanes), MIN_VOL, MAX_VOL)
    done = ~reachable
    for _ in range(max_iterations):
        idx = np.flatnonzero(~done)
        if idx.size == 0:
            break
        sub = lanes.take(idx)
        model, vega = sub.price_vega(vol[idx])
        err = model - sub.mid
        converged = (np.abs(err) < tol[idx]) | (high[idx] - low[idx] < VOL_TOL)
        done[idx[converged]] = True
        rich = err > 0  # the model is dearer than the mid: the root is below this vol
        high[idx] = np.where(rich, vol[idx], high[idx])
        low[idx] = np.where(rich, low[idx], vol[idx])
        vol[idx] = np.where(
            converged, vol[idx], _next_vol(vol[idx], err, vega, low[idx], high[idx])
        )
    solved = done & reachable
    code = np.where(solved, IvCode.OK, IvCode.NO_CONVERGENCE).astype(np.int8)
    return np.where(solved, vol, np.nan), code


def _next_vol(vol: FloatArray, err: FloatArray, vega: FloatArray, low: FloatArray,
              high: FloatArray) -> FloatArray:  # fmt: skip
    """Newton's step, or the bracket's midpoint where the step leaves it or vega is too flat."""
    flat = vega < MIN_VEGA
    step = vol - err / np.where(flat, 1.0, vega)
    bisect = flat | (step <= low) | (step >= high)
    return np.where(bisect, 0.5 * (low + high), step)


def _in_bracket(lanes: _Lanes, tol: FloatArray) -> BoolArray:
    """Lanes some vol in [MIN_VOL, MAX_VOL] can price: price is increasing in vol."""
    at_min = lanes.price_vega(np.full(lanes.mid.size, MIN_VOL))[0]
    at_max = lanes.price_vega(np.full(lanes.mid.size, MAX_VOL))[0]
    return (at_min - tol <= lanes.mid) & (lanes.mid <= at_max + tol)


def _start(lanes: _Lanes) -> FloatArray:
    """Manaster and Koehler's start, sqrt(2·|ln(S/K) + rT| / T): the vol where vega peaks, from
    which Newton's steps on a Black-Scholes price move steadily toward the root."""
    moneyness = np.log(lanes.spot / lanes.strike) + lanes.rate * lanes.years
    return np.sqrt(2.0 * np.abs(moneyness) / lanes.years)
