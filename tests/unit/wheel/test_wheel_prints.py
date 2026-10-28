"""The fill evidence's pairs (W3-02): each sold option's prints against its mids, from its sale
bar through its expiry session, rounded as a fill at mid is."""

from datetime import date, datetime
from typing import Any, cast

import polars as pl

from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.wheel.analytics import fill_evidence
from pmcc.wheel.market import PrintPairs, WheelMarket, print_pairs

FRI = date(2026, 9, 4)
PUT = OptionId("SYN", FRI, Right.PUT, Price.from_dollars(98))


def _at(day: int, hour: int) -> datetime:
    return datetime(2026, 9, day, hour, tzinfo=ET)


def _market(rows: list[tuple[datetime, int, int, int | None, bool, bool, int]]) -> WheelMarket:
    """A market holding only the Sep 4 puts: (bar_end, BID, ASK, TRDPRC_1, session_bar,
    valid_quote, strike_cents)."""
    frame = pl.DataFrame(
        rows, orient="row",
        schema={"bar_end": pl.Datetime("us", "America/New_York"), "BID": pl.Int64,
                "ASK": pl.Int64, "TRDPRC_1": pl.Int64, "session_bar": pl.Boolean,
                "valid_quote": pl.Boolean, "strike_cents": pl.Int64},
    )  # fmt: skip
    none = cast(Any, None)
    return WheelMarket("SYN", none, "", none, {(FRI, Right.PUT): frame})


def test_w3_02_pairs_run_from_the_sale_bar_to_the_expiry_and_round_half_even() -> None:
    k = PUT.strike_cents
    market = _market([
        (_at(1, 15), 10_000, 10_200, 10_100, True, True, k),   # before the sale: out
        (_at(2, 10), 10_000, 10_101, 10_050, True, True, k),   # the sale bar: mid 10050.5 → 10050
        (_at(2, 11), 10_000, 10_103, 10_200, True, True, k),   # mid 10051.5 → 10052; above the ask
        (_at(2, 12), 10_000, 10_200, None, True, True, k),     # no print: out
        (_at(2, 13), 0, 10_200, 10_100, True, False, k),       # no valid quote: out
        (_at(2, 18), 10_000, 10_200, 10_100, False, True, k),  # not a session bar: out
        (_at(3, 10), 10_000, 10_200, 10_100, True, True, k + 250),  # another strike: out
        (_at(4, 16), 9_000, 9_000, 9_000, True, True, k),      # a locked quote at expiry: in
    ])  # fmt: skip

    pairs = print_pairs(market, [(PUT, _at(2, 10))])

    assert pairs[Right.CALL] == PrintPairs()
    assert pairs[Right.PUT] == PrintPairs(
        mid=(10_050, 10_052, 9_000),
        trade=(10_050, 10_200, 9_000),
        spread=(101, 103, 0),
        within=(True, False, True),
    )


def test_w3_02_the_evidence_counts_prints_inside_the_quote_and_skips_locked_ones_in_the_gap() -> (
    None
):
    pairs = {Right.PUT: PrintPairs(mid=(10_050, 10_052, 9_000), trade=(10_050, 10_200, 9_000),
                                   spread=(101, 103, 0), within=(True, False, True))}  # fmt: skip

    evidence = fill_evidence(pairs, contracts=1)

    puts, calls = evidence.groups
    assert (puts.group, calls.group) == ("puts", "calls")
    assert puts.within_spread == 2 / 3
    assert (calls.within_spread, calls.fit, calls.points.mid) == (None, None, ())
    assert puts.fit is not None
    assert (puts.fit.n, puts.fit.locked) == (3, 1)
    assert evidence.fit == puts.fit
    assert evidence.within_spread == puts.within_spread
