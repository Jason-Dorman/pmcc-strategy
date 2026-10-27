"""The S&P 500 benchmark (WD-03, WD-17): two closes from `configs/benchmarks.yaml`.

The wheel is compared with the index's price return over the same window: from the last close
before the window, which the first decision could have known, to the window's last close.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pmcc.config.strategy import CONFIGS_DIR
from pmcc.config.yaml_file import read_yaml
from pmcc.domain.calendar import SessionCalendar

BENCHMARKS_PATH = CONFIGS_DIR / "benchmarks.yaml"


class BenchmarkError(Exception):
    """The benchmark file is malformed, or its closes don't bracket the window."""


@final
class IndexClose(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    day: date
    close: Decimal = Field(gt=0)


@final
class IndexBenchmark(BaseModel):
    """An index's close before the window and at its end, and where they came from."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    series: str = Field(min_length=1)
    start: IndexClose
    end: IndexClose
    source: str = Field(min_length=1)

    @property
    def price_return(self) -> Decimal:
        return self.end.close / self.start.close - 1


@final
class _File(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sp500: IndexBenchmark


def load_sp500(
    calendar: SessionCalendar, window_start: date, window_end: date, path: Path = BENCHMARKS_PATH
) -> IndexBenchmark:
    """The S&P 500's closes, checked against the window. Raises `BenchmarkError`."""
    try:
        sp500 = _File.model_validate(read_yaml(path)).sp500
    except (ValidationError, ValueError) as exc:
        raise BenchmarkError(f"{path}: {exc}") from exc
    before = calendar.sessions_before(window_start, 1)[0].day
    if sp500.start.day != before:
        raise BenchmarkError(
            f"{path}: the start close is {sp500.start.day}; the last close before the window is "
            f"{before}"
        )
    if sp500.end.day != window_end:
        raise BenchmarkError(
            f"{path}: the end close is {sp500.end.day}; the window ends {window_end}"
        )
    return sp500
