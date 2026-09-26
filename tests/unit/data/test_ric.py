"""RIC builder and parser, the form policy and OCC symbols (INV-11; Spec › RIC builder; LDG §3).

The builder zero-pads the day (DEC-01), and the parser reads both spellings.
"""

from datetime import date, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pmcc.data.ric import (
    MAX_STRIKE,
    ParsedRic,
    RicForm,
    build_ric,
    forms_to_ask,
    occ_symbol,
    parse_ric,
)
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import UNITS_PER_CENT, Price


def _option(root: str, expiry: date, right: Right, strike: str) -> OptionId:
    return OptionId(root, expiry, right, Price.from_dollars(strike))


def _spelled(option: OptionId, form: RicForm) -> str:
    """The RIC spelled from the grammar alone, not from ric.py's month tables: calls A-L, puts
    M-X, a zero-padded day, and a caret that takes the call letter."""
    first = {Right.CALL: "A", Right.PUT: "M"}[option.right]
    expiry, yy = option.expiry, option.expiry.year % 100
    live = (
        f"{option.root}{chr(ord(first) + expiry.month - 1)}{expiry.day:02d}{yy:02d}"
        f"{option.strike_cents:05d}.U"
    )
    caret = f"^{chr(ord('A') + expiry.month - 1)}{yy:02d}"
    return live + caret if form is RicForm.EXPIRED else live


def _arabic(digits: str) -> str:
    """ASCII digits as Arabic-Indic ones, which `int()` reads but a RIC must not contain."""
    return "".join(chr(0x660 + int(d)) for d in digits)


AAPL_190C = _option("AAPL", date(2026, 6, 5), Right.CALL, "190")
UUUU_14_50C = _option("UUUU", date(2026, 8, 21), Right.CALL, "14.50")
UUUU_11P = _option("UUUU", date(2026, 6, 12), Right.PUT, "11")
QQQ_625C = _option("QQQ", date(2026, 7, 10), Right.CALL, "625")
QQQ_710C = _option("QQQ", date(2026, 9, 18), Right.CALL, "710")

contracts = st.builds(
    OptionId,
    root=st.from_regex(r"[A-Z][A-Z0-9]{0,5}", fullmatch=True),
    expiry=st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)),
    right=st.sampled_from(Right),
    strike=st.integers(min_value=1, max_value=99_999).map(lambda c: Price(c * UNITS_PER_CENT)),
)
forms = st.sampled_from(RicForm)


@pytest.mark.parametrize(
    ("ric", "option", "form"),
    [
        pytest.param("AAPLF52619000.U^F26", AAPL_190C, RicForm.EXPIRED, id="spec-unpadded-day"),
        pytest.param("UUUUH212601450.U^H26", UUUU_14_50C, RicForm.EXPIRED, id="spec"),
        pytest.param("QQQG102662500.U^G26", QQQ_625C, RicForm.EXPIRED, id="ldg-expired"),
        pytest.param("QQQI182671000.U", QQQ_710C, RicForm.LIVE, id="ldg-live"),
        pytest.param("UUUUR122601100.U^F26", UUUU_11P, RicForm.EXPIRED, id="ldg-put"),
    ],
)
def test_inv_11_known_examples_parse(ric: str, option: OptionId, form: RicForm) -> None:
    assert parse_ric(ric) == ParsedRic(option, form)


def test_inv_11_builder_zero_pads_the_day() -> None:
    # Only the padded day resolves (DEC-01, LDG §3), so the spec's unpadded example rebuilds padded.
    spec = parse_ric("AAPLF52619000.U^F26")
    assert build_ric(spec.option, spec.form) == "AAPLF052619000.U^F26"
    assert build_ric(spec.option, RicForm.LIVE) == "AAPLF052619000.U"


def test_inv_11_parser_reads_both_day_spellings() -> None:
    assert parse_ric("AAPLF052619000.U^F26") == parse_ric("AAPLF52619000.U^F26")


@pytest.mark.parametrize(
    "ric",
    [
        "AAPLF052619000.U^F26",
        "UUUUH212601450.U^H26",
        "QQQG102662500.U^G26",
        "QQQI182671000.U",
        "UUUUR122601100.U^F26",
    ],
)
def test_inv_11_padded_examples_round_trip(ric: str) -> None:
    parsed = parse_ric(ric)
    assert build_ric(parsed.option, parsed.form) == ric


def test_inv_11_put_caret_uses_the_call_letter() -> None:
    # A June put's month letter is R, but its caret is ^F26: ^R26 returned no puts (LDG §3).
    assert build_ric(UUUU_11P, RicForm.EXPIRED) == "UUUUR122601100.U^F26"
    with pytest.raises(ValueError, match=r"\^F26"):
        parse_ric("UUUUR122601100.U^R26")


@pytest.mark.parametrize("right", list(Right))
@pytest.mark.parametrize("month", range(1, 13))
def test_inv_11_every_month_letter_and_caret_match_the_grammar(month: int, right: Right) -> None:
    # build_ric and parse_ric share one month table, so a round-trip can't see a transposed
    # letter. Pin all 24 letters, and the caret for each month, against the spelled-out grammar.
    option = _option("NVDA", date(2027, month, 15), right, "150")
    for form in RicForm:
        ric = _spelled(option, form)
        assert build_ric(option, form) == ric
        assert parse_ric(ric) == ParsedRic(option, form)


def test_inv_11_january_and_december_letters_for_both_rights() -> None:
    # The ends of both letter ranges, written out; January and December are LEAPS months.
    jan, dec = date(2027, 1, 15), date(2026, 12, 18)
    assert build_ric(_option("NVDA", jan, Right.CALL, "150"), RicForm.LIVE) == "NVDAA152715000.U"
    assert build_ric(_option("NVDA", dec, Right.CALL, "150"), RicForm.LIVE) == "NVDAL182615000.U"
    assert build_ric(_option("NVDA", jan, Right.PUT, "150"), RicForm.EXPIRED) == (
        "NVDAM152715000.U^A27"
    )
    assert build_ric(_option("NVDA", dec, Right.PUT, "150"), RicForm.EXPIRED) == (
        "NVDAX182615000.U^L26"
    )


def test_inv_11_strike_above_999_99_raises() -> None:
    assert Price.from_dollars("999.99") == MAX_STRIKE
    too_wide = _option("SPY", date(2026, 9, 18), Right.CALL, "1000")
    with pytest.raises(ValueError, match="five-digit strike"):
        build_ric(too_wide, RicForm.LIVE)
    with pytest.raises(ValueError, match="five-digit strike"):
        build_ric(too_wide, RicForm.EXPIRED)


@pytest.mark.parametrize(
    ("strike", "ric"),
    [
        pytest.param("999.99", "SPYI182699999.U", id="widest"),
        pytest.param("0.01", "SPYI182600001.U", id="narrowest"),
        # 4.02 * 100 is 401.99999999999994 in floats: the strike field must come from integers.
        pytest.param("4.02", "SPYI182600402.U", id="float-truncates-it"),
    ],
)
def test_inv_11_strikes_from_one_cent_to_999_99_build(strike: str, ric: str) -> None:
    assert build_ric(_option("SPY", date(2026, 9, 18), Right.CALL, strike), RicForm.LIVE) == ric


@pytest.mark.parametrize(
    "fetch_date",
    [pytest.param(date(2026, 9, 18), id="expiry-day"), pytest.param(date(2026, 3, 2), id="before")],
)
def test_inv_11_live_contracts_get_no_caret(fetch_date: date) -> None:
    asked = forms_to_ask(QQQ_710C.expiry, fetch_date)
    assert asked == (RicForm.LIVE,)
    assert [build_ric(QQQ_710C, form) for form in asked] == ["QQQI182671000.U"]


def test_ric_expired_contracts_ask_caret_then_live() -> None:
    # The day after expiry: the caret form first, then live for whatever didn't answer (DEC-45).
    asked = forms_to_ask(QQQ_710C.expiry, date(2026, 9, 19))
    assert asked == (RicForm.EXPIRED, RicForm.LIVE)
    assert [build_ric(QQQ_710C, form) for form in asked] == [
        "QQQI182671000.U^I26",
        "QQQI182671000.U",
    ]


def test_ric_form_values_are_what_the_manifest_records() -> None:
    assert [form.value for form in RicForm] == ["live", "expired"]


def test_ric_builder_reads_a_form_stored_as_text() -> None:
    # The manifest records RicForm values, so "expired" read back from JSON builds the caret form.
    assert build_ric(QQQ_710C, "expired") == "QQQI182671000.U^I26"  # type: ignore[arg-type]


@pytest.mark.parametrize("form", ["expird", "EXPIRED", None])
def test_ric_builder_refuses_what_is_not_a_form(form: object) -> None:
    # Anything else raises, rather than quietly building the live form.
    with pytest.raises(ValueError, match="RicForm"):
        build_ric(QQQ_710C, form)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "ric",
    [
        pytest.param("", id="empty"),
        pytest.param("NVDA.O", id="stock-ric"),
        pytest.param("aaplf052619000.u^f26", id="lower-case"),
        pytest.param("AAPLF052619000", id="no-venue"),
        pytest.param("AAPLF052619000.O", id="other-venue"),
        pytest.param("AAPLF052619000XU", id="no-dot-before-u"),
        pytest.param(" AAPLF052619000.U", id="leading-space"),
        pytest.param("AAPLF052619000.U ", id="trailing-space"),
        pytest.param("AAPLF052619000.U\n", id="trailing-newline"),
        pytest.param("AAPLF052619000.U^F26\n", id="newline-after-caret"),
        pytest.param("F052619000.U", id="no-root"),
        pytest.param("1AAPLF052619000.U", id="root-starts-with-a-digit"),
        pytest.param("AAPLY052619000.U", id="no-month-letter"),
        pytest.param("AAPLF2619000.U", id="too-few-digits"),
        pytest.param("AAPLF1052619000.U", id="too-many-digits"),
        pytest.param("AAPLF" + _arabic("05") + "2619000.U", id="non-ascii-day"),
        pytest.param("AAPLF05" + _arabic("26") + "19000.U", id="non-ascii-year"),
        pytest.param("AAPLF0526" + _arabic("19000") + ".U", id="non-ascii-strike"),
        pytest.param("AAPLF052619000.U^F" + _arabic("26"), id="non-ascii-caret-year"),
        pytest.param("AAPLF002619000.U", id="day-00"),
        pytest.param("AAPLF02619000.U", id="day-0"),
        pytest.param("AAPLB302619000.U", id="feb-30"),
        pytest.param("AAPLF052600000.U", id="zero-strike"),
        pytest.param("AAPLF052619000.U^G26", id="caret-month"),
        pytest.param("AAPLF052619000.U^F27", id="caret-year"),
        pytest.param("AAPLF052619000.U^F2", id="short-caret"),
        pytest.param("AAPLF052619000.U^", id="bare-caret"),
    ],
)
def test_inv_11_parser_rejects_malformed_rics(ric: str) -> None:
    with pytest.raises(ValueError, match="RIC"):
        parse_ric(ric)


@pytest.mark.parametrize("expiry", [date(1999, 12, 17), date(2100, 1, 15)])
def test_ric_two_digit_year_refuses_expiries_outside_2000_to_2099(expiry: date) -> None:
    option = OptionId("SPY", expiry, Right.CALL, Price.from_dollars("500"))
    with pytest.raises(ValueError, match="year"):
        build_ric(option, RicForm.LIVE)
    with pytest.raises(ValueError, match="year"):
        occ_symbol(option)


@pytest.mark.parametrize(
    ("option", "occ"),
    [
        pytest.param(QQQ_710C, "QQQ   260918C00710000", id="ldg"),
        pytest.param(UUUU_11P, "UUUU  260612P00011000", id="put"),
        pytest.param(UUUU_14_50C, "UUUU  260821C00014500", id="cents"),
        # 2.01 * 1000 is 2009.9999999999998 in floats: the strike field must come from integers.
        pytest.param(
            _option("SPY", date(2026, 9, 18), Right.CALL, "2.01"),
            "SPY   260918C00002010",
            id="float-truncates-it",
        ),
        pytest.param(
            _option("ABCDEF", date(2027, 1, 15), Right.CALL, "0.50"),
            "ABCDEF270115C00000500",
            id="six-character-root",
        ),
        pytest.param(
            _option("SPY", date(2026, 9, 18), Right.CALL, "99999.99"),
            "SPY   260918C99999990",
            id="widest-strike",
        ),
    ],
)
def test_occ_symbol_pads_the_root_and_writes_the_strike_in_thousandths(
    option: OptionId, occ: str
) -> None:
    assert occ_symbol(option) == occ


def test_occ_symbol_refuses_a_root_longer_than_six() -> None:
    with pytest.raises(ValueError, match="root"):
        occ_symbol(_option("ABCDEFG", date(2026, 9, 18), Right.CALL, "10"))


def test_occ_symbol_refuses_a_strike_wider_than_eight_digits() -> None:
    with pytest.raises(ValueError, match="strike"):
        occ_symbol(_option("SPY", date(2026, 9, 18), Right.CALL, "100000"))


@given(contracts, forms)
def test_inv_11_random_contracts_round_trip(option: OptionId, form: RicForm) -> None:
    ric = build_ric(option, form)
    assert ric == _spelled(option, form)
    assert parse_ric(ric) == ParsedRic(option, form)


@given(contracts.filter(lambda o: o.expiry.day < 10), forms)
def test_inv_11_unpadded_day_parses_to_the_same_contract(option: OptionId, form: RicForm) -> None:
    padded = build_ric(option, form)
    day_at = len(option.root) + 1  # just after the month letter
    assert padded[day_at] == "0"
    unpadded = padded[:day_at] + padded[day_at + 1 :]
    assert parse_ric(unpadded) == ParsedRic(option, form)


@given(contracts, st.integers(min_value=0, max_value=3660))
def test_inv_11_unexpired_contracts_never_get_a_caret(option: OptionId, days_left: int) -> None:
    fetch_date = option.expiry - timedelta(days=days_left)
    rics = [build_ric(option, form) for form in forms_to_ask(option.expiry, fetch_date)]
    assert len(rics) == 1
    assert "^" not in rics[0]


@given(contracts, st.integers(min_value=1, max_value=3660))
def test_ric_expired_contracts_always_ask_the_caret_first(option: OptionId, days_ago: int) -> None:
    fetch_date = option.expiry + timedelta(days=days_ago)
    assert forms_to_ask(option.expiry, fetch_date) == (RicForm.EXPIRED, RicForm.LIVE)


@given(contracts)
def test_occ_symbol_encodes_every_field_of_the_contract(option: OptionId) -> None:
    occ = occ_symbol(option)
    assert len(occ) == 21
    assert occ[:6].rstrip() == option.root
    assert occ[6:12] == f"{option.expiry:%y%m%d}"
    assert occ[12] == option.right.value
    assert int(occ[13:]) == option.strike_cents * 10
