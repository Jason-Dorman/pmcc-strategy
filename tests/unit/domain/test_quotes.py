"""`Quote`: only a valid quote exists, and its mid rounds half-even (DEC-44)."""

import pytest

from pmcc.domain.money import Price
from pmcc.domain.quotes import Quote


def _q(bid: int, ask: int) -> Quote:
    return Quote(Price(bid), Price(ask))


def test_quote_mid_is_the_average_of_bid_and_ask() -> None:
    assert _q(10_000, 10_200).mid == Price(10_100)


def test_quote_mid_rounds_a_half_unit_to_even() -> None:
    assert _q(10_000, 10_001).mid == Price(10_000)
    assert _q(10_001, 10_002).mid == Price(10_002)


@pytest.mark.parametrize(("bid", "ask"), [(0, 100), (-1, 100), (101, 100)])
def test_quote_refuses_an_invalid_quote(bid: int, ask: int) -> None:
    with pytest.raises(ValueError, match="not a valid quote"):
        _q(bid, ask)


def test_quote_allows_a_locked_market() -> None:
    assert _q(100, 100).mid == Price(100)
