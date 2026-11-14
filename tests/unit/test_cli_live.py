"""`pmcc live` (L2-03): one night from the command line, over a temporary repo and a fake close
snapshot. It prints one ASCII line, writes the order file at the root and under `mkt/`, and on a
bad book prints why, writes no order and exits 1 (PO, LD-14)."""

from datetime import date, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pmcc import cli
from pmcc.cli import app
from pmcc.config.calendar import load_calendar
from pmcc.domain.clock import ET
from pmcc.live.orders import read_orders
from pmcc.live.snapshot import CloseSnapshot
from tests.fakes.live import sanji_root, snapshot

NOW = datetime(2026, 11, 13, 22, 0, tzinfo=ET)
FRIDAY = date(2026, 11, 13)

runner = CliRunner()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    calendar = load_calendar()
    monkeypatch.chdir(tmp_path)  # logs/ land here
    monkeypatch.setattr(cli, "_now", lambda: NOW)

    def fake_snapshot(*_: object) -> CloseSnapshot:
        return snapshot(calendar, session=FRIDAY)

    monkeypatch.setattr(cli, "_close_snapshot", fake_snapshot)
    return sanji_root(tmp_path, FRIDAY)


def _live(root: Path, *args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["live", "--symbol", "nvda", "--root", str(root), *args])
    return result.exit_code, result.output


def test_l2_03_live_writes_mondays_order_and_says_so(repo: Path) -> None:
    code, output = _live(repo)

    assert code == 0, output
    (order,) = read_orders(repo / "open_orders.json")
    assert order.for_ == date(2026, 11, 16)
    assert (repo / "mkt" / "open_orders.json").is_file()
    assert "L-O1" in output
    assert "1 order(s) in open_orders.json" in output
    assert output.isascii()


def test_l2_03_live_dry_run_writes_nothing(repo: Path) -> None:
    code, output = _live(repo, "--dry-run")

    assert code == 0, output
    assert not (repo / "open_orders.json").exists()
    assert "dry run" in output


def test_ld_14_live_on_a_stale_book_writes_no_order_and_exits_1(repo: Path) -> None:
    sanji_root(repo, date(2026, 11, 12))

    code, output = _live(repo)

    assert code == 1
    assert "no new order" in output
    assert "L-B1" in output
    assert not (repo / "open_orders.json").exists()


def test_l2_03_live_refuses_a_symbol_the_config_does_not_trade(repo: Path) -> None:
    result = runner.invoke(app, ["live", "--symbol", "spy", "--root", str(repo)])

    assert result.exit_code == 1
    assert "trades NVDA" in result.output


def test_ld_14_live_with_a_bad_order_file_exits_1_without_a_traceback(repo: Path) -> None:
    (repo / "open_orders.json").write_text('[{"id": "x"}]', encoding="utf-8")

    code, output = _live(repo)

    assert code == 1
    assert "no new order" in output
    assert "L-B2" in output
