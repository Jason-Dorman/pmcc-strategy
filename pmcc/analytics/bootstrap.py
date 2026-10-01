"""The bootstrap CI of a mean weekly return (Spec › Uncertainty; P6-05; PO, DEC-61).

One function serves both uses. Its input is a week × symbol table of weekly returns: one column for
a run on its symbol, one per symbol for the pooled universe. Each of the 10,000 resamples draws
whole weeks (rows) with replacement, so in the pooled table every symbol moves with its week and
cross-symbol correlation isn't counted as independent evidence; its mean is the mean of every cell
drawn. The CI is the 2.5th and 97.5th percentiles of those means (numpy's default, linear,
interpolation).

The draws come from numpy's PCG64 seeded with `bootstrap.seed` from `configs/universe.yaml`, fresh
for every CI, so a CI never depends on which ran before it, and runs of equal length resample the
same weeks.
"""

import math
from collections.abc import Sequence

import numpy as np

from pmcc.export.analytics_models import MeanCI

RESAMPLES = 10_000
LEVEL = 0.95


def mean_ci(table: Sequence[Sequence[float]], seed: int) -> MeanCI | None:
    """The CI of `table`'s mean (rows are weeks, columns symbols), or None under 2 weeks. Raises
    `ValueError` for a ragged table or a value that isn't finite."""
    weeks = len(table)
    if weeks < 2:
        return None
    if len({len(row) for row in table}) != 1 or not table[0]:
        raise ValueError("a week × symbol table needs every week to hold one return per symbol")
    if not all(math.isfinite(v) for row in table for v in row):
        raise ValueError("every weekly return in the table must be finite")
    returns = np.asarray(table, dtype=np.float64)
    draws = np.random.Generator(np.random.PCG64(seed)).integers(0, weeks, size=(RESAMPLES, weeks))
    means = returns[draws].mean(axis=(1, 2))
    low, high = np.quantile(means, [(1 - LEVEL) / 2, (1 + LEVEL) / 2])
    return MeanCI(mean=float(returns.mean()), low=float(low), high=float(high), level=LEVEL,
                  resamples=RESAMPLES, seed=seed, weeks=weeks)  # fmt: skip
