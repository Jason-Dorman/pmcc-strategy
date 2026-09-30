"""INV-04: no decision reads data stamped after its decision time (Spec › Invariant tests).

Every MarketView accessor raises `LookAheadError` for a time after `now`, and no answer at `now`
depends on data after it: a view over the whole market answers exactly as a view over the market
cut off at `now` does.
"""

import math
from collections.abc import Callable
from datetime import date, datetime, timedelta

import numpy as np
import numpy.typing as npt
import polars as pl
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pmcc.data.load import SymbolData, load_symbol
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from pmcc.engine.market_view import HistoricalView, MarketData
from pmcc.strategy.ports import ExpiryKind, LookAheadError
from tests.fixtures.synthetic.market import Market, SyntheticSpec, generate

RATE = 0.0371
SPEC = SyntheticSpec(date(2026, 8, 31), date(2026, 9, 18), seed=11, hole_rate=0.1)
CUTS = 5  # views cut off at this many times across the window


class Cut(tuple[HistoricalView, HistoricalView, Market]):
    """(the whole market's view, the cut-off market's view, the market), with a short repr for
    hypothesis's reports."""

    def __repr__(self) -> str:
        return f"Cut(now={self[0].now.isoformat()})"


@pytest.fixture(scope="module")
def market(tmp_path_factory: pytest.TempPathFactory) -> tuple[Market, SymbolData]:
    root = tmp_path_factory.mktemp("inv04")
    written = generate(SPEC, root)
    return written, load_symbol(root, SPEC.symbol, written.calendar)


def _data(loaded: SymbolData, until: datetime | None = None) -> MarketData:
    def cut(frame: pl.DataFrame) -> pl.DataFrame:
        return frame if until is None else frame.filter(pl.col("bar_end") <= until)

    chains = {key: cut(frame) for key, frame in loaded.chains.items()}
    return MarketData.build(cut(loaded.stock), chains, loaded.calendar, RATE, SPEC.symbol)


@pytest.fixture(scope="module")
def views(
    market: tuple[Market, SymbolData],
) -> list[Cut]:
    """(the whole market's view, the cut-off market's view) at CUTS times in the window."""
    written, loaded = market
    whole = _data(loaded)
    window = [t for t in written.bar_ends if t.date() >= SPEC.window_start]
    step = len(window) // CUTS
    cuts = [window[i * step + 3] for i in range(CUTS)]
    return [Cut((whole.view(t), _data(loaded, t).view(t), written)) for t in cuts]


type Read = Callable[[HistoricalView, datetime | None], object]


def _reads(expiry: date, right: Right, strike: Price) -> dict[str, Read]:
    option = OptionId(SPEC.symbol, expiry, right, strike)
    return {
        "spot": lambda v, at: v.spot(at),
        "stock_quote": lambda v, at: v.stock_quote(at),
        "quote": lambda v, at: v.quote(option, at),
        "chain": lambda v, at: _chain_rows(v, expiry, right, at),
        "expiries_weekly": lambda v, at: v.expiries(ExpiryKind.WEEKLY, at),
        "expiries_monthly": lambda v, at: v.expiries(ExpiryKind.MONTHLY, at),
        "close_trades": lambda v, at: dict(v.close_trades(at)),
    }


def _chain_rows(view: HistoricalView, expiry: date, right: Right, at: datetime | None) -> object:
    chain = view.chain(expiry, right, at)
    q = chain.quotes
    return (chain.bar_end, q.strike.tolist(), q.bid.tolist(), q.ask.tolist(), q.valid.tolist(),
            q.code.tolist(), _floats(q.iv), _floats(q.delta))  # fmt: skip


def _floats(values: npt.NDArray[np.float64]) -> list[float | None]:
    """Comparable: NaN (unknown) as None, since NaN never equals itself."""
    return [None if math.isnan(v) else round(v, 12) for v in values.tolist()]


def _some_contract(view: HistoricalView) -> tuple[date, Right, Price]:
    expiry = view.expiries(ExpiryKind.WEEKLY)[0]
    chain = view.chain(expiry, Right.CALL)
    return expiry, Right.CALL, chain.strike(chain.size // 2)


ACCESSORS = ("spot", "stock_quote", "quote", "chain", "expiries_weekly", "expiries_monthly",
             "close_trades")  # fmt: skip


@pytest.mark.parametrize("name", ACCESSORS)
def test_inv_04_every_accessor_raises_after_now(views: list[Cut], name: str) -> None:
    view = views[1][0]
    read = _reads(*_some_contract(view))[name]
    for later in (view.now + timedelta(microseconds=1), view.now + timedelta(hours=1)):
        with pytest.raises(LookAheadError, match="INV-04"):
            read(view, later)


def test_inv_04_a_naive_time_is_refused(
    views: list[Cut],
) -> None:
    view = views[0][0]
    with pytest.raises(ValueError, match="naive"):
        view.spot(view.now.replace(tzinfo=None))


@given(data=st.data())
def test_inv_04_no_answer_depends_on_data_after_now(views: list[Cut], data: st.DataObject) -> None:
    whole, cut, written = data.draw(st.sampled_from(views))
    earlier = [t for t in written.bar_ends if t <= whole.now]
    at = data.draw(st.sampled_from([None, *earlier[-40:]]))
    expiries = whole.expiries(ExpiryKind.WEEKLY) + whole.expiries(ExpiryKind.MONTHLY)
    expiry = data.draw(st.sampled_from(expiries))
    right = data.draw(st.sampled_from([Right.CALL, Right.PUT]))
    strike = Price.from_dollars(data.draw(st.integers(min_value=60, max_value=140)))
    for name, read in _reads(expiry, right, strike).items():
        assert read(whole, at) == read(cut, at), name


@given(data=st.data())
def test_inv_04_no_returned_row_is_after_now(views: list[Cut], data: st.DataObject) -> None:
    view, _, _ = data.draw(st.sampled_from(views))
    for end in view.close_trades():
        assert end <= view.now
    for kind in ExpiryKind:
        for expiry in view.expiries(kind):
            assert expiry >= view.now.date()
            assert view.chain(expiry, Right.CALL).size > 0  # listed: it has a listed call
    chain = view.chain(view.expiries(ExpiryKind.WEEKLY)[0], Right.CALL)
    assert chain.bar_end <= view.now


def test_inv_04_views_share_the_market_but_not_the_clock(
    market: tuple[Market, SymbolData],
) -> None:
    written, loaded = market
    data = _data(loaded)
    early, late = written.bar_ends[-60], written.bar_ends[-1]
    assert data.view(early).spot() == Price.from_dollars(written.spot_at(early))
    with pytest.raises(LookAheadError):
        data.view(early).spot(late)
    assert data.view(late).spot(early) == data.view(early).spot()


def test_inv_04_holds_with_no_chains(market: tuple[Market, SymbolData]) -> None:
    """A view over a market with no chains still gates every read."""
    written, loaded = market
    data = MarketData.build(loaded.stock, {}, loaded.calendar, RATE, SPEC.symbol)
    view = data.view(written.bar_ends[-1])
    assert view.expiries(ExpiryKind.WEEKLY) == ()
    with pytest.raises(LookAheadError):
        view.close_trades(view.now + timedelta(hours=1))
