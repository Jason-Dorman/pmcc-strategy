"""Canonical JSON (PO, DEC-50): one byte form per value, and INV-13's timestamp drop."""

import math
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pmcc.domain.clock import ET
from pmcc.domain.money import Money
from pmcc.export import canonical


class Colour(StrEnum):
    RED = "red"


def test_dec_50_keys_are_sorted_with_no_whitespace_and_one_final_newline() -> None:
    text = canonical.dumps({"b": 1, "a": [True, None, "x"], "c": {"z": 0, "y": False}})

    assert text == '{"a":[true,null,"x"],"b":1,"c":{"y":false,"z":0}}\n'


def test_dec_50_dollars_print_to_four_places_as_numbers() -> None:
    values = [Money.from_dollars("1234.5"), Money(-7), Money(0)]

    assert canonical.dumps([m.to_dollars() for m in values]) == "[1234.5000,-0.0007,0.0000]\n"


def test_dec_50_negative_zero_dollars_print_as_zero() -> None:
    assert canonical.dumps(Decimal("-0.0000")) == "0.0000\n"


def test_dec_50_dollars_below_a_unit_are_refused_not_rounded() -> None:
    with pytest.raises(ValueError, match=r"\$0.0001"):
        canonical.dumps(Decimal("0.00005"))


def test_dec_50_non_finite_dollars_are_refused() -> None:
    with pytest.raises(ValueError, match="finite"):
        canonical.dumps(Decimal("NaN"))


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (0.1234567, "0.123457"),
        (0.8, "0.8"),
        (-0.0, "0.0"),
        (-0.0000001, "0.0"),
        (2.0, "2.0"),
        (1e-5, "1e-05"),
        (math.nan, "null"),
        (math.inf, "null"),
        (-math.inf, "null"),
    ],
)
def test_dec_50_floats_round_to_six_places_and_nan_is_null(value: float, text: str) -> None:
    assert canonical.dumps(value) == text + "\n"


def test_dec_50_times_carry_their_offset_and_dates_are_iso() -> None:
    t = datetime(2026, 3, 30, 10, tzinfo=ET)

    assert canonical.dumps([t, date(2026, 3, 30)]) == '["2026-03-30T10:00:00-04:00","2026-03-30"]\n'


def test_dec_50_a_naive_time_is_refused() -> None:
    with pytest.raises(ValueError, match="offset"):
        canonical.dumps(datetime(2026, 3, 30, 10))


def test_dec_50_text_keeps_non_ascii_and_escapes_quotes() -> None:
    text = canonical.dumps({"k": 'spot ≥ strike − 0.25 × EM "q"'})

    assert text == '{"k":"spot ≥ strike − 0.25 × EM \\"q\\""}\n'


def test_dec_50_a_str_enum_prints_as_its_value() -> None:
    assert canonical.dumps([Colour.RED]) == '["red"]\n'


def test_dec_50_tuples_are_arrays() -> None:
    assert canonical.dumps((1, (2,))) == "[1,[2]]\n"


def test_dec_50_non_string_keys_are_refused() -> None:
    with pytest.raises(TypeError, match="keys"):
        canonical.dumps({1: "a"})


@pytest.mark.parametrize("value", [object(), {1, 2}, b"bytes", range(2)])
def test_dec_50_a_value_with_no_json_form_is_refused(value: object) -> None:
    with pytest.raises(TypeError, match="no canonical JSON form"):
        canonical.dumps(value)


_json = st.recursive(
    st.none()
    | st.booleans()
    | st.integers(-(10**12), 10**12)
    | st.floats(allow_nan=False, allow_infinity=False, width=64)
    | st.integers(-(10**10), 10**10).map(lambda u: Money(u).to_dollars())
    | st.text(max_size=8)
    | st.datetimes(timezones=st.just(UTC)),
    lambda inner: (
        st.lists(inner, max_size=4) | st.dictionaries(st.text(max_size=4), inner, max_size=4)
    ),
    max_leaves=12,
)


@given(_json)
def test_dec_50_reading_and_dumping_again_gives_the_same_bytes(value: object) -> None:
    raw = canonical.to_bytes(value)

    assert canonical.to_bytes(canonical.loads(raw)) == raw


def _result(hour: int, sha: str) -> dict[str, object]:
    when = datetime(2026, 9, 30, hour, tzinfo=ET)
    manifest = {"run_timestamp": when, "git_sha": sha, "config_hash": "c", "git_dirty": False}
    return {"manifest": manifest, "ledger": [{"nav": Decimal("1.0000"), "delta": 0.5}]}


def test_inv_13_dropping_the_volatile_values_removes_only_them() -> None:
    a, b = canonical.to_bytes(_result(9, "a" * 40)), canonical.to_bytes(_result(11, "b" * 40))

    assert a != b
    assert canonical.drop_volatile(a) == canonical.drop_volatile(b)
    assert canonical.drop_volatile(a) == (
        b'{"ledger":[{"delta":0.5,"nav":1.0000}],"manifest":{"config_hash":"c","git_dirty":false}}\n'
    )


def test_inv_13_any_other_manifest_value_still_counts() -> None:
    changed = _result(9, "a" * 40)
    changed["manifest"] = {**changed["manifest"], "git_dirty": True}  # type: ignore[dict-item]

    first = canonical.drop_volatile(canonical.to_bytes(_result(9, "a" * 40)))
    assert first != canonical.drop_volatile(canonical.to_bytes(changed))


@pytest.mark.parametrize("missing", ["run_timestamp", "git_sha"])
def test_inv_13_a_file_missing_a_volatile_value_is_refused(missing: str) -> None:
    data = _result(9, "a" * 40)
    del data["manifest"][missing]  # type: ignore[attr-defined]

    with pytest.raises(KeyError):
        canonical.drop_volatile(canonical.to_bytes(data))


PADDED = [
    ("1234.5", "1234.5000"),
    ("10000", "10000.0000"),
    ("1E+1", "10.0000"),
    ("-3.25", "-3.2500"),
]


@pytest.mark.parametrize(("value", "text"), PADDED)
def test_dec_50_dollars_short_of_four_places_are_padded(value: str, text: str) -> None:
    assert canonical.dumps(Decimal(value)) == text + "\n"


def test_dec_92_verbatim_floats_print_unrounded() -> None:
    config = {"params": {"short_max_spread": 0.1234567, "em_buffer": 1e-7}, "n": [0.30, 2, "x"]}

    text = canonical.dumps(canonical.verbatim_floats(config))

    assert text == '{"n":[0.3,2,"x"],"params":{"em_buffer":1e-07,"short_max_spread":0.1234567}}\n'


def test_dec_92_verbatim_floats_leave_other_values_alone() -> None:
    assert canonical.verbatim_floats({"a": True, "b": None, "c": 3, "d": "0.1000"}) == {
        "a": True, "b": None, "c": 3, "d": "0.1000"}  # fmt: skip


def test_dec_92_verbatim_floats_refuse_nan() -> None:
    with pytest.raises(ValueError, match="JSON number"):
        canonical.verbatim_floats({"x": math.nan})
