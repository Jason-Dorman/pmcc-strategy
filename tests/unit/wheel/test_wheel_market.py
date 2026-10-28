"""The wheel's market (W2-02, WD-11): the cache's stock and calls with the wheel part's puts."""

import shutil
from datetime import date, datetime
from pathlib import Path

import pytest

from pmcc.config.calendar import load_calendar
from pmcc.data.cache import WHEEL_PART, CacheError, SymbolCache, data_manifest_hash
from pmcc.data.load import load_chains, load_symbol
from pmcc.domain.clock import ET
from pmcc.domain.instruments import Right
from pmcc.wheel.market import load_wheel_market
from tests.fixtures.synthetic.market import RATE, SyntheticSpec, generate

SPEC = SyntheticSpec(date(2026, 8, 31), date(2026, 9, 11), symbol="SYN")
LEFT_OUT = date(2026, 9, 11)  # week 2's expiry: its puts stay out of the part
WEEK1 = (date(2026, 8, 31), date(2026, 9, 4))
CAL = load_calendar()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """A synthetic cache whose put units, all but week 2's, are copied into the wheel part, as
    `fetch --wheel` would write its own."""
    generate(SPEC, tmp_path)
    symbol_dir = tmp_path / "SYN"
    part = symbol_dir / WHEEL_PART / "chains"
    part.mkdir(parents=True)
    for path in (symbol_dir / "chains").glob("*_P.*"):
        if not path.name.startswith(f"{LEFT_OUT:%Y-%m-%d}"):
            shutil.copy(path, part / path.name)
    return tmp_path


def test_wd_11_load_chains_reads_a_parts_units(root: Path) -> None:
    loaded = load_chains(SymbolCache(root, "SYN", part=WHEEL_PART), CAL)
    assert loaded.chains
    assert {right for _, right in loaded.chains} == {Right.PUT}
    assert len(loaded.units) == len(loaded.chains)


def test_wd_11_the_wheel_market_reads_calls_from_the_cache_and_puts_from_the_part(
    root: Path,
) -> None:
    market = load_wheel_market(root, "SYN", "SYN", CAL, RATE, WEEK1)
    read = [u for u in SymbolCache(root, "SYN").units() if u.right is not Right.PUT]
    part = SymbolCache(root, "SYN", part=WHEEL_PART).units()
    assert market.data_manifest_hash == data_manifest_hash(
        e for u in (*read, *part) for e in u.entries
    )
    assert market.data_manifest_hash != load_symbol(root, "SYN", CAL).data_manifest_hash
    view = market.data.view(datetime(2026, 9, 9, 12, tzinfo=ET))
    assert view.chain(LEFT_OUT, Right.PUT).size == 0  # the cache's own puts aren't read
    assert view.chain(LEFT_OUT, Right.CALL).size > 0


def test_wd_11_a_changed_part_file_is_refused(root: Path) -> None:
    put = next((root / "SYN" / WHEEL_PART / "chains").glob("*_P.parquet"))
    put.write_bytes(put.read_bytes() + b"\0")
    with pytest.raises(CacheError, match="changed"):
        load_wheel_market(root, "SYN", "SYN", CAL, RATE, WEEK1)


def test_wd_11_a_week_with_no_put_unit_stops_the_load(root: Path) -> None:
    # A gap in the data would read as empty chains and be logged as rule skips; it must not.
    with pytest.raises(CacheError, match="2026-09-11 puts"):
        load_wheel_market(root, "SYN", "SYN", CAL, RATE, (SPEC.window_start, SPEC.window_end))


def test_wd_11_a_week_with_no_call_unit_stops_the_load(root: Path) -> None:
    call = next((root / "SYN" / "chains").glob("2026-09-04_C.*"))
    aside = root / "SYN" / "superseded"
    aside.mkdir()
    for path in (root / "SYN" / "chains").glob("2026-09-04_C.*"):
        path.rename(aside / path.name)
    assert not call.exists()
    with pytest.raises(CacheError, match="2026-09-04 calls"):
        load_wheel_market(root, "SYN", "SYN", CAL, RATE, WEEK1)


def test_w2_03_a_window_past_the_stock_tape_stops_the_load(root: Path) -> None:
    # Sessions with no stock bars would have no spot, and every week would read as a W-T1 skip.
    with pytest.raises(CacheError, match="no stock bars on 5 of the window's 14 sessions"):
        load_wheel_market(root, "SYN", "SYN", CAL, RATE, (WEEK1[0], date(2026, 9, 18)))


def test_w2_03_the_market_names_puts_from_the_part_and_calls_from_the_cache(root: Path) -> None:
    market = load_wheel_market(root, "SYN", "SYN", CAL, RATE, WEEK1)
    part = load_chains(SymbolCache(root, "SYN", part=WHEEL_PART), CAL).chains
    cache = load_symbol(root, "SYN", CAL).chains
    put_ric = part[(WEEK1[1], Right.PUT)]["ric"][0]
    call_ric = cache[(WEEK1[1], Right.CALL)]["ric"][0]

    assert market.symbol == "SYN"
    assert put_ric in market.names.options.values()
    assert call_ric in market.names.options.values()
    assert market.names.stock == "SYN.O"
