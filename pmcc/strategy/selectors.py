"""Long- and short-leg selection: E-L2 + E-L3 and E-S2 + E-S3 (Spec › Trade rules: entry).

A selector reads only the `MarketView` and returns a `Selection`: the contract and the values that
justified it, which become blotter notes. It considers only contracts eligible on the bar: a valid
quote and a solved IV (Spec › Greeks and pricing; DEC-21). Ties break as the PO settled them
(DEC-29):

| Rule | Tie-break |
| --- | --- |
| E-L2 baseline, nearest target DTE | the later expiry |
| E-L3 baseline, delta nearest the target | lower spread %, then the lower strike |
| E-S3 baseline, delta nearest the target | lower spread %, then the higher strike |

DTE is whole days and strikes are integer units, so those ties are exact; spread % is compared as
an exact fraction of the integer BID and ASK. A delta is a float from the IV solve, so its distance
to the target is rounded to 9 places before comparing: equal distances tie, as DEC-29 intends.
"""

from dataclasses import dataclass
from datetime import date
from fractions import Fraction
from typing import Any, Protocol, final, runtime_checkable

import numpy as np

from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.domain.rules import RuleId
from pmcc.pricing.expiry import days_to_expiry
from pmcc.strategy.ports import ChainSnapshot, ExpiryKind, HeldLeg, MarketView, Selection

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
class NearestDeltaLong:
    """E-L3 baseline: the eligible call with delta nearest `target_delta`, over the E-L2 expiries;
    ties to the lower spread %, then the lower strike."""

    target_delta: float

    def pick(self, view: MarketView, expiries: tuple[date, ...]) -> Selection | None:
        rows = [(chain, i) for e in expiries for chain in [view.chain(e, Right.CALL)]
                for i in _eligible(chain)]  # fmt: skip
        if not rows:
            return None
        chain, row = min(rows, key=lambda cr: (
            _distance(cr[0].quotes.delta[cr[1]], self.target_delta),
            _spread(cr[0], cr[1]), cr[0].quotes.strike[cr[1]], cr[0].expiry,
        ))  # fmt: skip
        return _selection(view, chain, row, target_delta=self.target_delta)


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
        return _selection(view, chain, row, target_delta=self.target_delta, spot=spot)


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


def _distance(delta: float | np.floating[Any], target: float) -> float:
    """|delta − target|, rounded to DELTA_PLACES so float noise can't create or break a tie
    (DEC-29): 0.85 and 0.75 are equally far from 0.80."""
    return round(abs(float(delta) - target), DELTA_PLACES)


def _spread(chain: ChainSnapshot, row: int) -> Fraction:
    """(ASK − BID) / (ASK + BID), exact: spread % of mid over 2, which orders the same."""
    bid, ask = int(chain.quotes.bid[row]), int(chain.quotes.ask[row])
    return Fraction(ask - bid, ask + bid)


def _selection(view: MarketView, chain: ChainSnapshot, row: int, *, target_delta: float,
               spot: Price | None = None) -> Selection:  # fmt: skip
    q = chain.quotes
    option = OptionId(view.root, chain.expiry, chain.right, chain.strike(row))
    return Selection(
        option,
        {
            "expiry": chain.expiry.isoformat(),
            "dte": days_to_expiry(view.now, chain.expiry),
            "strike": str(option.strike.to_dollars()),
            "delta": round(float(q.delta[row]), 6),
            "target_delta": target_delta,
            "iv": round(float(q.iv[row]), 6),
            "mid": round(float(q.mid[row]), 4),
            "spread_pct": round(float(q.spread_pct[row]), 6),
            **({} if spot is None else {"spot": str(spot.to_dollars())}),
        },
    )
