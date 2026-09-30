"""The fill simulator (P3-05): INV-03, exact fills at each spread_capture, per-contract fees."""

from datetime import date, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pmcc.accounting.events import StockId
from pmcc.config.strategy import FillModel
from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.quotes import Quote
from pmcc.domain.rules import RuleId
from pmcc.engine.fills import fill, fill_price

T = datetime(2026, 8, 31, 10, tzinfo=ET)
OPTION = OptionId("SYN", date(2026, 9, 4), Right.CALL, Price.from_dollars(102))
RULE = RuleId("E-S1")
QUOTE = Quote(Price.from_dollars("1.00"), Price.from_dollars("1.03"))  # mid 1.015, half 0.015


def model(capture: float = 0.0, fee: str = "0") -> FillModel:
    return FillModel(spread_capture=capture, fee_per_contract=Money.from_dollars(fee))


def test_inv_03_no_quote_no_fill() -> None:
    assert fill(time=T, side=Side.BUY, instrument=OPTION, qty=1, quote=None, model=model(),
                rule_id=RULE) is None  # fmt: skip


@pytest.mark.parametrize(
    ("capture", "side", "units"),
    [
        (0.0, Side.BUY, 10_150),
        (0.0, Side.SELL, 10_150),
        (0.25, Side.BUY, 10_188),  # 1.01875: a half unit, rounded to even
        (0.25, Side.SELL, 10_112),  # 1.01125: a half unit, rounded to even
        (0.50, Side.BUY, 10_225),
        (0.50, Side.SELL, 10_075),
        (1.0, Side.BUY, 10_300),
        (1.0, Side.SELL, 10_000),
    ],
)
def test_inv_03_fills_are_exact_in_price_units(capture: float, side: Side, units: int) -> None:
    assert fill_price(QUOTE, side, capture) == Price(units)


def test_inv_03_capture_zero_fills_at_the_limit() -> None:
    odd = Quote(Price(10_001), Price(10_002))  # mid 10_001.5 → 10_002, as Quote.mid rounds
    event = fill(time=T, side=Side.SELL, instrument=OPTION, qty=1, quote=odd, model=model(),
                 rule_id=RULE)  # fmt: skip
    assert event is not None
    assert event.fill == event.limit == odd.mid


def test_fee_applies_per_contract() -> None:
    event = fill(time=T, side=Side.BUY, instrument=OPTION, qty=3, quote=QUOTE,
                 model=model(fee="0.65"), rule_id=RULE)  # fmt: skip
    assert event is not None
    assert event.fee == Money.from_dollars("1.95")
    assert event.cash_delta == Money(-10_150 * 300) - Money.from_dollars("1.95")


def test_stock_fills_carry_no_fee_and_multiplier_one() -> None:
    event = fill(time=T, side=Side.BUY, instrument=StockId("SYN"), qty=100, quote=QUOTE,
                 model=model(fee="0.65"), rule_id=RuleId("X-S5"))  # fmt: skip
    assert event is not None
    assert event.fee == Money.zero()
    assert event.cash_delta == Money(-10_150 * 100)


def test_the_audit_records_the_quote_and_capture() -> None:
    event = fill(time=T, side=Side.SELL, instrument=OPTION, qty=1, quote=QUOTE,
                 model=model(0.25), rule_id=RULE, audit={"delta": 0.3})  # fmt: skip
    assert event is not None
    assert event.audit == {"delta": 0.3, "bid": 10_000, "ask": 10_300, "spread_capture": 0.25}


@pytest.mark.parametrize("side", [Side.EXPIRE, Side.ASSIGN])
def test_only_buys_and_sells_fill_at_a_price(side: Side) -> None:
    with pytest.raises(ValueError, match="only a BUY or SELL"):
        fill_price(QUOTE, side, 0.0)


@given(
    bid=st.integers(1, 10_000_000),
    width=st.integers(0, 100_000),
    capture=st.sampled_from([0.0, 0.1, 0.25, 0.5, 0.75, 1.0]),
)
def test_inv_03_a_fill_lies_between_mid_and_the_far_side(
    bid: int, width: int, capture: float
) -> None:
    quote = Quote(Price(bid), Price(bid + width))
    buy, sell = fill_price(quote, Side.BUY, capture), fill_price(quote, Side.SELL, capture)
    assert quote.mid.units - 1 <= buy.units <= quote.ask.units
    assert quote.bid.units <= sell.units <= quote.mid.units + 1
    assert buy.units + sell.units in (bid * 2 + width, bid * 2 + width + 1, bid * 2 + width - 1)
