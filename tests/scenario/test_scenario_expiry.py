"""Holiday weeks, the half-day close, stale marks and INV-07 in full runs (TEST-STRATEGY §5)."""

from datetime import date, datetime
from pathlib import Path

from pmcc.domain.clock import ET
from pmcc.domain.instruments import OptionId, Side
from tests.fixtures.synthetic import scenarios as sc
from tests.fixtures.synthetic.store import SyntheticMarkets
from tests.scenario.harness import NO_TAKE_PROFIT, rows, run


def test_the_jul_3_week_expires_its_short_on_thursday(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "independence_day_week", sc.independence_day_week,
              overrides=NO_TAKE_PROFIT)  # fmt: skip
    sold = rows(out, "E-S1", Side.SELL)[0]
    assert isinstance(sold.instrument, OptionId)
    assert sold.instrument.expiry == date(2026, 7, 2)
    resolved = next(e for e in out.blotter if e.rule_id in ("X-S4", "X-S5"))
    assert resolved.time == datetime(2026, 7, 2, 16, tzinfo=ET)


def test_the_half_day_week_resolves_at_the_13_00_close(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "half_day_week", sc.half_day_week, overrides=NO_TAKE_PROFIT)
    sold = rows(out, "E-S1", Side.SELL)[0]
    assert isinstance(sold.instrument, OptionId)
    assert sold.instrument.expiry == date(2026, 11, 27)
    expired = rows(out, "X-S4", Side.EXPIRE)[0]
    assert expired.time == datetime(2026, 11, 27, 13, tzinfo=ET)
    assert not [r for r in out.ledger if r.time.date() == date(2026, 11, 27) and r.time.hour > 13]


def test_inv_07_no_short_is_open_after_its_expiry_session(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "random_walk", sc.random_walk)
    calendar = synthetic.get("random_walk", sc.random_walk).market.calendar
    shorts = [r for r in out.ledger if r.short is not None]
    assert shorts
    for row in shorts:
        assert row.short is not None
        assert row.time <= calendar.session(row.short.option.expiry).close_bar_end


def test_stale_long_marks_carry_the_last_mid_and_are_flagged(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "stale_long_marks", sc.stale_long_marks)
    wednesday = [r for r in out.ledger if r.time.date() == sc.WED]
    assert wednesday
    assert all("stale_long" in r.flags for r in wednesday)
    tuesday_close = next(r for r in out.ledger if r.time == datetime(2026, 9, 1, 16, tzinfo=ET))
    assert tuesday_close.long is not None
    assert all(r.long is not None and r.long.mark == tuesday_close.long.mark for r in wednesday)
    assert all(r.long is not None and r.long.delta is None for r in wednesday)
    thursday = next(r for r in out.ledger if r.time.date() == sc.THU)
    assert "stale_long" not in thursday.flags


def test_a_random_market_runs_clean_through_every_invariant(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    out = run(synthetic, tmp_path, "random_walk", sc.random_walk)
    assert len(out.ledger) == 4 * 7 * 5 - 7  # four weeks of bars, Labor Day closed
    for row in out.ledger:
        nav = row.cash
        if row.long is not None:
            nav += row.long.mark.notional(100, row.long.qty)
        if row.short is not None:
            nav -= row.short.mark.notional(100, row.short.qty)
        if row.stock is not None:
            nav += row.stock.mark.notional(1, row.stock.shares)
        assert row.nav == nav  # INV-02, from the published row alone
    assert out.ledger[-1].cash == out.book.cash
    assert out.blotter
