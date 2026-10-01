"""A contract's IV and Greeks on a bar, as the chain priced them (ARCHITECTURE §7; DEC-24, DEC-27).

The ledger records them for each held leg, and an option fill's audit records the IV it filled at,
so the Greek attribution can price a bar's change from what the engine saw (P6-04, DEC-63).
"""

import math

from pmcc.accounting.ledger import NO_GREEKS, LegGreeks
from pmcc.domain.instruments import OptionId
from pmcc.strategy.ports import MarketView


def leg_greeks(view: MarketView, option: OptionId) -> LegGreeks:
    """`option`'s chain row on the bar, or none known without a valid quote. A value pricing left
    unknown (NaN) is None: a call under its floor keeps DEC-27's Greeks but has no IV."""
    chain = view.chain(option.expiry, option.right)
    row = chain.row(option.strike)
    if row is None or not chain.quotes.valid[row]:
        return NO_GREEKS
    q = chain.quotes
    return LegGreeks(*(_known(float(values[row]))
                       for values in (q.iv, q.delta, q.gamma, q.theta, q.vega)))  # fmt: skip


def _known(value: float) -> float | None:
    return None if math.isnan(value) else value
