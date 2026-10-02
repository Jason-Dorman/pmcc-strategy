"""Performance metrics (P6-01; PO, DEC-60), each against numbers worked by hand.

The three-week fixture (`tests/fakes/records.py`) has its closes and trades in its docstring; the
small cases below each isolate one definition.
"""

import math
from datetime import date
from decimal import Decimal
from fractions import Fraction

import pytest

from pmcc.analytics.bootstrap import mean_ci
from pmcc.analytics.performance import (
    daily_rate,
    daily_returns,
    longest_underwater,
    max_drawdown,
    metrics,
    nav_close,
    sharpe,
    sortino,
    weekly_returns,
)
from pmcc.domain.money import Money
from tests.fakes.records import (
    FRI_1,
    FRI_3,
    Records,
    bar,
    three_weeks,
    week_of_closes,
)

SEED = 535
R = 0.0371  # the window's continuously compounded risk-free rate (DEC-11)
CLOSES = [10050, 10100, 9950, 10000, 10200, 10150, 9995, 10050, 10100, 10098,
          10300, 10250, 10350, 10400, 10500]  # fmt: skip


def money(*dollars: int | str) -> list[Money]:
    return [Money.from_dollars(d) for d in dollars]


# ---- session closes and returns -----------------------------------------------------------------


def test_dec_60_session_close_nav_is_each_sessions_last_bar() -> None:
    closes = nav_close(three_weeks().ledger)

    assert [p.nav for p in closes] == [Decimal(c) for c in CLOSES]
    assert closes[0].session == date(2026, 9, 14)  # 10,050 at 16:00, not 9,999.35 at 10:00
    assert closes[2].nav == Decimal(9950)  # Wed Sep 16: its close, not 9,900 at 11:00
    assert closes[-1].session == FRI_3


def test_dec_60_daily_return_is_close_over_previous_close_the_first_over_starting_cash() -> None:
    returns = daily_returns(money(*CLOSES), Money.from_dollars(10_000))

    expected = [Fraction(n, p) - 1 for n, p in zip(CLOSES, [10_000, *CLOSES[:-1]], strict=True)]
    assert returns == pytest.approx([float(r) for r in expected], abs=1e-15)
    assert returns[0] == pytest.approx(0.005)
    assert returns[2] == pytest.approx(9950 / 10100 - 1)


def test_dec_60_weekly_return_is_week_final_close_over_the_previous_the_first_over_cash() -> None:
    weeks = weekly_returns(three_weeks().ledger, Money.from_dollars(10_000))

    assert [w.week_final for w in weeks] == [FRI_1, date(2026, 9, 25), FRI_3]
    assert [w.nav for w in weeks] == [Decimal(10200), Decimal(10098), Decimal(10500)]
    assert [w.value for w in weeks] == [0.02, -0.01, 0.03981]  # 0.0398098…, kept at 6 places


def test_dec_60_a_holiday_friday_ends_its_week_on_thursday() -> None:
    """The week-final session is the week's last close, whatever weekday it falls on."""
    ledger = week_of_closes(date(2026, 3, 30), ["10100", "10200", "10300", "10400"])  # Good Friday

    (week,) = weekly_returns(ledger, Money.from_dollars(10_000))

    assert (week.week_final, week.value) == (date(2026, 4, 2), pytest.approx(0.04))


# ---- Sharpe and Sortino -------------------------------------------------------------------------


def test_dec_111_the_daily_risk_free_rate_compounds_r_over_252_trading_days() -> None:
    """r is continuously compounded, so a trading day earns e^(r/252) − 1."""
    assert daily_rate(0.0371) == pytest.approx(math.exp(0.0371 / 252) - 1)
    assert daily_rate(0.0) == 0.0


def test_dec_111_sharpe_is_excess_mean_over_sample_std_annualized_by_root_252() -> None:
    """+10%, −10%, +10% less 1% a day: excess mean 1/30 − 0.01, sample std 2/√300 (a constant
    shift leaves it), so Sharpe (1/30 − 0.01) ÷ (2/√300) × √252."""
    want = (1 / 30 - 0.01) / (2 / math.sqrt(300)) * math.sqrt(252)
    assert sharpe([0.1, -0.1, 0.1], 0.01) == pytest.approx(want)


def test_dec_111_with_no_risk_free_rate_sharpe_is_dec_60s_annualized() -> None:
    assert sharpe([0.1, -0.1, 0.1], 0.0) == pytest.approx(math.sqrt(252) / (2 * math.sqrt(3)))


def test_dec_111_sortino_counts_every_day_below_the_risk_free_rate_as_downside() -> None:
    """+10%, +0.5%, +10% less 1% a day: excess 0.09, −0.005, 0.09, so the +0.5% day is a loss:
    mean(min(e, 0)²) = 0.000025/3, Sortino = (0.175/3) ÷ √(0.000025/3) × √252."""
    want = (0.175 / 3) / math.sqrt(0.000025 / 3) * math.sqrt(252)
    assert sortino([0.1, 0.005, 0.1], 0.01) == pytest.approx(want)


def test_dec_111_sortino_with_no_risk_free_rate_divides_by_the_losses_over_every_day() -> None:
    """mean(min(r, 0)²) = 0.01/3 over all three days, so (1/30) ÷ √(0.01/3) = 1/√3, × √252."""
    assert sortino([0.1, -0.1, 0.1], 0.0) == pytest.approx(math.sqrt(252) / math.sqrt(3))


def test_dec_111_sharpe_and_sortino_are_null_without_a_divisor() -> None:
    assert sharpe([0.01, 0.01, 0.01], 0.001) is None  # no variation
    assert sharpe([0.01], 0.001) is None  # a sample std needs two
    assert sortino([0.01, 0.02], 0.001) is None  # no day below the rate
    assert sortino([], 0.001) is None
    assert sortino([0.0], 0.001) is None  # one flat day is below the rate, but no sample


# ---- drawdown and time underwater ---------------------------------------------------------------


def test_dec_60_max_drawdown_starts_from_the_starting_cash_as_the_first_peak() -> None:
    fall, share = max_drawdown(money(9_900, 10_050), Money.from_dollars(10_000))

    assert (fall, share) == (Money.from_dollars(100), pytest.approx(0.01))


def test_dec_60_drawdown_dollars_and_share_are_each_their_own_maximum() -> None:
    """$100 → $50 is the largest share (50%); $1,000 → $900 the largest fall in dollars ($100)."""
    fall, share = max_drawdown(money(50, 1_000, 900), Money.from_dollars(100))

    assert (fall, share) == (Money.from_dollars(100), pytest.approx(0.5))


def test_dec_60_max_drawdown_is_zero_when_nav_never_falls() -> None:
    assert max_drawdown(money(10_000, 10_100), Money.from_dollars(10_000)) == (Money.zero(), 0.0)


def test_dec_60_longest_underwater_counts_sessions_from_peak_to_recovery() -> None:
    """Peaks at closes 2 (10,100), 5 (10,200) and 11 (10,300); recovered at 5, 11 and 13: spells
    of 3, 6 and 2 sessions."""
    assert longest_underwater(money(*CLOSES), Money.from_dollars(10_000)) == 6


def test_dec_60_longest_underwater_runs_to_the_end_when_never_recovered() -> None:
    """Peak at close 1; closes 2 to 4 below it: 3 sessions to the end."""
    assert longest_underwater(money(10_100, 10_000, 9_000, 10_099), Money.from_dollars(10_000)) == 3


def test_dec_60_longest_underwater_counts_from_the_start_when_the_first_close_is_below() -> None:
    assert longest_underwater(money(9_000, 9_500), Money.from_dollars(10_000)) == 2


def test_dec_60_regaining_the_peak_exactly_is_a_recovery() -> None:
    assert longest_underwater(money(10_100, 10_000, 10_100), Money.from_dollars(10_000)) == 2


def test_dec_60_longest_underwater_is_zero_on_a_rising_nav() -> None:
    assert longest_underwater(money(10_000, 10_100, 10_200), Money.from_dollars(10_000)) == 0


# ---- the metrics ---------------------------------------------------------------------------------


def test_dec_60_metrics_on_three_weeks() -> None:
    run = three_weeks()
    got = metrics(run, SEED, R)
    rf = Fraction(math.expm1(R / 252))
    excess = [Fraction(n, p) - 1 - rf
              for n, p in zip(CLOSES, [10_000, *CLOSES[:-1]], strict=True)]  # fmt: skip
    mean = sum(excess) / len(excess)
    sample_var = sum((e - mean) ** 2 for e in excess) / (len(excess) - 1)
    downside = sum(min(e, Fraction(0)) ** 2 for e in excess) / len(excess)
    year = math.sqrt(252)

    assert got.pnl == Decimal(500)
    assert got.return_on_starting_nav == pytest.approx(0.05)
    assert got.max_drawdown == Decimal(205)  # 10,200 → 9,995 on Tue Sep 22
    assert got.max_drawdown_pct == pytest.approx(205 / 10200)
    assert got.longest_underwater_sessions == 6
    assert got.sessions == 15
    assert got.sharpe_annualized == pytest.approx(float(mean) / math.sqrt(float(sample_var)) * year)
    assert got.sortino_annualized == pytest.approx(float(mean) / math.sqrt(float(downside)) * year)
    assert got.weekly_return is not None
    assert got.weekly_return.mean == pytest.approx((0.02 - 0.01 + 0.03981) / 3)
    assert (got.weekly_return.weeks, got.weekly_return.seed) == (3, SEED)


def test_dec_60_intrabar_low_counts_for_drawdown_but_not_for_returns() -> None:
    """A bar at 9,000 inside a session that closes at 10,000: a $1,000 drawdown, but no daily
    return sees it."""
    day = date(2026, 9, 14)
    run = Records((bar(day, "9000", 12), bar(day, "10000")))

    got = metrics(run, SEED, R)

    assert (got.max_drawdown, got.max_drawdown_pct) == (Decimal(1000), pytest.approx(0.1))
    assert (got.sessions, got.sharpe_annualized, got.sortino_annualized) == (1, None, None)
    assert got.longest_underwater_sessions == 0


def test_dec_60_a_run_without_a_long_has_no_pnl_and_one_week_no_ci() -> None:
    run = Records(tuple(week_of_closes(date(2026, 9, 14), ["10000"] * 5, long=False)))

    got = metrics(run, SEED, R)

    assert (got.pnl, got.return_on_starting_nav) == (Decimal(0), 0.0)
    assert got.sharpe_annualized is None  # a flat NAV has no spread
    assert got.weekly_return is None  # one week: no CI


def test_dec_61_the_ci_is_drawn_from_the_weekly_returns_as_published() -> None:
    """Each weekly return is kept at the 6 places the file prints, so the CI rebuilt from the
    file's values is the run's own (and a one-symbol pooled CI equals it)."""
    run = three_weeks()
    got = metrics(run, SEED, R)
    weeks = weekly_returns(run.ledger, run.starting_cash)

    assert all(w.value == round(w.value, 6) for w in weeks)
    assert got.weekly_return == mean_ci([[w.value] for w in weeks], SEED)
