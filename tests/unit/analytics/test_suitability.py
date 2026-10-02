"""The suitability screen (P6-08; PO, DEC-66): quant's picks and G-3 read at each week's first
week-open bar, and the symbol's row from those weeks."""

import math
from datetime import date, datetime
from fractions import Fraction

import pytest

from pmcc.analytics.suitability import Screen, WeekReading, read_week, sample_bars, suitability
from pmcc.analytics.suitability import suitability_row as row_of
from pmcc.config.strategy import CONFIGS_DIR, load_strategy
from pmcc.domain.clock import ET
from pmcc.domain.instruments import Right
from pmcc.domain.money import Price
from pmcc.pricing.measures import realized_vol
from pmcc.strategy.gates import EventRatioGate
from pmcc.strategy.ports import ExpiryKind, GateStatus
from pmcc.strategy.registry import build_strategy
from pmcc.strategy.selectors import (
    CheapestReplacement,
    DteRangeExpiry,
    ExpectedMoveStrike,
    LongSelector,
    ShortSelector,
    WeekFinalExpiry,
)
from tests.fakes.view import CALENDAR, Row, StubView

MON = datetime(2026, 8, 31, 10, tzinfo=ET)
FRONT, NEXT = date(2026, 9, 4), date(2026, 9, 11)
FAR = date(2027, 3, 19)  # 200 days out
SCREEN = Screen(
    LongSelector(DteRangeExpiry(120, 270), CheapestReplacement(0.70, 0.90)),
    ShortSelector(WeekFinalExpiry(), ExpectedMoveStrike(1.0)),
    EventRatioGate(1.20),
)
ZIGZAG = [100 * math.exp(0.01 * (i % 2)) for i in range(21)]  # ±1% a day
RV = realized_vol([Price.from_dollars(v) for v in ZIGZAG])


def closes() -> dict[datetime, Price]:
    sessions = CALENDAR.sessions_before(MON.date(), len(ZIGZAG))
    return {s.close_bar_end: Price.from_dollars(v) for s, v in zip(sessions, ZIGZAG, strict=True)}


def front_calls(atm_iv: float = 0.45) -> list[Row]:
    """ATM call mid $1.60; with the put's $1.40, EM is $3.00 and quant's floor is $103."""
    return [
        Row(99, "2.18", "2.22", 0.60),
        Row(100, "1.58", "1.62", 0.52, iv=atm_iv),
        Row(101, "1.10", "1.14", 0.44),
        Row("102.5", "0.70", "0.74", 0.34),
        Row(103, "0.60", "0.64", 0.30),
        Row(104, "0.40", "0.46", 0.22),
    ]


def longs() -> list[Row]:
    """Extrinsic ÷ delta: 80 is $1.00 ÷ 0.85, 85 is $1.50 ÷ 0.78, 70 is out of the band."""
    return [Row(70, "30.80", "31.20", 0.95), Row(80, "20.90", "21.10", 0.85),
            Row(85, "16.40", "16.60", 0.78)]  # fmt: skip


def market(*, front: list[Row] | None = None, puts: list[Row] | None = None,
           following: list[Row] | None = None, monthly: list[Row] | None = None,
           history: dict[datetime, Price] | None = None) -> StubView:  # fmt: skip
    chains = {
        (FRONT, Right.CALL): front_calls() if front is None else front,
        (FRONT, Right.PUT): [Row(100, "1.38", "1.42", -0.48)] if puts is None else puts,
        (NEXT, Right.CALL): [Row(100, "1.98", "2.02", 0.52, iv=0.30)] if following is None
        else following,
        (FAR, Right.CALL): longs() if monthly is None else monthly,
    }  # fmt: skip
    return StubView(MON, spot_price=Price.from_dollars(100), chains=chains,
                    listed={ExpiryKind.MONTHLY: (FAR,)},
                    closes=closes() if history is None else history)  # fmt: skip


# ---- one week's reading -------------------------------------------------------------------------


def test_p6_08_reads_quants_picks_and_g_3_at_the_bar() -> None:
    reading = read_week(market(), SCREEN)

    assert reading.session == MON.date()
    assert reading.long_extrinsic_per_delta == pytest.approx(1.00 / (0.85 * 100))  # of spot
    assert reading.long_spread == Fraction(20, 2100)  # $0.20 ÷ $21.00
    assert reading.short_spread == Fraction(4, 62)  # the $103 call: $0.04 ÷ $0.62
    assert reading.credit == Fraction(60, 2100)  # its bid ÷ the long's mid
    assert reading.iv_over_rv20 == pytest.approx(0.45 / RV)
    assert reading.g3 is GateStatus.FIRE  # 0.45 ÷ 0.30 = 1.5 > 1.20


def test_p6_08_credit_is_the_bid_not_the_mid() -> None:
    """After half-spread: mid − (ASK − BID) ÷ 2 is the bid, whatever the spread."""
    wide = [r if r.strike != 103 else Row(103, "0.50", "0.74", 0.30) for r in front_calls()]
    assert read_week(market(front=wide), SCREEN).credit == Fraction(50, 2100)


def test_p6_08_short_pick_is_quants_lowest_strike_at_spot_plus_em() -> None:
    """With the put at $2.40, EM is $4.00: the floor is $104, so the $104 call is read."""
    reading = read_week(market(puts=[Row(100, "2.38", "2.42", -0.48)]), SCREEN)
    assert reading.short_spread == Fraction(6, 43)  # $0.06 ÷ $0.43
    assert reading.credit == Fraction(40, 2100)


def test_p6_08_a_week_without_a_long_reads_no_short() -> None:
    """A short is sold against a long (E-S1), so neither is read; IV ÷ RV20 and G-3 still are."""
    reading = read_week(market(monthly=[]), SCREEN)
    assert (reading.long_extrinsic_per_delta, reading.long_spread) == (None, None)
    assert (reading.short_spread, reading.credit) == (None, None)
    assert reading.iv_over_rv20 == pytest.approx(0.45 / RV)
    assert reading.g3 is GateStatus.FIRE


def test_p6_08_a_week_without_an_em_reads_the_long_alone() -> None:
    reading = read_week(market(puts=[Row(100, None, None)]), SCREEN)
    assert reading.long_spread == Fraction(20, 2100)
    assert (reading.short_spread, reading.credit) == (None, None)


def test_p6_08_iv_over_rv20_needs_both() -> None:
    assert read_week(market(history={}), SCREEN).iv_over_rv20 is None  # no RV20
    unquoted = [r if r.strike != 100 else Row(100, None, None) for r in front_calls()]
    assert read_week(market(front=unquoted), SCREEN).iv_over_rv20 is None  # no ATM IV


def test_p6_08_iv_over_rv20_without_variation_is_left_out() -> None:
    """21 equal closes give an RV20 of 0, so the ratio has no value: the week is left out of the
    mean, not counted as unbounded (G-4 passes on it instead) and not a division by zero."""
    sessions = CALENDAR.sessions_before(MON.date(), 21)
    flat = {s.close_bar_end: Price.from_dollars(100) for s in sessions}
    reading = read_week(market(history=flat), SCREEN)
    assert reading.iv_over_rv20 is None
    assert row_of("SYN", [reading], SCREEN).iv_rv20_weeks == 0


def test_p6_08_iv_over_rv20_reads_the_front_weeks_atm_call() -> None:
    reading = read_week(market(front=front_calls(atm_iv=0.30)), SCREEN)
    assert reading.iv_over_rv20 == pytest.approx(0.30 / RV)
    assert reading.g3 is GateStatus.PASS  # 0.30 ÷ 0.30


def test_p6_08_g_3_is_n_a_without_the_next_week() -> None:
    assert read_week(market(following=[]), SCREEN).g3 is GateStatus.NA


def test_g_3_check_is_the_gate_with_its_front_expiry() -> None:
    gate, view = EventRatioGate(1.20), market()
    result = gate.check(view, FRONT)
    assert (result.status, result.values["ratio"]) == (GateStatus.FIRE, 1.5)


# ---- the screen's rules -------------------------------------------------------------------------


def test_p6_08_screen_reads_quants_own_rules() -> None:
    screen = Screen.of(build_strategy(load_strategy(CONFIGS_DIR / "quant_pmcc.yaml")))
    assert isinstance(screen.long.strike, CheapestReplacement)
    assert isinstance(screen.short.strike, ExpectedMoveStrike)
    assert screen.event.max_ratio == 1.20


def test_p6_08_screen_refuses_a_strategy_without_g_3() -> None:
    with pytest.raises(ValueError, match="G-3"):
        Screen.of(build_strategy(load_strategy(CONFIGS_DIR / "baseline_pmcc.yaml")))


# ---- the sample ---------------------------------------------------------------------------------


def test_p6_08_samples_the_first_bar_of_each_week_open_session() -> None:
    """Labor Day closes Monday Sep 7 2026, so that week opens Tuesday."""
    bars = sample_bars(CALENDAR, date(2026, 8, 31), date(2026, 9, 18))
    assert bars == (datetime(2026, 8, 31, 10, tzinfo=ET), datetime(2026, 9, 8, 10, tzinfo=ET),
                    datetime(2026, 9, 14, 10, tzinfo=ET))  # fmt: skip


def test_p6_08_samples_only_weeks_whose_open_is_in_the_window() -> None:
    bars = sample_bars(CALENDAR, date(2026, 9, 1), date(2026, 9, 14))
    assert bars == (datetime(2026, 9, 8, 10, tzinfo=ET), datetime(2026, 9, 14, 10, tzinfo=ET))


# ---- the symbol's row ---------------------------------------------------------------------------


def week(day: int, *, per_delta: float | None = None, long: Fraction | None = None,
         short: Fraction | None = None, credit: Fraction | None = None,
         ratio: float | None = None, g3: GateStatus = GateStatus.PASS) -> WeekReading:  # fmt: skip
    return WeekReading(date(2026, 9, day), per_delta, long, short, credit, ratio, g3)


def test_p6_08_row_means_medians_and_counts_each_over_its_own_weeks() -> None:
    readings = [
        week(1, per_delta=0.01, long=Fraction(1, 100), short=Fraction(1, 10),
             credit=Fraction(1, 50), ratio=1.2, g3=GateStatus.FIRE),
        week(8, per_delta=0.03, long=Fraction(3, 100), ratio=0.8, g3=GateStatus.NA),
        week(14, per_delta=0.02, long=Fraction(2, 100), short=Fraction(3, 10),
             credit=Fraction(1, 25), g3=GateStatus.FIRE),
        week(21),
    ]  # fmt: skip

    row = row_of("SYN", readings, SCREEN)

    assert (row.symbol, row.weeks) == ("SYN", 4)
    assert row.long_weeks == 3
    assert row.long_extrinsic_per_delta_pct_spot == pytest.approx(0.02)
    assert row.median_spread_long_pct == 0.02
    assert row.short_weeks == 2
    assert row.median_spread_short_pct == 0.2  # an even count: the mean of the middle two
    assert row.weekly_credit_after_half_spread_pct_long_cost == 0.03
    assert (row.iv_rv20_weeks, row.iv_over_rv20) == (2, 1.0)
    assert (row.g3_weeks, row.g3_fires, row.g3_max_ratio) == (3, 2, 1.20)


def test_p6_08_row_without_readings_is_null_not_zero() -> None:
    row = row_of("SYN", [week(1, g3=GateStatus.NA)], SCREEN)
    assert row.weeks == 1
    assert (row.long_weeks, row.short_weeks, row.iv_rv20_weeks, row.g3_weeks) == (0, 0, 0, 0)
    assert row.long_extrinsic_per_delta_pct_spot is None
    assert (row.median_spread_long_pct, row.median_spread_short_pct) == (None, None)
    assert row.weekly_credit_after_half_spread_pct_long_cost is None
    assert (row.iv_over_rv20, row.g3_fires) == (None, 0)


def test_p6_08_row_is_exact_whatever_the_order() -> None:
    readings = [week(d, per_delta=v, long=Fraction(n, 7), short=Fraction(n, 9),
                     credit=Fraction(n, 11), ratio=v * 3) for d, v, n in
                ((1, 0.1, 1), (8, 0.2, 2), (14, 0.7, 3))]  # fmt: skip
    assert row_of("SYN", readings, SCREEN) == row_of("SYN", readings[::-1], SCREEN)
    assert row_of("SYN", readings, SCREEN).weekly_credit_after_half_spread_pct_long_cost == float(
        Fraction(6, 33))  # fmt: skip


def test_p6_08_row_takes_the_mean_or_median_each_measure_names() -> None:
    """Skewed weeks, so each mean differs from its median: the spreads are medians, the rest
    means (Spec; PO, DEC-66)."""
    readings = [week(d, per_delta=v, long=Fraction(n, 100), short=Fraction(n, 10),
                     credit=Fraction(n, 50), ratio=r) for d, v, n, r in
                ((1, 0.01, 1, 0.8), (8, 0.02, 2, 0.9), (14, 0.09, 9, 2.0))]  # fmt: skip

    row = row_of("SYN", readings, SCREEN)

    assert row.long_extrinsic_per_delta_pct_spot == pytest.approx(0.04)  # mean; median 0.02
    assert row.median_spread_long_pct == 0.02  # median; mean 0.04
    assert row.median_spread_short_pct == 0.2  # median; mean 0.4
    assert row.weekly_credit_after_half_spread_pct_long_cost == 0.08  # mean; median 0.04
    assert row.iv_over_rv20 == pytest.approx(3.7 / 3)  # mean; median 0.9


def test_p6_08_universe_file_lists_symbols_alphabetically() -> None:
    rows = [row_of(s, [week(1)], SCREEN) for s in ("TWO", "SYN")]
    assert [r.symbol for r in suitability(rows).rows] == ["SYN", "TWO"]


def test_p6_08_universe_file_refuses_a_symbol_twice() -> None:
    with pytest.raises(ValueError, match="SYN"):
        suitability([row_of("SYN", [week(1)], SCREEN)] * 2)
