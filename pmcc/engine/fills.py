"""The fill simulator (Spec › Fill model, ARCHITECTURE §8.3, INV-03).

- A limit at mid = (BID + ASK) / 2, filled on the decision bar. No valid BID/ASK on that bar, no
  fill: a print is never invented (INV-03).
- `spread_capture` c in [0, 1]: a buy fills at mid + c × half-spread, a sell at mid − c ×
  half-spread. The price is worked out exactly and rounded half-even to $0.0001 once (DEC-44), so
  c = 0 fills at exactly `Quote.mid`, the blotter's Limit.
- A fee per option contract; none on stock.

The event's audit records the quote and the capture, so `pmcc verify` can re-derive the fill
(DEC-51).
"""

from collections.abc import Mapping
from datetime import datetime
from fractions import Fraction

from pmcc.accounting.events import AuditValue, Event, Instrument, expected_cash
from pmcc.config.strategy import FillModel
from pmcc.domain.instruments import OptionId, Side
from pmcc.domain.money import Price
from pmcc.domain.quotes import Quote
from pmcc.domain.rules import RuleId


def fill_price(quote: Quote, side: Side, capture: float) -> Price:
    """mid ± capture × half-spread, exactly, rounded half-even to $0.0001."""
    if side not in (Side.BUY, Side.SELL):
        raise ValueError(f"only a BUY or SELL fills at a price, not {side}")
    share = Fraction(float.__repr__(float(capture)))
    if not 0 <= share <= 1:
        raise ValueError(f"spread_capture must be in [0, 1], got {capture}")
    bid, ask = quote.bid.units, quote.ask.units
    mid, half = Fraction(bid + ask, 2), Fraction(ask - bid, 2)
    exact = mid + share * half if side is Side.BUY else mid - share * half
    return Price(round(exact))


def fill(
    *,
    time: datetime,
    side: Side,
    instrument: Instrument,
    qty: int,
    quote: Quote | None,
    model: FillModel,
    rule_id: RuleId,
    notes: str = "",
    audit: Mapping[str, AuditValue] | None = None,
) -> Event | None:
    """The blotter row for a limit at mid on this bar, or None without a valid quote (INV-03)."""
    if quote is None:
        return None
    price = fill_price(quote, side, model.spread_capture)
    contracts = qty if isinstance(instrument, OptionId) else 0
    fee = model.fee_per_contract * contracts
    return Event(
        time=time,
        side=side,
        instrument=instrument,
        qty=qty,
        limit=quote.mid,
        fill=price,
        cash_delta=expected_cash(side, instrument, qty, price, fee),
        rule_id=rule_id,
        notes=notes,
        fee=fee,
        audit={
            **(audit or {}),
            "bid": quote.bid.units,
            "ask": quote.ask.units,
            "spread_capture": model.spread_capture,
        },
    )
