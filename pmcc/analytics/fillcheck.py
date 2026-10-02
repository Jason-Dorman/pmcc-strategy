"""The fill-assumption check (Spec › Fill-assumption check; P6-07; PO, DEC-64): how far a bar's
trade print sits from its end-of-bar mid, which every fill assumes.

- **Fit:** OLS of TRDPRC_1 (y) on mid (x), with slope, intercept, R² and N. The sums are taken in
  whole $0.0001 units and the coefficients as exact fractions, so a fit doesn't depend on the
  order of its points (INV-13) and the pooled fit equals a fit of every pair at once.
- **Gap:** the median |print − mid| ÷ (ASK − BID): 0 is a print at the mid, 0.5 one at the bid or
  the ask. A locked quote (BID = ASK) has no spread, so it is left out of the median and counted.
- **Groups:** shorts (weekly calls) and longs (the monthly long candidates), per symbol and
  pooled over the universe. Which bars each holds is `pmcc.data.fillcheck`'s (DEC-64). The long
  leg is expected to fit worse, and is published whatever it shows (HR-7).

A print can be up to an hour older than the end-of-bar quote it is paired with (DEC-64).
"""

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Protocol, final

from pmcc.domain.money import UNITS_PER_DOLLAR, Price
from pmcc.export.analytics_models import (
    FillCheck,
    FillGroup,
    FillPoints,
    Fit,
    PooledFillCheck,
    PooledFillGroup,
)

GROUPS = ("shorts", "longs")

type Columns = tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]  # mid, trade, spread


class FillPairs(Protocol):
    """A group's pairs as three columns of $0.0001 units, one entry per contract-bar."""

    @property
    def mid(self) -> Sequence[int]: ...
    @property
    def trade(self) -> Sequence[int]: ...
    @property
    def spread(self) -> Sequence[int]: ...


def fill_check(symbol: str, groups: Mapping[str, FillPairs]) -> FillCheck:
    """`{SYM}/fill_check.json`: every pair of each group and its fit. Raises `ValueError` unless
    `groups` holds exactly the shorts and the longs."""
    if set(groups) != set(GROUPS):
        raise ValueError(f"a fill check has the groups {GROUPS}, not {sorted(groups)}")
    return FillCheck(
        symbol=symbol,
        groups=tuple(FillGroup(group=g, points=_points(groups[g]), fit=fit(groups[g]))
                     for g in GROUPS),
    )  # fmt: skip


def pooled_fill_check(files: Sequence[FillCheck]) -> PooledFillCheck:
    """`universe/pooled_fill_check.json`: each group's fit over every symbol's pairs together."""
    columns: dict[str, list[Columns]] = {g: [] for g in GROUPS}
    for file in files:
        for group in file.groups:
            columns[group.group].append(sample(group.points))
    return PooledFillCheck(
        symbols=tuple(sorted(f.symbol for f in files)),
        groups=tuple(PooledFillGroup(group=g, fit=fit(_Joined.of(columns[g]))) for g in GROUPS),
    )


def fit(pairs: FillPairs) -> Fit | None:
    """The OLS fit and the median gap; None under 2 pairs or when every mid is the same."""
    x, y = pairs.mid, pairs.trade
    n = len(x)
    sx, sy = sum(x), sum(y)
    dx = n * sum(v * v for v in x) - sx * sx  # n² × the variance of x
    if n < 2 or dx == 0:
        return None
    dxy = n * sum(a * b for a, b in zip(x, y, strict=True)) - sx * sy
    dy = n * sum(v * v for v in y) - sy * sy
    slope = Fraction(dxy, dx)
    intercept = (sy - slope * sx) / n / UNITS_PER_DOLLAR
    gaps = [Fraction(abs(t - m), s) for m, t, s in zip(x, y, pairs.spread, strict=True) if s]
    return Fit(
        slope=float(slope),
        intercept=float(intercept),
        r2=float(Fraction(dxy * dxy, dx * dy)) if dy else None,
        n=n,
        median_abs_gap_pct_spread=float(statistics.median(gaps)) if gaps else None,
        locked=n - len(gaps),
    )


def sample(points: FillPoints) -> Columns:
    """A file's points back in $0.0001 units: the pairs they came from."""
    return (_units(points.mid), _units(points.trade), _units(points.spread))


def _points(pairs: FillPairs) -> FillPoints:
    return FillPoints(mid=_dollars(pairs.mid), trade=_dollars(pairs.trade),
                      spread=_dollars(pairs.spread))  # fmt: skip


def _dollars(units: Sequence[int]) -> tuple[Decimal, ...]:
    return tuple(Price(u).to_dollars() for u in units)


def _units(dollars: Sequence[Decimal]) -> tuple[int, ...]:
    return tuple(Price.from_dollars(d).units for d in dollars)


@final
@dataclass(frozen=True, slots=True)
class _Joined:
    """Several symbols' columns as one group's pairs."""

    mid: tuple[int, ...]
    trade: tuple[int, ...]
    spread: tuple[int, ...]

    @classmethod
    def of(cls, parts: Sequence[Columns]) -> "_Joined":
        mid, trade, spread = (tuple(v for p in parts for v in p[i]) for i in range(3))
        return cls(mid, trade, spread)
