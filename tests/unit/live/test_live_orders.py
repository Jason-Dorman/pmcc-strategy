"""Orders in the course's order language, Sanji's (LIVE-SPEC › Orders; L2-01; LINV-01).

Every rule the order page (https://jakevestal.github.io/server-logic-533/order.html) gives for
rejecting an order is checked before `open_orders.json` is written: an unknown field, an unknown
token, a missing required field, a quantity below 1. An invalid order fails and writes nothing.
"""

import json
from datetime import date
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from typing import Any

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from pmcc.domain.instruments import Right
from pmcc.domain.money import Price
from pmcc.live.orders import (
    FIELD_ORDER,
    Order,
    OrderError,
    order_id,
    parse_orders,
    pct_token,
    read_orders,
    render_orders,
    strike_token,
    write_orders,
)

ROOT = Path(__file__).resolve().parents[3]

# The order page's two examples, with the id and session it leaves to the student.
OPTION_LIMIT: dict[str, Any] = {
    "id": "wheel-2026-11-16-P-155",
    "for": "2026-11-16",
    "order_type": "lmt",
    "action": "SHT",
    "qty": 1,
    "underlying": 76792991,
    "contract": "put",
    "expiry": "5DTE+",
    "strike": "otm:1",
    "ref": "open",
    "lmt_prc": "mid",
}
SHARES_MARKET: dict[str, Any] = {
    "id": "shares-2026-11-16",
    "for": "2026-11-16",
    "order_type": "mkt",
    "action": "BUY",
    "qty": 100,
    "underlying": 76792991,
    "contract": "underlying",
    "ref": "open",
}


def _with(base: dict[str, Any], **changes: Any) -> dict[str, Any]:
    order = {**base, **changes}
    return {k: v for k, v in order.items() if v is not _DROP}


_DROP = object()


def _rejected(order: dict[str, Any]) -> OrderError:
    with pytest.raises(OrderError) as raised:
        parse_orders([order])
    return raised.value


def test_linv_01_the_order_pages_examples_are_valid() -> None:
    option, shares = parse_orders([OPTION_LIMIT, SHARES_MARKET])

    assert option.for_ == date(2026, 11, 16)
    assert option.strike == "otm:1"
    assert shares.expiry is None
    assert shares.lmt_prc is None


def test_linv_01_an_empty_book_is_an_empty_list() -> None:
    assert parse_orders([]) == ()


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"colour": "red"}, "unknown field"),
        ({"id": _DROP}, "id"),
        ({"for": _DROP}, "for"),
        ({"order_type": _DROP}, "order_type"),
        ({"action": _DROP}, "action"),
        ({"qty": _DROP}, "qty"),
        ({"underlying": _DROP}, "underlying"),
        ({"contract": _DROP}, "contract"),
        ({"id": ""}, "id"),
        ({"qty": 0}, "qty"),
        ({"qty": True}, "qty"),
        ({"qty": "1"}, "qty"),
        ({"qty": 1.5}, "qty"),
        ({"underlying": "NVDA"}, "underlying"),
        ({"underlying": 0}, "underlying"),
        ({"contract": ""}, "contract"),
        ({"contract": "future"}, "contract"),
        ({"for": "next"}, "for"),
        ({"for": "2026-13-01"}, "for"),
        ({"for": "2026-11-16T09:30"}, "for"),
        ({"order_type": "stp"}, "order_type"),
        ({"action": "SELL"}, "action"),
        ({"ref": "close"}, "ref"),
        ({"lmt_prc": _DROP}, "lmt_prc"),
        ({"order_type": "mkt"}, "lmt_prc"),
        ({"expiry": _DROP}, "expiry"),
        ({"strike": _DROP}, "strike"),
    ],
)
def test_linv_01_an_order_breaking_a_field_rule_is_rejected(
    change: dict[str, Any], reason: str
) -> None:
    error = _rejected(_with(OPTION_LIMIT, **change))

    assert reason in str(error)
    assert OPTION_LIMIT["id"] in str(error) or "id" in change


@pytest.mark.parametrize("field", ["expiry", "strike"])
def test_linv_01_shares_carry_no_expiry_or_strike(field: str) -> None:
    error = _rejected(_with(SHARES_MARKET, **{field: "atm" if field == "strike" else "W+"}))

    assert field in str(error)


@pytest.mark.parametrize("token", ["5DTE+", "5DTE-", "5DTE", "0DTE", "2026-11-20", "W+", "M+"])
def test_linv_01_every_expiry_token_on_the_page_is_valid(token: str) -> None:
    (order,) = parse_orders([_with(OPTION_LIMIT, expiry=token)])

    assert order.expiry == token


@pytest.mark.parametrize(
    "token",
    ["5DTE*", "DTE+", "-5DTE", "05DTE+", "007DTE", "W", "M", "W-", "2026-02-30", "2026-11-20 ", ""],
)
def test_linv_01_an_unknown_expiry_token_is_rejected(token: str) -> None:
    assert "expiry" in str(_rejected(_with(OPTION_LIMIT, expiry=token)))


@pytest.mark.parametrize(
    "token",
    [
        "250",
        "152.5",
        "atm",
        "otm:1",
        "itm:2",
        "pct:-5",
        "pct:+2",
        "pct:0",
        "delta:30",
        "delta:12.5",
        "premium:2",
        "premium:0.75",
    ],
)
def test_linv_01_every_strike_token_on_the_page_is_valid(token: str) -> None:
    (order,) = parse_orders([_with(OPTION_LIMIT, strike=token)])

    assert order.strike == token


@pytest.mark.parametrize(
    "token",
    [
        "otm:0",
        "otm:x",
        "itm:-1",
        "delta:-30",
        "delta:0",
        "delta:100",
        "premium:0",
        "pct:",
        "pct:3.5",  # the page shows whole percents only (LD-29)
        "pct:-4.8",
        "pct:-05",
        "0",
        "-250",
        "ATM",
        "vega:0.15",  # reserved: rejected until it is turned on
        "",
    ],
)
def test_linv_01_an_unknown_strike_token_is_rejected(token: str) -> None:
    assert "strike" in str(_rejected(_with(OPTION_LIMIT, strike=token)))


@pytest.mark.parametrize(
    "token", ["3.50", "0.05", "mid", "bid", "ask", "mid-0.05", "bid+0.10", "ask-0.05"]
)
def test_linv_01_every_limit_price_token_on_the_page_is_valid(token: str) -> None:
    (order,) = parse_orders([_with(OPTION_LIMIT, lmt_prc=token)])

    assert order.lmt_prc == token


@pytest.mark.parametrize("token", ["last", "mid-", "mid*2", "-1", "0", "MID", "1.2.3", ""])
def test_linv_01_an_unknown_limit_price_token_is_rejected(token: str) -> None:
    assert "lmt_prc" in str(_rejected(_with(OPTION_LIMIT, lmt_prc=token)))


def test_linv_01_tokens_must_be_strings() -> None:
    assert "strike" in str(_rejected(_with(OPTION_LIMIT, strike=155)))


def test_ld_19_two_orders_with_one_id_are_rejected() -> None:
    with pytest.raises(OrderError, match="twice"):
        parse_orders([OPTION_LIMIT, _with(OPTION_LIMIT, strike="atm")])


def test_linv_01_a_book_that_is_not_a_list_is_rejected() -> None:
    with pytest.raises(OrderError, match="list"):
        parse_orders(OPTION_LIMIT)


def test_l2_01_render_writes_the_pages_field_order_and_omits_what_is_absent() -> None:
    text = render_orders(parse_orders([OPTION_LIMIT, SHARES_MARKET]))
    first, second = json.loads(text)

    assert list(first) == list(FIELD_ORDER)
    assert list(second) == [f for f in FIELD_ORDER if f in SHARES_MARKET]


def test_l2_01_render_is_lf_two_space_json_with_a_final_newline() -> None:
    text = render_orders(parse_orders([SHARES_MARKET]))

    assert text.endswith("]\n")
    assert "\r" not in text
    assert '\n  {\n    "id": "shares-2026-11-16",\n' in text


def test_l2_01_an_empty_book_renders_as_an_empty_list() -> None:
    assert render_orders(()) == "[]\n"


def test_l2_01_orders_round_trip_through_the_file(tmp_path: Path) -> None:
    path = tmp_path / "open_orders.json"
    orders = parse_orders([OPTION_LIMIT, SHARES_MARKET])

    write_orders(path, orders)

    assert read_orders(path) == orders
    assert json.loads(path.read_text(encoding="utf-8")) == [OPTION_LIMIT, SHARES_MARKET]


def test_linv_01_an_invalid_order_fails_and_leaves_the_file_as_it_was(tmp_path: Path) -> None:
    path = tmp_path / "open_orders.json"
    path.write_bytes(b"[]\n")
    values: dict[str, Any] = {k: v for k, v in OPTION_LIMIT.items() if k != "for"}
    values.update(for_=date(2026, 11, 16), qty=0)
    bad = Order.model_construct(**values)

    with pytest.raises(OrderError, match="qty"):
        write_orders(path, (bad,))

    assert path.read_bytes() == b"[]\n"


def test_l2_01_a_missing_file_holds_no_orders(tmp_path: Path) -> None:
    assert read_orders(tmp_path / "open_orders.json") == ()


@pytest.mark.parametrize("text", ["{", "", '{"id": "x"}'])
def test_l2_01_an_unreadable_file_is_an_error(tmp_path: Path, text: str) -> None:
    path = tmp_path / "open_orders.json"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(OrderError, match=r"open_orders\.json"):
        read_orders(path)


@pytest.mark.parametrize(
    ("right", "strike", "expected"),
    [
        (Right.PUT, "pct:-5", "wheel-2026-11-16-P-pct-5"),
        (Right.PUT, "155", "wheel-2026-11-16-P-155"),
        (Right.CALL, "152.5", "wheel-2026-11-16-C-152.5"),
        (Right.CALL, "152.25", "wheel-2026-11-16-C-152.25"),
    ],
)
def test_ld_19_a_wheel_orders_id_names_its_session_right_and_strike(
    right: Right, strike: str, expected: str
) -> None:
    assert order_id(date(2026, 11, 16), right, strike) == expected


@pytest.mark.parametrize(
    ("strike", "token"), [("155", "155"), ("152.5", "152.5"), ("152.25", "152.25")]
)
def test_l_o1_a_strike_is_written_as_a_plain_number(strike: str, token: str) -> None:
    assert strike_token(Price.from_dollars(strike)) == token
    assert parse_orders([_with(OPTION_LIMIT, strike=token)])[0].strike == token


def test_ld_12_the_committed_order_file_is_valid() -> None:
    read_orders(ROOT / "open_orders.json")


@pytest.mark.parametrize(
    ("base", "field"),
    [
        (SHARES_MARKET, "lmt_prc"),
        (SHARES_MARKET, "expiry"),
        (SHARES_MARKET, "strike"),
        (OPTION_LIMIT, "ref"),
    ],
)
def test_linv_01_a_null_field_is_rejected_not_read_as_absent(
    base: dict[str, Any], field: str
) -> None:
    error = _rejected(_with(base, **{field: None}))

    assert f"{field} is null" in str(error)


def test_linv_01_a_date_expiry_before_the_orders_session_is_rejected() -> None:
    error = _rejected(_with(OPTION_LIMIT, expiry="2026-11-13"))

    assert "before the session" in str(error)


def test_linv_01_a_date_expiry_on_the_orders_session_is_valid() -> None:
    (order,) = parse_orders([_with(OPTION_LIMIT, expiry="2026-11-16")])

    assert order.expiry == "2026-11-16"


def test_l2_01_a_file_that_is_not_utf8_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "open_orders.json"
    path.write_bytes("[]".encode("utf-16"))  # PowerShell 5.1's default

    with pytest.raises(OrderError, match="UTF-8"):
        read_orders(path)


def test_l2_01_a_directory_where_the_file_belongs_is_an_error(tmp_path: Path) -> None:
    path = tmp_path / "open_orders.json"
    path.mkdir()

    with pytest.raises(OrderError, match=r"open_orders\.json"):
        read_orders(path)


# ---- LD-29: a put's strike as its distance from the close -------------------------------------


@pytest.mark.parametrize(
    ("strike", "close", "step", "token"),
    [
        ("155", "162.83", 1, "pct:-5"),  # Monday Nov 16's put: -4.81%
        ("150", "162.83", 1, "pct:-8"),  # -7.88%
        ("170", "162.83", 1, "pct:4"),  # 4.40%
        ("162.83", "162.83", 1, "pct:0"),
        ("155", "162.83", 2, "pct:-4"),  # to a multiple of L-O1's pct_step
    ],
)
def test_ld_29_a_strike_is_written_as_its_whole_percent_from_the_close(
    strike: str, close: str, step: int, token: str
) -> None:
    assert pct_token(Price.from_dollars(strike), Price.from_dollars(close), step) == token
    assert parse_orders([_with(OPTION_LIMIT, strike=token)])[0].strike == token


def _sanji_resolves(token: str, ref: Decimal, strikes: list[Decimal]) -> Decimal:
    """The order page's `pct:X`: ref × (1 + X/100), then the nearest listed strike; a put's tie
    goes further out of the money (down)."""
    target = ref * (1 + Decimal(token.removeprefix("pct:")) / 100)
    return min(strikes, key=lambda k: (abs(k - target), k))


def _ladder(close: Decimal) -> tuple[Decimal, list[Decimal]]:
    """Strikes at least 1.5% of the close apart, in $0.50s (NVDA's $2.50 at $162.83 is 1.54%)."""
    step = (close * Decimal("0.015") / Decimal("0.50")).to_integral_value(ROUND_CEILING)
    step *= Decimal("0.50")
    atm = (close / step).to_integral_value() * step
    return step, [atm + step * k for k in range(-12, 13) if atm + step * k > 0]


@settings(max_examples=300)
@given(
    close=st.decimals(min_value=Decimal("20"), max_value=Decimal("600"), places=2),
    steps=st.integers(min_value=1, max_value=8),
)
def test_ld_29_an_unchanged_open_resolves_to_the_strike_picked(close: Decimal, steps: int) -> None:
    """A whole percent moves Sanji's target at most half a percent of the close, under half a step
    on a ladder over 1% apart: when the stock opens where it closed, it lands on the picked
    strike, for any close and any out-of-the-money strike."""
    step, strikes = _ladder(close)
    picked = min(strikes, key=lambda k: abs(k - close)) - step * steps
    assume(0 < picked < close)
    token = pct_token(Price.from_dollars(picked), Price.from_dollars(close))

    assert _sanji_resolves(token, close, strikes) == picked


def test_ld_29_a_gap_at_the_open_moves_the_strike_with_the_stock() -> None:
    """Monday Nov 16's `pct:-5`: at Friday's close it's $155; a 6% gap down moves it to $145,
    still 5% below the stock, where a strike sent as `155` would be at the money."""
    close = Decimal("162.83")
    strikes = [Decimal(k) for k in range(130, 150, 5)] + [
        Decimal(150) + Decimal("2.5") * k for k in range(13)
    ]
    token = pct_token(Price.from_dollars("155"), Price.from_dollars(close))

    assert _sanji_resolves(token, close, strikes) == Decimal("155")
    assert _sanji_resolves(token, close * Decimal("0.94"), strikes) == Decimal("145")
    assert _sanji_resolves(token, close * Decimal("1.06"), strikes) == Decimal("165")
