"""`configs/universe.yaml`: the backtest window, r, and each symbol's identifiers (Spec › Universe).

One window for every symbol (DEC-07), one constant r stated with its source (DEC-11), and each
symbol's stock RIC and option root (DEC-12). The file is found from this module, not the working
directory, like the calendar. `starting_cash` joins with P3-09 (DEC-30) and the bootstrap seed with
P6-05 (DEC-61).
"""

import math
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pmcc.config.yaml_file import read_yaml
from pmcc.domain.calendar import SessionCalendar

UNIVERSE_PATH = Path(__file__).resolve().parents[2] / "configs" / "universe.yaml"

MIN_WEEKS = 10  # Spec › Universe: at least 10 weeks
BILL_DAYS = 91  # a 3-month Treasury bill's term: 13 weeks
RATE_DECIMALS = 4  # r is stated, and used, to 0.01%

_TICKER = r"^[A-Z][A-Z0-9]*$"  # OptionId's root rule, so a root here always builds a RIC
_STOCK_RIC = r"^[A-Z][A-Z0-9]*\.[A-Z]{1,2}$"  # ticker, dot, venue suffix (.O, .N, .P, …)


def continuous_rate(investment_yield_pct: float, days: int = BILL_DAYS) -> float:
    """The continuously compounded rate that discounts a bill like its quoted yield does.

    A bill's investment-basis yield is simple interest over its term, ACT/365, so it prices the
    bill at 1 / (1 + y·days/365). The continuous rate r gives the same price as e^(-r·days/365).
    """
    return math.log1p(investment_yield_pct / 100 * days / 365) * 365 / days


class Window(BaseModel):
    """The one backtest window: a week-open session to a week-final session, inclusive."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    start: date
    end: date

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.start > self.end:
            raise ValueError(f"the window starts {self.start}, after it ends {self.end}")
        return self

    def check_sessions(self, calendar: SessionCalendar) -> None:
        """Raises `ValueError` unless the window runs from a week-open session to a week-final
        session and spans at least 10 weekly expiries (DEC-07, Spec › Universe)."""
        if calendar.week_open(self.start).day != self.start:
            raise ValueError(f"the window must start on a week-open session; {self.start} isn't")
        if calendar.week_final(self.end).day != self.end:
            raise ValueError(f"the window must end on a week-final session; {self.end} isn't")
        weeks = len(calendar.weekly_expiries(self.start, self.end))
        if weeks < MIN_WEEKS:
            raise ValueError(f"the window must span at least {MIN_WEEKS} weeks; it spans {weeks}")


class RiskFreeRate(BaseModel):
    """r: one continuously compounded constant for the window, and the quote it came from."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: float = Field(ge=0, lt=1)
    quoted_pct: float = Field(ge=0, lt=100)  # the series' value on `as_of`, investment basis
    series: str = Field(min_length=1)
    as_of: date
    source: str = Field(min_length=1)

    @model_validator(mode="after")
    def _converted(self) -> Self:
        expected = round(continuous_rate(self.quoted_pct), RATE_DECIMALS)
        if self.value != expected:
            raise ValueError(
                f"r {self.value} isn't {self.series} {self.quoted_pct}% converted to continuous "
                f"compounding over a {BILL_DAYS}-day bill ({expected})"
            )
        return self


class Underlying(BaseModel):
    """One symbol and the identifiers LSEG knows it by."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str = Field(pattern=_TICKER)
    stock_ric: str = Field(pattern=_STOCK_RIC)
    option_root: str = Field(pattern=_TICKER)

    @model_validator(mode="after")
    def _own_ric(self) -> Self:
        if self.stock_ric.split(".")[0] != self.symbol:
            raise ValueError(f"{self.symbol}'s stock RIC {self.stock_ric} names another symbol")
        return self


class Universe(BaseModel):
    """The file as validated on its own. `load_universe` also checks the window's sessions."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    window: Window
    risk_free_rate: RiskFreeRate
    symbols: tuple[Underlying, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        twice = sorted(s for s, n in Counter(u.symbol for u in self.symbols).items() if n > 1)
        if twice:
            raise ValueError(f"symbols listed more than once: {twice}")
        if self.risk_free_rate.as_of >= self.window.start:
            raise ValueError(
                f"r is quoted on {self.risk_free_rate.as_of}, not before the window starts "
                f"{self.window.start}, so the first decision couldn't have known it"
            )
        return self


def read_universe_file(path: Path = UNIVERSE_PATH) -> Universe:
    """The validated file, without the calendar."""
    return Universe.model_validate(read_yaml(path))


def load_universe(calendar: SessionCalendar, path: Path = UNIVERSE_PATH) -> Universe:
    """The validated file, with its window checked against `calendar`."""
    universe = read_universe_file(path)
    universe.window.check_sessions(calendar)
    return universe
