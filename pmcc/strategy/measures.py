"""The measures rules read, taken through the `MarketView` on its bar (DEC-25, DEC-26).

`pmcc.pricing.measures` defines them on plain inputs; these gather those inputs as of the view's
`now`. The ATM strike is the listed call strike nearest spot (DEC-32), so a listed ATM strike with
no quote on the bar leaves its IV or EM unavailable rather than moving to a neighbour (DEC-91).

Quant E-S3 reads EM at the bar it selects on, the gates G-3 and G-4 read ATM IV and RV20 at the
decision bar, and the engine records EM at the short's entry for X-S3.
"""

from dataclasses import dataclass
from datetime import date
from typing import final

from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.pricing.measures import atm_iv, atm_strike, expected_move, rv20
from pmcc.strategy.ports import MarketView


@final
@dataclass(frozen=True, slots=True)
class AtmReading:
    """An expiry's ATM strike on the bar and its call's IV; either is None when unavailable."""

    expiry: date
    strike: Price | None
    iv: float | None


def atm_strike_at(view: MarketView, expiry: date) -> Price | None:
    """The listed call strike of `expiry` nearest spot, the lower on a tie; None without a spot
    or a listed call."""
    spot = view.spot()
    return None if spot is None else atm_strike(view.chain(expiry, Right.CALL).strikes(), spot)


def atm_reading(view: MarketView, expiry: date) -> AtmReading:
    """`expiry`'s ATM strike and its call's IV on this bar (G-3, G-4)."""
    spot = view.spot()
    if spot is None:
        return AtmReading(expiry, None, None)
    chain = view.chain(expiry, Right.CALL)
    strike = atm_strike(chain.strikes(), spot)
    iv = None if strike is None else atm_iv(chain.quotes, strike)
    return AtmReading(expiry, strike, iv)


def expected_move_at(view: MarketView, expiry: date) -> Price | None:
    """EM on this bar: `expiry`'s ATM call mid + ATM put mid; None unless both are quoted."""
    atm = atm_strike_at(view, expiry)
    if atm is None:
        return None
    call = view.quote(OptionId(view.root, expiry, Right.CALL, atm))
    put = view.quote(OptionId(view.root, expiry, Right.PUT, atm))
    return expected_move(call, put)


def rv20_at(view: MarketView) -> float | None:
    """RV20 at this bar, from the closes of the 21 sessions before its own (DEC-26)."""
    return rv20(view.calendar(), view.now, view.close_trades())
