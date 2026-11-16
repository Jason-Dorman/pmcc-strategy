"""The live wheel's picks from tonight's close snapshot (LIVE-SPEC › Trade rules; L2-03).

- **L-P3:** among puts struck below the close, with a valid quote at the close and a delta solved
  from its mid, the one whose delta is nearest −target; a tie goes to the lower strike.
- **L-C3:** among calls struck above the close and at or above the cost basis, the one whose delta
  is nearest target; a tie goes to the higher strike.
- **L-T1:** the pick's spread is at most `max_spread` of its mid.
- **L-P4:** cash covers the strike × the multiplier × contracts.

The deltas are the backtests' (LD-11): Black-Scholes, IV solved from the close's mid, dividend
yield 0, `rate` continuously compounded (LD-13), T from the close to the expiry session's close,
ACT/365. A contract whose IV doesn't solve has no delta and can't be picked, as in the wheel's
backtest. Pure functions of the snapshot: they read no files and ask LSEG nothing.
"""

import math
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal
from typing import final

import numpy as np

from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Money, Price
from pmcc.domain.quotes import Quote
from pmcc.live.snapshot import CloseSnapshot, OptionQuote
from pmcc.pricing.chain import PricedQuotes, price_quotes
from pmcc.pricing.expiry import years_between


@final
@dataclass(frozen=True, slots=True)
class Pick:
    """The contract chosen, its quote at the close, and the numbers that chose it."""

    option: OptionId
    bid: Price
    ask: Price
    delta: float
    iv: float
    spread_pct: float

    @property
    def mid(self) -> Price:
        """(BID + ASK) / 2, rounded as fills are (DEC-44)."""
        return Quote(self.bid, self.ask).mid


def select(
    snapshot: CloseSnapshot,
    right: Right,
    target: float,
    rate: float,
    calendar: SessionCalendar,
    floor: Price | None = None,
) -> Pick | None:
    """L-P3's put (`floor` None) or L-C3's call (`floor` the cost basis per share): the OTM
    contract whose delta is nearest `target` (negated for a put), or None if none has one."""
    quotes = [q for q in snapshot.options if q.option.right is right and q.quoted_at_close]
    if not quotes:
        return None
    priced = _priced(snapshot, quotes, right, rate, calendar)
    strikes = priced.strike
    close = snapshot.close.units
    otm = strikes < close if right is Right.PUT else strikes > close
    eligible = otm & ~np.isnan(priced.delta)
    if floor is not None:
        eligible &= strikes >= floor.units
    rows = np.flatnonzero(eligible)
    if rows.size == 0:
        return None
    signed = -target if right is Right.PUT else target
    away = -strikes[rows] if right is Right.PUT else strikes[rows]
    distance = np.abs(priced.delta[rows] - signed)
    row = int(rows[np.lexsort((-away, distance))[0]])
    chosen = quotes[row]
    return Pick(
        chosen.option,
        Price(int(priced.bid[row])),
        Price(int(priced.ask[row])),
        float(priced.delta[row]),
        float(priced.iv[row]),
        float(priced.spread_pct[row]),
    )


def liquid(pick: Pick, max_spread: float) -> bool:
    """L-T1: the pick's spread is no wider than `max_spread` of its mid."""
    return math.isfinite(pick.spread_pct) and pick.spread_pct <= max_spread


def secured(
    cash: Money, strike: Price, contracts: int, multiplier: int, allowance: float = 0.0
) -> bool:
    """L-P4: cash covers the shares a put's assignment would buy, with `allowance` (0.10: 10%)
    more for the gap at the open, where Sanji sets the strike (PO, LD-29). Rounded up to the
    $0.0001, in integer units."""
    notional = strike.notional(multiplier, contracts).units
    needed = (Decimal(notional) * (1 + Decimal(str(allowance)))).to_integral_value(ROUND_CEILING)
    return cash >= Money(int(needed))


def _priced(
    snapshot: CloseSnapshot,
    quotes: list[OptionQuote],
    right: Right,
    rate: float,
    calendar: SessionCalendar,
) -> PricedQuotes:
    closes = [q.close for q in quotes]
    years = years_between(
        snapshot.session.close_bar_end, calendar.session(snapshot.expiry).close_bar_end
    )
    return price_quotes(
        strike=np.array([q.option.strike.units for q in quotes], dtype=np.int64),
        bid=np.array([c.bid.units if c and c.bid else 0 for c in closes], dtype=np.int64),
        ask=np.array([c.ask.units if c and c.ask else 0 for c in closes], dtype=np.int64),
        valid=np.ones(len(quotes), dtype=np.bool_),
        spot=float(snapshot.close.units),
        years=years,
        rate=rate,
        is_call=right is Right.CALL,
    )
