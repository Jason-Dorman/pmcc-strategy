"""`live.json` (L4-01; UI-SPEC §6 › Live): the live wheel's page data from the root's files."""

import json
from collections.abc import Callable, Mapping
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from pmcc.export import canonical
from pmcc.export.live import LiveDataError, build_live, wheel_run
from pmcc.export.live_models import Live, SanjiFileOut
from pmcc.export.wheel_models import WheelResult
from pmcc.live.config import LiveConfig, load_live_config
from pmcc.live.orders import Order, write_orders

REPO = Path(__file__).resolve().parents[3]
WHEEL = REPO / "results" / "NVDA" / "wheel.json"

ORDER = Order.model_validate(
    {"id": "wheel-2026-11-16-P-155", "for": date(2026, 11, 16), "order_type": "lmt",
     "action": "SHT", "qty": 1, "underlying": 4815747, "contract": "put",
     "expiry": "2026-11-20", "strike": "155", "ref": "open", "lmt_prc": "mid"}
)  # fmt: skip
type Row = Mapping[str, object]

PICK: Row = {"contract": "put", "strike": "155", "expiry": "2026-11-20", "delta": -0.3188,
             "iv": 0.8823}  # fmt: skip
BEFORE_QUOTES: Row = {  # Nov 15's row, logged before the pick's quote was (LD-15)
    "run_at": "2026-11-15T22:31:26.205329-05:00", "last_session": "2026-11-13",
    "next_session": "2026-11-16", "state": "cash", "cash": "25000.00", "cost_basis": None,
    "outcome": "order", "rule": "L-O1",
    "reason": "sell 1 155.00 put expiring 2026-11-20 at the mid",
    "order_id": "wheel-2026-11-16-P-155", "pick": PICK, "open_orders": 1,
}  # fmt: skip
QUOTE: Row = {"bid": "2.41", "ask": "2.46", "mid": "2.435", "spread": 0.0205}
WITH_QUOTE: Row = {**BEFORE_QUOTES, "run_at": "2026-11-20T22:00:04-05:00",
                   "pick": {**PICK, **QUOTE}}  # fmt: skip
FAILED: Row = {**BEFORE_QUOTES, "run_at": "2026-11-17T22:00:03-05:00", "state": None,
               "cash": None, "outcome": "failed", "rule": "L-B1", "reason": "stale",
               "order_id": None, "pick": None, "open_orders": None}  # fmt: skip


@pytest.fixture(scope="module")
def config() -> LiveConfig:
    return load_live_config()


def _root(tmp: Path, *rows: Row) -> Path:
    write_orders(tmp / "open_orders.json", (ORDER,))
    (tmp / "live").mkdir()
    lines = "".join(json.dumps(row) + "\n" for row in rows)
    (tmp / "live" / "runs.jsonl").write_text(lines, encoding="utf-8", newline="\n")
    return tmp


def test_l4_01_live_holds_the_orders_the_rules_and_the_config(
    tmp_path: Path, config: LiveConfig
) -> None:
    live = build_live(_root(tmp_path, BEFORE_QUOTES), config, None)

    assert (live.symbol, live.underlying_conid) == ("NVDA", 4815747)
    assert live.starting_cash == Decimal("25000")
    assert live.risk_free.investment_yield_pct == 4.32
    assert [r.id for r in live.rules] == [r.id for r in config.rules]
    assert live.rules[0].words == config.rules[0].words()
    (order,) = live.orders
    assert order.model_dump()["for"] == "2026-11-16"
    assert (order.strike, order.lmt_prc, order.expiry) == ("155", "mid", "2026-11-20")


def test_l4_01_the_run_log_is_every_row_in_order_money_as_dollars(
    tmp_path: Path, config: LiveConfig
) -> None:
    live = build_live(_root(tmp_path, BEFORE_QUOTES, FAILED, WITH_QUOTE), config, None)

    assert [r.outcome for r in live.runs] == ["order", "failed", "order"]
    assert live.runs[0].cash == Decimal("25000.00")
    assert live.runs[1].state is None


def test_ld_15_a_pick_carries_its_quote_and_an_earlier_row_null(
    tmp_path: Path, config: LiveConfig
) -> None:
    live = build_live(_root(tmp_path, BEFORE_QUOTES, WITH_QUOTE), config, None)
    before, after = (r.pick for r in live.runs)

    assert before is not None
    assert after is not None
    assert (before.bid, before.ask, before.mid, before.spread) == (None, None, None, None)
    assert (after.bid, after.ask, after.mid) == (Decimal("2.41"), Decimal("2.46"), Decimal("2.435"))
    assert after.spread == 0.0205


def test_l4_01_sanjis_files_are_published_as_written_and_null_before_he_writes(
    tmp_path: Path, config: LiveConfig
) -> None:
    root = _root(tmp_path, BEFORE_QUOTES)
    before = build_live(root, config, None)
    assert (before.positions, before.fills) == (None, None)

    (root / "mkt").mkdir()
    positions = '{"symbol": "NVDA", "cash": 24876.123456789}\n'  # his key order, his digits
    (root / "mkt" / "positions.json").write_text(positions, encoding="utf-8", newline="\n")
    (root / "fills.json").write_text('[{"id": "x"}]', encoding="utf-8")
    live = build_live(root, config, None)

    assert live.positions == SanjiFileOut(path="mkt/positions.json", text=positions)
    assert live.fills == SanjiFileOut(path="fills.json", text='[{"id": "x"}]')


def test_l4_01_a_sanji_file_half_written_is_published_and_never_stops_the_export(
    tmp_path: Path, config: LiveConfig
) -> None:
    root = _root(tmp_path, BEFORE_QUOTES)
    (root / "positions.json").write_bytes(b'{"cash": 25\xff')

    live = build_live(root, config, None)

    assert live.positions == SanjiFileOut(path="positions.json", text='{"cash": 25\ufffd')


def test_l4_01_no_run_log_yet_means_no_runs(tmp_path: Path, config: LiveConfig) -> None:
    root = _root(tmp_path)
    (root / "live" / "runs.jsonl").unlink()

    assert build_live(root, config, None).runs == ()


def _write(name: str, text: str) -> Callable[[Path], object]:
    return lambda root: (root / name).write_text(text, encoding="utf-8")


DAMAGE: list[tuple[Callable[[Path], object], str]] = [
    (_write("live/runs.jsonl", "{}\n"), "line 1"),
    (_write("live/runs.jsonl", "not json\n"), "line 1"),
    (_write("open_orders.json", '[{"id": 1}]'), "open_orders.json"),
    (_write("open_orders.json", "["), "open_orders.json"),
]


@pytest.mark.parametrize(("damage", "names"), DAMAGE)
def test_l4_01_a_file_the_page_cant_read_stops_the_export(
    tmp_path: Path, config: LiveConfig, damage: Callable[[Path], object], names: str
) -> None:
    root = _root(tmp_path, BEFORE_QUOTES)
    damage(root)

    with pytest.raises(LiveDataError, match=names):
        build_live(root, config, None)


def test_l4_01_the_backtest_is_the_wheels_own_run_on_the_symbol(
    tmp_path: Path, config: LiveConfig
) -> None:
    result = WheelResult.model_validate_json(WHEEL.read_bytes())
    friction = result.manifest.model_copy(update={"run_id": "wheel--x"})
    wheels = [
        ("NVDA/wheel--x.json", result.model_copy(update={"manifest": friction})),
        ("NVDA/wheel.json", result),
    ]

    found = wheel_run("NVDA", wheels)
    assert found is not None
    live = build_live(_root(tmp_path, BEFORE_QUOTES), config, found)

    backtest = live.backtest
    assert backtest is not None
    assert backtest.path == "NVDA/wheel.json"
    assert backtest.pnl == result.summary.metrics.pnl
    assert backtest.sharpe_annualized == result.summary.metrics.sharpe_annualized
    assert backtest.baseline_sharpe_annualized == (
        result.summary.benchmarks.baseline_pmcc.sharpe_annualized
    )
    assert (backtest.start, backtest.end) == ("2026-03-30", "2026-09-25")
    assert wheel_run("QQQ", wheels) is None


def test_l4_01_live_json_round_trips_through_its_model(tmp_path: Path, config: LiveConfig) -> None:
    live = build_live(_root(tmp_path, BEFORE_QUOTES, WITH_QUOTE), config, None)
    raw = canonical.to_bytes(live.model_dump())

    again = Live.model_validate_json(raw, strict=False)
    assert canonical.to_bytes(again.model_dump()) == raw  # canonical floats: stable, not exact
    assert again.orders == live.orders
    assert again.runs[1].pick == live.runs[1].pick
    assert b'"for":"2026-11-16"' in raw


# --- Volatility (L4-02; PO, LD-33; LD-34) ---------------------------------------------------------

POINT: Row = {"session": "2026-11-17", "close": "155.46", "expiry": "2026-12-18",
              "strike": "155.00", "call_iv": 0.512, "put_iv": 0.524, "atm_iv": 0.518,
              "rv20": 0.471}  # fmt: skip
NO_ATM: Row = {**POINT, "session": "2026-11-16", "strike": None, "call_iv": None,
               "put_iv": None, "atm_iv": None}  # fmt: skip
SMILE: Row = {"session": "2026-11-17", "expiry": "2026-11-20", "close": "155.46",
              "pick": "147.50", "points": [
                  {"strike": "147.50", "right": "put", "iv": 0.58, "delta": -0.31},
                  {"strike": "160.00", "right": "call", "iv": 0.49, "delta": 0.27}]}  # fmt: skip


def _vol(root: Path, *rows: Row, smile: Row | None = SMILE) -> Path:
    lines = "".join(json.dumps(row) + "\n" for row in rows)
    (root / "live" / "vol.jsonl").write_text(lines, encoding="utf-8", newline="\n")
    if smile is not None:
        (root / "live" / "smile.json").write_text(json.dumps(smile), encoding="utf-8")
    return root


def test_ld_34_the_volatility_points_are_by_session_and_money_in_dollars(
    tmp_path: Path, config: LiveConfig
) -> None:
    live = build_live(_vol(_root(tmp_path), POINT, NO_ATM), config, None)

    assert [p.session for p in live.vol] == ["2026-11-16", "2026-11-17"]  # by session
    assert live.vol[0].atm_iv is None
    assert live.vol[1].close == Decimal("155.46")
    assert live.vol[1].rv20 == 0.471


def test_ld_34_the_smile_is_published_with_its_pick(tmp_path: Path, config: LiveConfig) -> None:
    smile = build_live(_vol(_root(tmp_path), POINT), config, None).smile

    assert smile is not None
    assert (smile.expiry, smile.pick) == ("2026-11-20", Decimal("147.50"))
    assert [p.right for p in smile.points] == ["put", "call"]


def test_ld_34_no_volatility_yet_means_none(tmp_path: Path, config: LiveConfig) -> None:
    live = build_live(_root(tmp_path), config, None)

    assert (live.vol, live.smile) == ((), None)


VOL_DAMAGE: list[tuple[Callable[[Path], object], str]] = [
    (_write("live/vol.jsonl", "{}\n"), "vol.jsonl line 1"),
    (_write("live/vol.jsonl", json.dumps(POINT) + "\n" + json.dumps(POINT) + "\n"), "twice"),
    (_write("live/smile.json", "{"), "smile.json"),
]


@pytest.mark.parametrize(("damage", "names"), VOL_DAMAGE)
def test_ld_34_a_volatility_file_the_page_cant_read_stops_the_export(
    tmp_path: Path, config: LiveConfig, damage: Callable[[Path], object], names: str
) -> None:
    root = _vol(_root(tmp_path), POINT)
    damage(root)

    with pytest.raises(LiveDataError, match=names):
        build_live(root, config, None)
