"""The wheel's selection rules (Spec › Trade rules): pure functions of what `MarketView` shows.

- **W-P3:** among puts struck below spot with a delta solved from the bar's mid, the one whose
  delta is nearest −target; a tie goes to the lower strike.
- **W-C3:** among calls struck above spot and at or above the cost basis, with a delta, the one
  whose delta is nearest target; a tie goes to the higher strike. None → `None`, and the week is
  skipped (WD-08).
- **W-T1:** the pick's quote is valid on the bar and its spread is at most `max_spread` of mid.
- **ITM at expiry (WD-15):** a put below its strike, a call above it, at the closing trade.

A contract without a valid quote, or whose IV didn't solve, has no delta on the bar and can't be
picked there (Spec › Conventions). Rules read the market only through `MarketView`.
"""

import math
from dataclasses import dataclass, field
from datetime import date
from typing import final

import numpy as np

from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.domain.quotes import Quote
from pmcc.strategy.ports import MarketView, Values


@final
@dataclass(frozen=True, slots=True)
class Pick:
    """The contract a selector chose on a bar, its quote, and the values that justified it."""

    option: OptionId
    quote: Quote
    delta: float
    spread_pct: float
    spot: Price
    values: Values = field(default_factory=dict[str, float | int | str | bool | None])


def select_put(view: MarketView, expiry: date, target: float) -> Pick | None:
    """W-P3's put for `expiry` on this bar, or None if no OTM put has a delta here."""
    return _nearest(view, expiry, Right.PUT, -target, floor=None)


def select_call(view: MarketView, expiry: date, target: float, floor: Price) -> Pick | None:
    """W-C3's call for `expiry` on this bar: OTM, struck at or above `floor` (the cost basis per
    share), delta nearest `target`. None if no such call has a delta here."""
    return _nearest(view, expiry, Right.CALL, target, floor=floor)


def passes_trigger(pick: Pick, max_spread: float) -> bool:
    """W-T1: the pick has a valid quote (it does, or it had no delta) within the spread limit."""
    return pick.spread_pct <= max_spread


def finishes_itm(option: OptionId, closing_spot: Price) -> bool:
    """WD-15: a put is assigned below its strike, a call above it; at the strike, neither."""
    if option.right is Right.PUT:
        return closing_spot < option.strike
    return closing_spot > option.strike


def _nearest(
    view: MarketView, expiry: date, right: Right, target: float, floor: Price | None
) -> Pick | None:
    spot = view.spot()
    if spot is None:
        return None
    chain = view.chain(expiry, right)
    q = chain.quotes
    strikes = q.strike
    otm = strikes < spot.units if right is Right.PUT else strikes > spot.units
    eligible = q.valid & otm & ~np.isnan(q.delta)
    if floor is not None:
        eligible &= strikes >= floor.units
    rows = np.flatnonzero(eligible)
    if rows.size == 0:
        return None
    # Nearest delta; a tie goes further out of the money (lower put, higher call strike).
    away = -strikes[rows] if right is Right.PUT else strikes[rows]
    distance = np.abs(q.delta[rows] - target)
    row = int(rows[np.lexsort((-away, distance))[0]])
    quote = chain.quotes.quote(row)
    if quote is None:  # eligible rows are valid
        return None
    delta, spread = float(q.delta[row]), float(q.spread_pct[row])
    option = OptionId(view.root, expiry, right, chain.strike(row))
    values: Values = {
        "delta": round(delta, 4),
        "target_delta": target,
        "spot": str(spot.to_dollars()),
        "mid": str(quote.mid.to_dollars()),
        "spread_pct": round(spread, 4) if math.isfinite(spread) else None,
    }
    if floor is not None:
        values["basis_floor"] = str(floor.to_dollars())
    return Pick(option, quote, delta, spread, spot, values)
