"""The fill-assumption check (P6-07; PO, DEC-64): OLS of TRDPRC_1 on mid with slope, intercept, R²
and N, and the median |print − mid| as a share of the spread, per group and pooled. Every number
here is worked by hand."""

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction

import pytest

from pmcc.analytics.fillcheck import GROUPS, fill_check, fit, pooled_fill_check, sample


@dataclass(frozen=True, slots=True)
class Pairs:
    mid: tuple[int, ...]
    trade: tuple[int, ...]
    spread: tuple[int, ...]


def pairs(*rows: tuple[str, str, str]) -> Pairs:
    """(mid, trade, spread) in dollars → $0.0001 units."""
    mid, trade, spread = (tuple(int(Decimal(row[i]) * 10_000) for row in rows) for i in range(3))
    return Pairs(mid, trade, spread)


EMPTY = Pairs((), (), ())

# x̄ 2.5, ȳ 2.525; Σ(x − x̄)² 5, Σ(x − x̄)(y − ȳ) 5, Σ(y − ȳ)² 5.0125: slope 1, intercept 0.025,
# R² 5² ÷ (5 × 5.0125) = 400/401.
LINE = pairs(("1.00", "1.05", "0.10"), ("2.00", "1.95", "0.10"), ("3.00", "3.10", "0.20"),
             ("4.00", "4.00", "0.00"))  # fmt: skip


def test_p6_07_fit_is_ols_of_trade_on_mid_worked_by_hand() -> None:
    result = fit(LINE)

    assert result is not None
    assert (result.slope, result.intercept, result.n) == (1.0, 0.025, 4)
    assert result.r2 == float(Fraction(400, 401))


def test_p6_07_fit_is_exact_whatever_the_order_of_the_points() -> None:
    backwards = Pairs(LINE.mid[::-1], LINE.trade[::-1], LINE.spread[::-1])

    assert fit(backwards) == fit(LINE)


def test_p6_07_median_gap_is_a_share_of_the_spread_without_locked_quotes() -> None:
    """Gaps 0.02, 0.05, 0.05 and 0.30 over spreads 0.10, 0.10, 0.20 and 0.30: 0.2, 0.5 (at the
    bid), 0.25 and 1.0 (half a spread past the ask). The locked quote is left out, so the median
    of four is (0.25 + 0.5) ÷ 2."""
    rows = pairs(("1.00", "1.02", "0.10"), ("2.00", "1.95", "0.10"), ("3.00", "3.05", "0.20"),
                 ("4.00", "4.30", "0.30"), ("5.00", "5.00", "0.00"))  # fmt: skip

    result = fit(rows)

    assert result is not None
    assert (result.median_abs_gap_pct_spread, result.locked, result.n) == (0.375, 1, 5)


def test_p6_07_median_gap_is_null_when_every_quote_is_locked() -> None:
    result = fit(pairs(("1.00", "1.00", "0"), ("2.00", "2.01", "0")))

    assert result is not None
    assert (result.median_abs_gap_pct_spread, result.locked) == (None, 2)


@pytest.mark.parametrize(
    "rows",
    [
        EMPTY,
        pairs(("1.00", "1.05", "0.10")),
        pairs(("1.00", "1.05", "0.10"), ("1.00", "0.95", "0.10")),  # every mid the same
    ],
    ids=["none", "one", "one-mid"],
)
def test_p6_07_no_fit_without_two_distinct_mids(rows: Pairs) -> None:
    assert fit(rows) is None


def test_p6_07_r2_is_null_when_every_trade_is_the_same() -> None:
    result = fit(pairs(("1.00", "1.50", "1.00"), ("2.00", "1.50", "1.00")))

    assert result is not None
    assert (result.slope, result.intercept, result.r2) == (0.0, 1.5, None)


def test_p6_07_fill_check_has_shorts_then_longs_with_every_pair_in_dollars() -> None:
    check = fill_check("NVDA", {"longs": EMPTY, "shorts": LINE})

    assert check.symbol == "NVDA"
    assert [g.group for g in check.groups] == list(GROUPS) == ["shorts", "longs"]
    shorts, longs = check.groups
    assert shorts.points.mid == (Decimal("1"), Decimal("2"), Decimal("3"), Decimal("4"))
    assert shorts.points.trade[0] == Decimal("1.05")
    assert shorts.points.spread[3] == Decimal(0)
    assert shorts.fit == fit(LINE)
    assert (longs.points.mid, longs.fit) == ((), None)


def test_p6_07_fill_check_refuses_another_set_of_groups() -> None:
    with pytest.raises(ValueError, match="shorts"):
        fill_check("NVDA", {"longs": LINE})


def test_p6_07_a_files_points_give_back_the_pairs_they_came_from() -> None:
    shorts = fill_check("NVDA", {"shorts": LINE, "longs": EMPTY}).groups[0]

    assert sample(shorts.points) == (LINE.mid, LINE.trade, LINE.spread)


def test_p6_07_pooled_fits_every_symbols_pairs_together() -> None:
    """LINE split across two symbols pools back to LINE's own fit."""
    first, second = (Pairs(LINE.mid[s], LINE.trade[s], LINE.spread[s])
                     for s in (slice(0, 2), slice(2, 4)))  # fmt: skip
    files = [fill_check("TSLA", {"shorts": second, "longs": EMPTY}),
             fill_check("AAPL", {"shorts": first, "longs": LINE})]  # fmt: skip

    pooled = pooled_fill_check(files)

    assert pooled.symbols == ("AAPL", "TSLA")
    assert [(g.group, g.fit) for g in pooled.groups] == [("shorts", fit(LINE)),
                                                         ("longs", fit(LINE))]  # fmt: skip
