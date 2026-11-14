"""The close snapshot the live wheel decides from (LIVE-SPEC › Data; LD-11; L1-02).

One night's LSEG pull: the last completed session's close, and every put and call within 10% of
it for the expiry of the next session's week, each with its bid and ask at the close. A strike
LSEG doesn't list comes back unlisted, never as an error.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from itertools import pairwise

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.config.universe import Underlying
from pmcc.data.fetch import Retry
from pmcc.data.ric import RicForm, build_ric
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.live.snapshot import (
    CloseSnapshot,
    OptionQuote,
    SnapshotError,
    describe,
    last_completed,
    next_session,
    snapshot_report,
    strike_ladder,
    take_snapshot,
)
from tests.fakes.lseg import FakeLseg, fake_provider

NVDA = Underlying(symbol="NVDA", stock_ric="NVDA.O", option_root="NVDA")
FRIDAY_NIGHT = datetime(2026, 11, 13, 22, 0, tzinfo=ET)
EXPIRY = date(2026, 11, 20)
# Fri Nov 13 2026 is EST (UTC-5): bars starting 14:00, 15:00 (the close bar) and 16:00 ET.
INDEX = (datetime(2026, 11, 13, 19), datetime(2026, 11, 13, 20), datetime(2026, 11, 13, 21))
NO_WAIT = Retry(sleep=lambda _: None)


@pytest.fixture(scope="module")
def calendar() -> SessionCalendar:
    return load_calendar()


def _ric(right: Right, strike: str) -> str:
    return build_ric(OptionId("NVDA", EXPIRY, right, Price.from_dollars(strike)), RicForm.LIVE)


def _market(**extra: dict[str, list[float | None]]) -> FakeLseg:
    listed = {
        "NVDA.O": {"TRDPRC_1": [199.0, 200.0, 201.5]},
        _ric(Right.PUT, "195"): {"BID": [2.9, 3.0, None], "ASK": [3.1, 3.2, None]},
        _ric(Right.CALL, "205"): {"BID": [2.7, 2.9, None], "ASK": [2.9, 3.1, None]},
        _ric(Right.PUT, "190"): {"BID": [0.4, 0.0, None], "ASK": [0.5, 0.05, None]},
        _ric(Right.CALL, "210"): {"BID": [1.0], "ASK": [1.1]},
    }
    return FakeLseg(listed={**listed, **extra}, index=INDEX)


def _snapshot(calendar: SessionCalendar, fake: FakeLseg | None = None) -> CloseSnapshot:
    provider = fake_provider(fake if fake is not None else _market())
    return take_snapshot(provider, NVDA, calendar, FRIDAY_NIGHT, NO_WAIT)


def _quote(snapshot: CloseSnapshot, right: Right, strike: str) -> OptionQuote:
    wanted = Price.from_dollars(strike)
    return next(
        q for q in snapshot.options if q.option.right is right and q.option.strike == wanted
    )


def test_l_s1_friday_night_plans_monday_and_the_week_expires_friday(
    calendar: SessionCalendar,
) -> None:
    assert last_completed(calendar, FRIDAY_NIGHT).day == date(2026, 11, 13)
    assert next_session(calendar, FRIDAY_NIGHT).day == date(2026, 11, 16)


def test_l_s1_before_the_close_the_close_read_is_yesterdays_and_it_plans_today(
    calendar: SessionCalendar,
) -> None:
    friday_morning = datetime(2026, 11, 13, 10, 0, tzinfo=ET)

    assert last_completed(calendar, friday_morning).day == date(2026, 11, 12)
    assert next_session(calendar, friday_morning).day == date(2026, 11, 13)


def test_l_s1_a_monday_morning_run_plans_monday_not_tuesday(calendar: SessionCalendar) -> None:
    monday_morning = datetime(2026, 11, 16, 8, 0, tzinfo=ET)

    assert last_completed(calendar, monday_morning).day == date(2026, 11, 13)
    assert next_session(calendar, monday_morning).day == date(2026, 11, 16)


def test_l_p2_thanksgiving_week_expires_on_its_half_day_friday(
    calendar: SessionCalendar,
) -> None:
    wednesday_night = datetime(2026, 11, 25, 22, 0, tzinfo=ET)
    snapshot_day = next_session(calendar, wednesday_night)

    assert snapshot_day.day == date(2026, 11, 27)
    assert calendar.week_final(snapshot_day.day).day == date(2026, 11, 27)


def test_ld_11_the_ladder_spans_ten_percent_either_side_in_250_cent_steps() -> None:
    ladder = strike_ladder(Price.from_dollars("200"))

    assert ladder[0] == Price.from_dollars("180")
    assert ladder[-1] == Price.from_dollars("220")
    assert len(ladder) == 17
    assert all((b - a) == Price.from_dollars("2.5") for a, b in pairwise(ladder))


def test_ld_11_the_ladder_rounds_outwards_to_whole_steps() -> None:
    ladder = strike_ladder(Price.from_dollars("201.37"))

    assert ladder[0] == Price.from_dollars("180")  # 181.23 rounded down
    assert ladder[-1] == Price.from_dollars("222.5")  # 221.51 rounded up


def test_l1_02_the_close_is_the_close_bars_last_trade(calendar: SessionCalendar) -> None:
    snapshot = _snapshot(calendar)

    assert snapshot.close == Price.from_dollars("200")  # the 15:00 ET bar, not 16:00's 201.50
    assert snapshot.session.day == date(2026, 11, 13)
    assert snapshot.expiry == EXPIRY


def test_l1_02_every_ladder_strike_is_asked_as_a_put_and_a_call(calendar: SessionCalendar) -> None:
    snapshot = _snapshot(calendar)

    assert len(snapshot.options) == 34
    assert {q.option.expiry for q in snapshot.options} == {EXPIRY}


def test_l1_02_a_quote_at_the_close_is_read_from_the_close_bar(calendar: SessionCalendar) -> None:
    put = _quote(_snapshot(calendar), Right.PUT, "195")

    assert put.listed
    assert put.close is not None
    assert (put.close.bid, put.close.ask) == (Price.from_dollars("3.0"), Price.from_dollars("3.2"))
    assert put.close.valid


def test_l_t1_a_zero_bid_at_the_close_is_not_a_valid_quote(calendar: SessionCalendar) -> None:
    put = _quote(_snapshot(calendar), Right.PUT, "190")

    assert put.listed
    assert put.close is not None
    assert not put.close.valid


def test_l1_02_a_listed_contract_with_no_close_bar_has_no_close_quote(
    calendar: SessionCalendar,
) -> None:
    call = _quote(_snapshot(calendar), Right.CALL, "210")

    assert call.listed
    assert call.close is None


def test_l1_02_a_strike_lseg_does_not_list_comes_back_unlisted(calendar: SessionCalendar) -> None:
    put = _quote(_snapshot(calendar), Right.PUT, "182.5")

    assert not put.listed
    assert put.close is None


def test_l1_02_no_close_for_the_stock_stops_before_any_option_is_asked(
    calendar: SessionCalendar,
) -> None:
    fake = FakeLseg(listed={"NVDA.O": {"TRDPRC_1": [None, None, 201.5]}}, index=INDEX)

    with pytest.raises(SnapshotError, match="no close"):
        _snapshot(calendar, fake)

    assert all(r.universe == ("NVDA.O",) for r in fake.requests)


def test_l1_02_an_earlier_trade_never_stands_in_for_a_missing_close_bar(
    calendar: SessionCalendar,
) -> None:
    # The 14:00 ET bar traded, but the close bar (15:00-16:00 ET) isn't there yet.
    fake = FakeLseg(listed={"NVDA.O": {"TRDPRC_1": [199.0, None, None]}}, index=INDEX)

    with pytest.raises(SnapshotError, match="close bar"):
        _snapshot(calendar, fake)

    assert all(r.universe == ("NVDA.O",) for r in fake.requests)


def test_l1_02_the_report_is_json_with_counts_and_every_contract(
    calendar: SessionCalendar,
) -> None:
    report = json.loads(json.dumps(snapshot_report(_snapshot(calendar))))

    assert report["stock"] == {"ric": "NVDA.O", "close": "200.00"}
    assert report["expiry"] == "2026-11-20"
    assert report["next_session"] == "2026-11-16"
    assert report["counts"] == {
        "asked": 34,
        "listed": {"put": 2, "call": 2},
        "quoted_at_close": {"put": 1, "call": 1},
    }
    first = report["options"][0]
    assert set(first) == {"ric", "right", "strike", "listed", "bid", "ask", "last", "valid"}
    assert Decimal(first["strike"]) == Decimal("180.00")


def test_ld_15_the_summary_line_carries_counts_but_no_prices(calendar: SessionCalendar) -> None:
    text = describe(_snapshot(calendar))

    assert "2026-11-20" in text
    assert "listed 2 puts and 2 calls" in text
    assert "200" not in text
    assert "$" not in text.replace("$2.50", "")
