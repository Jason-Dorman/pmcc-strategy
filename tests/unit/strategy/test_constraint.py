"""E-S5 and the gates G-1, G-2 (INV-06; DEC-22)."""

from datetime import date, datetime

from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.domain.quotes import Quote
from pmcc.strategy.gates import NoQuoteGate, StructuralConstraint, StructuralGate
from pmcc.strategy.ports import GateStatus, HeldLeg, Selection, ShortDecision
from tests.fakes.view import ROOT, StubView

MON = datetime(2026, 8, 31, 10, tzinfo=ET)
LONG = HeldLeg(OptionId(ROOT, date(2027, 2, 19), Right.CALL, Price.from_dollars(80)), 1,
               Price.from_dollars("21.00"), MON)  # fmt: skip
SHORT_EXPIRY = date(2026, 9, 4)


def short(strike: str) -> Price:
    return Price.from_dollars(strike)


def test_e_s5_equality_fails_the_strict_inequality() -> None:
    # gap 102 − 80 = 22 > debit 21.00 − 1.00 = 20: holds
    assert StructuralConstraint().check(LONG, short("102"), Price.from_dollars("1.00")).satisfied
    # gap 101 − 80 = 21; debit 21.00 − 0.00: equal → fails
    assert not StructuralConstraint().check(LONG, short("101"), Price(0)).satisfied


def test_e_s5_one_unit_either_side_of_the_boundary() -> None:
    at = StructuralConstraint().check(LONG, short("101"), Price(1))  # debit 20.9999 < 21
    assert at.satisfied
    under = StructuralConstraint().check(LONG, short("100.99"), Price(99))  # 20.99 vs 20.9901
    assert not under.satisfied


def test_e_s5_uses_the_long_entry_fill_not_its_mark() -> None:
    check = StructuralConstraint().check(LONG, short("102"), Price.from_dollars("0.50"))
    assert check.debit == Price.from_dollars("20.50")
    assert check.gap == Price.from_dollars("22")


def decision(strike: str, bid: str, ask: str) -> ShortDecision:
    option = OptionId(ROOT, SHORT_EXPIRY, Right.CALL, Price.from_dollars(strike))
    quote = Quote(Price.from_dollars(bid), Price.from_dollars(ask))
    return ShortDecision(Selection(option), quote, LONG)


def test_g_2_fires_when_e_s5_fails() -> None:
    gate = StructuralGate(StructuralConstraint())
    result = gate.evaluate(StubView(MON), decision("100.50", "0.01", "0.03"))  # 20.50 vs 20.98
    assert result.status is GateStatus.FIRE
    assert result.values["satisfied"] is False


def test_g_2_passes_when_e_s5_holds() -> None:
    gate = StructuralGate(StructuralConstraint())
    result = gate.evaluate(StubView(MON), decision("102", "0.98", "1.02"))
    assert result.status is GateStatus.PASS
    assert result.values == {"strike_gap": "22.0000", "net_debit": "20.0000", "satisfied": True}


def test_g_1_fires_with_its_reason() -> None:
    result = NoQuoteGate().fire({"bars_checked": 7}, "never passed E-T1")
    assert result.status is GateStatus.FIRE
    assert str(result.rule_id) == "G-1"
    assert NoQuoteGate().passed({}).status is GateStatus.PASS
