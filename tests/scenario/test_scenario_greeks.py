"""What the engine records for the Greek attribution (P6-04; DEC-24, DEC-27, DEC-63): each bar's
spot, each held leg's IV and Greeks, and the IV every option fill was at, all exactly as the chain
priced the bar. Two markets, each with A5's hold to the Friday check: the quant PMCC on
`random_walk`, whose short expires (X-S4), and the baseline on `late_friday_surge`, whose short is
assigned (X-S5) and its stock sold and covered."""

import math
from collections.abc import Callable
from pathlib import Path

import pytest

from pmcc.accounting.ledger import NO_GREEKS, LegGreeks
from pmcc.domain.instruments import OptionId, Side
from pmcc.engine.loop import RunOutput
from pmcc.strategy.ports import MarketView
from tests.fixtures.synthetic.market import SyntheticSpec
from tests.fixtures.synthetic.scenarios import BUILDERS, random_walk
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario.harness import BASELINE, NO_TAKE_PROFIT, QUANT, run

MARKETS: dict[str, tuple[Callable[[], SyntheticSpec], str]] = {
    "random_walk": (random_walk, QUANT),
    "late_friday_surge": (BUILDERS["late_friday_surge"], BASELINE),
}


def _run(synthetic: SyntheticMarkets, tmp_path: Path, name: str) -> RunOutput:
    build, strategy = MARKETS[name]
    return run(synthetic, tmp_path, name, build, overrides=NO_TAKE_PROFIT, strategy=strategy)


def _priced(view: MarketView, option: OptionId) -> LegGreeks:
    """The chain's row, written out here rather than through `leg_greeks`."""
    chain = view.chain(option.expiry, option.right)
    row = chain.row(option.strike)
    assert row is not None
    q = chain.quotes
    values = [float(v[row]) for v in (q.iv, q.delta, q.gamma, q.theta, q.vega)]
    return LegGreeks(*(None if math.isnan(v) else v for v in values))


@pytest.mark.parametrize("name", MARKETS)
def test_p6_04_the_ledger_records_the_bars_spot_and_each_legs_greeks(
    synthetic: SyntheticMarkets, tmp_path: Path, name: str
) -> None:
    out = _run(synthetic, tmp_path, name)
    data = synthetic.get(name, MARKETS[name][0]).data
    priced = 0
    for row in out.ledger:
        view = data.view(row.time)
        assert row.spot == view.spot()
        for leg in (row.long, row.short):
            if leg is None:
                continue
            if leg.stale:
                assert leg.greeks == NO_GREEKS
                continue
            assert leg.greeks == _priced(view, leg.option)
            priced += 1
    assert priced > 50


@pytest.mark.parametrize("name", MARKETS)
def test_p6_04_every_option_fill_records_the_iv_it_filled_at(
    synthetic: SyntheticMarkets, tmp_path: Path, name: str
) -> None:
    out = _run(synthetic, tmp_path, name)
    data = synthetic.get(name, MARKETS[name][0]).data
    fills = [e for e in out.blotter if e.is_option and e.side in (Side.BUY, Side.SELL)]
    for event in fills:
        assert isinstance(event.instrument, OptionId)
        expected = _priced(data.view(event.time), event.instrument).iv
        assert event.audit["fill_iv"] == expected
    assert {e.side for e in fills} == {Side.BUY, Side.SELL}


@pytest.mark.parametrize(("name", "side"), [("random_walk", Side.EXPIRE),
                                            ("late_friday_surge", Side.ASSIGN)])  # fmt: skip
def test_p6_04_an_expiry_an_assignment_and_stock_rows_carry_no_fill_iv(
    synthetic: SyntheticMarkets, tmp_path: Path, name: str, side: Side
) -> None:
    """X-S4 and X-S5 have no fill, and the stock X-S5 sells and covers is no option."""
    out = _run(synthetic, tmp_path, name)
    unfilled = [e for e in out.blotter if e.side is side]
    stock = [e for e in out.blotter if not e.is_option]

    assert unfilled
    assert all("fill_iv" not in e.audit for e in unfilled)
    assert len(stock) == (2 if side is Side.ASSIGN else 0)  # sold at the strike, then covered
    assert all("fill_iv" not in e.audit for e in stock)
