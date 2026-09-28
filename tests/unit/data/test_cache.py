"""The raw cache: atomic unit writes, never overwriting, sidecars, the manifest and its hash.

DEC-46. Pulls come from `FakeLseg` through the real `LsegProvider` and `fetch_contracts`
(`tests.fakes.pulls`), so what is cached is what a real fetch returns.
"""

import json
import shutil
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from pmcc.data import cache as cache_module
from pmcc.data import files
from pmcc.data.cache import (
    CacheError,
    Status,
    SymbolCache,
    UnitPull,
    bars_sha256,
    chain_pull,
    data_manifest_hash,
    stock_pull,
)
from pmcc.data.discovery import Band, Pad, Region, Unit
from pmcc.data.fetch import BarRequest, fetch_contracts, fetch_rics
from pmcc.data.provider import Interval
from pmcc.data.ric import RicForm, build_ric, occ_symbol
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price
from tests.fakes.lseg import fake_provider
from tests.fakes.pulls import (
    CHAIN,
    DAY,
    EXPIRY,
    FETCH_DATE,
    FETCHED_AT,
    FIELDS,
    PUTS,
    STOCK,
    STOCK_RIC,
    SYMBOL,
    call,
    market,
    option_bars,
    pull_chain,
    pull_stock,
    put,
    request,
)

LATER = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)


def _cache(root: Path, symbol: str = SYMBOL) -> SymbolCache:
    return SymbolCache(root, symbol)


def _sidecar(cache: SymbolCache, unit: str = CHAIN.name) -> dict[str, Any]:
    return json.loads(cache.sidecar_path(unit).read_bytes())


def _manifest(cache: SymbolCache) -> dict[str, Any]:
    return json.loads(cache.manifest_path.read_bytes())


def _files(root: Path) -> list[str]:
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())


# --- The unit's parquet -----------------------------------------------------------------------


def test_cache_parquet_holds_the_bars_raw_as_returned(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_chain(market({100: option_bars()}), [100]))
    frame = pl.read_parquet(cache.parquet_path(CHAIN.name))
    ric = build_ric(call(100), RicForm.EXPIRED)
    assert frame.columns == ["bar_start_utc", "ric", "expiry", "strike_cents", "right", *FIELDS]
    assert frame.schema["bar_start_utc"] == pl.Datetime("us", "UTC")
    assert frame.rows() == [
        (datetime(2026, 9, 14, 17, tzinfo=UTC), ric, EXPIRY, 10_000, "C", 1.0, 1.2, 1.1),
        (datetime(2026, 9, 14, 18, tzinfo=UTC), ric, EXPIRY, 10_000, "C", 1.1, 1.3, None),
    ]


def test_cache_parquet_keeps_a_column_for_a_field_that_never_came_back(tmp_path: Path) -> None:
    fake = market({100: {"BID": [1.0, 1.1, None], "ASK": [1.2, 1.3, None]}})
    cache = _cache(tmp_path)
    cache.write_unit(pull_chain(fake, [100]))
    frame = pl.read_parquet(cache.parquet_path(CHAIN.name))
    assert frame["TRDPRC_1"].null_count() == frame.height
    assert _sidecar(cache)["fields_returned"] == ["ASK", "BID"]


def test_cache_stock_parquet_has_no_contract_columns(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_stock(market({})))
    frame = pl.read_parquet(cache.parquet_path(STOCK.name))
    assert frame["ric"].unique().to_list() == [STOCK_RIC]
    assert frame.select("expiry", "strike_cents", "right").null_count().row(0) == (3, 3, 3)
    assert frame["BID"].to_list() == [180.01, 180.11, 180.21]


# --- The sidecar (LDG §5) ---------------------------------------------------------------------


def test_cache_sidecar_records_the_request(tmp_path: Path) -> None:
    band = Band(Region.NEAR_MONEY, Price.from_dollars(95), Price.from_dollars(105), Pad(2), Pad(6))
    unit = Unit(CHAIN.name, DAY, DAY, EXPIRY, Right.CALL, (band,))
    cache = _cache(tmp_path)
    cache.write_unit(pull_chain(market({100: option_bars()}), [100], unit=unit, steps=[100]))
    side = _sidecar(cache)
    assert side["request"]["fields"] == list(FIELDS)
    assert (side["request"]["start"], side["request"]["end_exclusive"]) == (
        "2026-09-14",
        "2026-09-15",
    )
    assert side["request"]["interval"] == "hourly"
    assert "UTC" in side["request"]["tz"]
    assert side["request"]["bands"] == [
        {"region": "near_money", "low": "95.0000", "high": "105.0000", "step_cents": 100}
    ]
    assert (side["expiry"], side["right"]) == ("2026-09-18", "C")


def test_cache_sidecar_records_forms_misses_and_pull_date(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_chain(market({100: option_bars()}), [100, 999]))
    side = _sidecar(cache)
    answered = build_ric(call(100), RicForm.EXPIRED)
    assert side["ric_form_used"] == {answered: "expired"}
    never = side["unanswered"][occ_symbol(call(999))]
    assert [m["ric"] for m in never] == [
        build_ric(call(999), RicForm.EXPIRED),
        build_ric(call(999), RicForm.LIVE),
    ]
    assert {m["reason"] for m in never} == {"no_data"}
    assert side["errors"]  # the rejected batch and the single-RIC no-data answers
    assert side["pulled_at"] == "2026-09-26T14:30:00+00:00"


def test_cache_counts_contracts_not_rics(tmp_path: Path) -> None:
    """A strike asked under both forms is one contract (LDG §5)."""
    cache = _cache(tmp_path)
    cache.write_unit(pull_chain(market({100: option_bars(), 101: option_bars()}), [100, 101, 999]))
    side = _sidecar(cache)
    assert side["counts"] == {"requested": 3, "answered": 2, "unanswered": 1}
    statuses = [e["status"] for e in side["entries"]]
    assert statuses.count("answered") + statuses.count("unanswered") == 3


def test_cache_live_answer_after_a_caret_miss_is_recorded_as_live(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_chain(market({100: option_bars()}, form=RicForm.LIVE), [100]))
    (entry,) = _sidecar(cache)["entries"]
    assert (entry["ric"], entry["form"]) == (build_ric(call(100), RicForm.LIVE), "live")


def test_cache_refuses_a_pull_missing_a_requested_contract() -> None:
    options = [call(100), call(101)]
    result = fetch_contracts(
        fake_provider(market({100: option_bars()})), options[:1], request(CHAIN), FETCH_DATE
    )
    with pytest.raises(ValueError, match="per contract"):
        chain_pull(SYMBOL, CHAIN, request(CHAIN), (), options, result, FETCHED_AT)


def test_cache_refuses_a_pull_with_a_contract_nobody_requested() -> None:
    options = [call(100), call(101)]
    result = fetch_contracts(
        fake_provider(market({100: option_bars()})), options, request(CHAIN), FETCH_DATE
    )
    with pytest.raises(ValueError, match="per contract"):
        chain_pull(SYMBOL, CHAIN, request(CHAIN), (), options[:1], result, FETCHED_AT)


def test_cache_refuses_a_contract_outside_the_unit() -> None:
    put = OptionId(SYMBOL, EXPIRY, Right.PUT, Price.from_dollars(100))
    result = fetch_contracts(fake_provider(market({})), [put], request(CHAIN), FETCH_DATE)
    with pytest.raises(ValueError, match="outside unit"):
        chain_pull(SYMBOL, CHAIN, request(CHAIN), (), [put], result, FETCHED_AT)


def test_cache_refuses_a_request_for_other_dates_than_the_unit() -> None:
    pull = pull_chain(market({100: option_bars()}), [100])
    wrong = BarRequest(FIELDS, DAY, date(2026, 9, 16), Interval.HOURLY)
    with pytest.raises(ValueError, match="DEC-47"):
        replace(pull, request=wrong)


def test_cache_refuses_daily_bars() -> None:
    pull = pull_chain(market({100: option_bars()}), [100])
    daily = BarRequest(FIELDS, DAY, date(2026, 9, 15), Interval.DAILY)
    with pytest.raises(ValueError, match="hourly"):
        replace(pull, request=daily)


def test_cache_refuses_a_step_count_that_isnt_the_bands() -> None:
    pull = pull_chain(market({100: option_bars()}), [100])
    with pytest.raises(ValueError, match="bands"):
        replace(pull, steps=(100,))


def test_cache_refuses_a_stock_pull_of_several_rics() -> None:
    rics = [STOCK_RIC, "NVDA.N"]
    result = fetch_rics(fake_provider(market({})), rics, request(STOCK))
    with pytest.raises(ValueError, match="one RIC"):
        stock_pull(SYMBOL, STOCK, request(STOCK), result, FETCHED_AT)


def test_cache_records_an_unanswered_stock(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_stock(market({}, stock=None)))
    (entry,) = _sidecar(cache, STOCK.name)["entries"]
    assert (entry["instrument"], entry["status"], entry["rows"]) == (STOCK_RIC, "unanswered", 0)


# --- Atomic writes ----------------------------------------------------------------------------


def test_cache_interrupted_parquet_write_leaves_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(*_: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(files.os, "link", fail)
    with pytest.raises(OSError, match="disk full"):
        _cache(tmp_path).write_unit(pull_chain(market({100: option_bars()}), [100]))
    assert _files(tmp_path) == []


def test_cache_interrupted_sidecar_write_leaves_no_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = files.write_new

    def parquet_only(path: Path, data: bytes) -> None:
        if path.name.endswith(".sidecar.json"):
            raise KeyboardInterrupt
        real(path, data)

    monkeypatch.setattr(cache_module, "write_new", parquet_only)
    with pytest.raises(KeyboardInterrupt):
        _cache(tmp_path).write_unit(pull_chain(market({100: option_bars()}), [100]))
    assert _files(tmp_path) == []


def test_cache_unit_is_cached_once_its_sidecar_is_written(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    assert not cache.has_unit(CHAIN.name)
    cache.write_unit(pull_chain(market({100: option_bars()}), [100]))
    assert cache.has_unit(CHAIN.name)
    assert _files(tmp_path) == [
        "NVDA/chains/2026-09-18_C.parquet",
        "NVDA/chains/2026-09-18_C.sidecar.json",
        "NVDA/manifest.json",
    ]


# --- Never overwritten ------------------------------------------------------------------------


def test_cache_existing_unit_is_never_overwritten(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_chain(market({100: option_bars()}), [100]))
    before = {p: (tmp_path / p).read_bytes() for p in _files(tmp_path)}
    again = pull_chain(market({100: option_bars(bump=0.5)}), [100], fetched_at=LATER)
    with pytest.raises(FileExistsError, match="never overwritten"):
        cache.write_unit(again)
    assert {p: (tmp_path / p).read_bytes() for p in _files(tmp_path)} == before


def test_cache_orphan_parquet_blocks_its_unit_and_is_kept(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    orphan = cache.parquet_path(CHAIN.name)
    orphan.parent.mkdir(parents=True)
    orphan.write_bytes(b"killed mid-write")
    assert cache.orphans() == (orphan,)
    with pytest.raises(FileExistsError):
        cache.write_unit(pull_chain(market({100: option_bars()}), [100]))
    assert orphan.read_bytes() == b"killed mid-write"


def test_cache_refuses_another_symbols_unit(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="TSLA"):
        _cache(tmp_path, "TSLA").write_unit(pull_chain(market({100: option_bars()}), [100]))


def test_cache_unit_moved_aside_is_pulled_again(tmp_path: Path) -> None:
    """The PO's re-pull (DEC-46): move the unit's two files; the manifest follows the sidecars."""
    cache = _cache(tmp_path)
    cache.write_unit(pull_stock(market({})))
    cache.write_unit(pull_chain(market({100: option_bars()}), [100]))
    aside = cache.dir / "superseded"
    aside.mkdir()
    for path in (cache.parquet_path(CHAIN.name), cache.sidecar_path(CHAIN.name)):
        shutil.move(path, aside / path.name)
    assert not cache.has_unit(CHAIN.name)
    cache.write_unit(pull_chain(market({100: option_bars(bump=0.5)}), [100], fetched_at=LATER))
    assert _manifest(cache)["units"] == ["stock", CHAIN.name]
    assert _sidecar(cache)["pulled_at"] == LATER.isoformat()


# --- The manifest and the data-manifest hash --------------------------------------------------


def test_cache_manifest_lists_every_contract_of_every_unit(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_stock(market({})))
    cache.write_unit(pull_chain(market({100: option_bars()}), [100, 999]))
    manifest = _manifest(cache)
    assert manifest["units"] == ["stock", CHAIN.name]
    rows = {(e["unit"], e["instrument"]): e for e in manifest["entries"]}
    assert set(rows) == {
        ("stock", STOCK_RIC),
        (CHAIN.name, occ_symbol(call(100))),
        (CHAIN.name, occ_symbol(call(999))),
    }
    answered = rows[(CHAIN.name, occ_symbol(call(100)))]
    assert answered["rows"] == 2
    assert answered["first_bar"] == "2026-09-14T17:00:00+00:00"
    assert answered["last_bar"] == "2026-09-14T18:00:00+00:00"
    assert answered["fetched_at"] == FETCHED_AT.isoformat()
    assert len(answered["sha256"]) == 64
    assert rows[(CHAIN.name, occ_symbol(call(999)))]["status"] == Status.UNANSWERED


def test_cache_manifest_is_canonical_json(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_stock(market({})))
    raw = cache.manifest_path.read_bytes()
    assert raw.endswith(b"}\n")
    assert b"\r" not in raw
    assert raw == (json.dumps(json.loads(raw), indent=2, sort_keys=True) + "\n").encode()


def _hash(root: Path, symbol: str = SYMBOL) -> str:
    return _manifest(_cache(root, symbol))["data_manifest_hash"]


def _write(root: Path, *pulls: UnitPull) -> None:
    for pull in pulls:
        SymbolCache(root, pull.symbol).write_unit(pull)


def test_cache_hash_ignores_fetch_times(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    _write(first, pull_stock(market({})), pull_chain(market({100: option_bars()}), [100]))
    _write(
        second,
        pull_stock(market({}), fetched_at=LATER),
        pull_chain(market({100: option_bars()}), [100], fetched_at=LATER),
    )
    assert _hash(first) == _hash(second)
    assert _manifest(_cache(first))["entries"] != _manifest(_cache(second))["entries"]


def test_cache_hash_ignores_which_form_answered(tmp_path: Path) -> None:
    """PO, DEC-46: identical bars under the caret or the live RIC hash the same."""
    caret, live = tmp_path / "caret", tmp_path / "live"
    _write(caret, pull_chain(market({100: option_bars()}, form=RicForm.EXPIRED), [100]))
    _write(live, pull_chain(market({100: option_bars()}, form=RicForm.LIVE), [100]))
    assert _hash(caret) == _hash(live)


def test_cache_hash_changes_with_a_bar(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    _write(first, pull_chain(market({100: option_bars()}), [100]))
    _write(second, pull_chain(market({100: option_bars(bump=0.01)}), [100]))
    assert _hash(first) != _hash(second)


def test_cache_hash_changes_when_a_contract_goes_unanswered(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    _write(first, pull_chain(market({100: option_bars(), 101: option_bars()}), [100, 101]))
    _write(second, pull_chain(market({100: option_bars()}), [100, 101]))
    assert _hash(first) != _hash(second)


def test_cache_hash_changes_with_a_new_unit(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_stock(market({})))
    before = _hash(tmp_path)
    cache.write_unit(pull_chain(market({100: option_bars()}), [100]))
    assert _hash(tmp_path) != before


def test_cache_hash_is_untouched_by_another_symbol(tmp_path: Path) -> None:
    _write(tmp_path, pull_stock(market({})))
    before = _hash(tmp_path)
    _write(tmp_path, pull_stock(market({}), symbol="TSLA"))
    assert _hash(tmp_path) == before


def test_cache_sidecar_format_is_checked(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_stock(market({})))
    path = cache.sidecar_path(STOCK.name)
    side = json.loads(path.read_bytes())
    path.write_bytes(json.dumps({**side, "format": 99}).encode())
    with pytest.raises(CacheError, match="format"):
        cache.units()


def _bars(ric: str, last_ask: float | None = 1.3, last_hour: int = 18) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "bar_start_utc": [
                datetime(2026, 9, 14, 17, tzinfo=UTC),
                datetime(2026, 9, 14, last_hour, tzinfo=UTC),
            ],
            "ric": [ric, ric],
            "BID": [1.0, 1.1],
            "ASK": [1.2, last_ask],
        }
    )


def test_cache_bars_hash_covers_every_bar() -> None:
    assert bars_sha256(_bars("A"), ["BID", "ASK"]) != bars_sha256(_bars("A", 1.31), ["BID", "ASK"])


def test_cache_bars_hash_covers_stamps_and_empty_cells() -> None:
    base = bars_sha256(_bars("A"), ["BID", "ASK"])
    assert bars_sha256(_bars("A", last_hour=19), ["BID", "ASK"]) != base
    assert bars_sha256(_bars("A", None), ["BID", "ASK"]) != base


def test_cache_bars_hash_ignores_the_ric_and_row_order() -> None:
    base = bars_sha256(_bars("A"), ["BID", "ASK"])
    assert bars_sha256(_bars("B").reverse(), ["ASK", "BID"]) == base


def _three_fields(bid: float = 1.0, trade: float = 1.1, ask: float = 1.2) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "bar_start_utc": [datetime(2026, 9, 14, 17, tzinfo=UTC)],
            "ric": ["A"],
            "ASK": [ask],
            "BID": [bid],
            "TRDPRC_1": [trade],
        }
    )


@pytest.mark.parametrize(
    "changed",
    [
        {"bid": 1.01},
        {"trade": 1.11},
        {"ask": 1.21},
        {"trade": 1.10001},
        {"bid": 1.00005},
        {"bid": 1.0000001},  # the 7th significant digit: %g would drop it
    ],
)
def test_cache_bars_hash_covers_every_field_to_the_last_digit(changed: dict[str, float]) -> None:
    fields = ["BID", "ASK", "TRDPRC_1"]
    assert bars_sha256(_three_fields(**changed), fields) != bars_sha256(_three_fields(), fields)


def test_cache_data_manifest_hash_ignores_entry_order(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_stock(market({})))
    cache.write_unit(pull_chain(market({100: option_bars(), 101: option_bars()}), [100, 101, 999]))
    listed = [e for u in cache.units() for e in u.entries]
    assert data_manifest_hash(reversed(listed)) == data_manifest_hash(listed)


def test_cache_entry_summarizes_each_contracts_own_bars(tmp_path: Path) -> None:
    one_bar = {"BID": [2.0, None, None], "ASK": [2.2, None, None]}
    cache = _cache(tmp_path)
    cache.write_unit(pull_chain(market({100: option_bars(), 101: one_bar}), [100, 101]))
    rows = {e["instrument"]: e for e in _sidecar(cache)["entries"]}
    two, one = rows[occ_symbol(call(100))], rows[occ_symbol(call(101))]
    assert (two["rows"], two["first_bar"], two["last_bar"]) == (
        2,
        "2026-09-14T17:00:00+00:00",
        "2026-09-14T18:00:00+00:00",
    )
    assert (one["rows"], one["first_bar"], one["last_bar"]) == (
        1,
        "2026-09-14T17:00:00+00:00",
        "2026-09-14T17:00:00+00:00",
    )
    alone = tmp_path / "alone"
    SymbolCache(alone, SYMBOL).write_unit(pull_chain(market({100: option_bars()}), [100]))
    (only,) = _sidecar(SymbolCache(alone, SYMBOL))["entries"]
    assert two["sha256"] == only["sha256"]


def test_cache_put_unit_holds_puts(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_chain(market({}, puts={100: option_bars()}), [100], unit=PUTS))
    frame = pl.read_parquet(cache.parquet_path(PUTS.name))
    assert frame["right"].unique().to_list() == ["P"]
    assert frame["ric"].unique().to_list() == [build_ric(put(100), RicForm.EXPIRED)]
    assert _sidecar(cache, PUTS.name)["right"] == "P"


def test_cache_refuses_a_contract_of_another_expiry() -> None:
    other = OptionId(SYMBOL, date(2026, 9, 25), Right.CALL, Price.from_dollars(100))
    result = fetch_contracts(fake_provider(market({})), [other], request(CHAIN), FETCH_DATE)
    with pytest.raises(ValueError, match="outside unit"):
        chain_pull(SYMBOL, CHAIN, request(CHAIN), (), [other], result, FETCHED_AT)


def test_cache_records_why_a_contract_went_unanswered(tmp_path: Path) -> None:
    """A RIC that answers with no bars in the window is `empty`, not `no_data` (DEC-49)."""
    no_bars = {"BID": [None, None, None], "ASK": [None, None, None]}
    cache = _cache(tmp_path)
    cache.write_unit(pull_chain(market({100: option_bars(), 101: no_bars}), [100, 101]))
    (caret, live) = _sidecar(cache)["unanswered"][occ_symbol(call(101))]
    assert (caret["reason"], live["reason"]) == ("empty", "no_data")


def test_cache_pull_refuses_a_contract_both_answered_and_unanswered() -> None:
    pull = pull_chain(market({100: option_bars()}), [100, 999])
    both = {**pull.unanswered, **{k: () for k in pull.answered}}
    with pytest.raises(ValueError, match="both"):
        replace(pull, unanswered=both)


def test_cache_pull_refuses_bars_from_a_ric_that_didnt_answer() -> None:
    pull = pull_chain(market({100: option_bars()}), [100])
    with pytest.raises(ValueError, match="answering RICs"):
        replace(pull, answered={})


def test_cache_pull_refuses_a_naive_fetch_time() -> None:
    pull = pull_chain(market({100: option_bars()}), [100])
    with pytest.raises(ValueError, match="tz-aware"):
        replace(pull, fetched_at=datetime(2026, 9, 26, 14, 30))


def test_cache_unit_renamed_in_place_is_refused(tmp_path: Path) -> None:
    """Moved aside means out of `chains/`: a pair renamed beside it is never read as the unit."""
    cache = _cache(tmp_path)
    cache.write_unit(pull_stock(market({})))
    cache.write_unit(pull_chain(market({100: option_bars()}), [100]))
    for path in (cache.parquet_path(CHAIN.name), cache.sidecar_path(CHAIN.name)):
        path.rename(path.with_name(path.name.replace("_C.", "_C_old.")))
    with pytest.raises(CacheError, match="renamed in place"):
        cache.units()
    before = _files(tmp_path)
    with pytest.raises(CacheError, match="renamed in place"):
        cache.write_unit(pull_chain(market({100: option_bars()}), [100]))
    assert _files(tmp_path) == before


def test_cache_unreadable_sidecar_stops_a_write_before_it_starts(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    cache.write_unit(pull_stock(market({})))
    path = cache.sidecar_path(STOCK.name)
    path.write_bytes(json.dumps({**json.loads(path.read_bytes()), "format": 99}).encode())
    with pytest.raises(CacheError, match="format"):
        cache.write_unit(pull_chain(market({100: option_bars()}), [100]))
    assert not cache.parquet_path(CHAIN.name).exists()


def test_cache_partial_left_by_a_killed_write_doesnt_block_the_unit(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    stale = cache.dir / "chains" / "2026-09-18_C.parquet.partial"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"killed")
    cache.write_unit(pull_chain(market({100: option_bars()}), [100]))
    assert cache.has_unit(CHAIN.name)
    assert cache.orphans() == ()
