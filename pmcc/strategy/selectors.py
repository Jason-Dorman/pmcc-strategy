"""Long- and short-leg selection: E-L2 + E-L3 and E-S2 + E-S3 (Spec › Trade rules: entry).

A selector reads only the `MarketView` and returns a `Selection`: the contract and the values that
justified it, which become blotter notes. It considers only contracts eligible on the bar: a valid
quote and a solved IV (Spec › Greeks and pricing; DEC-21). Ties break as the PO settled them
(DEC-29):

| Rule | Tie-break |
| --- | --- |
| E-L2 baseline, nearest target DTE | the later expiry |
| E-L3 baseline, delta nearest the target | lower spread %, then the lower strike |
| E-L3 quant, lowest extrinsic ÷ delta | lower spread %, the earlier expiry, the lower strike |
| E-S3 baseline, delta nearest the target | lower spread %, then the higher strike |

E-L2 quant keeps every expiry in its range, and E-S3 quant's lowest strike can't tie.

DTE is whole days and strikes are integer units, so those ties are exact; spread % is compared as
an exact fraction of the integer BID and ASK, and E-S3 quant's threshold is exact in price units.
A delta is a float from the IV solve, so a delta distance, a delta on a band's edge and E-L3
quant's extrinsic ÷ delta are rounded to 9 places before comparing: equal values tie, as DEC-29
intends.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from typing import Any, Protocol, final, runtime_checkable

import numpy as np

from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_DOLLAR, Price
from pmcc.domain.rules import RuleId
from pmcc.pricing.expiry import days_to_expiry
from pmcc.strategy.measures import expected_move_at
from pmcc.strategy.ports import (
    ChainSnapshot,
    ExpiryKind,
    HeldLeg,
    MarketView,
    Selection,
    Value,
    Values,
)
from pmcc.strategy.trigger import as_fraction

E_L2, E_L3, E_S2, E_S3 = RuleId("E-L2"), RuleId("E-L3"), RuleId("E-S2"), RuleId("E-S3")
DELTA_PLACES = 9  # the IV solve pins delta far tighter than this, but not to the last bit


@runtime_checkable
class LongExpiryRule(Protocol):  # E-L2
    def candidates(self, view: MarketView) -> tuple[date, ...]: ...


@runtime_checkable
class LongStrikeRule(Protocol):  # E-L3
    def pick(self, view: MarketView, expiries: tuple[date, ...]) -> Selection | None: ...


@runtime_checkable
class ShortExpiryRule(Protocol):  # E-S2
    def expiry(self, view: MarketView) -> date: ...


@runtime_checkable
class ShortStrikeRule(Protocol):  # E-S3
    def pick(self, view: MarketView, expiry: date, long: HeldLeg) -> Selection | None: ...


@final
@dataclass(frozen=True, slots=True)
class NearestDteExpiry:
    """E-L2 baseline: the listed monthly expiry nearest `target_dte` days out; ties to the later."""

    target_dte: int

    def candidates(self, view: MarketView) -> tuple[date, ...]:
        listed = view.expiries(ExpiryKind.MONTHLY)
        if not listed:
            return ()

        def distance(expiry: date) -> tuple[int, int]:
            return abs(days_to_expiry(view.now, expiry) - self.target_dte), -expiry.toordinal()

        return (min(listed, key=distance),)


@final
@dataclass(frozen=True, slots=True)
class DteRangeExpiry:
    """E-L2 quant: every listed monthly expiry from `min_dte` to `max_dte` days out, inclusive."""

    min_dte: int
    max_dte: int

    def candidates(self, view: MarketView) -> tuple[date, ...]:
        return tuple(e for e in view.expiries(ExpiryKind.MONTHLY)
                     if self.min_dte <= days_to_expiry(view.now, e) <= self.max_dte)  # fmt: skip


@final
@dataclass(frozen=True, slots=True)
class NearestDeltaLong:
    """E-L3 baseline: the eligible call with delta nearest `target_delta`, over the E-L2 expiries;
    ties to the lower spread %, then the lower strike."""

    target_delta: float

    def pick(self, view: MarketView, expiries: tuple[date, ...]) -> Selection | None:
        rows = _rows(view, expiries)
        if not rows:
            return None
        chain, row = min(rows, key=lambda cr: (
            _distance(cr[0].quotes.delta[cr[1]], self.target_delta),
            _spread(cr[0], cr[1]), cr[0].quotes.strike[cr[1]], cr[0].expiry,
        ))  # fmt: skip
        return _selection(view, chain, row, rule={"target_delta": self.target_delta}, context={})


@final
@dataclass(frozen=True, slots=True)
class CheapestReplacement:
    """E-L3 quant: among eligible calls with delta from `min_delta` to `max_delta` (inclusive)
    across the E-L2 expiries, the lowest extrinsic ÷ delta, where extrinsic = mid − max(0, spot −
    strike); ties to the lower spread %, then the earlier expiry, then the lower strike. None
    without a spot."""

    min_delta: float
    max_delta: float

    def pick(self, view: MarketView, expiries: tuple[date, ...]) -> Selection | None:
        spot = view.spot()
        if spot is None:
            return None
        rows = [(c, i) for c, i in _rows(view, expiries) if self._in_band(c.quotes.delta[i])]
        if not rows:
            return None

        def score(cr: tuple[ChainSnapshot, int]) -> float:
            chain, row = cr
            return _per_delta(_extrinsic(chain, row, spot), chain.quotes.delta[row])

        chain, row = min(rows, key=lambda cr: (
            score(cr), _spread(cr[0], cr[1]), cr[0].expiry, cr[0].quotes.strike[cr[1]],
        ))  # fmt: skip
        extrinsic = _extrinsic(chain, row, spot)
        rule: Values = {
            "extrinsic": str(extrinsic.to_dollars()),
            "extrinsic_per_delta": round(score((chain, row)), 6),
            "candidates": len(rows),
        }
        return _selection(view, chain, row, rule=rule, context=_spot(spot))

    def _in_band(self, delta: float | np.floating[Any]) -> bool:
        return self.min_delta <= round(float(delta), DELTA_PLACES) <= self.max_delta


@final
@dataclass(frozen=True, slots=True)
class WeekFinalExpiry:
    """E-S2: the expiry on the week's final trading session (Thursday when Friday is closed)."""

    def expiry(self, view: MarketView) -> date:
        return view.calendar().week_final(view.now.date()).day


@final
@dataclass(frozen=True, slots=True)
class NearestDeltaShort:
    """E-S3 baseline: the eligible out-of-the-money call (strike above spot) with delta nearest
    `target_delta`; ties to the lower spread %, then the higher strike. None without a spot."""

    target_delta: float

    def pick(self, view: MarketView, expiry: date, long: HeldLeg) -> Selection | None:
        spot = view.spot()
        if spot is None:
            return None
        chain = view.chain(expiry, Right.CALL)
        rows = [i for i in _eligible(chain) if chain.quotes.strike[i] > spot.units]
        if not rows:
            return None
        row = min(rows, key=lambda i: (
            _distance(chain.quotes.delta[i], self.target_delta), _spread(chain, i),
            -chain.quotes.strike[i],
        ))  # fmt: skip
        return _selection(view, chain, row, rule={"target_delta": self.target_delta},
                          context=_spot(spot))  # fmt: skip


@final
@dataclass(frozen=True, slots=True)
class ExpectedMoveStrike:
    """E-S3 quant: the lowest eligible strike at or above spot + `k` × EM, where EM is the E-S2
    expiry's ATM straddle mid on this bar (DEC-25). None without a spot or an EM.

    Only a contract eligible on the bar is considered (DEC-21), so a listed strike with no quote
    is passed over for the next one up."""

    k: float

    def pick(self, view: MarketView, expiry: date, long: HeldLeg) -> Selection | None:
        spot = view.spot()
        em = expected_move_at(view, expiry)
        if spot is None or em is None:
            return None
        floor = min_strike(spot, em, self.k)
        chain = view.chain(expiry, Right.CALL)
        rows = [i for i in _eligible(chain) if chain.quotes.strike[i] >= floor.units]
        if not rows:
            return None
        row = min(rows, key=lambda i: int(chain.quotes.strike[i]))
        context: Values = {**_spot(spot), "em": str(em.to_dollars()), "k": self.k,
                           "min_strike": str(floor.to_dollars())}  # fmt: skip
        return _selection(view, chain, row, rule={}, context=context)


def min_strike(spot: Price, em: Price, k: float) -> Price:
    """spot + k × EM, rounded up to a whole $0.0001: a strike is at or above the exact value if
    and only if it is at or above this."""
    return Price(math.ceil(spot.units + as_fraction(k) * em.units))


@final
@dataclass(frozen=True, slots=True)
class LongSelector:
    """E-L2 then E-L3."""

    expiry: LongExpiryRule
    strike: LongStrikeRule

    def select(self, view: MarketView) -> Selection | None:
        expiries = self.expiry.candidates(view)
        return self.strike.pick(view, expiries) if expiries else None


@final
@dataclass(frozen=True, slots=True)
class ShortSelector:
    """E-S2 then E-S3, against the long it would be sold on."""

    expiry: ShortExpiryRule
    strike: ShortStrikeRule

    def select(self, view: MarketView, long: HeldLeg) -> Selection | None:
        return self.strike.pick(view, self.expiry.expiry(view), long)


def _eligible(chain: ChainSnapshot) -> list[int]:
    return [int(i) for i in np.flatnonzero(chain.quotes.eligible & chain.quotes.valid)]


def _rows(view: MarketView, expiries: tuple[date, ...]) -> list[tuple[ChainSnapshot, int]]:
    """Every eligible call across `expiries`, as (chain, row)."""
    return [(chain, i) for e in expiries for chain in [view.chain(e, Right.CALL)]
            for i in _eligible(chain)]  # fmt: skip


def _distance(delta: float | np.floating[Any], target: float) -> float:
    """|delta − target|, rounded to DELTA_PLACES so float noise can't create or break a tie
    (DEC-29): 0.85 and 0.75 are equally far from 0.80."""
    return round(abs(float(delta) - target), DELTA_PLACES)


def _extrinsic(chain: ChainSnapshot, row: int, spot: Price) -> Price:
    """mid − max(0, spot − strike), in exact units, from the quote's mid (Spec › E-L3)."""
    quote = chain.quotes.quote(row)
    if quote is None:  # `_eligible` keeps only rows with a valid quote
        raise EngineError(f"E-L3: {chain.expiry} row {row} has no quote")
    return Price(quote.mid.units - max(0, spot.units - int(chain.quotes.strike[row])))


def _per_delta(extrinsic: Price, delta: float | np.floating[Any]) -> float:
    """Extrinsic dollars per unit of delta, rounded to DELTA_PLACES so equal ratios tie (DEC-29):
    1.70 ÷ 0.85 and 1.40 ÷ 0.70 are both 2."""
    return round(extrinsic.units / (UNITS_PER_DOLLAR * float(delta)), DELTA_PLACES)


def _spread(chain: ChainSnapshot, row: int) -> Fraction:
    """(ASK − BID) / (ASK + BID), exact: spread % of mid over 2, which orders the same."""
    bid, ask = int(chain.quotes.bid[row]), int(chain.quotes.ask[row])
    return Fraction(ask - bid, ask + bid)


def _spot(spot: Price) -> dict[str, Value]:
    return {"spot": str(spot.to_dollars())}


def _selection(view: MarketView, chain: ChainSnapshot, row: int, *, rule: Mapping[str, Value],
               context: Mapping[str, Value]) -> Selection:  # fmt: skip
    """The contract on `row` and its values: the contract's, then the `rule`'s own after its
    delta, then the `context` it was picked in (spot, EM)."""
    q = chain.quotes
    option = OptionId(view.root, chain.expiry, chain.right, chain.strike(row))
    quote = q.quote(row)  # the exact mid, as fills use it; not the float column (DEC-92)
    return Selection(
        option,
        {
            "expiry": chain.expiry.isoformat(),
            "dte": days_to_expiry(view.now, chain.expiry),
            "strike": str(option.strike.to_dollars()),
            "delta": round(float(q.delta[row]), 6),
            **rule,
            "iv": round(float(q.iv[row]), 6),
            "mid": None if quote is None else str(quote.mid.to_dollars()),
            "spread_pct": round(float(q.spread_pct[row]), 6),
            **context,
        },
    )
