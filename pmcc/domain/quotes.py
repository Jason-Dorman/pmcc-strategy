"""A valid two-sided quote and its mid (LDG §4.7, DEC-44)."""

from dataclasses import dataclass
from fractions import Fraction
from typing import final

from pmcc.domain.money import Price


@final
@dataclass(frozen=True, slots=True)
class Quote:
    """BID and ASK on one bar. Only a valid quote exists: BID > 0, ASK > 0 and ASK ≥ BID."""

    bid: Price
    ask: Price

    def __post_init__(self) -> None:
        if not (0 < self.bid.units <= self.ask.units):
            raise ValueError(f"not a valid quote: BID {self.bid} ASK {self.ask}")

    @property
    def mid(self) -> Price:
        """(BID + ASK) / 2, rounded half-even to $0.0001 as fills are (DEC-44)."""
        return Price(round(Fraction(self.bid.units + self.ask.units, 2)))
