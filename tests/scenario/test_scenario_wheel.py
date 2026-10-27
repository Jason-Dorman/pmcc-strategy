"""The wheel end to end on scripted synthetic markets (W2-02): every rule fires where it should.

Weeks as in `tests/fixtures/synthetic/scenarios.py`: week 1 is Mon Aug 31 to Fri Sep 4 2026, week 2
Tue Sep 8 (Labor Day) to Fri Sep 11, week 3 Sep 14 to 18. Spot sits at $100 unless a scenario
moves it; weeklies trade at 40% IV with a 4% spread, so the entry trigger passes on the first bar.
The engine checks WINV-01 to 03 and 05 to 09 on every bar and event, and raises if one fails, so
every scenario that returns has held them.
"""

from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, time
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

import pytest

from pmcc.accounting.events import Event
from pmcc.config.strategy import FillModel
from pmcc.config.universe import Window, read_universe_file
from pmcc.domain.clock import ET
from pmcc.domain.errors import EngineError
from pmcc.domain.instruments import OptionId, Right, Side
from pmcc.domain.money import Money, Price
from pmcc.domain.rules import RuleId
from pmcc.engine.invariants import InvariantViolation
from pmcc.wheel import engine
from pmcc.wheel.book import WheelState
from pmcc.wheel.config import WHEEL_PATH, WheelConfig, WheelRunConfig, load_wheel
from pmcc.wheel.engine import WheelRun, run_wheel
from tests.fixtures.synthetic.market import Cell, IvSurface, SpotPath, SyntheticSpec, knot
from tests.fixtures.synthetic.store import SyntheticMarkets

MON, FRI = date(2026, 8, 31), date(2026, 9, 4)
WEEK2_OPEN, WEEK2_END = date(2026, 9, 8), date(2026, 9, 11)
WEEK3_OPEN, WEEK3_END = date(2026, 9, 14), date(2026, 9, 18)
CASH = Money.from_dollars(25_000)
BASE = SyntheticSpec(MON, WEEK2_END, spot=100.0, iv=IvSurface(weekly=0.40, monthly=0.20))


def _at(day: date, hour: int) -> datetime:
    return datetime.combine(day, time(hour), tzinfo=ET)


def _path(*knots: tuple[datetime, float]) -> SpotPath:
    return SpotPath((knot(MON, 10, 100.0), *knots))


def _run(synthetic: SyntheticMarkets, name: str, build: Callable[[], SyntheticSpec], *,
         cash: Money = CASH, wheel: WheelConfig | None = None,
         start: date | None = None) -> WheelRun:  # fmt: skip
    """The wheel (the shipped one, or `wheel`) with `cash`, over the market's window or from
    `start`."""
    loaded = synthetic.get(f"wheel_{name}", build)
    spec = loaded.market.spec
    funded = (wheel or load_wheel()).model_copy(update={"starting_cash": cash})
    window = Window(start=start or spec.window_start, end=spec.window_end)
    rate = read_universe_file().risk_free_rate
    return run_wheel(loaded.data, WheelRunConfig(wheel=funded, window=window, risk_free_rate=rate))


def _variant(tmp_path: Path, *changes: tuple[str, str]) -> WheelConfig:
    """The shipped wheel.yaml with each (old, new) text replaced, through the real loader."""
    text = WHEEL_PATH.read_text(encoding="utf-8")
    for old, new in changes:
        assert old in text
        text = text.replace(old, new)
    path = tmp_path / "wheel.yaml"
    path.write_text(text, encoding="utf-8", newline="\n")
    return load_wheel(path)


def _rows(run: WheelRun) -> list[tuple[str, str, str]]:
    """Each blotter row as (rule, side, instrument kind)."""

    def kind(e: Event) -> str:
        return e.instrument.right.name if isinstance(e.instrument, OptionId) else "STOCK"

    return [(e.rule_id, e.side.value, kind(e)) for e in run.blotter]


def _option(e: Event) -> OptionId:
    assert isinstance(e.instrument, OptionId)
    return e.instrument


def quiet() -> SyntheticSpec:
    return replace(BASE, path=_path())


def assigned_then_called() -> SyntheticSpec:
    """Week 1 falls to $92 by Friday's close: the put is assigned. Week 2 opens at $92, below the
    cost basis, so the call is floored there; spot rallies to $110 and the shares are called."""
    knots = (knot(MON, 16, 100.0), knot(FRI, 16, 92.0), knot(WEEK2_OPEN, 10, 92.0),
             knot(WEEK2_END, 16, 110.0))  # fmt: skip
    return replace(BASE, path=_path(*knots))


def assigned_then_collapse() -> SyntheticSpec:
    """Assigned at Friday's $75 close, and spot stays there for two weeks: no call at or above the
    cost basis has a quote, so no call is sold (W-C3)."""
    return replace(BASE, window_end=WEEK3_END,
                   path=_path(knot(MON, 16, 100.0), knot(FRI, 16, 75.0)))  # fmt: skip


def _wide_puts(day: date, *, first_bar_only: bool = False) -> Callable[..., tuple[Cell, Cell]]:
    def hook(option: OptionId, t: datetime, bid: Cell, ask: Cell) -> tuple[Cell, Cell]:
        hit = t.date() == day and option.right is Right.PUT
        if hit and (not first_bar_only or t == _at(day, 10)) and bid and ask:
            mid = (bid + ask) / 2
            return round(mid * 0.8, 2), round(mid * 1.2, 2)  # 40% of mid
        return bid, ask

    return hook


def wide_monday() -> SyntheticSpec:
    return replace(BASE, path=_path(), quote_hook=_wide_puts(MON))


def wide_first_bar() -> SyntheticSpec:
    return replace(BASE, path=_path(), quote_hook=_wide_puts(MON, first_bar_only=True))


# --- The put ----------------------------------------------------------------------------------


def test_w_p1_x1_a_quiet_market_sells_a_put_each_week_and_lets_it_expire(
    synthetic: SyntheticMarkets,
) -> None:
    run = _run(synthetic, "quiet", quiet)

    assert _rows(run) == [("W-P1", "SELL", "PUT"), ("W-X1", "EXPIRE", "PUT")] * 2
    sales = [e for e in run.blotter if e.side is Side.SELL]
    assert [e.time for e in sales] == [_at(MON, 10), _at(WEEK2_OPEN, 10)]
    assert all(_option(e).strike < Price.from_dollars(100) for e in sales)  # out of the money
    assert [(g.outcome, g.rule_id) for g in run.gate_log] == [("sold", "W-P1")] * 2
    assert run.book.cash == CASH + sum((e.cash_delta for e in sales), Money.zero())


def test_w_p3_picks_the_put_nearest_minus_030_delta(synthetic: SyntheticMarkets) -> None:
    sale = _run(synthetic, "quiet", quiet).blotter[0]
    delta = sale.audit["delta"]
    assert isinstance(delta, float)
    assert abs(delta + 0.30) < 0.1
    assert sale.fill == sale.limit  # at mid (WD-23)


def test_w_p4_reserves_the_strike_while_the_put_is_open(synthetic: SyntheticMarkets) -> None:
    run = _run(synthetic, "quiet", quiet)
    put = _option(run.blotter[0])
    row = next(r for r in run.ledger if r.time == _at(MON, 12))
    assert row.state is WheelState.PUT
    assert row.reserved == put.strike.notional(100, 1)
    assert row.free_cash == row.cash - row.reserved
    assert row.put is not None
    assert row.put.option == put


def test_w_p4_skips_every_week_cash_cant_secure(synthetic: SyntheticMarkets) -> None:
    run = _run(synthetic, "quiet", quiet, cash=Money.from_dollars(5_000))

    assert run.blotter == ()
    assert [(g.outcome, g.rule_id) for g in run.gate_log] == [("skipped", "W-P4")] * 2
    assert run.book.cash == Money.from_dollars(5_000)


def test_w_t1_a_monday_with_no_liquid_put_is_skipped(synthetic: SyntheticMarkets) -> None:
    run = _run(synthetic, "wide_monday", wide_monday)

    assert run.gate_log[0].outcome == "skipped"
    assert run.gate_log[0].rule_id == "W-T1"
    assert run.gate_log[1].outcome == "sold"
    assert run.blotter[0].time == _at(WEEK2_OPEN, 10)


def test_w_t1_sells_on_the_first_bar_that_passes(synthetic: SyntheticMarkets) -> None:
    run = _run(synthetic, "wide_first_bar", wide_first_bar)
    assert run.blotter[0].time == _at(MON, 11)


# --- Assignment and the call ------------------------------------------------------------------


def test_w_x2_c1_x4_assigned_then_called_away(synthetic: SyntheticMarkets) -> None:
    run = _run(synthetic, "assigned_then_called", assigned_then_called)

    assert _rows(run) == [
        ("W-P1", "SELL", "PUT"),
        ("W-X2", "ASSIGN", "PUT"),
        ("W-X2", "BUY", "STOCK"),
        ("W-C1", "SELL", "CALL"),
        ("W-X4", "ASSIGN", "CALL"),
        ("W-X4", "SELL", "STOCK"),
    ]
    put_sale, _, buy, call_sale, _, sell = run.blotter
    put, call = _option(put_sale), _option(call_sale)
    assert (buy.qty, buy.fill, buy.time) == (100, put.strike, _at(FRI, 16))
    assert (sell.qty, sell.fill, sell.time) == (100, call.strike, _at(WEEK2_END, 16))
    assert run.book.state is WheelState.CASH
    expected = CASH + put_sale.cash_delta + call_sale.cash_delta + buy.cash_delta + sell.cash_delta
    assert run.book.cash == expected


def test_w_x2_cost_basis_is_the_strike_less_the_credits(synthetic: SyntheticMarkets) -> None:
    run = _run(synthetic, "assigned_then_called", assigned_then_called)
    put_sale, _, _, call_sale, _, _ = run.blotter
    strike = _option(put_sale).strike
    after_assignment = next(r for r in run.ledger if r.time == _at(FRI, 16))
    basis = Fraction(strike.notional(100, 1).units - put_sale.cash_delta.units, 100)
    assert after_assignment.cost_basis == Price(round(basis))
    after_call = next(r for r in run.ledger if r.time == call_sale.time)
    lower = Fraction(call_sale.cash_delta.units, 100)
    assert after_call.cost_basis == Price(round(basis - lower))


def test_w_c3_the_call_is_floored_at_the_cost_basis(synthetic: SyntheticMarkets) -> None:
    run = _run(synthetic, "assigned_then_called", assigned_then_called)
    _, _, _, call_sale, _, _ = run.blotter
    call = _option(call_sale)
    basis = next(r for r in run.ledger if r.time == _at(FRI, 16)).cost_basis
    assert basis is not None
    assert call.strike >= basis
    delta = call_sale.audit["delta"]
    assert isinstance(delta, float)
    assert delta < 0.30  # the floor, not the delta, set the strike
    assert call_sale.audit["basis_floor"] == str(basis.to_dollars())


def test_w_c3_no_call_at_or_above_the_basis_skips_the_week(synthetic: SyntheticMarkets) -> None:
    run = _run(synthetic, "assigned_then_collapse", assigned_then_collapse)

    assert [e.rule_id for e in run.blotter] == ["W-P1", "W-X2", "W-X2"]
    assert [(g.state, g.outcome, g.rule_id) for g in run.gate_log] == [
        (WheelState.CASH, "sold", "W-P1"),
        (WheelState.SHARES, "skipped", "W-C3"),
        (WheelState.SHARES, "skipped", "W-C3"),
    ]
    last = run.ledger[-1]
    assert (last.state, last.shares, last.call) == (WheelState.SHARES, 100, None)
    assert last.stock_mark is not None
    assert last.nav == last.cash + last.stock_mark.notional(1, 100)  # W-X5: marked, not sold


# --- Expiry at the strike ---------------------------------------------------------------------


def _put_strike(synthetic: SyntheticMarkets) -> float:
    return float(_option(_run(synthetic, "quiet", quiet).blotter[0]).strike.to_dollars())


def test_wd_15_a_put_closing_at_its_strike_expires(synthetic: SyntheticMarkets) -> None:
    strike = _put_strike(synthetic)

    def at_strike() -> SyntheticSpec:
        return replace(BASE, path=_path(knot(MON, 16, 100.0), knot(FRI, 16, strike)))

    run = _run(synthetic, "at_strike", at_strike)
    assert _rows(run)[:2] == [("W-P1", "SELL", "PUT"), ("W-X1", "EXPIRE", "PUT")]


def test_wd_15_a_put_closing_a_cent_below_is_assigned(synthetic: SyntheticMarkets) -> None:
    strike = _put_strike(synthetic)

    def a_cent_below() -> SyntheticSpec:
        return replace(BASE, path=_path(knot(MON, 16, 100.0), knot(FRI, 16, strike - 0.01)))

    run = _run(synthetic, "a_cent_below", a_cent_below)
    assert _rows(run)[1:3] == [("W-X2", "ASSIGN", "PUT"), ("W-X2", "BUY", "STOCK")]


# --- Calendar ---------------------------------------------------------------------------------


def test_w_p2_a_holiday_week_expires_on_thursday(synthetic: SyntheticMarkets) -> None:
    def independence_day() -> SyntheticSpec:
        return replace(BASE, window_start=date(2026, 6, 29), window_end=date(2026, 7, 10),
                       path=None)  # fmt: skip

    run = _run(synthetic, "independence_day", independence_day)
    first = _option(run.blotter[0])
    assert first.expiry == date(2026, 7, 2)
    settled = run.blotter[1]
    assert settled.time == _at(date(2026, 7, 2), 16)


def test_w_ledger_has_a_row_per_session_bar(synthetic: SyntheticMarkets) -> None:
    run = _run(synthetic, "quiet", quiet)
    assert len(run.ledger) == 9 * 7  # 5 + 4 sessions (Labor Day), 7 bars each
    assert [r.time for r in run.ledger] == sorted(r.time for r in run.ledger)


def test_w_random_walk_holds_every_invariant(synthetic: SyntheticMarkets) -> None:
    def walk() -> SyntheticSpec:
        return replace(BASE, window_end=date(2026, 9, 25), seed=11, hole_rate=0.05)

    run = _run(synthetic, "walk", walk)
    # Every option expires at its week's close, so each week opens holding cash or shares, and
    # gets exactly one gate-log row: sold, or skipped with its reason.
    assert [g.session for g in run.gate_log] == [MON, WEEK2_OPEN, WEEK3_OPEN, date(2026, 9, 21)]
    assert all(r.state in (WheelState.CASH, WheelState.SHARES) for r in run.ledger
               if r.time.hour == 16 and r.time.weekday() == 4)  # fmt: skip
    for sale in (e for e in run.blotter if e.side is Side.SELL and e.rule_id == "W-C1"):
        floor = sale.audit["basis_floor"]
        assert isinstance(floor, str)
        assert _option(sale).strike >= Price.from_dollars(Decimal(floor))


# --- Review fixes: calls that expire, the running basis, skips, marks, sizing ------------------


def assigned_then_flat() -> SyntheticSpec:
    """Assigned at Friday's $96.50 close; spot stays there for two weeks, so each week's call (at or
    above the cost basis, above spot) expires out of the money (W-X3)."""
    return replace(BASE, window_end=WEEK3_END,
                   path=_path(knot(MON, 16, 100.0), knot(FRI, 16, 96.5)))  # fmt: skip


def _wide_calls_on(day: date) -> Callable[..., tuple[Cell, Cell]]:
    def hook(option: OptionId, t: datetime, bid: Cell, ask: Cell) -> tuple[Cell, Cell]:
        if t.date() == day and option.right is Right.CALL and bid and ask:
            mid = (bid + ask) / 2
            return round(mid * 0.8, 2), round(mid * 1.2, 2)  # 40% of mid
        return bid, ask

    return hook


def wide_calls_week2() -> SyntheticSpec:
    return replace(assigned_then_flat(), quote_hook=_wide_calls_on(WEEK2_OPEN))


def unquoted_close() -> SyntheticSpec:
    """Assigned at Friday's $96.50 close, on a bar where the stock trades but has no quote."""

    def stock(t: datetime, spot: float) -> tuple[Cell, Cell, Cell]:
        if t == _at(FRI, 16):
            return None, None, spot
        return round(spot - 0.01, 2), round(spot + 0.01, 2), spot

    return replace(assigned_then_flat(), window_end=WEEK2_END, stock_hook=stock)


def tradeless_expiry() -> SyntheticSpec:
    """The stock never trades on Friday, the put's expiry: there is no closing trade."""

    def stock(t: datetime, spot: float) -> tuple[Cell, Cell, Cell]:
        bid, ask = round(spot - 0.01, 2), round(spot + 0.01, 2)
        return bid, ask, (None if t.date() == FRI else spot)

    return replace(BASE, path=_path(), stock_hook=stock)


def falls_after_open() -> SyntheticSpec:
    return replace(BASE, path=_path(knot(MON, 11, 96.0)))


def test_w_x3_a_call_expiring_out_of_the_money_keeps_the_shares(
    synthetic: SyntheticMarkets,
) -> None:
    run = _run(synthetic, "assigned_then_flat", assigned_then_flat)

    assert _rows(run) == [
        ("W-P1", "SELL", "PUT"),
        ("W-X2", "ASSIGN", "PUT"),
        ("W-X2", "BUY", "STOCK"),
        ("W-C1", "SELL", "CALL"),
        ("W-X3", "EXPIRE", "CALL"),
        ("W-C1", "SELL", "CALL"),
        ("W-X3", "EXPIRE", "CALL"),
    ]
    assert run.book.state is WheelState.SHARES
    assert run.book.shares == 100


def test_w_c3_the_basis_falls_by_every_call_credit(synthetic: SyntheticMarkets) -> None:
    run = _run(synthetic, "assigned_then_flat", assigned_then_flat)
    put_sale, _, _, call1, _, call2, _ = run.blotter
    strike = _option(put_sale).strike.notional(100, 1).units
    expected = Fraction(strike - put_sale.cash_delta.units, 100)
    for call in (call1, call2):
        floor = call.audit["basis_floor"]  # the basis before this call
        assert floor == str(Price(round(expected)).to_dollars())
        assert _option(call).strike >= Price(round(expected))
        expected -= Fraction(call.cash_delta.units, 100)
        row = next(r for r in run.ledger if r.time == call.time)
        assert row.cost_basis == Price(round(expected))


def test_w_t1_a_shares_week_with_only_wide_calls_is_skipped_under_w_t1(
    synthetic: SyntheticMarkets,
) -> None:
    run = _run(synthetic, "wide_calls_week2", wide_calls_week2)
    week2 = next(g for g in run.gate_log if g.session == WEEK2_OPEN)
    assert (week2.state, week2.outcome, week2.rule_id) == (WheelState.SHARES, "skipped", "W-T1")
    week3 = next(g for g in run.gate_log if g.session == WEEK3_OPEN)
    assert (week3.outcome, week3.rule_id) == ("sold", "W-C1")


def test_wd_25_assigned_shares_with_no_quote_are_marked_at_the_close_and_flagged(
    synthetic: SyntheticMarkets,
) -> None:
    run = _run(synthetic, "unquoted_close", unquoted_close)
    assigned = next(r for r in run.ledger if r.time == _at(FRI, 16))
    assert assigned.stock_mark == Price.from_dollars("96.50")  # the close, not the strike
    assert "stale_stock" in assigned.flags
    assert assigned.nav == assigned.cash + Price.from_dollars("96.50").notional(1, 100)
    reopen = next(r for r in run.ledger if r.time == _at(WEEK2_OPEN, 10))
    assert "stale_stock" not in reopen.flags


def test_wd_15_an_expiry_session_without_a_trade_stops_the_run(
    synthetic: SyntheticMarkets,
) -> None:
    with pytest.raises(EngineError, match="no closing trade") as raised:
        _run(synthetic, "tradeless_expiry", tradeless_expiry)
    assert "X-S4" not in str(raised.value)


def test_w_p1_a_window_starting_mid_week_sells_at_the_next_weeks_open(
    synthetic: SyntheticMarkets,
) -> None:
    run = _run(synthetic, "quiet", quiet, start=date(2026, 9, 2))
    assert [g.session for g in run.gate_log] == [WEEK2_OPEN]
    assert run.blotter[0].time == _at(WEEK2_OPEN, 10)


def test_w_p4_a_put_refused_on_one_bar_can_sell_on_a_later_one(
    synthetic: SyntheticMarkets,
) -> None:
    put_10 = _option(_run(synthetic, "falls_after_open", falls_after_open).blotter[0]).strike
    # Enough cash for a put struck $2 lower, not for the 10:00 one, credit counted.
    tight = put_10.notional(100, 1) - Money.from_dollars(200)
    run = _run(synthetic, "falls_after_open", falls_after_open, cash=tight)

    sale = run.blotter[0]
    assert sale.time > _at(MON, 10)
    assert _option(sale).strike < put_10
    assert (run.gate_log[0].outcome, run.gate_log[0].rule_id) == ("sold", "W-P1")


def test_w_p4_fees_and_two_contracts_secure_and_cost_the_whole_position(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    wheel = _variant(tmp_path, ("params: {contracts: 1}", "params: {contracts: 2}"),
                     ("fee_per_contract: 0.00", "fee_per_contract: 0.65"))  # fmt: skip
    run = _run(synthetic, "assigned_then_flat", assigned_then_flat,
               cash=Money.from_dollars(50_000), wheel=wheel)  # fmt: skip
    put_sale, _, buy, call1, *_ = run.blotter
    assert (put_sale.qty, put_sale.fee, buy.qty, call1.qty) == (
        2,
        Money.from_dollars("1.30"),
        200,
        2,
    )
    strike = _option(put_sale).strike.notional(100, 2).units
    basis = Fraction(strike - put_sale.cash_delta.units, 200)  # net of the fee
    after = next(r for r in run.ledger if r.time == _at(FRI, 16))
    assert after.cost_basis == Price(round(basis))
    row = next(r for r in run.ledger if r.time == call1.time)
    assert row.cost_basis == Price(round(basis - Fraction(call1.cash_delta.units, 200)))


def test_w_p4_two_contracts_need_twice_the_cash(
    synthetic: SyntheticMarkets, tmp_path: Path
) -> None:
    wheel = _variant(tmp_path, ("params: {contracts: 1}", "params: {contracts: 2}"))
    run = _run(synthetic, "quiet", quiet, cash=Money.from_dollars(15_000), wheel=wheel)
    assert run.blotter == ()
    assert {g.rule_id for g in run.gate_log} == {"W-P4"}


# --- The engine's own guards ------------------------------------------------------------------


def test_winv_03_a_fill_off_the_fill_model_stops_the_run(
    synthetic: SyntheticMarkets, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = engine.fill
    other = FillModel(spread_capture=0.5, fee_per_contract=Money.zero())

    def off_model(**kwargs: Any) -> Event | None:
        kwargs["model"] = other
        return real(**kwargs)

    monkeypatch.setattr(engine, "fill", off_model)
    with pytest.raises(InvariantViolation, match="INV-03"):
        _run(synthetic, "quiet", quiet)


def test_winv_09_a_row_under_a_rule_the_config_lacks_stops_the_run(
    synthetic: SyntheticMarkets, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(engine, "W_P1", RuleId("E-S1"))
    with pytest.raises(InvariantViolation, match="INV-09"):
        _run(synthetic, "quiet", quiet)


def test_winv_every_bar_is_checked(
    synthetic: SyntheticMarkets, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[datetime] = []
    real = engine.check_bar

    def spy(now: datetime, *args: Any) -> None:
        calls.append(now)
        real(now, *args)

    monkeypatch.setattr(engine, "check_bar", spy)
    run = _run(synthetic, "quiet", quiet)
    assert calls == [r.time for r in run.ledger]


def test_w_run_refuses_a_market_priced_at_another_rate(
    synthetic: SyntheticMarkets, monkeypatch: pytest.MonkeyPatch
) -> None:
    loaded = synthetic.get("wheel_quiet", quiet)
    monkeypatch.setattr(loaded.data, "rate", 0.05)  # its IVs and Greeks would be r = 5%'s
    with pytest.raises(EngineError, match="priced at r"):
        _run(synthetic, "quiet", quiet)
