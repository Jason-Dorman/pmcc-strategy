"""Cycle statistics (P6-02; PO, DEC-62): one cycle per week, worked by hand on the three-week
fixture (`tests/fakes/records.py`) and on small cases for each edge."""

from datetime import date
from decimal import Decimal

import pytest

from pmcc.analytics.cycles import EXIT_RULES, cycle_stats, cycles, exit_mix, skips_by_rule
from pmcc.domain.instruments import Side
from pmcc.export.analytics_models import Cycle
from tests.fakes.records import (
    FRI_1,
    FRI_3,
    LONG,
    STOCK,
    W1,
    W2,
    W3,
    Records,
    at,
    bar,
    short_call,
    skipped,
    sold,
    three_weeks,
    trade,
    week_of_closes,
)


def _cycle(pnl: str, *, outcome: str = "sold", held: bool = True, credit: str | None = "100",
           buyback: str | None = "0", long_cost: str | None = "4000") -> Cycle:  # fmt: skip
    """A week for the statistics alone; its dates don't matter there."""
    traded = outcome == "sold"
    return Cycle(
        week_open=W1, week_final=FRI_1, outcome=outcome, rule_id="E-S1" if traded else "G-2",
        long_held=held, credit=Decimal(credit) if traded and credit else None,
        buyback=Decimal(buyback) if traded and buyback else None,
        long_cost=Decimal(long_cost) if traded and long_cost else None,
        exit_rule_id="X-S1" if traded else None, pnl=Decimal(pnl),
    )  # fmt: skip


# ---- the cycles ---------------------------------------------------------------------------------


def test_dec_62_one_cycle_per_week_with_its_nav_change() -> None:
    weeks = cycles(three_weeks())

    assert [(c.week_open, c.week_final) for c in weeks] == [
        (W1, FRI_1), (W2, date(2026, 9, 25)), (W3, FRI_3)]  # fmt: skip
    assert [c.pnl for c in weeks] == [Decimal(200), Decimal(-102), Decimal(402)]
    assert [c.long_held for c in weeks] == [True, True, True]


def test_dec_62_a_traded_week_carries_its_short_cash_net_of_fees() -> None:
    first = cycles(three_weeks())[0]

    assert (first.outcome, first.rule_id) == ("sold", "E-S1")
    assert first.credit == Decimal("199.35")  # $2.00 × 100 − $0.65
    assert first.buyback == Decimal("50.65")  # $0.50 × 100 + $0.65
    assert first.long_cost == Decimal("4000.65")
    assert first.exit_rule_id == "X-S1"


def test_dec_62_a_skipped_week_has_no_short() -> None:
    second = cycles(three_weeks())[1]

    assert (second.outcome, second.rule_id) == ("skipped", "G-2")
    assert (second.credit, second.buyback, second.long_cost, second.exit_rule_id) == (
        None, None, None, None)  # fmt: skip


def test_dec_62_an_expired_short_buys_back_at_zero_against_the_long_it_was_sold_on() -> None:
    """Week 3 rolls the long (X-L2) before selling: the short's long is the new $5,000.65 one."""
    third = cycles(three_weeks())[2]

    assert (third.credit, third.buyback, third.exit_rule_id) == (
        Decimal("99.35"), Decimal(0), "X-S4")  # fmt: skip
    assert third.long_cost == Decimal("5000.65")


def test_dec_63_an_assigned_short_buys_back_at_zero_its_stock_apart() -> None:
    """X-S5: the ASSIGN row has no cash, and the stock sold at the strike and covered later is
    the stock's, not the short leg's (DEC-63)."""
    fri, mon = date(2026, 9, 18), date(2026, 9, 21)
    run = Records(
        tuple(week_of_closes(W1, ["10000"] * 5) + week_of_closes(W2, ["9900"] * 5)),
        (
            trade(at(W1, 10), Side.BUY, LONG, "40.00", "E-L1"),
            trade(at(W1, 11), Side.SELL, short_call(fri), "2.00", "E-S1"),
            trade(at(fri), Side.ASSIGN, short_call(fri), None, "X-S5"),
            trade(at(fri), Side.SELL, STOCK, "105.00", "X-S5"),
            trade(at(mon, 10), Side.BUY, STOCK, "107.00", "X-S5"),
        ),
        (sold(W1), skipped(W2, "G-2")),
    )

    first, second = cycles(run)

    assert (first.credit, first.buyback, first.exit_rule_id) == (
        Decimal("199.35"), Decimal(0), "X-S5")  # fmt: skip
    assert (second.credit, second.buyback) == (None, None)  # the cover isn't a short's buyback
    assert exit_mix(run.blotter)["X-S5"] == 1


def test_dec_62_a_long_carried_in_and_sold_on_the_first_bar_was_held_that_week() -> None:
    """X-L1 sells the weekend's long at 10:00 Monday and the re-entry never completes: no row of
    the week ends with a long, but its P&L is that long's, so the week counts as held."""
    ledger = [
        *week_of_closes(W1, ["10000"] * 5),
        bar(W2, "9990", 10, long=False),
        *week_of_closes(W2, ["9990"] * 5, long=False),
    ]
    run = Records(tuple(ledger),
                  (trade(at(W1, 10), Side.BUY, LONG, "40.00", "E-L1"),
                   trade(at(W2, 10), Side.SELL, LONG, "39.90", "X-L1")),
                  (skipped(W1, "G-2"), skipped(W2, "X-L1")))  # fmt: skip

    first, second = cycles(run)

    assert (first.long_held, second.long_held) == (True, True)
    assert second.pnl == Decimal(-10)
    assert cycle_stats((first, second)).weeks_long_held == 2


def test_dec_62_a_long_bought_partway_through_the_week_was_held_that_week() -> None:
    ledger = [bar(W1, "10000", long=False), *week_of_closes(date(2026, 9, 15), ["10000"] * 4)]
    run = Records(tuple(ledger), (trade(at(date(2026, 9, 15), 10), Side.BUY, LONG, "40.00",
                                        "E-L1"),), (skipped(W1, "E-S1"),))  # fmt: skip

    (week,) = cycles(run)

    assert week.long_held


def test_dec_62_a_week_after_the_long_is_sold_and_never_replaced_held_none() -> None:
    """The long sold on the week's first bar was held then; the next week, flat, held none."""
    ledger = (week_of_closes(W1, ["10000"] * 5, long=True)
              + week_of_closes(W2, ["9990"] * 5, long=False)
              + week_of_closes(W3, ["9990"] * 5, long=False))  # fmt: skip
    run = Records(tuple(ledger), (), (skipped(W1, "G-2"), skipped(W2, "X-L1"),
                                     skipped(W3, "E-S1")))  # fmt: skip

    assert [c.long_held for c in cycles(run)] == [True, True, False]


def test_dec_62_a_week_with_no_long_held_says_so() -> None:
    run = Records(tuple(week_of_closes(W1, ["10000"] * 5, long=False)), (),
                  (skipped(W1, "E-S1"),))  # fmt: skip

    (week,) = cycles(run)

    assert (week.long_held, week.outcome, week.rule_id) == (False, "skipped", "E-S1")


def test_dec_62_a_week_without_its_gate_log_row_is_refused() -> None:
    run = Records(tuple(week_of_closes(W1, ["10000"] * 5)))

    with pytest.raises(ValueError, match="no gate-log row"):
        cycles(run)


# ---- the statistics -----------------------------------------------------------------------------


def test_dec_62_statistics_on_three_weeks() -> None:
    stats = cycle_stats(cycles(three_weeks()))

    assert (stats.weeks, stats.weeks_traded, stats.weeks_skipped) == (3, 2, 1)
    assert stats.weeks_long_held == 3
    assert stats.win_rate == pytest.approx(2 / 3)
    assert stats.average_win == Decimal(301)  # (200 + 402) / 2
    assert stats.average_loss == Decimal(-102)
    assert stats.payoff_ratio == pytest.approx(301 / 102)
    # (199.35 − 50.65 + 99.35 − 0) ÷ (199.35 + 99.35)
    assert stats.premium_captured_pct == pytest.approx(248.05 / 298.70)
    assert stats.credit_pct_of_long_cost == pytest.approx((199.35 / 4000.65 + 99.35 / 5000.65) / 2)


def test_dec_62_win_statistics_cover_only_weeks_with_a_long_held() -> None:
    weeks = [_cycle("50"), _cycle("-25"), _cycle("-1000", outcome="skipped", held=False)]

    stats = cycle_stats(weeks)

    assert (stats.weeks, stats.weeks_long_held) == (3, 2)
    assert stats.win_rate == pytest.approx(0.5)
    assert stats.average_loss == Decimal(-25)


def test_dec_62_a_flat_week_is_neither_a_win_nor_a_loss_but_counts_in_the_rate() -> None:
    stats = cycle_stats([_cycle("10"), _cycle("0")])

    assert stats.win_rate == pytest.approx(0.5)
    assert (stats.average_loss, stats.payoff_ratio) == (None, None)


def test_dec_62_average_win_rounds_half_even_to_the_unit() -> None:
    """$0.0002 and $0.0003 average $0.00025: half-even to $0.0002, where half-up gives $0.0003;
    $0.0001 and $0.0002 average $0.00015: half-even to $0.0002."""
    assert cycle_stats([_cycle("0.0002"), _cycle("0.0003")]).average_win == Decimal("0.0002")
    assert cycle_stats([_cycle("0.0001"), _cycle("0.0002")]).average_win == Decimal("0.0002")


def test_dec_62_premium_captured_is_weighted_by_credit_not_a_mean_of_ratios() -> None:
    """$100 kept whole and $1,000 bought back in full: $100 of $1,100, not the ratios' mean 50%."""
    weeks = [_cycle("100", credit="100", buyback="0"),
             _cycle("-5", credit="1000", buyback="1000")]  # fmt: skip

    assert cycle_stats(weeks).premium_captured_pct == pytest.approx(100 / 1100)


def test_dec_62_statistics_are_null_without_the_weeks_they_need() -> None:
    stats = cycle_stats([_cycle("0", outcome="skipped", held=False)])

    assert (stats.weeks_traded, stats.weeks_skipped, stats.weeks_long_held) == (0, 1, 0)
    assert (stats.win_rate, stats.average_win, stats.average_loss, stats.payoff_ratio) == (
        None, None, None, None)  # fmt: skip
    assert (stats.premium_captured_pct, stats.credit_pct_of_long_cost) == (None, None)


# ---- exit mix and skips -------------------------------------------------------------------------


def test_dec_62_exit_mix_counts_every_exit_rule_even_at_zero() -> None:
    mix = exit_mix(three_weeks().blotter)

    assert list(mix) == list(EXIT_RULES)
    assert EXIT_RULES == ("X-S1", "X-S2", "X-S3", "X-S4", "X-S5", "X-L1", "X-L2")
    assert mix == {"X-S1": 1, "X-S2": 0, "X-S3": 0, "X-S4": 1, "X-S5": 0, "X-L1": 0, "X-L2": 1}


def test_dec_62_skips_are_counted_by_rule_id() -> None:
    log = (sold(W1), skipped(W2, "G-4"), skipped(W3, "G-2"), skipped(date(2026, 10, 5), "G-4"))

    assert skips_by_rule(log) == {"G-2": 1, "G-4": 2}
    assert list(skips_by_rule(log)) == ["G-2", "G-4"]
