"""The synthetic market (P3-03): deterministic, in the cache format, one smoke test per builder."""

from datetime import date, datetime, time
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from pmcc.data.load import load_symbol
from pmcc.domain.clock import ET
from pmcc.domain.instruments import Right
from pmcc.engine.market_view import MarketData
from pmcc.strategy.ports import ExpiryKind
from tests.fixtures.synthetic import scenarios
from tests.fixtures.synthetic.market import Market, generate
from tests.fixtures.synthetic.store import SyntheticMarkets

RATE = 0.0371


def _files(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_same_seed_writes_identical_files(tmp_path: Path) -> None:
    spec = scenarios.random_walk(seed=21)
    generate(spec, tmp_path / "a")
    generate(spec, tmp_path / "b")
    first, second = _files(tmp_path / "a"), _files(tmp_path / "b")
    assert first.keys() == second.keys()
    assert first == second


def test_another_seed_writes_another_market(tmp_path: Path) -> None:
    a = generate(scenarios.random_walk(seed=1), tmp_path / "a")
    b = generate(scenarios.random_walk(seed=2), tmp_path / "b")
    assert a.spots.tolist() != b.spots.tolist()


def test_the_market_is_what_the_loader_reads(tmp_path: Path) -> None:
    written = generate(scenarios.random_walk(), tmp_path)
    loaded = load_symbol(tmp_path, "SYN", written.calendar)
    session = loaded.stock.filter(pl.col("session_bar"))
    assert session.height == len(written.bar_ends)
    assert session["valid_quote"].all()
    chain_units = {(u.expiry, u.right) for u in written.units if u.expiry is not None}
    assert set(loaded.chains) == chain_units


def test_the_warm_up_covers_rv20(tmp_path: Path) -> None:
    written = generate(scenarios.random_walk(), tmp_path)
    first = written.bar_ends[0].date()
    assert len(written.calendar.sessions(first, date(2026, 8, 28))) == 22


def _data(synthetic: SyntheticMarkets, name: str) -> MarketData:
    return synthetic.get(name, scenarios.BUILDERS[name]).data


def _market(synthetic: SyntheticMarkets, name: str) -> Market:
    return synthetic.get(name, scenarios.BUILDERS[name]).market


def _at(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=ET)


@pytest.mark.parametrize("name", sorted(scenarios.BUILDERS))
def test_every_builder_writes_a_loadable_market(synthetic: SyntheticMarkets, name: str) -> None:
    spec = synthetic.get(name, scenarios.BUILDERS[name]).market.spec
    data = _data(synthetic, name)
    view = data.view(_at(spec.window_start, 10) if spec.window_start.weekday() == 0 else
                     _at(spec.window_end, 16))  # fmt: skip
    assert view.spot() is not None
    assert view.expiries(ExpiryKind.MONTHLY)
    assert view.expiries(ExpiryKind.WEEKLY)


def test_quiet_is_flat(synthetic: SyntheticMarkets) -> None:
    written = _market(synthetic, "quiet")
    assert set(written.spots.tolist()) == {100.0}


def test_premium_collapse_falls_by_tuesday(synthetic: SyntheticMarkets) -> None:
    written = _market(synthetic, "premium_collapse")
    assert written.spot_at(_at(scenarios.MON, 16)) == 100.0
    assert written.spot_at(_at(scenarios.TUE, 16)) == 94.0
    assert written.spot_at(_at(scenarios.FRI, 16)) == 94.0


def test_rally_through_strike_reaches_108(synthetic: SyntheticMarkets) -> None:
    written = _market(synthetic, "rally_through_strike")
    assert written.spot_at(_at(scenarios.WED, 12)) == 108.0


def test_friday_within_buffer_sits_below_the_strike_at_check(synthetic: SyntheticMarkets) -> None:
    written = _market(synthetic, "friday_within_buffer")
    assert written.spot_at(_at(scenarios.THU, 16)) == 100.0
    assert written.spot_at(_at(scenarios.FRI, 15)) == 101.7


def test_late_friday_surge_jumps_on_the_close_bar(synthetic: SyntheticMarkets) -> None:
    written = _market(synthetic, "late_friday_surge")
    assert written.spot_at(_at(scenarios.FRI, 15)) == 100.0
    assert written.spot_at(_at(scenarios.FRI, 16)) == 104.0


def test_long_delta_drop_ends_week_1_at_70(synthetic: SyntheticMarkets) -> None:
    written = _market(synthetic, "long_delta_drop")
    assert written.spot_at(_at(scenarios.FRI, 16)) == 70.0
    assert written.spot_at(_at(scenarios.WEEK2_OPEN, 10)) == 70.0


def test_no_quote_monday_quotes_week_1_wide_all_monday(synthetic: SyntheticMarkets) -> None:
    data = _data(synthetic, "no_quote_monday")
    for hour in (10, 13, 16):
        chain = data.view(_at(scenarios.MON, hour)).chain(scenarios.WEEK1_EXPIRY, Right.CALL)
        assert (chain.quotes.spread_pct[chain.quotes.valid] > 0.1).all()  # fails E-T1
    tuesday = data.view(_at(scenarios.TUE, 10)).chain(scenarios.WEEK1_EXPIRY, Right.CALL)
    assert (tuesday.quotes.spread_pct[tuesday.quotes.valid] < 0.3).any()


def test_expensive_long_prices_monthlies_far_above_weeklies(synthetic: SyntheticMarkets) -> None:
    data = _data(synthetic, "expensive_long")
    view = data.view(_at(scenarios.MON, 10))
    monthly = view.chain(view.expiries(ExpiryKind.MONTHLY)[2], Right.CALL)
    weekly = view.chain(scenarios.WEEK1_EXPIRY, Right.CALL)
    assert np.median(monthly.quotes.iv[monthly.quotes.eligible]) > 0.7
    assert np.median(weekly.quotes.iv[weekly.quotes.eligible]) < 0.5


def test_entry_retry_quotes_monthlies_wide_on_monday_only(synthetic: SyntheticMarkets) -> None:
    data = _data(synthetic, "entry_retry")
    expiry = data.view(_at(scenarios.MON, 10)).expiries(ExpiryKind.MONTHLY)[3]
    monday = data.view(_at(scenarios.MON, 12)).chain(expiry, Right.CALL).quotes
    tuesday = data.view(_at(scenarios.TUE, 10)).chain(expiry, Right.CALL).quotes
    assert (monday.spread_pct[monday.valid] > 0.3).all()
    assert (tuesday.spread_pct[tuesday.valid] < 0.3).all()


def test_first_bar_wide_quotes_wide_on_the_first_bar_only(synthetic: SyntheticMarkets) -> None:
    data = _data(synthetic, "first_bar_wide")
    first = data.view(_at(scenarios.MON, 10)).chain(scenarios.WEEK1_EXPIRY, Right.CALL).quotes
    second = data.view(_at(scenarios.MON, 11)).chain(scenarios.WEEK1_EXPIRY, Right.CALL).quotes
    assert (first.spread_pct[first.valid] > 0.1).all()
    assert (second.spread_pct[second.valid] < 0.3).any()


def test_stale_long_marks_has_no_monthly_quote_on_wednesday(synthetic: SyntheticMarkets) -> None:
    data = _data(synthetic, "stale_long_marks")
    view = data.view(_at(scenarios.WED, 14))
    expiry = view.expiries(ExpiryKind.MONTHLY)[3]
    assert not view.chain(expiry, Right.CALL).quotes.valid.any()
    assert view.chain(expiry, Right.CALL, _at(scenarios.TUE, 16)).quotes.valid.any()


def test_half_day_week_ends_on_a_13_00_close(synthetic: SyntheticMarkets) -> None:
    written = _market(synthetic, "half_day_week")
    friday = written.calendar.session(date(2026, 11, 27))
    assert friday.is_half_day
    assert written.calendar.week_final(date(2026, 11, 23)).day == date(2026, 11, 27)
    assert _at(date(2026, 11, 27), 13) in written.bar_ends
    assert _at(date(2026, 11, 27), 14) not in written.bar_ends


def test_independence_day_week_expires_thursday(synthetic: SyntheticMarkets) -> None:
    data = _data(synthetic, "independence_day_week")
    assert data.view(_at(date(2026, 6, 29), 10)).expiries(ExpiryKind.WEEKLY)[0] == date(2026, 7, 2)


def test_event_week_bumps_only_the_front_week(synthetic: SyntheticMarkets) -> None:
    data = _data(synthetic, "event_week")
    view = data.view(_at(scenarios.MON, 10))
    front = view.chain(scenarios.WEEK1_EXPIRY, Right.CALL).quotes
    following = view.chain(date(2026, 9, 11), Right.CALL).quotes
    assert front.iv[front.eligible].mean() > 0.5
    assert following.iv[following.eligible].mean() < 0.45


def test_rv_above_iv_walks_at_60_vol_under_20_iv(tmp_path: Path) -> None:
    spec = scenarios.rv_above_iv()
    assert spec.vol == 0.60
    assert spec.iv.base == 0.20
    written = generate(spec, tmp_path)
    assert len(set(written.spots.tolist())) > 100


def test_tiny_premium_prices_the_0_30_delta_short_under_10c(synthetic: SyntheticMarkets) -> None:
    data = _data(synthetic, "tiny_premium")
    chain = data.view(_at(scenarios.MON, 10)).chain(scenarios.WEEK1_EXPIRY, Right.CALL).quotes
    otm = chain.eligible & (chain.strike > 100 * 10_000)
    nearest = np.flatnonzero(otm)[np.argmin(np.abs(chain.delta[otm] - 0.30))]
    assert chain.mid[nearest] < 0.10
