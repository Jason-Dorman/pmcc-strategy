"""Leg attribution (P6-03; PO, DEC-63), worked by hand on small runs (`tests/fakes/legs.py`)."""

from datetime import date
from decimal import Decimal

import pytest

from pmcc.analytics.attribution import leg_attribution
from pmcc.domain.instruments import Side
from pmcc.domain.money import Money
from pmcc.export.analytics_models import LegPoint
from tests.fakes.legs import Held, Tick, tape
from tests.fakes.records import (
    FRI_1,
    LONG,
    LONG_2,
    STOCK,
    W1,
    W2,
    Records,
    at,
    short_call,
    three_weeks,
    trade,
)

TUE_1, WED_1 = date(2026, 9, 15), date(2026, 9, 16)
FRI_2 = date(2026, 9, 25)
SHORT = short_call(FRI_1)


def _roll() -> Records:
    """From $10,000, fees $0.65 a contract:

    - Mon 10:00, spot 115: buy the $80 long at $40.00 (−4,000.65).
    - Mon 11:00, spot 116: sell the $105 short at $2.00 (+199.35); the long marks $41.
    - Wed 12:00, spot 117: buy the short back at $0.50 (−50.65); the long marks $42.
    - Mon 10:00, spot 120: X-L2 sells the long at $45.00 (+4,499.35) and buys the $85 at $50.00
      (−5,000.65).
    - Fri 16:00, spot 122: the $85 marks $52.

    Long: −4,000.65 + 4,499.35 − 5,000.65 + 5,200 = 698.05. Short: 199.35 − 50.65 = 148.70.
    P&L 846.75. Intrinsic: the $80 from 35 to 40 (+500), the $85 from 35 to 37 (+200): +700, so
    extrinsic −1.95, the three long fees (each long's extrinsic was $5 in and $5 out, $15 and $15).
    """
    ticks = [
        Tick(at(W1, 10), "115", Held(LONG, "40")),
        Tick(at(W1, 11), "116", Held(LONG, "41"), Held(SHORT, "2.00")),
        Tick(at(WED_1, 12), "117", Held(LONG, "42")),
        Tick(at(W2, 10), "120", Held(LONG_2, "50")),
        Tick(at(FRI_2), "122", Held(LONG_2, "52")),
    ]
    blotter = [
        trade(at(W1, 10), Side.BUY, LONG, "40.00", "E-L1"),
        trade(at(W1, 11), Side.SELL, SHORT, "2.00", "E-S1"),
        trade(at(WED_1, 12), Side.BUY, SHORT, "0.50", "X-S1"),
        trade(at(W2, 10), Side.SELL, LONG, "45.00", "X-L2"),
        trade(at(W2, 10), Side.BUY, LONG_2, "50.00", "E-L1"),
    ]
    return tape(ticks, blotter)


def test_dec_63_the_short_leg_is_its_credits_less_its_buybacks_net_of_fees() -> None:
    legs = leg_attribution(_roll())

    assert legs.short_credits == Decimal("199.35")
    assert legs.short_buybacks == Decimal("50.65")
    assert legs.net_short_premium == Decimal("148.70")
    assert (legs.short_open, legs.assignment_stock_pnl) == (Decimal(0), Decimal(0))


def test_dec_63_the_long_leg_splits_into_its_intrinsic_and_extrinsic_change() -> None:
    legs = leg_attribution(_roll())

    assert legs.long_pnl == Decimal("698.05")
    assert legs.long_intrinsic == Decimal("700")  # +500 on the $80, +200 on the $85
    assert legs.long_extrinsic == Decimal("-1.95")  # the three long fees


def test_dec_63_the_series_has_each_sessions_close() -> None:
    """Each session's last bar: Mon 99.35 (−4,000.65 + 4,100) and 199.35; Wed 199.35 and 148.70;
    Mon 498.05 (−4,501.95 + 5,000); Fri 698.05."""
    series = leg_attribution(_roll()).series

    assert series == (
        LegPoint(session=W1, long_pnl=Decimal("99.35"), net_short_premium=Decimal("199.35")),
        LegPoint(session=WED_1, long_pnl=Decimal("199.35"), net_short_premium=Decimal("148.70")),
        LegPoint(session=W2, long_pnl=Decimal("498.05"), net_short_premium=Decimal("148.70")),
        LegPoint(session=FRI_2, long_pnl=Decimal("698.05"), net_short_premium=Decimal("148.70")),
    )


def test_dec_63_an_assigned_shorts_stock_is_shown_apart() -> None:
    """X-S5: the short ($1.00, +99.35) is assigned at Friday's close, spot 108, with no cash, and
    100 shares are sold short at the $105 strike (+10,500); they are covered Monday at $108.50
    (−10,850). Stock −350; net short premium 99.35, its buyback $0. The long: −4,000.65, marked
    $47.50 at the end: +749.35, intrinsic 20 → 28.50 (+850), extrinsic −100.65. P&L 498.70."""
    ticks = [
        Tick(at(W1, 10), "100", Held(LONG, "40")),
        Tick(at(W1, 11), "100", Held(LONG, "40"), Held(SHORT, "1.00")),
        Tick(at(FRI_1), "108", Held(LONG, "47"), stock=(-100, "108")),
        Tick(at(W2, 10), "108.50", Held(LONG, "47.50")),
    ]
    blotter = [
        trade(at(W1, 10), Side.BUY, LONG, "40.00", "E-L1"),
        trade(at(W1, 11), Side.SELL, SHORT, "1.00", "E-S1"),
        trade(at(FRI_1), Side.ASSIGN, SHORT, None, "X-S5"),
        trade(at(FRI_1), Side.SELL, STOCK, "105", "X-S5"),
        trade(at(W2, 10), Side.BUY, STOCK, "108.50", "X-S5"),
    ]
    legs = leg_attribution(tape(ticks, blotter))

    assert (legs.short_credits, legs.short_buybacks) == (Decimal("99.35"), Decimal(0))
    assert legs.assignment_stock_pnl == Decimal(-350)
    assert legs.long_pnl == Decimal("749.35")
    assert (legs.long_intrinsic, legs.long_extrinsic) == (Decimal(850), Decimal("-100.65"))


def test_dec_63_stock_still_held_at_the_end_counts_at_its_mark() -> None:
    """Assigned at Friday's close and never covered: the stock is −100 × $108 + $10,500 = −300."""
    ticks = [
        Tick(at(W1, 11), "100", short=Held(SHORT, "1.00")),
        Tick(at(FRI_1), "108", stock=(-100, "108")),
    ]
    blotter = [
        trade(at(W1, 11), Side.SELL, SHORT, "1.00", "E-S1"),
        trade(at(FRI_1), Side.ASSIGN, SHORT, None, "X-S5"),
        trade(at(FRI_1), Side.SELL, STOCK, "105", "X-S5"),
    ]
    assert leg_attribution(tape(ticks, blotter)).assignment_stock_pnl == Decimal(-300)


def test_p6_03_a_short_open_at_the_end_is_reported_at_its_mark() -> None:
    """Sold for $2.00 (+199.35) and marked $1.50 at the end: the net short premium is the credit,
    and the open short (150) is apart, so the legs still add up to the P&L (49.35)."""
    ticks = [
        Tick(at(W1, 11), "100", short=Held(SHORT, "2.00")),
        Tick(at(TUE_1, 16), "99", short=Held(SHORT, "1.50")),
    ]
    run = tape(ticks, [trade(at(W1, 11), Side.SELL, SHORT, "2.00", "E-S1")])
    legs = leg_attribution(run)

    assert (legs.net_short_premium, legs.short_open) == (Decimal("199.35"), Decimal(150))
    assert run.ledger[-1].nav - run.starting_cash == Money.from_dollars("49.35")


def test_dec_23_a_long_bought_on_a_bar_without_a_trade_takes_the_last_spot() -> None:
    """The entry bar has no spot, so the 10:00 spot of 115 is its S: intrinsic 35 → 37."""
    ticks = [
        Tick(at(W1, 10), "115"),
        Tick(at(W1, 11), None, Held(LONG, "40")),
        Tick(at(W1, 16), "117", Held(LONG, "42")),
    ]
    run = tape(ticks, [trade(at(W1, 11), Side.BUY, LONG, "40.00", "E-L1")])

    assert leg_attribution(run).long_intrinsic == Decimal(200)


def test_dec_63_the_intrinsic_change_scales_with_the_contracts_held() -> None:
    """Two $80 contracts bought at $40.00 (spot 115, fees 2 × $0.65) and marked $42 at spot 117:
    intrinsic 35 → 37 on 200 shares is +400; the long made 8,400 − 8,001.30 = 398.70, so its
    extrinsic is −1.30, the two fees."""
    ticks = [
        Tick(at(W1, 10), "115", Held(LONG, "40", qty=2)),
        Tick(at(W1, 16), "117", Held(LONG, "42", qty=2)),
    ]
    run = tape(ticks, [trade(at(W1, 10), Side.BUY, LONG, "40.00", "E-L1", contracts=2)])
    legs = leg_attribution(run)

    assert (legs.long_pnl, legs.long_intrinsic) == (Decimal("398.70"), Decimal(400))
    assert legs.long_extrinsic == Decimal("-1.30")


def test_p6_03_no_spot_at_or_before_a_long_entry_raises() -> None:
    ticks = [Tick(at(W1, 10), None, Held(LONG, "40"))]
    run = tape(ticks, [trade(at(W1, 10), Side.BUY, LONG, "40.00", "E-L1")])

    with pytest.raises(ValueError, match="no spot"):
        leg_attribution(run)


def test_p6_03_rows_that_dont_add_up_to_the_pnl_raise() -> None:
    """The cycle fixture's NAVs are made up, so its legs can't add up to them."""
    with pytest.raises(ValueError, match="add up"):
        leg_attribution(three_weeks())


def test_p6_03_a_run_without_bars_raises() -> None:
    with pytest.raises(ValueError, match="without bars"):
        leg_attribution(Records(()))
