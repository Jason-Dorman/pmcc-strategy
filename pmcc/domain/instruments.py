"""Option identity and the blotter's sides (Spec › Blotter)."""

import re
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import final

from pmcc.domain.money import UNITS_PER_CENT, Price

OPTION_MULTIPLIER = 100  # shares per option contract

_ROOT = re.compile(r"[A-Z][A-Z0-9]*")


class Right(StrEnum):
    CALL = "C"
    PUT = "P"


class Side(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    EXPIRE = "EXPIRE"
    ASSIGN = "ASSIGN"


@final
@dataclass(frozen=True, order=True, slots=True)
class OptionId:
    """One listed contract. Sorts by root, expiry, right, then strike."""

    root: str
    expiry: date
    right: Right
    strike: Price

    def __post_init__(self) -> None:
        if not _ROOT.fullmatch(self.root):
            raise ValueError(f"option root must be upper-case letters and digits: {self.root!r}")
        if self.strike.units <= 0 or self.strike.units % UNITS_PER_CENT:
            raise ValueError(f"strike must be a positive whole number of cents: {self.strike}")

    @property
    def strike_cents(self) -> int:
        return self.strike.units // UNITS_PER_CENT
