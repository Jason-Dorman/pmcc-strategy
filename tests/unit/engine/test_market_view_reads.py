"""MarketView's accessors, point-in-time listing (PO, DEC-32) and session-bar reads (P3-02)."""

from datetime import date, datetime, time
from pathlib import Path

import pytest

from pmcc.data.load import load_symbol
from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.engine.market_view import MarketData
from pmcc.pricing.iv import IvCode
from pmcc.strategy.ports import ExpiryKind
from tests.fixtures.synthetic.market import Cell, SyntheticSpec, generate

RATE = 0.0371
WEEKLY = date(2026, 9, 11)
LATE_MONTHLY = date(2027, 1, 15)
STRIKE = Price.from_dollars(105)
GAPPY = Price.from_dollars(104)  # listed from the start, then no row at all on Sep 3 14:00
NO_TRADE = datetime(2026, 9, 2, 11, tzinfo=ET)
PRE_MARKET = datetime(2026, 9, 1, 9, tzinfo=ET)  # the 08:00-09:00 bar: not a session bar
POST_CLOSE = datetime(2026, 9, 1, 17, tzinfo=ET)


def at(day: int, hour: int) -> datetime:
    return datetime.combine(date(2026, 9, day), time(hour), tzinfo=ET)


def _quote_hook(option: OptionId, t: datetime, bid: Cell, ask: Cell) -> tuple[Cell, Cell] | None:
    if option.expiry == WEEKLY and option.strike == GAPPY and t == at(3, 14):
        return None  # a listed contract with no row on one bar
    if option.expiry == WEEKLY and option.strike == STRIKE:
        if t in (PRE_MARKET, POST_CLOSE):
            return bid, ask  # valid, but outside the session: doesn't list it
        if t < at(1, 10):
            return None  # no row yet
        if t < at(2, 12) or at(3, 10) <= t <= at(3, 16):
            return 0.0, ask  # a row, but a zero bid: no valid quote
    if option.expiry == LATE_MONTHLY and t < at(4, 13):
        return None  # the whole expiry lists on Fri Sep 4 at 13:00
    return bid, ask


def _stock_hook(t: datetime, spot: float) -> tuple[Cell, Cell, Cell]:
    if t == NO_TRADE:
        return None, None, None
    return round(spot - 0.01, 2), round(spot + 0.01, 2), spot


SPEC = SyntheticSpec(
    date(2026, 8, 31),
    date(2026, 9, 11),
    seed=3,
    quote_hook=_quote_hook,
    stock_hook=_stock_hook,
    extended_hours=True,
)


@pytest.fixture(scope="module")
def data(tmp_path_factory: pytest.TempPathFactory) -> MarketData:
    root: Path = tmp_path_factory.mktemp("view")
    written = generate(SPEC, root)
    loaded = load_symbol(root, SPEC.symbol, written.calendar)
    return MarketData.build(loaded.stock, loaded.chains, loaded.calendar, RATE, SPEC.symbol)


def _strikes(data: MarketData, t: datetime) -> list[Price]:
    return list(data.view(t).chain(WEEKLY, Right.CALL).strikes())


def test_dec_32_a_strike_is_hidden_before_its_first_valid_quote(data: MarketData) -> None:
    assert STRIKE not in _strikes(data, at(1, 15))  # rows with a zero bid: not listed yet
    assert STRIKE not in _strikes(data, at(2, 11))
    assert STRIKE in _strikes(data, at(2, 12))  # its first valid quote


def test_dec_32_a_listed_strike_stays_listed_without_a_quote(data: MarketData) -> None:
    view = data.view(at(3, 14))
    chain = view.chain(WEEKLY, Right.CALL)
    row = chain.row(STRIKE)
    assert row is not None
    assert not chain.quotes.valid[row]
    assert view.quote(OptionId(SPEC.symbol, WEEKLY, Right.CALL, STRIKE)) is None


def test_dec_32_an_expiry_is_listed_from_its_first_quote(data: MarketData) -> None:
    assert LATE_MONTHLY not in data.view(at(4, 12)).expiries(ExpiryKind.MONTHLY)
    assert LATE_MONTHLY in data.view(at(4, 13)).expiries(ExpiryKind.MONTHLY)
    assert data.view(at(4, 12)).chain(LATE_MONTHLY, Right.CALL).size == 0


def test_dec_32_an_earlier_read_sees_the_earlier_listing(data: MarketData) -> None:
    view = data.view(at(4, 15))
    assert STRIKE not in view.chain(WEEKLY, Right.CALL, at(2, 11)).strikes()
    assert LATE_MONTHLY not in view.expiries(ExpiryKind.MONTHLY, at(4, 12))


def test_expiries_split_weekly_and_monthly(data: MarketData) -> None:
    view = data.view(at(11, 10))
    weekly = view.expiries(ExpiryKind.WEEKLY)
    monthly = view.expiries(ExpiryKind.MONTHLY)
    assert weekly[0] == WEEKLY  # Sep 4's has expired
    assert date(2026, 9, 18) in weekly  # the third Friday is a weekly too
    assert date(2026, 9, 18) in monthly
    assert WEEKLY not in monthly
    assert list(weekly) == sorted(weekly)


def test_quote_is_the_bars_bid_and_ask(data: MarketData) -> None:
    view = data.view(at(8, 13))  # Tue: Labor Day moved the week's open
    option = OptionId(SPEC.symbol, WEEKLY, Right.CALL, STRIKE)
    quote = view.quote(option)
    assert quote is not None
    chain = view.chain(WEEKLY, Right.CALL)
    row = chain.row(STRIKE)
    assert row is not None
    assert quote.bid.units == chain.quotes.bid[row]
    assert quote.ask.units == chain.quotes.ask[row]


def test_quote_refuses_another_root(data: MarketData) -> None:
    with pytest.raises(ValueError, match="option root"):
        data.view(at(8, 13)).quote(OptionId("OTHER", WEEKLY, Right.CALL, STRIKE))


def test_spot_is_none_when_the_stock_did_not_trade(data: MarketData) -> None:
    view = data.view(at(2, 15))
    assert view.spot(NO_TRADE) is None
    assert view.stock_quote(NO_TRADE) is None
    assert view.spot(at(2, 12)) is not None
    assert view.stock_quote(at(2, 12)) is not None


def test_close_trades_hold_only_closes_at_or_before_now(data: MarketData) -> None:
    mid_session = data.view(at(3, 12)).close_trades()
    assert at(2, 16) in mid_session
    assert at(3, 16) not in mid_session
    assert at(3, 16) in data.view(at(3, 16)).close_trades()
    assert all(t.time() == time(16) for t in mid_session)


def test_a_time_that_is_not_a_session_bar_reads_nothing(data: MarketData) -> None:
    view = data.view(at(8, 16))
    for t in (datetime(2026, 9, 7, 12, tzinfo=ET), datetime(2026, 9, 8, 9, 30, tzinfo=ET)):
        assert view.spot(t) is None
        assert view.chain(WEEKLY, Right.CALL, t).size == 0


def test_chain_snapshots_are_shared_between_views(data: MarketData) -> None:
    first = data.view(at(8, 14)).chain(WEEKLY, Right.CALL)
    again = data.view(at(9, 10)).chain(WEEKLY, Right.CALL, at(8, 14))
    assert first is again


def test_the_calendar_answers_for_future_days(data: MarketData) -> None:
    view = data.view(at(1, 10))
    assert view.calendar().week_open(date(2026, 9, 8)).day == date(2026, 9, 8)


def test_dec_32_a_listed_strike_with_no_row_on_a_bar_stays_in_the_chain(data: MarketData) -> None:
    chain = data.view(at(3, 14)).chain(WEEKLY, Right.CALL)
    row = chain.row(GAPPY)
    assert row is not None  # still listed, though the bar has no row for it
    assert not chain.quotes.valid[row]
    assert chain.quotes.code[row] == IvCode.NO_QUOTE
    assert data.view(at(3, 14)).quote(OptionId(SPEC.symbol, WEEKLY, Right.CALL, GAPPY)) is None
    assert list(chain.strikes()) == sorted(chain.strikes())


def test_dec_06_extended_hours_quotes_never_list_a_contract(data: MarketData) -> None:
    """The strike has valid quotes pre-market and post-close on Sep 1, but only zero bids in the
    session until Sep 2 12:00: it lists then, not before."""
    assert STRIKE not in _strikes(data, at(1, 16))
    assert STRIKE not in _strikes(data, at(2, 11))
    assert STRIKE in _strikes(data, at(2, 12))


def test_dec_06_extended_hours_bars_give_no_spot_quote_or_chain(data: MarketData) -> None:
    view = data.view(at(2, 10))
    for t in (PRE_MARKET, POST_CLOSE):
        assert view.spot(t) is None
        assert view.stock_quote(t) is None
        assert view.chain(WEEKLY, Right.CALL, t).size == 0
    assert view.spot(at(1, 10)) is not None


def test_close_trades_are_the_close_bars_trades(data: MarketData) -> None:
    view = data.view(at(3, 12))
    closes = view.close_trades()
    for day in (1, 2):
        assert closes[at(day, 16)] == view.spot(at(day, 16))
    assert view.spot(at(1, 15)) != view.spot(at(1, 16))  # so the wrong bar would be caught
