"""`OptionId`, `Right`, `Side` and `RuleId` (ARCHITECTURE §3.2, Spec › Blotter)."""

from datetime import date

import pytest

from pmcc.domain.instruments import OPTION_MULTIPLIER, OptionId, Right, Side
from pmcc.domain.money import Price
from pmcc.domain.rules import RuleId

JUN_19 = date(2026, 6, 19)


def test_instruments_option_multiplier_is_one_hundred() -> None:
    assert OPTION_MULTIPLIER == 100


def test_instruments_right_values_are_c_and_p() -> None:
    assert [r.value for r in Right] == ["C", "P"]
    assert Right("C") is Right.CALL


def test_instruments_side_values_match_the_blotter() -> None:
    assert [s.value for s in Side] == ["BUY", "SELL", "EXPIRE", "ASSIGN"]


def test_instruments_option_id_holds_root_expiry_right_strike() -> None:
    opt = OptionId("NVDA", JUN_19, Right.CALL, Price.from_dollars("115.50"))
    assert opt.root == "NVDA"
    assert opt.expiry == JUN_19
    assert opt.right is Right.CALL
    assert opt.strike == Price(1_155_000)
    assert opt.strike_cents == 11_550


def test_instruments_option_id_is_a_hashable_value() -> None:
    a = OptionId("NVDA", JUN_19, Right.CALL, Price(1_000_000))
    b = OptionId("NVDA", JUN_19, Right.CALL, Price(1_000_000))
    assert a == b
    assert len({a, b}) == 1


def test_instruments_option_ids_sort_by_root_expiry_right_strike() -> None:
    later = OptionId("NVDA", date(2026, 6, 26), Right.CALL, Price(900_000))
    low = OptionId("NVDA", JUN_19, Right.CALL, Price(900_000))
    high = OptionId("NVDA", JUN_19, Right.CALL, Price(1_000_000))
    put = OptionId("NVDA", JUN_19, Right.PUT, Price(900_000))
    assert sorted([later, put, high, low]) == [low, high, put, later]


@pytest.mark.parametrize("root", ["", "nvda", "NV DA", "NVDA.O"])
def test_instruments_option_id_rejects_a_malformed_root(root: str) -> None:
    with pytest.raises(ValueError, match="root"):
        OptionId(root, JUN_19, Right.CALL, Price(1_000_000))


@pytest.mark.parametrize("units", [0, -100, 1_000_050])
def test_instruments_option_id_strike_is_positive_whole_cents(units: int) -> None:
    with pytest.raises(ValueError, match="strike"):
        OptionId("NVDA", JUN_19, Right.CALL, Price(units))


@pytest.mark.parametrize(
    "text",
    ["E-T1", "E-L1", "E-L4", "E-S5", "G-1", "G-5", "X-S1", "X-S5", "X-L1", "X-L2", "X-E1"],
)
def test_rule_id_accepts_spec_rule_ids(text: str) -> None:
    rid = RuleId(text)
    assert rid == text
    assert str(rid) == text


@pytest.mark.parametrize("text", ["", "e-s3", "E-S", "E-X1", "G-", "X-T1", "ES3", " E-S3", "E-S10"])
def test_rule_id_rejects_malformed_ids(text: str) -> None:
    with pytest.raises(ValueError, match="rule ID"):
        RuleId(text)
