"""Gates G-3, G-4 and G-5 at their boundaries, and `n/a` when an input is missing (P4-02;
DEC-22, DEC-25, DEC-26)."""

import math
from collections.abc import Sequence
from datetime import date, datetime

import pytest

from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.domain.quotes import Quote
from pmcc.pricing.iv import IvCode
from pmcc.pricing.measures import realized_vol
from pmcc.strategy.gates import EventRatioGate, MinPremiumGate, VrpGate
from pmcc.strategy.ports import GateStatus, HeldLeg, Selection, ShortDecision
from tests.fakes.view import CALENDAR, ROOT, Row, StubView

MON = datetime(2026, 8, 31, 10, tzinfo=ET)
MON_DAY = MON.date()
FRONT, NEXT = date(2026, 9, 4), date(2026, 9, 11)
LONG = HeldLeg(OptionId(ROOT, date(2027, 2, 19), Right.CALL, Price.from_dollars(80)), 1,
               Price.from_dollars("21.00"), MON)  # fmt: skip


def decision(expiry: date = FRONT, bid: str = "0.60", ask: str = "0.64") -> ShortDecision:
    option = OptionId(ROOT, expiry, Right.CALL, Price.from_dollars(103))
    return ShortDecision(Selection(option), Quote(Price.from_dollars(bid),
                                                  Price.from_dollars(ask)), LONG)  # fmt: skip


def atm_chain(iv: float | None, *, code: IvCode = IvCode.OK) -> list[Row]:
    """Strikes 99 to 101 around a $100 spot; the ATM call at `iv`, or unquoted with None."""
    atm = Row(100, None, None) if iv is None else Row(100, "1.58", "1.62", 0.52, code, iv)
    return [Row(99, "2.18", "2.22", 0.60, iv=0.99), atm, Row(101, "1.10", "1.14", 0.44, iv=0.99)]


def view(front: list[Row] | None, following: list[Row] | None = None, *, spot: str | None = "100",
         closes: dict[datetime, Price] | None = None, now: datetime = MON) -> StubView:  # fmt: skip
    chains = {(FRONT, Right.CALL): front, (NEXT, Right.CALL): following}
    return StubView(
        now,
        spot_price=None if spot is None else Price.from_dollars(spot),
        chains={k: v for k, v in chains.items() if v is not None},
        closes=closes or {},
    )


# ---- G-3: front-week ATM IV ÷ next-week ATM IV > max_ratio -----------------------------------


def test_g_3_a_ratio_on_the_threshold_passes() -> None:
    result = EventRatioGate(1.20).evaluate(view(atm_chain(0.36), atm_chain(0.30)), decision())
    assert result.status is GateStatus.PASS
    assert result.values["ratio"] == 1.2


def test_g_3_a_ratio_just_over_the_threshold_fires() -> None:
    result = EventRatioGate(1.20).evaluate(view(atm_chain(0.3601), atm_chain(0.30)), decision())
    assert result.status is GateStatus.FIRE
    assert result.values["ratio"] == pytest.approx(1.200333, abs=1e-6)


def test_g_3_a_ratio_on_the_threshold_but_for_float_noise_passes() -> None:
    # 0.342 ÷ 0.285 is 1.2, but 1.2000000000000002 in floats.
    result = EventRatioGate(1.20).evaluate(view(atm_chain(0.342), atm_chain(0.285)), decision())
    assert result.status is GateStatus.PASS
    assert result.values["ratio"] == 1.2


def test_g_3_compares_the_ratio_it_publishes() -> None:
    """Results print floats to 6 places (DEC-50), so the ratio is compared at 6: 1.2000004 is
    1.2 and passes, 1.200001 fires, and a published ratio re-derives its status (DEC-95)."""
    near = EventRatioGate(1.20).evaluate(view(atm_chain(0.36000012), atm_chain(0.30)), decision())
    assert (near.status, near.values["ratio"]) == (GateStatus.PASS, 1.2)
    over = EventRatioGate(1.20).evaluate(view(atm_chain(0.3600003), atm_chain(0.30)), decision())
    assert (over.status, over.values["ratio"]) == (GateStatus.FIRE, 1.200001)


def test_g_3_values_name_both_weeks() -> None:
    result = EventRatioGate(1.20).evaluate(view(atm_chain(0.45), atm_chain(0.30)), decision())
    assert result.values == {
        "front_expiry": "2026-09-04", "front_atm_strike": "100.0000", "front_atm_iv": 0.45,
        "next_expiry": "2026-09-11", "next_atm_strike": "100.0000", "next_atm_iv": 0.30,
        "ratio": 1.5, "max_ratio": 1.20,
    }  # fmt: skip


@pytest.mark.parametrize(
    ("front", "following", "reason"),
    [
        (atm_chain(0.36), None, "no next-week ATM IV"),  # next week not listed
        (atm_chain(0.36), atm_chain(None), "no next-week ATM IV"),  # its ATM call unquoted
        (atm_chain(0.36), atm_chain(0.30, code=IvCode.NO_CONVERGENCE), "no next-week ATM IV"),
        (atm_chain(None), atm_chain(0.30), "no front-week ATM IV"),
    ],
    ids=["next-unlisted", "next-unquoted", "next-iv-failed", "front-unquoted"],
)
def test_g_3_a_missing_atm_iv_is_n_a(front: list[Row], following: list[Row] | None,
                                    reason: str) -> None:  # fmt: skip
    """A gate whose inputs are unavailable records `n/a` and doesn't fire (DEC-22)."""
    result = EventRatioGate(1.20).evaluate(view(front, following), decision())
    assert result.status is GateStatus.NA
    assert result.reason == reason
    assert result.values["ratio"] is None


def test_g_3_no_spot_is_n_a() -> None:
    result = EventRatioGate(1.20).evaluate(view(atm_chain(0.36), atm_chain(0.30), spot=None),
                                           decision())  # fmt: skip
    assert result.status is GateStatus.NA


def test_g_3_next_week_is_the_following_weeks_final_session() -> None:
    """The week after Jun 26 2026 expires Thursday Jul 2, since Friday Jul 3 is closed."""
    now = datetime(2026, 6, 22, 10, tzinfo=ET)
    front, following = date(2026, 6, 26), date(2026, 7, 2)
    stub = StubView(now, spot_price=Price.from_dollars(100),
                    chains={(front, Right.CALL): atm_chain(0.45),
                            (following, Right.CALL): atm_chain(0.30)})  # fmt: skip
    result = EventRatioGate(1.20).evaluate(stub, decision(front))
    assert result.status is GateStatus.FIRE
    assert result.values["next_expiry"] == "2026-07-02"


def test_g_3_each_week_uses_its_own_atm_strike() -> None:
    following = [Row(95, "5.10", "5.20", 0.80, iv=0.99), Row("102.5", "1.00", "1.04", 0.40,
                 iv=0.30)]  # fmt: skip
    result = EventRatioGate(1.20).evaluate(view(atm_chain(0.36), following), decision())
    assert result.values["next_atm_strike"] == "102.5000"
    assert result.values["next_atm_iv"] == 0.30


# ---- G-4: front-week ATM IV ÷ RV20 < min_ratio -----------------------------------------------


def closes(values: Sequence[float], before: date = MON_DAY) -> dict[datetime, Price]:
    """The close-bar trades of the len(values) sessions before `before`."""
    sessions = CALENDAR.sessions_before(before, len(values))
    return {s.close_bar_end: Price.from_dollars(v) for s, v in zip(sessions, values, strict=True)}


ZIGZAG = [100 * math.exp(0.01 * (i % 2)) for i in range(21)]  # ±1% a day
RV = realized_vol([Price.from_dollars(v) for v in ZIGZAG])


def test_g_4_a_ratio_on_the_threshold_passes() -> None:
    result = VrpGate(1.00).evaluate(view(atm_chain(RV), closes=closes(ZIGZAG)), decision())
    assert result.status is GateStatus.PASS
    assert result.values["ratio"] == 1.0


def test_g_4_a_ratio_just_under_the_threshold_fires() -> None:
    result = VrpGate(1.00).evaluate(view(atm_chain(RV * 0.9999), closes=closes(ZIGZAG)),
                                    decision())  # fmt: skip
    assert result.status is GateStatus.FIRE
    assert result.values["rv20"] == pytest.approx(RV, abs=1e-6)
    assert result.values["min_ratio"] == 1.00


def test_g_4_a_ratio_on_the_threshold_but_for_float_noise_passes() -> None:
    stub = view(atm_chain(RV * (1 - 1e-12)), closes=closes(ZIGZAG))
    result = VrpGate(1.00).evaluate(stub, decision())
    assert (result.status, result.values["ratio"]) == (GateStatus.PASS, 1.0)


def test_g_4_values_record_the_front_week_and_rv20() -> None:
    result = VrpGate(1.00).evaluate(view(atm_chain(RV * 0.9999), closes=closes(ZIGZAG)),
                                    decision())  # fmt: skip
    assert result.values == {
        "front_atm_strike": "100.0000", "front_atm_iv": round(RV * 0.9999, 6),
        "rv20": round(RV, 6), "ratio": 0.9999, "min_ratio": 1.00,
    }  # fmt: skip


def test_g_4_threshold_scales_the_comparison() -> None:
    stub = view(atm_chain(RV * 1.05), closes=closes(ZIGZAG))
    assert VrpGate(1.00).evaluate(stub, decision()).status is GateStatus.PASS
    assert VrpGate(1.10).evaluate(stub, decision()).status is GateStatus.FIRE


def test_g_4_a_missing_close_is_n_a() -> None:
    """RV20 needs all 21 closes (DEC-26): with one missing, it's unavailable."""
    series = closes(ZIGZAG)
    del series[min(series)]
    result = VrpGate(1.00).evaluate(view(atm_chain(0.10), closes=series), decision())
    assert result.status is GateStatus.NA
    assert result.reason == "no RV20"


def test_g_4_a_missing_front_week_atm_iv_is_n_a() -> None:
    result = VrpGate(1.00).evaluate(view(atm_chain(None), closes=closes(ZIGZAG)), decision())
    assert result.status is GateStatus.NA
    assert result.reason == "no front-week ATM IV"


def test_g_4_flat_closes_never_fire() -> None:
    """RV20 of zero: IV ÷ RV20 is unbounded, above any threshold, so the gate passes."""
    result = VrpGate(1.00).evaluate(view(atm_chain(0.30), closes=closes([100.0] * 21)),
                                    decision())  # fmt: skip
    assert result.status is GateStatus.PASS
    assert result.values["rv20"] == 0.0
    assert result.values["ratio"] is None


# ---- G-5: selected short mid < min_mid -------------------------------------------------------


def test_g_5_a_mid_on_the_minimum_passes() -> None:
    result = MinPremiumGate(Price.from_dollars("0.10")).evaluate(
        view(None), decision(bid="0.09", ask="0.11")
    )
    assert result.status is GateStatus.PASS
    assert result.values == {"mid": "0.1000", "min_mid": "0.1000"}


def test_g_5_one_unit_under_the_minimum_fires() -> None:
    result = MinPremiumGate(Price.from_dollars("0.10")).evaluate(
        view(None), decision(bid="0.0998", ask="0.1000")
    )
    assert result.status is GateStatus.FIRE
    assert result.values["mid"] == "0.0999"
