"""`Price` and `Money`: integer $0.0001 units, quantized half-even (DEC-44, ARCHITECTURE §4.1)."""

from decimal import Decimal, localcontext
from fractions import Fraction

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pmcc.domain.money import UNITS_PER_DOLLAR, Money, Price

units = st.integers(min_value=-(10**12), max_value=10**12)


def test_money_units_per_dollar_is_ten_thousand() -> None:
    assert UNITS_PER_DOLLAR == 10_000


@pytest.mark.parametrize(
    ("dollars", "expected"),
    [
        ("1.23445", 12344),  # tie rounds to the even unit
        ("1.23455", 12346),
        ("1.23435", 12344),
        ("-1.23445", -12344),
        ("0.00005", 0),
        ("0.00015", 2),
        ("1.234451", 12345),  # above the tie rounds up
        ("1.234449", 12344),
        ("2", 20000),
    ],
)
def test_money_price_quantizes_half_even(dollars: str, expected: int) -> None:
    assert Price.from_dollars(dollars) == Price(expected)
    assert Price.from_dollars(Decimal(dollars)) == Price(expected)


def test_money_price_quantizes_floats_by_their_shortest_repr() -> None:
    # Float 1.23445 is stored as 1.23445000000000004…, just above the tie, so its binary
    # value would round up to 12345. Its repr "1.23445" is the quote as printed: a tie.
    assert Price.from_dollars(1.23445) == Price(12344)
    assert Price.from_dollars(1.23455) == Price(12346)
    assert Price.from_dollars(0.1 + 0.2) == Price(3000)


def test_money_price_quantizes_numpy_float64_like_a_float() -> None:
    assert Price.from_dollars(np.float64(1.23445)) == Price(12344)
    assert Money.from_dollars(np.array([1.5])[0]) == Money(15_000)


def test_money_price_quantizes_exactly_beyond_28_significant_digits() -> None:
    # Just above the tie; a 28-digit decimal multiply would round it onto the tie first.
    assert Price.from_dollars("1.000050000000000000000000000001") == Price(10001)
    assert Price.from_dollars(Decimal("1.000049999999999999999999999999")) == Price(10000)


def test_money_ignores_the_ambient_decimal_context() -> None:
    with localcontext() as ctx:
        ctx.prec = 3
        assert Price.from_dollars("123.45675") == Price(1_234_568)
        assert str(Money(123_456_789).to_dollars()) == "12345.6789"


def test_money_to_dollars_keeps_four_decimals_for_huge_amounts() -> None:
    assert str(Money(10**28 + 1).to_dollars()) == "1000000000000000000000000.0001"


def test_money_price_quantizes_fractions_half_even() -> None:
    assert Price.from_dollars(Fraction(1, 20_000)) == Price(0)  # exactly half a unit
    assert Price.from_dollars(Fraction(3, 20_000)) == Price(2)
    assert Price.from_dollars(Fraction(1, 3)) == Price(3333)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), "abc", "NaN"])
def test_money_price_rejects_non_finite_or_malformed_dollars(bad: float | str) -> None:
    with pytest.raises(ValueError, match="dollar"):
        Price.from_dollars(bad)


@pytest.mark.parametrize("bad", [1.5, True, "1"])
def test_money_units_must_be_an_int(bad: object) -> None:
    with pytest.raises(TypeError):
        Price(bad)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        Money(bad)  # type: ignore[arg-type]


def test_money_price_arithmetic_stays_in_price() -> None:
    assert Price(30_000) - Price(12_500) == Price(17_500)
    assert Price(1) + Price(2) == Price(3)
    assert -Price(5) == Price(-5)


def test_money_arithmetic_stays_in_money() -> None:
    assert Money(100) + Money(-250) == Money(-150)
    assert Money(100) - Money(250) == Money(-150)
    assert -Money(7) == Money(-7)
    assert Money(35_000) * 3 == Money(105_000)
    assert 3 * Money(35_000) == Money(105_000)


def test_money_price_notional_is_exact_money() -> None:
    # One contract at $12.3456 per share: 123456 units x 100 shares.
    assert Price(123_456).notional(multiplier=100, qty=1) == Money(12_345_600)
    assert Price(123_456).notional(multiplier=100, qty=3) == Money(37_036_800)
    assert Price(123_456).notional(multiplier=1, qty=-100) == Money(-12_345_600)


def test_money_price_and_money_never_mix() -> None:
    with pytest.raises(TypeError):
        Price(1) + Money(1)  # type: ignore[operator]
    with pytest.raises(TypeError):
        Money(1) - Price(1)  # type: ignore[operator]
    with pytest.raises(TypeError):
        Money(1) * 1.5  # type: ignore[operator]
    assert Price(1) != Money(1)


def test_money_values_order_within_their_type() -> None:
    assert Price(1) < Price(2)
    assert Money(-1) < Money(0) <= Money(0)
    assert sorted([Price(3), Price(-1), Price(2)]) == [Price(-1), Price(2), Price(3)]
    with pytest.raises(TypeError):
        _ = Price(1) < Money(2)  # type: ignore[operator]


def test_money_to_dollars_has_four_decimals() -> None:
    assert Price(12_345).to_dollars() == Decimal("1.2345")
    assert str(Money(-5).to_dollars()) == "-0.0005"
    assert str(Money(20_000).to_dollars()) == "2.0000"
    assert str(Money.zero().to_dollars()) == "0.0000"


def test_money_values_are_hashable() -> None:
    assert len({Price(1), Price(1), Price(2)}) == 2
    assert len({Money(1), Money(1)}) == 1


@given(units, units)
def test_money_addition_and_subtraction_are_exact_inverses(a: int, b: int) -> None:
    assert Money(a) + Money(b) - Money(b) == Money(a)
    assert Price(a) + Price(b) - Price(b) == Price(a)


@given(units)
def test_money_to_dollars_round_trips_through_from_dollars(u: int) -> None:
    assert Price.from_dollars(Price(u).to_dollars()) == Price(u)
    assert Money.from_dollars(Money(u).to_dollars()) == Money(u)


@given(units, st.integers(min_value=1, max_value=1000), st.integers(-1000, 1000))
def test_money_notional_equals_repeated_addition(u: int, multiplier: int, qty: int) -> None:
    assert Price(u).notional(multiplier=multiplier, qty=qty) == Money(u * multiplier * qty)
