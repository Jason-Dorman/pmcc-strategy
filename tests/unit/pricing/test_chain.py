"""The chain pricer (P2-04; ARCHITECTURE §7): per-bar IV, Greeks and eligibility, the held-contract
rule (PO, DEC-27), and a whole symbol priced once and memoized per (bar, expiry, right).

Frames here have the loader's columns (`load_symbol`, ARCHITECTURE §6.5): prices are Int64
$0.0001 units, `bar_end` is ET, and `session_bar` and `valid_quote` are set.
"""

import math
from datetime import UTC, date, datetime, time

import numpy as np
import polars as pl
import pytest

from pmcc.config.calendar import load_calendar
from pmcc.domain.clock import ET
from pmcc.domain.instruments import Right
from pmcc.domain.money import Price
from pmcc.pricing.black_scholes import greeks
from pmcc.pricing.chain import PricedQuotes, price_quotes, price_symbol
from pmcc.pricing.expiry import years_to_expiry
from pmcc.pricing.iv import IvCode, implied_vol

CAL = load_calendar()
R = 0.0371
EXPIRY = date(2026, 11, 6)  # the Friday after the clock change on Sun Nov 1
ET_TYPE = pl.Datetime("us", "America/New_York")


def _u(dollars: float) -> int:
    return Price.from_dollars(dollars).units


def _one(
    strike: float, bid: float, ask: float, *, spot: float = 100.0, t: float = 0.1,
    call: bool = True, valid: bool = True,
) -> PricedQuotes:  # fmt: skip
    return price_quotes(
        strike=np.array([_u(strike)], dtype=np.int64),
        bid=np.array([_u(bid)], dtype=np.int64),
        ask=np.array([_u(ask)], dtype=np.int64),
        valid=np.array([valid]),
        spot=float(_u(spot)) if not math.isnan(spot) else math.nan,
        years=t,
        rate=R,
        is_call=call,
    )


# ---- one bar: price_quotes


def test_chain_prices_a_valid_quote_from_its_mid() -> None:
    got = _one(100, 2.00, 2.10)
    iv = implied_vol(2.05, 100.0, 100.0, 0.1, R, True)
    g = greeks(100.0, 100.0, 0.1, R, float(iv.vol.item()), True)

    assert got.code[0] == IvCode.OK
    assert got.eligible[0]
    assert got.mid[0] == pytest.approx(2.05)
    assert got.iv[0] == pytest.approx(float(iv.vol.item()), abs=1e-12)
    assert got.delta[0] == pytest.approx(float(g.delta.item()))
    assert got.gamma[0] == pytest.approx(float(g.gamma.item()))
    assert got.theta[0] == pytest.approx(float(g.theta.item()))
    assert got.vega[0] == pytest.approx(float(g.vega.item()))


def test_chain_iv_uses_the_exact_mid_not_the_rounded_one() -> None:
    got = _one(100, 2.0000, 2.0001)
    exact = implied_vol(2.00005, 100.0, 100.0, 0.1, R, True)
    rounded = implied_vol(2.0000, 100.0, 100.0, 0.1, R, True)  # Quote.mid rounds half-even

    assert got.mid[0] == 2.00005
    assert got.iv[0] == float(exact.vol.item())
    assert got.iv[0] != float(rounded.vol.item())


def test_chain_spread_is_a_share_of_mid() -> None:
    assert _one(100, 1.90, 2.10).spread_pct[0] == pytest.approx(0.10)


def test_chain_extrinsic_is_mid_less_intrinsic() -> None:
    # Spec › E-L3: extrinsic = mid - max(0, spot - strike)
    assert _one(80, 21.00, 21.20).extrinsic[0] == pytest.approx(1.10)
    assert _one(120, 0.40, 0.50).extrinsic[0] == pytest.approx(0.45)
    assert _one(120, 20.40, 20.60, call=False).extrinsic[0] == pytest.approx(0.50)


def test_chain_without_a_valid_quote_is_ineligible_and_unpriced() -> None:
    got = _one(100, 0.00, 2.10, valid=False)

    assert got.code[0] == IvCode.NO_QUOTE
    assert not got.eligible[0]
    for values in (got.mid, got.spread_pct, got.iv, got.delta, got.gamma, got.theta, got.vega,
                   got.extrinsic):  # fmt: skip
        assert math.isnan(values[0])


def test_chain_without_a_spot_is_ineligible() -> None:
    got = _one(100, 2.00, 2.10, spot=math.nan)

    assert got.code[0] == IvCode.NO_SPOT
    assert not got.eligible[0]
    assert math.isnan(got.delta[0])
    assert math.isnan(got.extrinsic[0])


def test_dec_27_a_call_below_the_floor_is_ineligible_but_keeps_deep_itm_greeks() -> None:
    k, t = 60.0, 0.4
    got = _one(k, 39.00, 39.10, t=t)  # the floor is 100 - 60·e^(-rT) ≈ 40.88

    assert got.code[0] == IvCode.BELOW_FLOOR
    assert not got.eligible[0]
    assert math.isnan(got.iv[0])
    assert got.delta[0] == 1.0
    assert got.gamma[0] == 0.0
    assert got.vega[0] == 0.0
    assert got.theta[0] == pytest.approx(-R * k * math.exp(-R * t))


def test_dec_27_a_put_below_the_floor_gets_no_greeks() -> None:
    # Only calls are ever held; a put's IV failure leaves its Greeks unknown.
    got = _one(140, 38.00, 38.10, call=False)

    assert got.code[0] == IvCode.BELOW_FLOOR
    assert math.isnan(got.delta[0])


def _no_greeks(got: PricedQuotes) -> bool:
    return all(math.isnan(g[0]) for g in (got.delta, got.gamma, got.theta, got.vega))


def test_dec_27_a_call_above_its_cap_gets_no_greeks() -> None:
    got = _one(90, 100.00, 100.10)  # a call can't be worth more than the stock

    assert got.code[0] == IvCode.ABOVE_CAP
    assert _no_greeks(got)


def test_dec_27_a_call_no_vol_can_price_gets_no_greeks() -> None:
    # $5 of extrinsic on an at-the-money call an hour from expiry: dearer than a 500% vol makes it.
    got = _one(100, 5.00, 5.10, t=1 / (365 * 24))

    assert got.code[0] == IvCode.NO_CONVERGENCE
    assert _no_greeks(got)


def test_dec_27_a_deep_itm_call_at_the_expiry_close_gets_no_greeks() -> None:
    got = _one(60, 39.00, 39.10, t=0.0)  # under its floor too, but expired outranks it

    assert got.code[0] == IvCode.EXPIRED
    assert _no_greeks(got)


def test_dec_27_a_call_with_no_spot_gets_no_greeks() -> None:
    got = _one(60, 39.00, 39.10, spot=math.nan)

    assert got.code[0] == IvCode.NO_SPOT
    assert _no_greeks(got)


def test_chain_at_finds_a_strikes_row() -> None:
    got = price_quotes(
        strike=np.array([_u(95), _u(100)], dtype=np.int64),
        bid=np.array([_u(5.6), _u(2.0)], dtype=np.int64),
        ask=np.array([_u(5.8), _u(2.1)], dtype=np.int64),
        valid=np.array([True, True]),
        spot=float(_u(100)),
        years=0.1,
        rate=R,
        is_call=True,
    )

    assert got.at(Price.from_dollars(100)) == 1
    assert got.at(Price.from_dollars(97.5)) is None


# ---- a whole symbol: price_symbol


def _et(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=ET)


def _stock(rows: list[tuple[datetime, float | None, bool]]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "bar_end": [r[0] for r in rows],
            "TRDPRC_1": [None if r[1] is None else _u(r[1]) for r in rows],
            "session_bar": [r[2] for r in rows],
        },
        schema={"bar_end": ET_TYPE, "TRDPRC_1": pl.Int64, "session_bar": pl.Boolean},
    )


def _chain(rows: list[tuple[datetime, float, float, float, bool]]) -> pl.DataFrame:
    """(bar_end, strike, bid, ask, session_bar); a bid of 0 makes the quote invalid."""
    return pl.DataFrame(
        {
            "bar_end": [r[0] for r in rows],
            "strike_cents": [round(r[1] * 100) for r in rows],
            "BID": [_u(r[2]) for r in rows],
            "ASK": [_u(r[3]) for r in rows],
            "valid_quote": [r[2] > 0 for r in rows],
            "session_bar": [r[4] for r in rows],
        },
        schema={"bar_end": ET_TYPE, "strike_cents": pl.Int64, "BID": pl.Int64, "ASK": pl.Int64,
                "valid_quote": pl.Boolean, "session_bar": pl.Boolean},
    )  # fmt: skip


FRI = date(2026, 10, 30)
MON = date(2026, 11, 2)
STOCK = _stock([
    (_et(FRI, 15), 100.0, True),
    (_et(FRI, 16), 101.0, True),
    (_et(FRI, 17), 250.0, False),  # the post-close stub: no session, never a spot
    (_et(MON, 10), None, True),  # no trade on this bar
    (_et(EXPIRY, 16), 103.0, True),
])  # fmt: skip
CALLS = _chain([
    (_et(FRI, 16), 105, 0.90, 1.00, True),
    (_et(FRI, 16), 100, 2.60, 2.70, True),
    (_et(FRI, 15), 100, 2.10, 2.20, True),
    (_et(FRI, 17), 100, 2.00, 2.90, False),
    (_et(MON, 10), 100, 2.40, 2.50, True),
    (_et(EXPIRY, 16), 100, 3.00, 3.10, True),
    (_et(EXPIRY, 16), 105, 0.00, 0.05, True),
])  # fmt: skip


def test_chain_snapshot_prices_the_bar_with_its_own_spot_and_time() -> None:
    priced = price_symbol(STOCK, {(EXPIRY, Right.CALL): CALLS}, CAL, R)
    now = _et(FRI, 16)
    t = years_to_expiry(now, CAL.session(EXPIRY))

    snap = priced.snapshot(now, EXPIRY, Right.CALL)
    want = price_quotes(
        strike=np.array([_u(100), _u(105)], dtype=np.int64),
        bid=np.array([_u(2.60), _u(0.90)], dtype=np.int64),
        ask=np.array([_u(2.70), _u(1.00)], dtype=np.int64),
        valid=np.array([True, True]),
        spot=float(_u(101)),
        years=t,
        rate=R,
        is_call=True,
    )

    assert snap is not None
    np.testing.assert_array_equal(snap.strike, want.strike)
    np.testing.assert_array_equal(snap.iv, want.iv)
    np.testing.assert_array_equal(snap.delta, want.delta)
    np.testing.assert_array_equal(snap.code, want.code)


def test_chain_time_to_expiry_counts_the_clock_change() -> None:
    priced = price_symbol(STOCK, {(EXPIRY, Right.CALL): CALLS}, CAL, R)
    now = _et(FRI, 15)

    snap = priced.snapshot(now, EXPIRY, Right.CALL)
    alone = price_quotes(
        strike=np.array([_u(100)], dtype=np.int64),
        bid=np.array([_u(2.10)], dtype=np.int64),
        ask=np.array([_u(2.20)], dtype=np.int64),
        valid=np.array([True]),
        spot=float(_u(100)),
        years=years_to_expiry(now, CAL.session(EXPIRY)),
        rate=R,
        is_call=True,
    )

    assert snap is not None
    assert snap.iv[0] == alone.iv[0]


def test_chain_a_bar_with_no_stock_trade_has_no_spot() -> None:
    priced = price_symbol(STOCK, {(EXPIRY, Right.CALL): CALLS}, CAL, R)

    snap = priced.snapshot(_et(MON, 10), EXPIRY, Right.CALL)

    assert snap is not None
    assert snap.code[0] == IvCode.NO_SPOT


def test_chain_prices_session_bars_only() -> None:
    priced = price_symbol(STOCK, {(EXPIRY, Right.CALL): CALLS}, CAL, R)

    assert priced.snapshot(_et(FRI, 17), EXPIRY, Right.CALL) is None


def test_chain_a_bar_or_unit_with_no_rows_has_no_snapshot() -> None:
    priced = price_symbol(STOCK, {(EXPIRY, Right.CALL): CALLS}, CAL, R)

    assert priced.snapshot(_et(FRI, 12), EXPIRY, Right.CALL) is None
    assert priced.snapshot(_et(FRI, 16), EXPIRY, Right.PUT) is None


def test_chain_the_expiry_close_bar_is_expired() -> None:
    priced = price_symbol(STOCK, {(EXPIRY, Right.CALL): CALLS}, CAL, R)

    snap = priced.snapshot(_et(EXPIRY, 16), EXPIRY, Right.CALL)

    assert snap is not None
    assert list(snap.code) == [IvCode.EXPIRED, IvCode.EXPIRED]


def test_chain_snapshots_are_memoized_per_bar_expiry_and_right() -> None:
    priced = price_symbol(STOCK, {(EXPIRY, Right.CALL): CALLS}, CAL, R)
    now = _et(FRI, 16)

    assert priced.snapshot(now, EXPIRY, Right.CALL) is priced.snapshot(now, EXPIRY, Right.CALL)


def test_chain_the_memo_keeps_rights_and_expiries_apart() -> None:
    later = date(2026, 11, 13)
    puts = _chain([(_et(FRI, 16), 95, 0.40, 0.50, True)])
    other = _chain([(_et(FRI, 16), 110, 1.10, 1.20, True)])
    chains = {(EXPIRY, Right.CALL): CALLS, (EXPIRY, Right.PUT): puts, (later, Right.CALL): other}
    priced = price_symbol(STOCK, chains, CAL, R)
    now = _et(FRI, 16)

    calls = priced.snapshot(now, EXPIRY, Right.CALL)
    same_bar_puts = priced.snapshot(now, EXPIRY, Right.PUT)
    same_bar_later = priced.snapshot(now, later, Right.CALL)

    assert calls is not None
    assert same_bar_puts is not None
    assert same_bar_later is not None
    assert list(calls.strike) == [_u(100), _u(105)]
    assert list(same_bar_puts.strike) == [_u(95)]
    assert list(same_bar_later.strike) == [_u(110)]


def test_chain_snapshot_finds_a_bar_given_in_any_zone() -> None:
    priced = price_symbol(STOCK, {(EXPIRY, Right.CALL): CALLS}, CAL, R)
    now = _et(FRI, 16)

    assert priced.snapshot(now.astimezone(UTC), EXPIRY, Right.CALL) is priced.snapshot(
        now, EXPIRY, Right.CALL
    )


def test_chain_snapshot_refuses_a_naive_time() -> None:
    # A naive time would be read in the machine's zone: Eastern on the PO's box, UTC in CI.
    priced = price_symbol(STOCK, {(EXPIRY, Right.CALL): CALLS}, CAL, R)

    with pytest.raises(ValueError, match="naive"):
        priced.snapshot(datetime(2026, 10, 30, 16), EXPIRY, Right.CALL)


def test_chain_an_option_bar_the_stock_tape_lacks_has_no_spot() -> None:
    # LSEG leaves out a bar with no values, and the loader doesn't fill it in.
    stock = STOCK.filter(pl.col("bar_end") != _et(FRI, 15))
    priced = price_symbol(stock, {(EXPIRY, Right.CALL): CALLS}, CAL, R)

    snap = priced.snapshot(_et(FRI, 15), EXPIRY, Right.CALL)

    assert snap is not None
    assert list(snap.code) == [IvCode.NO_SPOT]


def test_chain_counts_iv_outcomes_over_session_bars() -> None:
    priced = price_symbol(STOCK, {(EXPIRY, Right.CALL): CALLS}, CAL, R)

    counts = priced.codes(EXPIRY, Right.CALL)

    # Fri 15:00 and 16:00 (3 contracts) solve, Monday has no spot, and expiry's close has two
    # rows; the post-close stub isn't a session bar.
    assert counts == {IvCode.OK: 3, IvCode.NO_SPOT: 1, IvCode.EXPIRED: 2}
    assert priced.codes(EXPIRY, Right.PUT) == {}


def test_chain_an_empty_unit_prices_to_nothing() -> None:
    # NVDA's May 2027 unit is cached with no rows: it wasn't listed in the window (DEC-08).
    priced = price_symbol(STOCK, {(EXPIRY, Right.CALL): CALLS.clear()}, CAL, R)

    assert priced.codes(EXPIRY, Right.CALL) == {}
    assert priced.snapshot(_et(FRI, 16), EXPIRY, Right.CALL) is None


def test_chain_refuses_a_chain_expiry_the_calendar_doesnt_trade() -> None:
    with pytest.raises(ValueError, match="not a trading session"):
        price_symbol(STOCK, {(date(2026, 11, 7), Right.CALL): CALLS}, CAL, R)
