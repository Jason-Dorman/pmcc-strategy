"""`pmcc calibrate` (P3-09, DEC-30): measure, verify, and write the starting cash with its basis
into the universe file, or with `--check`, recompute it and compare.

The market is the synthetic `random_walk`, cached in a temporary directory. A test universe in the
working directory stands in for configs/universe.yaml, both as the file read and the file written.
"""

from collections.abc import Callable
from datetime import UTC
from pathlib import Path

import pytest
from typer.testing import CliRunner

from pmcc import calibration, cli
from pmcc.cli import app
from pmcc.config.capital import MARKER, StartingCash
from pmcc.config.strategy import CONFIGS_DIR
from pmcc.config.universe import UNIVERSE_PATH, Universe, read_universe_file
from pmcc.config.yaml_file import parse_yaml
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import ET
from pmcc.domain.money import Money
from tests.fixtures.synthetic.market import generate
from tests.fixtures.synthetic.scenarios import random_walk

_REAL_VALIDATE = cli.validate_universe  # before any test replaces it
BASELINE = (CONFIGS_DIR / "baseline_pmcc.yaml").as_posix()

runner = CliRunner()


def _universe() -> str:
    spec = random_walk()
    shipped = UNIVERSE_PATH.read_text(encoding="utf-8")
    rate = shipped[shipped.index("risk_free_rate:") : shipped.index("# The universe")]
    return (
        f"# a test universe\nwindow: {{start: {spec.window_start}, end: {spec.window_end}}}\n"
        f"{rate}symbols:\n  - {{symbol: SYN, stock_ric: SYN.O, option_root: SYN}}  # kept\n"
    )


@pytest.fixture(scope="module")
def market(tmp_path_factory: pytest.TempPathFactory) -> Path:
    cache = tmp_path_factory.mktemp("market")
    generate(random_walk(), cache)
    return cache


@pytest.fixture
def universe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The universe file, read and written in place of configs/universe.yaml."""
    monkeypatch.chdir(tmp_path)  # logs/ land here
    path = tmp_path / "universe.yaml"
    path.write_text(_universe(), encoding="utf-8", newline="\n")

    def stand_in(_calendar: SessionCalendar) -> Universe:
        return read_universe_file(path)

    def validate(text: str, _calendar: SessionCalendar) -> None:
        # The file as written, less the calendar's ten-week check: the market's window is four.
        Universe.model_validate(parse_yaml(text))

    monkeypatch.setattr(cli, "load_universe", stand_in)
    monkeypatch.setattr(cli, "validate_universe", validate)
    monkeypatch.setattr(cli, "UNIVERSE_PATH", path)
    return path


def _calibrate(cache: Path, *extra: str) -> tuple[int, str]:
    args = ["calibrate", "--symbol", "syn", "--config", BASELINE, "--cache", str(cache), *extra]
    result = runner.invoke(app, args)
    return result.exit_code, result.output


def test_dec_30_calibrate_writes_a_provisional_block_after_the_file(
    universe: Path, market: Path
) -> None:
    code, output = _calibrate(market)

    assert code == 0, output
    text = universe.read_text(encoding="utf-8")
    assert text.startswith(_universe() + "\n" + MARKER)
    cash = read_universe_file(universe).starting_cash
    assert cash is not None
    assert cash.provisional  # quant_pmcc isn't calibrated
    (entry,) = cash.entries
    assert (entry.symbol, entry.strategy) == ("SYN", "baseline_pmcc")
    assert cash.value.units % Money.from_dollars(5_000).units == 0
    assert f"Starting cash {cash.value.to_dollars()} (provisional), from:" in output
    assert f"SYN baseline_pmcc: {entry.contract}" in output
    assert (
        f"Available funds at {cash.value.to_dollars()} (reported, not refused; DEC-30):" in output
    )
    assert "SYN baseline_pmcc: lowest " in output
    assert "bar(s) below zero" in output
    assert "Written to configs/universe.yaml." in output
    assert "Log: logs/calibrate_" in output


def test_dec_30_calibrate_is_reproducible_and_check_confirms_it(
    universe: Path, market: Path
) -> None:
    _calibrate(market)
    first = universe.read_bytes()

    code, output = _calibrate(market)  # replaces its own provisional block
    assert code == 0, output
    assert universe.read_bytes() == first

    code, output = _calibrate(market, "--check")
    assert code == 0, output
    assert "starting_cash matches" in output
    assert universe.read_bytes() == first


def _edits(cash: StartingCash) -> dict[str, tuple[str, str]]:
    """Edits that keep the file loadable but aren't what calibrate writes."""
    entry = cash.entries[0]
    cost, value = entry.cost.to_dollars(), cash.value.to_dollars()
    return {
        "cost": (f"cost: '{cost}'", f"cost: '{cost - 1}'"),
        "calibration-cash": ("cash: '1000000.0000'", "cash: '2000000.0000'"),
        "same-instant-in-utc": (entry.time.isoformat(), entry.time.astimezone(UTC).isoformat()),
        "value-as-a-number": (f"value: '{value}'", f"value: {int(value)}"),
        "header-comment": ("only ever removed by hand", "removed however you like"),
    }


@pytest.mark.parametrize("edit", ["cost", "calibration-cash", "same-instant-in-utc",
                                  "value-as-a-number", "header-comment"])  # fmt: skip
def test_dec_93_calibrate_check_fails_on_any_byte_that_differs(
    universe: Path, market: Path, edit: str
) -> None:
    """--check is byte for byte: the file must be exactly what calibrate would write."""
    _calibrate(market)
    text = universe.read_text(encoding="utf-8")
    cash = read_universe_file(universe).starting_cash
    assert cash is not None
    old, new = _edits(cash)[edit]
    assert old in text
    changed = text.replace(old, new)
    universe.write_text(changed, encoding="utf-8", newline="\n")
    read_universe_file(universe)  # still loads: only --check can tell

    code, output = _calibrate(market, "--check")

    assert code == 1
    assert "doesn't match this calibration" in output
    assert universe.read_text(encoding="utf-8") == changed


def test_dec_93_calibrate_writes_entry_times_in_new_york(universe: Path, market: Path) -> None:
    _calibrate(market)
    cash = read_universe_file(universe).starting_cash
    assert cash is not None
    time = cash.entries[0].time
    assert time.utcoffset() == ET.utcoffset(time.replace(tzinfo=None))
    assert f"time: '{time.isoformat()}'" in universe.read_text(encoding="utf-8")


def test_dec_93_calibrate_validates_with_the_calendar_before_writing(
    universe: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real check: the four-week synthetic window fails the ten-week rule, so nothing is
    written."""
    monkeypatch.setattr(cli, "validate_universe", _REAL_VALIDATE)

    code, output = _calibrate(market)

    assert code == 1
    assert "at least 10 weeks" in output
    assert "it is unchanged" in output
    assert universe.read_text(encoding="utf-8") == _universe()


def test_dec_93_calibrate_fails_cleanly_when_the_file_cant_be_replaced(
    universe: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def locked(path: Path, _data: bytes) -> None:
        raise PermissionError(13, "Access is denied", str(path))

    monkeypatch.setattr(cli, "replace_file", locked)

    code, output = _calibrate(market)

    assert code == 1
    assert "Access is denied" in output
    assert "it is unchanged" in output
    assert universe.read_text(encoding="utf-8") == _universe()


def test_dec_30_calibrate_check_fails_without_a_block(universe: Path, market: Path) -> None:
    code, output = _calibrate(market, "--check")

    assert code == 1
    assert "doesn't match" in output
    assert universe.read_text(encoding="utf-8") == _universe()


def test_dec_30_calibrate_never_replaces_a_final_value(universe: Path, market: Path) -> None:
    final = (
        "starting_cash: {value: 5000, provisional: false, cash_multiple: 2, cash_round_to: 5000, "
        "calibration_cash: 1000000, entries: ["
        "{symbol: SYN, strategy: baseline_pmcc, time: '2026-07-06T10:00:00-04:00', contract: X, "
        "cost: 900}, {symbol: SYN, strategy: quant_pmcc, time: '2026-07-06T10:00:00-04:00', "
        "contract: X, cost: 900}]}\n"
    )
    universe.write_text(_universe() + final, encoding="utf-8", newline="\n")

    code, output = _calibrate(market)

    assert code == 1
    assert "holds a final starting_cash" in output
    assert "Remove its block by hand" in output
    assert universe.read_text(encoding="utf-8") == _universe() + final


def test_dec_30_calibrate_refuses_a_provisional_value_written_by_hand(
    universe: Path, market: Path
) -> None:
    """A valid block without calibrate's marker: replacing it could lose what was around it."""
    by_hand = (
        "starting_cash: {value: 5000, provisional: true, cash_multiple: 2, cash_round_to: 5000, "
        "calibration_cash: 1000000, entries: ["
        "{symbol: SYN, strategy: baseline_pmcc, time: '2026-07-06T10:00:00-04:00', contract: X, "
        "cost: 900}]}\n"
    )
    universe.write_text(_universe() + by_hand, encoding="utf-8", newline="\n")

    code, output = _calibrate(market)

    assert code == 1
    assert "without pmcc calibrate's block" in output
    assert "it is unchanged" in output
    assert universe.read_text(encoding="utf-8") == _universe() + by_hand


def test_dec_30_calibrate_defaults_to_both_strategies(universe: Path, market: Path) -> None:
    """Until P4-03 writes configs/quant_pmcc.yaml, the default calibration can't run."""
    result = runner.invoke(app, ["calibrate", "--symbol", "SYN", "--cache", str(market)])

    assert result.exit_code == 1
    assert "quant_pmcc.yaml" in result.output
    assert universe.read_text(encoding="utf-8") == _universe()


def test_dec_30_calibrate_refuses_a_symbol_outside_the_universe(
    universe: Path, market: Path
) -> None:
    result = runner.invoke(app, ["calibrate", "--symbol", "NVDA", "--config", BASELINE])

    assert result.exit_code == 1
    assert "isn't in configs/universe.yaml" in result.output
    assert universe.read_text(encoding="utf-8") == _universe()


def test_dec_30_calibrate_without_a_cache_fails_and_writes_nothing(
    universe: Path, tmp_path: Path
) -> None:
    code, output = _calibrate(tmp_path / "empty_cache")

    assert code == 1
    assert "SYN:" in output
    assert universe.read_text(encoding="utf-8") == _universe()


def test_dec_30_calibrate_fails_rather_than_write_a_value_that_blocks_entries(
    universe: Path, market: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(calibration, "starting_cash_for", _fixed(Money.from_dollars(100)))

    code, output = _calibrate(market)

    assert code == 1
    assert "calibration failed" in output
    assert "configs/universe.yaml is unchanged" in output
    assert universe.read_text(encoding="utf-8") == _universe()


def _fixed(value: Money) -> Callable[..., Money]:
    """A stand-in for `starting_cash_for` that always answers `value`."""

    def rule(*_args: object) -> Money:
        return value

    return rule
