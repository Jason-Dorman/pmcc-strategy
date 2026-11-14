"""One night of the live wheel, end to end on a temporary repo (L2-03; LINV-01 to LINV-08).

Sanji's price file, the order file at the root and under `mkt/`, and the run log live in `tmp_path`;
the close snapshot is the Black-Scholes fake. LSEG is asked only through the snapshot source, and
only the night before a week's first session.
"""

import json
from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path
from typing import cast

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.data.provider import ProviderOutageError
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET
from pmcc.domain.money import Money, Price
from pmcc.live.book import Book, BookError, WheelState
from pmcc.live.config import LiveConfig, StrikeParams, load_live_config
from pmcc.live.orders import Order, parse_orders, read_orders, write_orders
from pmcc.live.run import LiveError, Night, decide, describe_night, run_night, sessions_for
from pmcc.live.snapshot import CloseSnapshot
from tests.fakes.live import sanji_root, snapshot

FRIDAY = date(2026, 11, 13)
MONDAY = date(2026, 11, 16)
FRIDAY_NIGHT = datetime(2026, 11, 13, 22, 0, tzinfo=ET)
MONDAY_NIGHT = datetime(2026, 11, 16, 22, 0, tzinfo=ET)


@pytest.fixture(scope="module")
def calendar() -> SessionCalendar:
    return load_calendar()


@pytest.fixture(scope="module")
def config() -> LiveConfig:
    return load_live_config()


class Source:
    """The snapshot source: counts the asks, and serves (or raises) what it's given."""

    def __init__(self, make: Callable[[], CloseSnapshot]) -> None:
        self._make = make
        self.asked = 0
        self.bands: list[StrikeParams] = []

    def __call__(self, band: StrikeParams) -> CloseSnapshot:
        self.asked += 1
        self.bands.append(band)
        return self._make()


def _night(
    root: Path,
    calendar: SessionCalendar,
    config: LiveConfig,
    now: datetime = FRIDAY_NIGHT,
    source: Source | None = None,
    *,
    dry_run: bool = False,
) -> Night:
    src = source if source is not None else Source(lambda: snapshot(calendar, session=FRIDAY))
    return run_night(root, now, calendar, config, src, dry_run=dry_run)


def _log(root: Path) -> list[dict[str, object]]:
    path = root / "live" / "runs.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _hand_order(day: date, ident: str = "test-hand") -> Order:
    (order,) = parse_orders(
        [
            {
                "id": ident,
                "for": day.isoformat(),
                "order_type": "lmt",
                "action": "BUY",
                "qty": 1,
                "underlying": 756733,
                "contract": "underlying",
                "lmt_prc": "1.00",
            }
        ]
    )
    return order


# --- Friday night: Monday's put ------------------------------------------------------------------


def test_l_o1_friday_night_sells_mondays_put(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    night = _night(sanji_root(tmp_path, FRIDAY), calendar, config)

    order = night.decision.order
    assert night.decision.rule == "L-O1"
    assert order is not None
    assert (order.for_, order.action, order.contract, order.qty) == (MONDAY, "SHT", "put", 1)
    assert (order.order_type, order.lmt_prc, order.ref) == ("lmt", "mid", "open")
    assert order.expiry == "2026-11-20"
    assert order.underlying == 4815747
    assert order.id == f"wheel-2026-11-16-P-{order.strike}"


def test_ld_04_the_same_file_is_written_at_the_root_and_under_mkt(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    night = _night(sanji_root(tmp_path, FRIDAY), calendar, config)

    root_file = (tmp_path / "open_orders.json").read_bytes()
    assert (tmp_path / "mkt" / "open_orders.json").read_bytes() == root_file
    assert read_orders(tmp_path / "open_orders.json") == night.orders


def test_l2_03_the_run_log_gets_one_row_with_the_pick_but_no_quotes(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    night = _night(sanji_root(tmp_path, FRIDAY), calendar, config)

    (row,) = _log(tmp_path)
    assert row["outcome"] == "order"
    assert row["rule"] == "L-O1"
    assert row["state"] == "cash"
    assert row["cash"] == "25000.00"
    assert row["next_session"] == "2026-11-16"
    assert row["order_id"] == night.decision.order.id  # type: ignore[union-attr]
    pick = cast(dict[str, object], row["pick"])
    assert set(pick) == {"contract", "strike", "expiry", "delta", "iv"}  # no bid, ask or mid


def test_l2_03_a_dry_run_writes_nothing(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    night = _night(sanji_root(tmp_path, FRIDAY), calendar, config, dry_run=True)

    assert night.decision.order is not None
    assert not (tmp_path / "open_orders.json").exists()
    assert not (tmp_path / "mkt").exists()
    assert _log(tmp_path) == []
    assert "dry run: nothing written" in describe_night(night, dry_run=True)


def test_linv_08_the_same_inputs_give_the_same_files(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    first = _night(sanji_root(tmp_path, FRIDAY), calendar, config, dry_run=True)
    second = _night(tmp_path, calendar, config, dry_run=True)

    assert first.orders == second.orders
    assert {**first.row, "run_at": None} == {**second.row, "run_at": None}


# --- Which nights ask LSEG ------------------------------------------------------------------------


def test_l_p1_monday_night_plans_tuesday_asks_lseg_nothing_and_keeps_mondays_order(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    friday = _night(sanji_root(tmp_path, FRIDAY), calendar, config)
    sanji_root(tmp_path, MONDAY, extra_days=[FRIDAY])
    source = Source(lambda: snapshot(calendar, session=MONDAY))

    night = _night(tmp_path, calendar, config, MONDAY_NIGHT, source)

    assert source.asked == 0
    assert night.decision.rule == "L-P1"
    assert night.decision.order is None
    assert night.orders == friday.orders  # LD-19: Monday's put stays all week


def test_ld_19_an_order_drops_once_its_week_has_ended(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    _night(sanji_root(tmp_path, FRIDAY), calendar, config)
    next_friday = date(2026, 11, 20)
    sanji_root(tmp_path, next_friday)
    source = Source(lambda: snapshot(calendar, session=next_friday))

    night = _night(tmp_path, calendar, config, datetime(2026, 11, 20, 22, 0, tzinfo=ET), source)

    (order,) = night.orders
    assert order.for_ == date(2026, 11, 23)
    assert order.expiry == "2026-11-27"  # Thanksgiving week: the half-day Friday


def test_ld_19_a_rerun_the_same_night_replaces_the_wheel_order(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    _night(sanji_root(tmp_path, FRIDAY), calendar, config)
    moved = Source(lambda: snapshot(calendar, session=FRIDAY, close="170.00"))

    night = _night(tmp_path, calendar, config, FRIDAY_NIGHT, moved)

    wheel = [o for o in night.orders if o.id.startswith("wheel-")]
    assert len(wheel) == 1
    assert wheel[0] == night.decision.order


def test_ld_19_an_order_placed_by_hand_is_kept_through_its_week(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    sanji_root(tmp_path, FRIDAY)
    hand = _hand_order(MONDAY)
    write_orders(tmp_path / "open_orders.json", (hand,))

    night = _night(tmp_path, calendar, config)

    assert night.orders[0] == hand
    assert len(night.orders) == 2


# --- Stop and fail (PO, LD-14) --------------------------------------------------------------------


def test_l_b1_a_stale_book_writes_no_order_and_logs_the_failure(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    sanji_root(tmp_path, date(2026, 11, 12))
    source = Source(lambda: snapshot(calendar, session=FRIDAY))

    with pytest.raises(BookError, match="L-B1"):
        _night(tmp_path, calendar, config, source=source)

    assert source.asked == 0
    assert not (tmp_path / "open_orders.json").exists()
    (row,) = _log(tmp_path)
    assert (row["outcome"], row["rule"]) == ("failed", "L-B1")


def test_l_b2_a_sanji_book_of_unknown_format_writes_no_order(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    sanji_root(tmp_path, FRIDAY)
    (tmp_path / "mkt").mkdir()
    (tmp_path / "mkt" / "positions.json").write_text("{}", encoding="utf-8")

    with pytest.raises(BookError, match="L-B2"):
        _night(tmp_path, calendar, config)

    assert not (tmp_path / "open_orders.json").exists()
    assert _log(tmp_path)[0]["rule"] == "L-B2"


def test_l_b2_a_bad_order_already_in_the_file_writes_no_order(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    sanji_root(tmp_path, FRIDAY)
    bad = b'[{"id": "x", "for": "next"}]\n'
    (tmp_path / "open_orders.json").write_bytes(bad)

    with pytest.raises(BookError, match="L-B2"):
        _night(tmp_path, calendar, config)

    assert (tmp_path / "open_orders.json").read_bytes() == bad


def test_ld_24_a_run_before_the_close_is_refused_and_writes_nothing(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    sanji_root(tmp_path, FRIDAY)

    with pytest.raises(LiveError, match="before today's close"):
        _night(tmp_path, calendar, config, datetime(2026, 11, 16, 15, 0, tzinfo=ET))

    assert _log(tmp_path) == []


def test_l_p3_an_lseg_outage_writes_no_order_and_logs_the_failure(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    def outage() -> CloseSnapshot:
        raise ProviderOutageError("the LSEG platform session did not open")

    with pytest.raises(ProviderOutageError):
        _night(sanji_root(tmp_path, FRIDAY), calendar, config, source=Source(outage))

    assert not (tmp_path / "open_orders.json").exists()
    (row,) = _log(tmp_path)
    assert (row["outcome"], row["rule"]) == ("failed", "L-P3")


# --- The rules that decline -----------------------------------------------------------------------


def test_l_p4_too_little_cash_sells_nothing(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    poor = _with_cash(config, "1000.00")

    night = _night(sanji_root(tmp_path, FRIDAY), calendar, poor)

    assert night.decision.rule == "L-P4"
    assert night.decision.order is None
    assert night.orders == ()


def test_l_t1_a_wide_spread_sells_nothing(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    wide = Source(lambda: snapshot(calendar, session=FRIDAY, spread=0.30))

    night = _night(sanji_root(tmp_path, FRIDAY), calendar, config, source=wide)

    assert night.decision.rule == "L-T1"
    assert night.orders == ()


def test_l_p2_no_put_listed_for_the_expiry_sells_nothing(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    empty = Source(lambda: replace(snapshot(calendar, session=FRIDAY), options=()))

    night = _night(sanji_root(tmp_path, FRIDAY), calendar, config, source=empty)

    assert night.decision.rule == "L-P2"


# --- The other states (decide alone: Sanji's book can't show them yet) ----------------------------


def test_l_c1_holding_shares_sells_a_call_at_or_above_the_cost_basis(
    calendar: SessionCalendar, config: LiveConfig
) -> None:
    book = Book(WheelState.SHARES, Money.from_dollars("9000"), cost_basis=Price.from_dollars("165"))
    source = Source(lambda: snapshot(calendar, session=FRIDAY))

    decision = decide(book, calendar.session(MONDAY), calendar, config, source)

    assert decision.rule == "L-O1"
    assert decision.order is not None
    assert decision.order.contract == "call"
    assert decision.pick is not None
    assert decision.pick.option.strike >= Price.from_dollars("165")


@pytest.mark.parametrize(("state", "rule"), [(WheelState.PUT, "L-P1"), (WheelState.CALL, "L-C1")])
def test_l_p1_and_l_c1_an_open_option_is_left_to_sanji(
    calendar: SessionCalendar, config: LiveConfig, state: WheelState, rule: str
) -> None:
    source = Source(lambda: snapshot(calendar, session=FRIDAY))
    book = Book(state, Money.from_dollars("25000"), cost_basis=Price.from_dollars("150"))

    decision = decide(book, calendar.session(MONDAY), calendar, config, source)

    assert (decision.rule, decision.order, source.asked) == (rule, None, 0)


def test_l_s1_a_weekend_run_plans_monday_from_fridays_close(calendar: SessionCalendar) -> None:
    last, upcoming = sessions_for(calendar, datetime(2026, 11, 15, 22, 0, tzinfo=ET))

    assert (last.day, upcoming.day) == (FRIDAY, MONDAY)


def _with_cash(config: LiveConfig, cash: str) -> LiveConfig:
    rules = tuple(
        r.model_copy(update={"params": {**r.params, "starting_cash": cash}})
        if r.id == "L-P4"
        else r
        for r in config.rules
    )
    return config.model_copy(update={"rules": rules})


# --- The code review's fixes ----------------------------------------------------------------------


def test_l_p3_the_snapshot_is_asked_with_l_p3s_band(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    source = Source(lambda: snapshot(calendar, session=FRIDAY))

    _night(sanji_root(tmp_path, FRIDAY), calendar, config, source=source)

    assert source.bands == [config.strike("L-P3")]


def test_ld_25_friday_saturday_and_sunday_nights_each_place_mondays_order_once(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    sanji_root(tmp_path, FRIDAY)
    nights = [datetime(2026, 11, d, 22, 0, tzinfo=ET) for d in (13, 14, 15)]

    placed = [_night(tmp_path, calendar, config, night).decision.order for night in nights]

    assert all(order is not None for order in placed)
    (order,) = read_orders(tmp_path / "open_orders.json")
    assert order == placed[-1]
    assert len(_log(tmp_path)) == 3


def test_ld_14_a_snapshot_for_the_wrong_session_logs_a_failed_row(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    stale = Source(lambda: snapshot(calendar, session=date(2026, 11, 12)))

    with pytest.raises(LiveError, match="plans"):
        _night(sanji_root(tmp_path, FRIDAY), calendar, config, source=stale)

    (row,) = _log(tmp_path)
    assert (row["outcome"], row["rule"]) == ("failed", "L-S1")
    assert not (tmp_path / "open_orders.json").exists()


def test_ld_14_a_write_that_fails_logs_a_failed_row(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    sanji_root(tmp_path, FRIDAY)
    (tmp_path / "mkt").write_text("not a directory", encoding="utf-8")

    with pytest.raises(OSError, match="mkt"):
        _night(tmp_path, calendar, config)

    (row,) = _log(tmp_path)
    assert (row["outcome"], row["rule"]) == ("failed", "L-O1")


def test_ld_04_order_files_that_differ_stop_the_run(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    sanji_root(tmp_path, FRIDAY)
    write_orders(tmp_path / "open_orders.json", (_hand_order(MONDAY),))
    write_orders(tmp_path / "mkt" / "open_orders.json", ())

    with pytest.raises(BookError, match="differ"):
        _night(tmp_path, calendar, config)

    assert _log(tmp_path)[0]["rule"] == "L-B2"


def test_ld_24_a_run_past_the_calendar_is_refused_and_writes_nothing(
    tmp_path: Path, calendar: SessionCalendar, config: LiveConfig
) -> None:
    sanji_root(tmp_path, FRIDAY)

    with pytest.raises(LiveError, match="outside the session calendar"):
        _night(tmp_path, calendar, config, datetime(2031, 1, 6, 22, 0, tzinfo=ET))

    assert _log(tmp_path) == []
