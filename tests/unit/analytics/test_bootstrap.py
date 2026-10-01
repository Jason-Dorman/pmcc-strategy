"""The bootstrap CI of the mean weekly return (P6-05; PO, DEC-61): 10,000 resamples of whole weeks
from numpy's PCG64 at the universe's seed, a 95% percentile interval; pooled, each resample takes
whole weeks across every symbol at once."""

import numpy as np
import pytest

from pmcc.analytics.bootstrap import LEVEL, RESAMPLES, mean_ci

SEED = 535
# Twelve irregular weeks: their resample means have no ties at the 2.5th and 97.5th percentiles,
# so the oracle pins the seed and the interpolation (a short series ties there for any seed).
WEEKS = [0.015683, 0.028114, -0.019897, -0.025093, 0.020998, 0.015839, -0.023975, -0.004594,
         0.029672, -0.003115, -0.033453, 0.006717]  # fmt: skip


def _column(values: list[float]) -> list[list[float]]:
    return [[v] for v in values]


def _percentile(sorted_means: list[float], q: float) -> float:
    """numpy's default ("linear") percentile, written out: interpolate at q × (n − 1)."""
    position = q * (len(sorted_means) - 1)
    below = int(position)
    above = min(below + 1, len(sorted_means) - 1)
    return sorted_means[below] + (position - below) * (sorted_means[above] - sorted_means[below])


def test_dec_61_ci_is_the_percentile_interval_of_10000_resampled_means() -> None:
    """The oracle draws the same week indices and averages each resample in plain Python. Its
    order statistics either side of each percentile differ, so another seed or another
    interpolation (nearest, lower, higher) would miss it."""
    ci = mean_ci(_column(WEEKS), SEED)

    n = len(WEEKS)
    draws = np.random.Generator(np.random.PCG64(SEED)).integers(0, n, size=(10_000, n))
    rows: list[list[int]] = draws.tolist()
    means = sorted(sum(WEEKS[i] for i in row) / n for row in rows)
    assert means[249] < means[250]  # 0.025 × 9,999 = 249.975
    assert means[9749] < means[9750]  # 0.975 × 9,999 = 9,749.025
    assert ci is not None
    assert ci.mean == pytest.approx(sum(WEEKS) / n)
    assert ci.low == pytest.approx(_percentile(means, 0.025), abs=1e-15)
    assert ci.high == pytest.approx(_percentile(means, 0.975), abs=1e-15)
    assert ci.low < ci.mean < ci.high


def test_dec_61_ci_records_its_seed_resamples_level_and_weeks() -> None:
    ci = mean_ci(_column(WEEKS), SEED)

    assert ci is not None
    assert (ci.seed, ci.resamples, ci.level, ci.weeks) == (SEED, 10_000, 0.95, 12)
    assert (RESAMPLES, LEVEL) == (10_000, 0.95)  # Spec › Uncertainty


def test_dec_61_ci_is_reproducible_from_its_seed() -> None:
    """The same seed draws the same interval; another seed draws another, not just a new label."""
    first, again, other = (mean_ci(_column(WEEKS), s) for s in (SEED, SEED, SEED + 1))

    assert first == again
    assert first is not None
    assert other is not None
    assert (first.low, first.high) != (other.low, other.high)


def test_dec_61_a_constant_series_has_a_ci_of_one_point() -> None:
    ci = mean_ci(_column([0.01] * 6), SEED)

    assert ci is not None
    assert (ci.mean, ci.low, ci.high) == pytest.approx((0.01, 0.01, 0.01))


def test_dec_61_under_two_weeks_there_is_no_ci() -> None:
    assert mean_ci(_column([0.01]), SEED) is None
    assert mean_ci([], SEED) is None


def test_dec_61_pooled_over_one_symbol_is_that_symbols_ci() -> None:
    """Two identical symbols resample the same weeks, so their pooled CI is one symbol's (to the
    last bits numpy's summation order leaves)."""
    single, doubled = mean_ci(_column(WEEKS), SEED), mean_ci([[w, w] for w in WEEKS], SEED)

    assert single is not None
    assert doubled is not None
    assert (doubled.mean, doubled.low, doubled.high) == pytest.approx(
        (single.mean, single.low, single.high), abs=1e-15)  # fmt: skip


def test_dec_61_pooled_resamples_whole_weeks_so_the_symbols_move_together() -> None:
    """Two symbols whose weeks always cancel: every resample keeps both halves of each week it
    draws, so every mean is 0. Resampling the symbols apart would scatter the means instead."""
    table = [[w, -w] for w in WEEKS]

    ci = mean_ci(table, SEED)

    assert ci is not None
    assert (ci.mean, ci.low, ci.high) == pytest.approx((0.0, 0.0, 0.0), abs=1e-15)
    assert ci.weeks == len(WEEKS)


def test_dec_61_a_ragged_or_non_finite_table_is_refused() -> None:
    with pytest.raises(ValueError, match="table"):
        mean_ci([[0.01, 0.02], [0.03]], SEED)
    with pytest.raises(ValueError, match="finite"):
        mean_ci(_column([0.01, float("nan")]), SEED)
