"""E-L2, E-L3 and E-S3 quant at their boundaries, with DEC-29's quant tie-breaks (P4-01)."""

from datetime import date, datetime

import pytest

from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.pricing.iv import IvCode
from pmcc.strategy.ports import ExpiryKind, HeldLeg, Selection
from pmcc.strategy.selectors import (
    CheapestReplacement,
    DteRangeExpiry,
    ExpectedMoveStrike,
    LongSelector,
    ShortSelector,
    WeekFinalExpiry,
)
from tests.fakes.view import ROOT, Row, StubView

MON = datetime(2026, 8, 31, 10, tzinfo=ET)
WEEKLY = date(2026, 9, 4)
D119, D120 = date(2026, 12, 28), date(2026, 12, 29)  # days from Mon Aug 31
D270, D271 = date(2027, 5, 28), date(2027, 5, 29)
NEAR, FAR = date(2027, 1, 15), date(2027, 3, 19)  # 137 and 200 days
LONG = HeldLeg(OptionId(ROOT, FAR, Right.CALL, Price.from_dollars(80)), 1,
               Price.from_dollars(22), MON)  # fmt: skip


def dollars(value: str) -> Price:
    return Price.from_dollars(value)


def strike(selection: Selection | None) -> float | None:
    return None if selection is None else float(selection.option.strike.to_dollars())


# ---- E-L2 quant: every monthly 120 to 270 DTE -------------------------------------------------


def test_e_l2_quant_keeps_every_monthly_in_the_range_inclusive() -> None:
    view = StubView(MON, listed={ExpiryKind.MONTHLY: (D119, D120, NEAR, D270, D271)})
    assert DteRangeExpiry(120, 270).candidates(view) == (D120, NEAR, D270)


def test_e_l2_quant_reads_only_monthlies() -> None:
    view = StubView(MON, listed={ExpiryKind.WEEKLY: (NEAR,), ExpiryKind.MONTHLY: (FAR,)})
    assert DteRangeExpiry(120, 270).candidates(view) == (FAR,)


def test_e_l2_quant_none_in_range_selects_nothing() -> None:
    view = StubView(MON, spot_price=dollars("100"), listed={ExpiryKind.MONTHLY: (D119, D271)},
                    chains={(D119, Right.CALL): [Row(80, "20.90", "21.10", 0.85)]})  # fmt: skip
    assert DteRangeExpiry(120, 270).candidates(view) == ()
    selector = LongSelector(DteRangeExpiry(120, 270), CheapestReplacement(0.70, 0.90))
    assert selector.select(view) is None


# ---- E-L3 quant: lowest extrinsic ÷ delta in the delta band ----------------------------------


def long_view(chains: dict[date, list[Row]], spot: str | None = "100") -> StubView:
    return StubView(
        MON,
        spot_price=None if spot is None else dollars(spot),
        chains={(e, Right.CALL): rows for e, rows in chains.items()},
        listed={ExpiryKind.MONTHLY: tuple(sorted(chains))},
    )


def pick_long(view: StubView) -> Selection | None:
    return LongSelector(DteRangeExpiry(120, 270), CheapestReplacement(0.70, 0.90)).select(view)


def test_e_l3_quant_picks_the_lowest_extrinsic_per_delta() -> None:
    # 80: extrinsic 21.00 − 20 = 1.00 at 0.85 → 1.18; 85: 16.50 − 15 = 1.50 at 0.78 → 1.92
    view = long_view({FAR: [Row(80, "20.90", "21.10", 0.85), Row(85, "16.40", "16.60", 0.78)]})
    assert strike(pick_long(view)) == 80


def test_e_l3_quant_searches_across_every_e_l2_expiry() -> None:
    # FAR's 80 carries more time value (2.00 at 0.85) than NEAR's (1.00 at 0.84).
    view = long_view({NEAR: [Row(80, "20.90", "21.10", 0.84)],
                      FAR: [Row(80, "21.90", "22.10", 0.85)]})  # fmt: skip
    selected = pick_long(view)
    assert selected is not None
    assert selected.option.expiry == NEAR


@pytest.mark.parametrize(("delta", "inside"), [(0.70, True), (0.6999, False), (0.90, True),
                                               (0.9001, False)])  # fmt: skip
def test_e_l3_quant_delta_band_is_inclusive(delta: float, inside: bool) -> None:
    # The out-of-band row is far cheaper per delta, so it wins exactly when it's in the band.
    view = long_view({FAR: [Row(70, "30.00", "30.10", delta), Row(80, "22.90", "23.10", 0.80)]})
    assert strike(pick_long(view)) == (70 if inside else 80)


def test_e_l3_quant_a_float_on_the_band_edge_counts_as_inside() -> None:
    view = long_view({FAR: [Row(70, "30.00", "30.10", 0.7 - 1e-12),
                            Row(80, "22.90", "23.10", 0.80)]})  # fmt: skip
    assert strike(pick_long(view)) == 70


def test_e_l3_quant_extrinsic_is_mid_less_intrinsic_at_spot() -> None:
    # An out-of-the-money strike has no intrinsic: all of its mid is extrinsic.
    view = long_view({FAR: [Row(80, "20.90", "21.10", 0.85), Row(105, "0.40", "0.42", 0.72)]})
    selected = pick_long(view)
    assert strike(selected) == 105  # 0.41 ÷ 0.72 beats 1.00 ÷ 0.85
    assert selected is not None
    assert selected.values["extrinsic"] == "0.4100"


def test_e_l3_quant_a_score_tie_goes_to_the_lower_spread() -> None:
    # 80: 1.70 ÷ 0.85 = 2; 85: 1.40 ÷ 0.70 = 2. The 85 quotes the tighter spread.
    view = long_view({FAR: [Row(80, "21.50", "21.90", 0.85), Row(85, "16.39", "16.41", 0.70)]})
    assert strike(pick_long(view)) == 85


def test_e_l3_quant_a_score_and_spread_tie_goes_to_the_earlier_expiry() -> None:
    row = Row(80, "20.90", "21.10", 0.85)
    view = long_view({NEAR: [row], FAR: [row]})
    selected = pick_long(view)
    assert selected is not None
    assert selected.option.expiry == NEAR


def test_e_l3_quant_then_the_lower_strike() -> None:
    # Both score 2 on a spread of exactly 2% of mid.
    view = long_view({FAR: [Row(85, "16.236", "16.564", 0.70), Row(80, "21.483", "21.917", 0.85)]})
    assert strike(pick_long(view)) == 80


def test_e_l3_quant_the_spread_decides_before_the_expiry() -> None:
    """Tied on score across two expiries: the tighter spread wins, even on the later expiry."""
    view = long_view({NEAR: [Row(80, "20.80", "21.20", 0.85)],
                      FAR: [Row(80, "20.95", "21.05", 0.85)]})  # fmt: skip
    selected = pick_long(view)
    assert selected is not None
    assert selected.option.expiry == FAR


def test_e_l3_quant_the_expiry_decides_before_the_strike() -> None:
    """Tied on score and spread: the earlier expiry wins, even with the higher strike."""
    view = long_view({NEAR: [Row(85, "16.236", "16.564", 0.70)],
                      FAR: [Row(80, "21.483", "21.917", 0.85)]})  # fmt: skip
    selected = pick_long(view)
    assert selected is not None
    assert (selected.option.expiry, strike(selected)) == (NEAR, 85)


def test_e_l3_quant_scores_equal_but_for_float_noise_tie() -> None:
    """0.50 ÷ 0.90 and 0.45 ÷ 0.81 are both 5/9, but in floats the second is one bit lower. Rounded
    to 9 places they tie (DEC-29), and the tighter spread, the 80, wins."""
    view = long_view({FAR: [Row(80, "20.49", "20.51", 0.90), Row(85, "15.40", "15.50", 0.81)]})
    assert strike(pick_long(view)) == 80


def test_e_l3_quant_skips_ineligible_and_unquoted_contracts() -> None:
    view = long_view({FAR: [Row(75, "25.00", "25.10", 0.80, code=IvCode.NO_CONVERGENCE),
                            Row(78, None, None, 0.80),
                            Row(85, "16.40", "16.60", 0.78)]})  # fmt: skip
    assert strike(pick_long(view)) == 85


def test_e_l3_quant_no_spot_selects_nothing() -> None:
    assert pick_long(long_view({FAR: [Row(80, "20.90", "21.10", 0.85)]}, spot=None)) is None


def test_e_l3_quant_nothing_in_the_band_selects_nothing() -> None:
    assert pick_long(long_view({FAR: [Row(80, "20.90", "21.10", 0.95)]})) is None


def test_e_l3_quant_selection_values_explain_the_pick() -> None:
    # The 70 is eligible but out of the band, so it isn't a candidate.
    view = long_view({FAR: [Row(70, "30.00", "30.10", 0.95), Row(80, "20.90", "21.10", 0.85),
                            Row(85, "16.40", "16.60", 0.78)]})  # fmt: skip
    selected = pick_long(view)
    assert selected is not None
    assert selected.values["extrinsic"] == "1.0000"
    assert selected.values["extrinsic_per_delta"] == pytest.approx(1 / 0.85, abs=1e-6)
    assert selected.values["candidates"] == 2
    assert selected.values["spot"] == "100.0000"
    assert selected.values["dte"] == 200
    assert selected.values["mid"] == "21.0000"


# ---- E-S3 quant: the lowest strike at or above spot + k × EM ---------------------------------


def short_view(spot: str | None = "100", *, call_atm: tuple[str, str] | None = ("1.58", "1.62"),
               put_atm: tuple[str, str] | None = ("1.38", "1.42"),
               calls: tuple[Row, ...] = ()) -> StubView:  # fmt: skip
    """ATM $100 with EM = 1.60 + 1.40 = $3.00 by default, and `calls` above it."""
    atm_call = Row(100, *(call_atm or (None, None)), 0.52)
    atm_put = Row(100, *(put_atm or (None, None)))
    chains = {
        (WEEKLY, Right.CALL): (Row(99, "2.18", "2.22", 0.60), atm_call, *calls),
        (WEEKLY, Right.PUT): (atm_put,),
    }
    return StubView(MON, spot_price=None if spot is None else dollars(spot), chains=chains)


STRIKES = (Row(102, "0.60", "0.64", 0.28), Row(103, "0.38", "0.42", 0.20),
           Row(104, "0.20", "0.24", 0.12))  # fmt: skip


def pick_short(view: StubView, k: float = 1.0) -> Selection | None:
    return ShortSelector(WeekFinalExpiry(), ExpectedMoveStrike(k)).select(view, LONG)


def test_e_s3_quant_a_strike_on_the_threshold_is_selected() -> None:
    assert strike(pick_short(short_view(calls=STRIKES))) == 103  # 100 + 1.0 × 3.00


def test_e_s3_quant_one_unit_over_the_threshold_moves_up_a_strike() -> None:
    view = short_view(call_atm=("1.5801", "1.6201"), calls=STRIKES)  # EM 3.0001
    assert strike(pick_short(view)) == 104


def test_e_s3_quant_k_scales_the_expected_move() -> None:
    calls = (Row("102.25", "0.50", "0.54", 0.25), *STRIKES)
    assert strike(pick_short(short_view(calls=calls), k=0.75)) == 102.25  # 100 + 2.25
    assert strike(pick_short(short_view(calls=calls), k=1.25)) == 104  # 100 + 3.75


def test_e_s3_quant_threshold_is_exact_in_price_units() -> None:
    view = short_view(call_atm=("1.5801", "1.6201"), calls=(Row("102.25", "0.50", "0.54", 0.25),
                      Row("102.26", "0.49", "0.53", 0.25)))  # fmt: skip
    selected = pick_short(view, k=0.75)  # 100 + 0.75 × 3.0001 = 102.250075: 102.25 is under it
    assert strike(selected) == 102.26
    assert selected is not None
    assert selected.values["min_strike"] == "102.2501"


def test_e_s3_quant_threshold_is_rounded_up_not_to_nearest() -> None:
    view = short_view(call_atm=("1.5801", "1.6201"), calls=(Row("100.75", "0.90", "0.94", 0.35),
                      Row("100.76", "0.89", "0.93", 0.35)))  # fmt: skip
    selected = pick_short(view, k=0.25)  # 100 + 0.25 × 3.0001 = 100.750025: 100.75 is under it
    assert strike(selected) == 100.76
    assert selected is not None
    assert selected.values["min_strike"] == "100.7501"


def test_e_s3_quant_takes_the_lowest_eligible_strike_at_or_above() -> None:
    """Selectors consider only contracts eligible on the bar (DEC-21): a listed 103 with no quote,
    or one whose IV fails, is passed over for the next strike up."""
    unquoted = (Row(103, None, None), Row(104, "0.20", "0.24", 0.12))
    assert strike(pick_short(short_view(calls=unquoted))) == 104
    failed = (Row(103, "0.38", "0.42", code=IvCode.NO_CONVERGENCE), Row(104, "0.20", "0.24", 0.12))
    assert strike(pick_short(short_view(calls=failed))) == 104


def test_e_s3_quant_no_spot_selects_nothing() -> None:
    assert pick_short(short_view(spot=None, calls=STRIKES)) is None


def test_e_s3_quant_no_expected_move_selects_nothing() -> None:
    """EM needs a valid ATM call and put quote (DEC-25): the listed ATM strike without one leaves
    EM unavailable, rather than moving to a neighbour (DEC-91)."""
    assert pick_short(short_view(calls=STRIKES, call_atm=None)) is None
    assert pick_short(short_view(calls=STRIKES, put_atm=None)) is None


def test_e_s3_quant_an_unquoted_atm_call_doesnt_move_em_to_a_quoted_neighbour() -> None:
    """The $99 straddle is fully quoted, but the listed ATM strike is $100 (DEC-25, DEC-91)."""
    view = short_view(calls=STRIKES, call_atm=None)
    chains = {
        **view.chains,
        (WEEKLY, Right.PUT): (Row(99, "0.98", "1.02"), Row(100, "1.38", "1.42")),
    }
    assert pick_short(StubView(MON, spot_price=view.spot_price, chains=chains)) is None


def test_e_s3_quant_em_uses_the_call_chains_atm_strike() -> None:
    """Spot $100.40: the calls' ATM is $100, though a $100.50 put is nearer; EM is the $100
    straddle."""
    view = short_view(spot="100.40", calls=STRIKES)
    puts = (Row(100, "1.38", "1.42"), Row("100.5", "1.60", "1.64"))
    selected = pick_short(StubView(MON, spot_price=view.spot_price,
                                   chains={**view.chains, (WEEKLY, Right.PUT): puts}))  # fmt: skip
    assert selected is not None
    assert selected.values["em"] == "3.0000"


def test_e_s3_quant_nothing_listed_at_or_above_selects_nothing() -> None:
    assert pick_short(short_view(calls=(Row(102, "0.60", "0.64", 0.28),))) is None


def test_e_s3_quant_selection_values_explain_the_pick() -> None:
    selected = pick_short(short_view(calls=STRIKES))
    assert selected is not None
    assert selected.values["spot"] == "100.0000"
    assert selected.values["em"] == "3.0000"
    assert selected.values["k"] == 1.0
    assert selected.values["min_strike"] == "103.0000"
    assert selected.values["delta"] == 0.20
