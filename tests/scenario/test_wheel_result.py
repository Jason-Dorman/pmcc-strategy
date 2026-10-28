"""The wheel's result file (W2-03): its rows mirror the engine's run, it carries what produced it,
it is canonical, and a re-run is byte-identical once the volatile values are dropped (WINV-10).

The market is `winv10_run.full_wheel`: five weeks in which every booking and skip rule fires.
"""

import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.domain.instruments import OptionId
from pmcc.export import canonical
from pmcc.export.results import to_bytes, write_result
from pmcc.export.wheel_models import WheelResult
from pmcc.wheel.config import WHEEL_RULE_IDS
from pmcc.wheel.engine import WheelRun, run_wheel
from pmcc.wheel.invariants import RUNTIME_INVARIANTS
from pmcc.wheel.market import WheelMarket, load_wheel_market
from tests.scenario import winv10_run

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def cache(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("wheel_cache")
    winv10_run.generate_market(root)
    return root


@pytest.fixture(scope="module")
def market(cache: Path) -> WheelMarket:
    cfg = winv10_run.config()
    return load_wheel_market(cache, "SYN", "SYN", load_calendar(), cfg.risk_free_rate.value,
                             (cfg.window.start, cfg.window.end))  # fmt: skip


@pytest.fixture(scope="module")
def run(market: WheelMarket) -> WheelRun:
    return run_wheel(market.data, winv10_run.config())


@pytest.fixture(scope="module")
def result(cache: Path) -> WheelResult:
    return winv10_run.result(cache)


def _d(units: int) -> Decimal:
    return Decimal(units).scaleb(-4)


# ---- the rows -----------------------------------------------------------------------------------


def test_w2_03_the_result_reaches_every_row_shape(result: WheelResult) -> None:
    assert [(r.rule_id, r.side, r.instrument.kind) for r in result.blotter] == [
        ("W-P1", "SELL", "put"), ("W-X1", "EXPIRE", "put"),
        ("W-P1", "SELL", "put"), ("W-X2", "ASSIGN", "put"), ("W-X2", "BUY", "stock"),
        ("W-C1", "SELL", "call"), ("W-X3", "EXPIRE", "call"),
        ("W-C1", "SELL", "call"), ("W-X4", "ASSIGN", "call"), ("W-X4", "SELL", "stock"),
    ]  # fmt: skip
    assert [(g.state, g.outcome.kind, g.outcome.rule_id) for g in result.gate_log] == [
        ("cash", "sold", "W-P1"), ("cash", "sold", "W-P1"), ("shares", "skipped", "W-C3"),
        ("shares", "sold", "W-C1"), ("shares", "sold", "W-C1"),
    ]  # fmt: skip
    assert {row.state for row in result.ledger} == {"cash", "put", "shares", "call"}
    assert result.summary.flag_counts == {"stale_call": 6, "stale_put": 6}


def test_w2_03_the_blotter_mirrors_the_engine(result: WheelResult, run: WheelRun) -> None:
    assert len(result.blotter) == len(run.blotter)
    for row, event in zip(result.blotter, run.blotter, strict=True):
        assert (row.time, row.side, row.qty, row.rule_id, row.notes) == (
            event.time, event.side.value, event.qty, event.rule_id, event.notes)  # fmt: skip
        assert row.cash_delta == _d(event.cash_delta.units)
        assert row.fill == (None if event.fill is None else _d(event.fill.units))
        assert row.limit == (None if event.limit is None else _d(event.limit.units))
        assert row.audit == dict(event.audit)


def test_w2_03_every_instrument_is_named_by_the_ric_its_cache_answered(
    result: WheelResult, market: WheelMarket
) -> None:
    """Puts come from the wheel part, calls and the stock from the symbol's cache."""
    for row, event in zip(result.blotter, run_wheel(market.data, winv10_run.config()).blotter,
                          strict=True):  # fmt: skip
        if isinstance(event.instrument, OptionId):
            assert row.instrument == market.names.instrument(event.instrument)
            assert row.instrument.occ is not None
            assert row.instrument.ric.startswith("SYN")
        else:
            assert (row.instrument.ric, row.instrument.kind) == ("SYN.O", "stock")


def test_w2_03_the_ledger_mirrors_the_engine(result: WheelResult, run: WheelRun) -> None:
    assert len(result.ledger) == len(run.ledger) == 168  # 5 weeks of session bars
    for out, row in zip(result.ledger, run.ledger, strict=True):
        assert (out.time, out.state, out.shares, out.flags) == (
            row.time, row.state.value, row.shares, row.flags)  # fmt: skip
        assert (out.cash, out.reserved, out.free_cash, out.nav) == tuple(
            _d(m.units) for m in (row.cash, row.reserved, row.free_cash, row.nav))  # fmt: skip
        assert out.cost_basis == (None if row.cost_basis is None else _d(row.cost_basis.units))
        assert out.stock_mark == (None if row.stock_mark is None else _d(row.stock_mark.units))
        for leg, held in ((out.put, row.put), (out.call, row.call)):
            assert (leg is None) == (held is None)
            if leg is not None and held is not None:
                assert (leg.qty, leg.mark, leg.stale, leg.delta) == (
                    held.qty, _d(held.mark.units), held.stale, held.greeks.delta)  # fmt: skip
                assert leg.instrument.strike == _d(held.option.strike.units)


def test_w2_03_the_gate_log_mirrors_the_engine(result: WheelResult, run: WheelRun) -> None:
    for out, row in zip(result.gate_log, run.gate_log, strict=True):
        assert (out.session, out.state, out.decision_time, out.notes) == (
            row.session, row.state.value, row.decision_time, row.notes)  # fmt: skip
        assert out.selected == (None if row.selected is None else dict(row.selected))


# ---- what produced it ---------------------------------------------------------------------------


def test_w2_03_the_manifest_records_what_produced_the_run(
    result: WheelResult, market: WheelMarket
) -> None:
    manifest = result.manifest
    assert (manifest.symbol, manifest.run_id, manifest.strategy_id) == ("SYN", "wheel", "wheel")
    assert manifest.config_hash == winv10_run.config().config_hash()
    assert manifest.data_manifest_hash == market.data_manifest_hash
    assert (manifest.git_sha, manifest.git_dirty) == (winv10_run.PROVENANCE.git.sha, False)
    assert manifest.lock_hash == winv10_run.PROVENANCE.lock_hash


def test_w2_03_the_rule_text_is_every_rule_rendered_from_the_config(result: WheelResult) -> None:
    assert list(result.rule_text) == [str(i) for i in WHEEL_RULE_IDS]
    for rule in result.config.wheel.rules:
        assert result.rule_text[str(rule.id)].summary == rule.text().summary


def test_w2_03_the_summary_records_every_runtime_invariant_held(result: WheelResult) -> None:
    assert [(c.id, c.held) for c in result.summary.invariants] == [
        (i, True) for i in RUNTIME_INVARIANTS
    ]


def test_w2_03_the_starting_cash_is_the_wheel_configs(result: WheelResult) -> None:
    assert result.starting_cash == Decimal("25000")  # WD-10


# ---- the file -----------------------------------------------------------------------------------


def test_w2_03_the_file_is_canonical_and_reads_back_to_the_same_bytes(
    result: WheelResult, tmp_path: Path
) -> None:
    path = write_result(result, tmp_path)

    assert path == tmp_path / "SYN" / "wheel.json"
    raw = path.read_bytes()
    assert canonical.to_bytes(canonical.loads(raw)) == raw
    again = WheelResult.model_validate_json(raw)
    assert to_bytes(again) == raw
    assert again.config.config_hash() == again.manifest.config_hash
    assert b'"starting_cash":25000.0000' in raw


def test_winv_10_the_same_run_twice_in_one_process_writes_identical_bytes(cache: Path) -> None:
    assert to_bytes(winv10_run.result(cache)) == to_bytes(winv10_run.result(cache))


def _start(cache: Path, out: Path, hour: int, sha: str, seed: str) -> subprocess.Popen[bytes]:
    command = [sys.executable, "-m", "tests.scenario.winv10_run", str(cache), str(out), str(hour),
               sha]  # fmt: skip
    env = {**os.environ, "PYTHONHASHSEED": seed}
    return subprocess.Popen(command, cwd=REPO_ROOT, env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)  # fmt: skip


def test_winv_10_two_runs_are_byte_identical_once_the_volatile_values_are_dropped(
    cache: Path, tmp_path: Path
) -> None:
    """Two fresh processes: different run times, commits and hash seeds."""
    runs = [
        _start(cache, tmp_path / out, hour, sha, seed)
        for out, hour, sha, seed in (("a", 9, "a" * 40, "2"), ("b", 11, "b" * 40, "6"))
    ]
    for proc in runs:
        output, _ = proc.communicate(timeout=300)
        assert proc.returncode == 0, output.decode(errors="replace")

    first, second = ((tmp_path / d / "SYN" / "wheel.json").read_bytes() for d in "ab")
    assert first != second  # the run time and commit differ...
    assert canonical.drop_volatile(first) == canonical.drop_volatile(second)  # ...only


def test_winv_10_the_subprocess_entry_is_the_in_process_run(cache: Path, tmp_path: Path) -> None:
    path = winv10_run.main(cache, tmp_path, 9)

    assert path.read_bytes() == to_bytes(winv10_run.result(cache))


# ---- the reported numbers (W3-01) ---------------------------------------------------------------


def test_wd_28_trade_pnl_is_each_positions_cash_on_the_row_that_closes_it(
    result: WheelResult,
) -> None:
    pnl = [(r.rule_id, r.side, r.trade_pnl) for r in result.blotter]
    put1, put2, call1, call2 = (r.cash_delta for r in result.blotter if r.side == "SELL"
                                and r.instrument.kind != "stock")  # fmt: skip

    assert pnl == [
        ("W-P1", "SELL", None), ("W-X1", "EXPIRE", put1),
        ("W-P1", "SELL", None), ("W-X2", "ASSIGN", put2), ("W-X2", "BUY", None),
        ("W-C1", "SELL", None), ("W-X3", "EXPIRE", call1),
        ("W-C1", "SELL", None), ("W-X4", "ASSIGN", call2),
        ("W-X4", "SELL", Decimal("0")),  # bought and called away at the same $98
    ]  # fmt: skip
    closes = [r.nav for r in result.ledger if r.time.hour == 16]
    realized = sum((r.trade_pnl for r in result.blotter if r.trade_pnl is not None), Decimal(0))
    assert realized == closes[-1] - result.starting_cash  # nothing held at the end


def test_wd_20_the_metrics_follow_from_the_ledger(result: WheelResult) -> None:
    m = result.summary.metrics
    closes = [r.nav for r in result.ledger if r.time.hour == 16]
    peak, fall = result.starting_cash, Decimal(0)
    for row in result.ledger:
        peak = max(peak, row.nav)
        fall = max(fall, peak - row.nav)

    assert m.sessions == len(closes) == 24
    assert m.pnl == closes[-1] - result.starting_cash
    assert m.return_on_starting_cash == pytest.approx(float(m.pnl / result.starting_cash))
    assert m.max_drawdown == fall
    assert m.sharpe_annualized is not None


def test_wd_29_cycle_stats_count_a_cycle_from_assignment_to_call_away(result: WheelResult) -> None:
    c = result.summary.cycle_stats

    assert (c.puts_sold, c.puts_expired, c.puts_assigned) == (2, 1, 1)
    assert (c.calls_sold, c.calls_expired, c.calls_called_away) == (2, 1, 1)
    assert (c.weeks, c.weeks_sold, dict(c.weeks_skipped)) == (5, 4, {"W-C3": 1})
    assert c.complete_cycles == 1  # the expired put is not a cycle
    assert c.open_at_end is False
    sold = [r.cash_delta for r in result.blotter
            if r.side == "SELL" and r.instrument.kind != "stock"]  # fmt: skip
    assert c.premium == sum(sold, Decimal(0))
    assert list(c.time_in_state) == ["cash", "put", "shares", "call"]
    assert sum(c.time_in_state.values()) == pytest.approx(1.0)
    by_state = {s: sum(r.state == s for r in result.ledger) for s in c.time_in_state}
    assert {s: n / len(result.ledger) for s, n in by_state.items()} == c.time_in_state


def test_wd_29_each_claim_is_judged_from_the_summarys_numbers(result: WheelResult) -> None:
    summary = result.summary
    pmcc, sp500 = summary.benchmarks.baseline_pmcc, summary.benchmarks.sp500

    assert summary.benchmarks == winv10_run.BENCHMARKS
    assert [(v.claim, v.wheel, v.benchmark) for v in summary.thesis] == [
        (1, float(summary.metrics.pnl), 0.0),
        (2, round(summary.metrics.sharpe_annualized or 0, 6), pmcc.sharpe_annualized),
        (3, round(summary.metrics.return_on_starting_cash, 6), sp500.price_return),
    ]
    assert [v.met for v in summary.thesis] == [
        v.wheel is not None and v.benchmark is not None and v.wheel > v.benchmark
        for v in summary.thesis
    ]


# ---- the fill evidence (W3-02) ------------------------------------------------------------------


def test_w3_02_the_fill_evidence_pairs_every_sold_options_prints_with_its_mids(
    result: WheelResult, market: WheelMarket, run: WheelRun
) -> None:
    sold = [e for e in run.blotter if isinstance(e.instrument, OptionId) and e.side.value == "SELL"]
    expected: dict[str, int] = {"puts": 0, "calls": 0}
    for event in sold:
        option = event.instrument
        assert isinstance(option, OptionId)
        frame = market.chains[(option.expiry, option.right)]
        bars = [end for end, strike, session, valid, trade in frame.select(
                    "bar_end", "strike_cents", "session_bar", "valid_quote", "TRDPRC_1").iter_rows()
                if strike == option.strike_cents and session and valid and trade is not None
                and event.time <= end and end.date() <= option.expiry]  # fmt: skip
        expected["puts" if option.right.name == "PUT" else "calls"] += len(bars)
    evidence = result.fill_evidence

    assert evidence.contracts == len(sold) == 4
    assert {g.group: len(g.points.mid) for g in evidence.groups} == expected
    assert [g.group for g in evidence.groups] == ["puts", "calls"]
    assert evidence.fit is not None
    assert evidence.fit.n == sum(expected.values())
    for group in evidence.groups:
        assert group.fit is not None
        assert group.fit.n == len(group.points.trade) == len(group.points.spread)
        assert group.fit.r2 is not None
        assert group.fit.r2 > 0.99  # the synthetic market prints at its mid
