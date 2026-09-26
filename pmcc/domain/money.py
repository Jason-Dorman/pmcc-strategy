"""Integer money (DEC-44): prices and cash are counts of $0.0001 units, never floats."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import final

UNITS_PER_DOLLAR = 10_000
UNITS_PER_CENT = 100

type Dollars = Decimal | Fraction | float | str


def _quantize(value: Dollars) -> int:
    """Dollars → units, rounding half-even. A float is read by its shortest repr.

    The arithmetic is exact (Fraction), so no decimal context precision can round twice.
    """
    exact = value if isinstance(value, Fraction) else Fraction(_as_decimal(value))
    return round(exact * UNITS_PER_DOLLAR)  # round() on a Fraction is half-even


def _as_decimal(value: Decimal | float | str) -> Decimal:
    # float.__repr__, not repr(): numpy 2 reprs np.float64 as "np.float64(1.5)".
    text = float.__repr__(value) if isinstance(value, float) else value
    try:
        dec = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"not a dollar amount: {value!r}") from None
    if not dec.is_finite():
        raise ValueError(f"dollar amount must be finite: {value!r}")
    return dec


def _to_dollars(units: int) -> Decimal:
    return Decimal(f"{units}e-4")  # exact, always 4 decimal places, whatever the context


def _check_units(units: object) -> None:
    if type(units) is not int:
        raise TypeError(f"money units must be an int, got {type(units).__name__}")


def _same[T](kind: type[T], other: object) -> T:
    if not isinstance(other, kind):
        raise TypeError(f"cannot combine {kind.__name__} with {type(other).__name__}")
    return other


@final
@dataclass(frozen=True, order=True, slots=True)
class Price:
    """A per-share price in $0.0001 units. A difference of two prices is a price."""

    units: int

    def __post_init__(self) -> None:
        _check_units(self.units)

    @classmethod
    def from_dollars(cls, value: Dollars) -> Price:
        return cls(_quantize(value))

    def to_dollars(self) -> Decimal:
        return _to_dollars(self.units)

    def notional(self, multiplier: int, qty: int) -> Money:
        """Price * multiplier * qty, exactly (100 per option contract, 1 per share)."""
        return Money(self.units * multiplier * qty)

    def __add__(self, other: Price) -> Price:
        return Price(self.units + _same(Price, other).units)

    def __sub__(self, other: Price) -> Price:
        return Price(self.units - _same(Price, other).units)

    def __neg__(self) -> Price:
        return Price(-self.units)


@final
@dataclass(frozen=True, order=True, slots=True)
class Money:
    """Cash, market value or P&L in $0.0001 units."""

    units: int

    def __post_init__(self) -> None:
        _check_units(self.units)

    @classmethod
    def zero(cls) -> Money:
        return cls(0)

    @classmethod
    def from_dollars(cls, value: Dollars) -> Money:
        return cls(_quantize(value))

    def to_dollars(self) -> Decimal:
        return _to_dollars(self.units)

    def __add__(self, other: Money) -> Money:
        return Money(self.units + _same(Money, other).units)

    def __sub__(self, other: Money) -> Money:
        return Money(self.units - _same(Money, other).units)

    def __neg__(self) -> Money:
        return Money(-self.units)

    def __mul__(self, factor: int) -> Money:
        _check_units(factor)
        return Money(self.units * factor)

    def __rmul__(self, factor: int) -> Money:
        return self * factor
