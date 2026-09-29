"""The chain pricer: IV, Greeks and eligibility for every contract on every session bar (P2-04).

- **One bar** (`price_quotes`): each contract's mid is (BID + ASK) / 2 of a valid quote, exact
  (not rounded to $0.0001), and its IV is solved from that mid with the bar's spot and T. A
  contract is **eligible** only when its IV solves (Spec › Greeks and pricing).
- **Held contracts (PO, DEC-27):** a call whose mid is under the no-arbitrage floor gets the
  zero-vol limit of a deep ITM call: δ = 1, Γ = vega = 0, θ = -r·K·e^(-rT). It stays ineligible, so
  selection never picks it, but X-S2 and X-L1 still see a deep ITM leg. Every other failure leaves
  the Greeks unknown (NaN). Only calls are ever held, so a put below its floor gets no Greeks.
- **A whole symbol** (`price_symbol`): every session bar of every chain unit, priced in one
  vectorized pass per unit. Spot is the underlying's TRDPRC_1 on the same bar (DEC-23), and T runs
  to the expiry session's close (DEC-24). `PricedSymbol.snapshot` slices one bar of one unit and
  keeps it, so every run over the symbol shares it.

Pricing is per bar and uses only that bar's rows. Which contracts are *listed* at a bar, and the
rule that only fresh quotes trigger rules (DEC-27), are MarketView's (P3-02).
"""

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import final

import numpy as np
import numpy.typing as npt
import polars as pl

from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import to_et
from pmcc.domain.instruments import Right
from pmcc.domain.money import UNITS_PER_CENT, UNITS_PER_DOLLAR, Price
from pmcc.domain.sessions import Session
from pmcc.pricing.black_scholes import BoolArray, FloatArray, Floats, Rights, greeks
from pmcc.pricing.expiry import years_to_expiry
from pmcc.pricing.iv import CodeArray, ImpliedVol, IvCode, implied_vol

type IntArray = npt.NDArray[np.int64]
type UnitKey = tuple[date, Right]

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MICROSECOND = timedelta(microseconds=1)


@final
@dataclass(frozen=True, slots=True)
class PricedQuotes:
    """One chain on one bar, a row per contract in strike order. Dollars are floats; NaN is
    unknown. `code` says why a contract has no IV (`IvCode`)."""

    strike: IntArray  # $0.0001 units
    mid: FloatArray
    spread_pct: FloatArray  # (ASK - BID) / mid
    iv: FloatArray
    code: CodeArray
    delta: FloatArray
    gamma: FloatArray
    theta: FloatArray
    vega: FloatArray
    extrinsic: FloatArray  # mid - intrinsic at spot (Spec › E-L3)

    @property
    def eligible(self) -> BoolArray:
        return self.code == IvCode.OK

    def at(self, strike: Price) -> int | None:
        """The row of `strike`, or None if it has no row on this bar."""
        hits = np.flatnonzero(self.strike == strike.units)
        return int(hits[0]) if hits.size else None

    def rows(self, start: int, stop: int) -> "PricedQuotes":
        s = slice(start, stop)
        return PricedQuotes(self.strike[s], self.mid[s], self.spread_pct[s], self.iv[s],
                            self.code[s], self.delta[s], self.gamma[s], self.theta[s],
                            self.vega[s], self.extrinsic[s])  # fmt: skip


def price_quotes(*, strike: IntArray, bid: IntArray | FloatArray, ask: IntArray | FloatArray,
                 valid: BoolArray, spot: Floats, years: Floats, rate: float,
                 is_call: Rights) -> PricedQuotes:  # fmt: skip
    """Price contracts from their quotes. Prices and spot are in $0.0001 units (spot NaN when the
    underlying has no trade); BID and ASK are read only where `valid`."""
    n = strike.size
    k = strike.astype(np.float64) / UNITS_PER_DOLLAR
    s = np.broadcast_to(np.asarray(spot, dtype=np.float64) / UNITS_PER_DOLLAR, n)
    t = np.broadcast_to(np.asarray(years, dtype=np.float64), n)
    call = np.broadcast_to(np.asarray(is_call, dtype=np.bool_), n)
    b, a = np.asarray(bid, dtype=np.float64), np.asarray(ask, dtype=np.float64)
    mid = np.where(valid, (b + a) / (2 * UNITS_PER_DOLLAR), np.nan)
    spread = np.where(valid, (a - b) / UNITS_PER_DOLLAR, np.nan) / mid
    solved = implied_vol(mid, s, k, t, rate, call)
    delta, gamma, theta, vega = _greeks(s, k, t, rate, call, solved)
    intrinsic = np.maximum(np.where(call, s - k, k - s), 0.0)
    return PricedQuotes(strike, mid, spread, solved.vol, solved.code, delta, gamma, theta, vega,
                        mid - intrinsic)  # fmt: skip


def _greeks(s: FloatArray, k: FloatArray, t: FloatArray, rate: float, call: BoolArray,
            solved: ImpliedVol) -> tuple[FloatArray, ...]:  # fmt: skip
    """Greeks where the IV solved; DEC-27's deep ITM limit for a call under its floor; NaN
    elsewhere."""
    out = [np.full(s.size, np.nan) for _ in range(4)]
    ok = solved.code == IvCode.OK
    if ok.any():
        g = greeks(s[ok], k[ok], t[ok], rate, solved.vol[ok], call[ok])
        for values, column in zip(out, (g.delta, g.gamma, g.theta, g.vega), strict=True):
            values[ok] = column
    held = call & (solved.code == IvCode.BELOW_FLOOR)
    delta, gamma, theta, vega = out
    delta[held], gamma[held], vega[held] = 1.0, 0.0, 0.0
    theta[held] = -rate * k[held] * np.exp(-rate * t[held])
    return delta, gamma, theta, vega


@final
@dataclass(frozen=True, slots=True)
class _PricedUnit:
    """One chain unit's session bars, priced, in (bar_end, strike) order, with each bar's rows."""

    quotes: PricedQuotes
    bars: Mapping[int, tuple[int, int]]  # bar_end in µs since the epoch -> (start, stop)


@final
class PricedSymbol:
    """A symbol's chains, priced once. Snapshots are kept per (bar, expiry, right)."""

    def __init__(self, units: Mapping[UnitKey, _PricedUnit]) -> None:
        self._units = dict(units)
        self._snapshots: dict[tuple[int, date, Right], PricedQuotes | None] = {}

    def snapshot(self, bar_end: datetime, expiry: date, right: Right) -> PricedQuotes | None:
        """The chain's contracts on the session bar ending at `bar_end`, or None if it has no
        rows there."""
        key = (_micros(bar_end), expiry, right)
        if key not in self._snapshots:
            self._snapshots[key] = self._slice(*key)
        return self._snapshots[key]

    def codes(self, expiry: date, right: Right) -> dict[IvCode, int]:
        """How many of the unit's session contract-bars ended with each `IvCode`."""
        unit = self._units.get((expiry, right))
        if unit is None:
            return {}
        counts = Counter(IvCode(int(c)) for c in unit.quotes.code)
        return dict(sorted(counts.items()))

    def _slice(self, micros: int, expiry: date, right: Right) -> PricedQuotes | None:
        unit = self._units.get((expiry, right))
        span = None if unit is None else unit.bars.get(micros)
        return None if unit is None or span is None else unit.quotes.rows(*span)


def price_symbol(stock: pl.DataFrame, chains: Mapping[UnitKey, pl.DataFrame],
                 calendar: SessionCalendar, rate: float) -> PricedSymbol:  # fmt: skip
    """Price every session bar of every chain, as `load_symbol` loaded them (ARCHITECTURE §6.5).
    Raises ValueError for an expiry that isn't a session."""
    spot = stock.filter(pl.col("session_bar")).select("bar_end", spot=pl.col("TRDPRC_1"))
    return PricedSymbol(
        {
            (expiry, right): _price_unit(frame, spot, calendar.session(expiry), rate, right)
            for (expiry, right), frame in chains.items()
        }
    )


def _price_unit(frame: pl.DataFrame, spot: pl.DataFrame, expiry: Session, rate: float,
                right: Right) -> _PricedUnit:  # fmt: skip
    rows = (
        frame.filter(pl.col("session_bar"))
        .join(spot, on="bar_end", how="left")
        .sort("bar_end", "strike_cents")
    )
    ends: list[datetime] = rows["bar_end"].to_list()
    micros = np.array([_micros(e) for e in ends], dtype=np.int64)
    firsts = np.flatnonzero(np.diff(micros, prepend=micros[:1] - 1))  # where a new bar begins
    stops = np.append(firsts[1:], len(ends)) if ends else firsts
    years = np.empty(len(ends))
    for start, stop in zip(firsts, stops, strict=True):
        years[start:stop] = years_to_expiry(ends[start], expiry)
    quotes = price_quotes(
        strike=rows["strike_cents"].to_numpy().astype(np.int64) * UNITS_PER_CENT,
        bid=rows["BID"].cast(pl.Float64).to_numpy(),
        ask=rows["ASK"].cast(pl.Float64).to_numpy(),
        valid=rows["valid_quote"].to_numpy().astype(np.bool_),
        spot=rows["spot"].cast(pl.Float64).fill_null(np.nan).to_numpy(),
        years=years,
        rate=rate,
        is_call=right is Right.CALL,
    )
    bars = {int(micros[a]): (int(a), int(b)) for a, b in zip(firsts, stops, strict=True)}
    return _PricedUnit(quotes, bars)


def _micros(t: datetime) -> int:
    """A tz-aware time as whole µs since the epoch: an exact key, whatever its zone. A naive time
    is refused: `astimezone` would read it in the machine's zone (DEC-58)."""
    return (to_et(t).astimezone(UTC) - _EPOCH) // _MICROSECOND
