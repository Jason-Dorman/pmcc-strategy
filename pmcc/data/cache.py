"""The raw cache: one parquet and one sidecar per fetch unit, and the symbol's manifest (DEC-46).

```
data_cache/{SYM}/manifest.json
data_cache/{SYM}/stock.parquet                  stock.sidecar.json
data_cache/{SYM}/chains/{YYYY-MM-DD}_{C|P}.parquet    ….sidecar.json
```

- **A unit is its parquet and its sidecar.** The parquet is written first and the sidecar last,
  each whole or not at all (`write_new`), so a unit exists once its sidecar does. A write that
  fails before the sidecar is written removes the parquet it wrote, so it leaves no file. Only a
  process killed between the two leaves a parquet with no sidecar, and the next write of that unit
  refuses rather than replace it.
- **Nothing is overwritten.** A unit already cached is refused. To pull one again, the user moves
  its two files out of the unit's folder (e.g. into `{SYM}/superseded/`) and the next fetch pulls
  it (PO, DEC-46). A sidecar must sit at its own unit's path: one renamed in place is refused, not
  read as the unit it records.
- **The sidecar** holds what LDG §5 asks for, plus the unit's manifest entries: one per contract
  asked, so answered + unanswered = requested counts contracts, not RICs.
- **`manifest.json` is an index,** rebuilt from the sidecars after every write. The sidecars are
  the record, and the loader reads them.
- **The data-manifest hash** covers what the data is: each contract's identity, status, row count,
  first and last bar, and a hash of its bars. It leaves out when a contract was fetched and which
  RIC form answered, so re-pulling identical bars never changes it (PO, DEC-46).
"""

import hashlib
import io
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, final

import polars as pl

from pmcc.data.discovery import Region, StepMeasure, StepSource, Unit
from pmcc.data.fetch import BarRequest, ContractsResult, Miss, RequestError, RicsResult
from pmcc.data.files import replace_file, write_new
from pmcc.data.provider import Interval, RawHistory
from pmcc.data.ric import RicForm, occ_symbol, parse_ric
from pmcc.domain.instruments import OptionId, Right
from pmcc.domain.money import Price

FORMAT = 1
STOCK_UNIT = "stock"
MANIFEST = "manifest.json"
SUPERSEDED = "superseded"  # where a user moves units to pull them again; never read
PARQUET = ".parquet"
SIDECAR = ".sidecar.json"
TZ_CONVENTION = (
    "bar_start_utc is LSEG's stamp: the bar's start, in UTC (LDG §4.8). "
    "bar_end = bar_start + 1h, in America/New_York, is added at load (DEC-06)."
)
KEY_COLUMNS = {
    "bar_start_utc": pl.Datetime("us", "UTC"),
    "ric": pl.String(),
    "expiry": pl.Date(),
    "strike_cents": pl.Int64(),
    "right": pl.String(),
}


class CacheError(Exception):
    """The cache on disk isn't what its sidecars say: a missing, changed or orphaned file."""


class Status(StrEnum):
    ANSWERED = "answered"
    UNANSWERED = "unanswered"


# --- What a unit's fetch returned -------------------------------------------------------------


@final
@dataclass(frozen=True, slots=True)
class UnitPull:
    """One unit's answers, ready to cache.

    `answered` maps each contract that answered (its OCC symbol, or the stock's RIC) to the RIC
    that answered, and `unanswered` maps each one that didn't to the RICs asked for it. Together
    they are every contract asked, once (LDG §5). `steps` is the strike step of each of the unit's
    bands, in cents (DEC-84), and `increments` says how each was found (DEC-14; empty when the
    steps were given, not measured). Build one with `chain_pull` or `stock_pull`.
    """

    symbol: str
    unit: Unit
    request: BarRequest
    steps: tuple[int, ...]
    history: RawHistory
    answered: Mapping[str, str]
    unanswered: Mapping[str, tuple[str, ...]]
    ric_form_used: Mapping[str, RicForm]
    misses: Mapping[str, Miss]
    errors: tuple[RequestError, ...]
    fetched_at: datetime
    increments: tuple[StepMeasure, ...] = ()

    def __post_init__(self) -> None:
        if self.request.interval is not Interval.HOURLY:
            raise ValueError("the cache holds hourly bars only")
        if (self.request.start, self.request.end_exclusive) != _dates(self.unit):
            raise ValueError(f"the request's dates aren't unit {self.unit.name}'s (DEC-47)")
        if len(self.steps) != len(self.unit.bands):
            raise ValueError(f"unit {self.unit.name} has {len(self.unit.bands)} bands, not steps")
        if self.increments and tuple(m.step for m in self.increments) != self.steps:
            raise ValueError("each band's step must be the one its increment measure found")
        if self.answered.keys() & self.unanswered.keys():
            raise ValueError("a contract can't be both answered and unanswered")
        if self.history.rics() != frozenset(self.answered.values()):
            raise ValueError("the bars must be exactly the answering RICs'")
        if self.fetched_at.utcoffset() is None:
            raise ValueError("fetched_at must be tz-aware")


def _dates(unit: Unit) -> tuple[date, date]:
    return unit.start, unit.end + timedelta(days=1)


def chain_pull(
    symbol: str,
    unit: Unit,
    request: BarRequest,
    steps: Sequence[int],
    options: Sequence[OptionId],
    result: ContractsResult,
    fetched_at: datetime,
    increments: Sequence[StepMeasure] = (),
) -> UnitPull:
    """A chain unit's pull. Raises `ValueError` unless every contract in `options` is either
    answered or unanswered in `result`, and nothing else is (LDG §5, per contract)."""
    asked = set(options)
    strays = sorted(o for o in asked if (o.expiry, o.right) != (unit.expiry, unit.right))
    if strays:
        raise ValueError(f"contracts outside unit {unit.name}: {strays[:3]}")
    if set(result.answered) | set(result.unanswered) != asked:
        raise ValueError("answered + unanswered must be the contracts requested, per contract")
    tried: dict[OptionId, list[str]] = {}
    for ric in result.requested:
        tried.setdefault(parse_ric(ric).option, []).append(ric)
    return UnitPull(
        symbol=symbol,
        unit=unit,
        request=request,
        steps=tuple(steps),
        history=result.history,
        answered={occ_symbol(o): ric for o, ric in result.answered.items()},
        unanswered={occ_symbol(o): tuple(tried.get(o, ())) for o in result.unanswered},
        ric_form_used=result.ric_form_used,
        misses=result.misses,
        errors=result.errors,
        fetched_at=fetched_at,
        increments=tuple(increments),
    )


def stock_pull(
    symbol: str, unit: Unit, request: BarRequest, result: RicsResult, fetched_at: datetime
) -> UnitPull:
    """The stock unit's pull: one RIC, the stock's own."""
    if len(result.requested) != 1:
        raise ValueError(f"the stock unit asks for one RIC, not {len(result.requested)}")
    (ric,) = result.requested
    return UnitPull(
        symbol=symbol,
        unit=unit,
        request=request,
        steps=(),
        history=result.history,
        answered={ric: ric} if ric in result.answered else {},
        unanswered={} if ric in result.answered else {ric: (ric,)},
        ric_form_used={},
        misses=result.misses,
        errors=result.errors,
        fetched_at=fetched_at,
    )


# --- Manifest entries and the data-manifest hash ----------------------------------------------


@final
@dataclass(frozen=True, slots=True)
class Entry:
    """One contract's manifest row. `ric` and `form` are the RIC that answered and its form."""

    instrument: str
    unit: str
    status: Status
    ric: str | None
    form: RicForm | None
    rows: int
    first_bar: datetime | None
    last_bar: datetime | None
    sha256: str | None
    fetched_at: datetime

    def content(self) -> dict[str, object]:
        """What the data-manifest hash covers: not `ric`, `form` or `fetched_at` (DEC-46)."""
        return {
            "instrument": self.instrument,
            "unit": self.unit,
            "status": self.status.value,
            "rows": self.rows,
            "first_bar": _iso(self.first_bar),
            "last_bar": _iso(self.last_bar),
            "sha256": self.sha256,
        }

    def to_json(self) -> dict[str, object]:
        return {
            **self.content(),
            "ric": self.ric,
            "form": None if self.form is None else self.form.value,
            "fetched_at": _iso(self.fetched_at),
        }

    @classmethod
    def from_json(cls, raw: Mapping[str, Any]) -> "Entry":
        return cls(
            instrument=raw["instrument"],
            unit=raw["unit"],
            status=Status(raw["status"]),
            ric=raw["ric"],
            form=None if raw["form"] is None else RicForm(raw["form"]),
            rows=raw["rows"],
            first_bar=_datetime(raw["first_bar"]),
            last_bar=_datetime(raw["last_bar"]),
            sha256=raw["sha256"],
            fetched_at=_parse_datetime(raw["fetched_at"]),
        )


def data_manifest_hash(entries: Iterable[Entry]) -> str:
    """sha256 of every entry's content, in (unit, instrument) order (DEC-46)."""
    content = sorted((e.content() for e in entries), key=lambda c: (c["unit"], c["instrument"]))
    return hashlib.sha256(_canonical(content)).hexdigest()


def bars_sha256(bars: pl.DataFrame, fields: Sequence[str]) -> str:
    """sha256 of one contract's bars: each bar's start and its fields' values, in time order.

    The RIC isn't part of it, so the same bars hash the same under either form (DEC-46).
    """
    digest = hashlib.sha256()
    names = sorted(fields)
    for stamp, *values in bars.sort("bar_start_utc").select("bar_start_utc", *names).iter_rows():
        cells = "|".join("" if v is None else float.__repr__(v) for v in values)
        digest.update(f"{stamp.isoformat()}|{cells}\n".encode())
    return digest.hexdigest()


# --- The unit's files -------------------------------------------------------------------------


def unit_frame(pull: UnitPull) -> pl.DataFrame:
    """The parquet's rows: one per RIC and bar, raw as returned (ARCHITECTURE §6.4).

    `bar_start_utc`, `ric`, `expiry`, `strike_cents` and `right` (null for the stock), then one
    float64 column per field requested, null where the answer had no value.
    """
    fields = pull.request.fields
    schema = pl.Schema({**KEY_COLUMNS, **dict.fromkeys(fields, pl.Float64())})
    rows = pull.history.rows.filter(pl.col("field").is_in(fields))
    if rows.is_empty():
        return pl.DataFrame(schema=schema)
    wide = rows.rename({"bar_start": "bar_start_utc"}).pivot(
        on="field", index=["bar_start_utc", "ric"], values="value"
    )
    missing = [pl.lit(None, pl.Float64()).alias(f) for f in fields if f not in wide.columns]
    return (
        _with_contracts(wide.with_columns(missing), pull.unit)
        .select(list(schema))
        .cast(schema)
        .sort("ric", "bar_start_utc")
    )


def _with_contracts(wide: pl.DataFrame, unit: Unit) -> pl.DataFrame:
    """Each RIC's contract, parsed from the RIC; nulls for the stock."""
    if unit.expiry is None:
        return wide.with_columns(
            pl.lit(None, KEY_COLUMNS[c]).alias(c) for c in ("expiry", "strike_cents", "right")
        )
    rics: list[str] = wide["ric"].unique().to_list()
    options = [parse_ric(ric).option for ric in rics]
    contracts = pl.DataFrame(
        {
            "ric": rics,
            "expiry": [o.expiry for o in options],
            "strike_cents": [o.strike_cents for o in options],
            "right": [o.right.value for o in options],
        },
    )
    return wide.join(contracts, on="ric", how="left")


def entries(pull: UnitPull, frame: pl.DataFrame) -> tuple[Entry, ...]:
    """One entry per contract asked: answered ones with their bars' summary and hash."""
    fetched = pull.fetched_at.astimezone(UTC)
    found = [
        _answered_entry(pull, instrument, ric, frame.filter(pl.col("ric") == ric), fetched)
        for instrument, ric in pull.answered.items()
    ]
    missed = [
        Entry(
            instrument, pull.unit.name, Status.UNANSWERED, None, None, 0, None, None, None, fetched
        )
        for instrument in pull.unanswered
    ]
    return tuple(sorted(found + missed, key=lambda e: e.instrument))


def _answered_entry(
    pull: UnitPull, instrument: str, ric: str, bars: pl.DataFrame, fetched: datetime
) -> Entry:
    stamps: list[datetime] = bars["bar_start_utc"].to_list()
    return Entry(
        instrument=instrument,
        unit=pull.unit.name,
        status=Status.ANSWERED,
        ric=ric,
        form=pull.ric_form_used.get(ric),
        rows=bars.height,
        first_bar=min(stamps),
        last_bar=max(stamps),
        sha256=bars_sha256(bars, pull.request.fields),
        fetched_at=fetched,
    )


def sidecar(
    pull: UnitPull, file: str, file_sha256: str, unit_entries: Sequence[Entry]
) -> dict[str, object]:
    """The unit's sidecar (LDG §5; ARCHITECTURE §6.4)."""
    unit, request = pull.unit, pull.request
    returned = sorted(set(pull.history.rows["field"].to_list()) & set(request.fields))
    return {
        "format": FORMAT,
        "symbol": pull.symbol,
        "unit": unit.name,
        "file": file,
        "file_sha256": file_sha256,
        "expiry": None if unit.expiry is None else unit.expiry.isoformat(),
        "right": None if unit.right is None else unit.right.value,
        "request": {
            "fields": list(request.fields),
            "start": request.start.isoformat(),
            "end_exclusive": request.end_exclusive.isoformat(),
            "interval": request.interval.value,
            "tz": TZ_CONVENTION,
            "bands": [
                {
                    "region": band.region.value,
                    "low": str(band.low.to_dollars()),
                    "high": str(band.high.to_dollars()),
                    "step_cents": step,
                    "increment": _increment(pull.increments[i]) if pull.increments else None,
                }
                for i, (band, step) in enumerate(zip(unit.bands, pull.steps, strict=True))
            ],
        },
        "fields_returned": returned,
        "counts": {
            "requested": len(pull.answered) + len(pull.unanswered),
            "answered": len(pull.answered),
            "unanswered": len(pull.unanswered),
        },
        "ric_form_used": {ric: form.value for ric, form in sorted(pull.ric_form_used.items())},
        "unanswered": {
            instrument: [_miss(ric, pull.misses.get(ric)) for ric in rics]
            for instrument, rics in sorted(pull.unanswered.items())
        },
        "errors": [
            {
                "rics": list(e.rics),
                "error_class": e.error_class,
                "codes": list(e.codes),
                "message": e.message,
            }
            for e in pull.errors
        ],
        "pulled_at": _iso(pull.fetched_at.astimezone(UTC)),
        "entries": [e.to_json() for e in unit_entries],
    }


def _increment(measure: StepMeasure) -> dict[str, object]:
    return {
        "session": measure.session.isoformat(),
        "anchors_cents": list(measure.anchors),
        "answered_cents": list(measure.answered),
        "source": measure.source.value,
    }


def _miss(ric: str, miss: Miss | None) -> dict[str, object]:
    if miss is None:
        return {"ric": ric, "reason": None, "codes": [], "message": None}
    return {
        "ric": ric,
        "reason": miss.reason.value,
        "codes": list(miss.codes),
        "message": miss.message,
    }


# --- One symbol's cache -----------------------------------------------------------------------


@final
@dataclass(frozen=True, slots=True)
class CachedBand:
    """A band as its unit's sidecar records it. `source` is `None` when the step was given."""

    region: Region
    low: Price
    high: Price
    step: int
    source: StepSource | None


@final
@dataclass(frozen=True, slots=True)
class CachedUnit:
    """A unit as its sidecar records it."""

    name: str
    file: str
    file_sha256: str
    expiry: date | None
    right: Right | None
    start: date
    end_exclusive: date
    entries: tuple[Entry, ...]
    bands: tuple[CachedBand, ...] = ()
    fields: tuple[str, ...] = ()
    fields_returned: tuple[str, ...] = ()


@final
class SymbolCache:
    """`data_cache/{SYM}/`: write units, list them, and read their sidecars back."""

    def __init__(self, root: Path, symbol: str) -> None:
        self.root = root
        self.symbol = symbol
        self.dir = root / symbol

    def parquet_path(self, unit: str) -> Path:
        return self.dir / f"{unit}{PARQUET}"

    def sidecar_path(self, unit: str) -> Path:
        return self.dir / f"{unit}{SIDECAR}"

    @property
    def manifest_path(self) -> Path:
        return self.dir / MANIFEST

    def has_unit(self, unit: str) -> bool:
        """Whether `unit` is cached: its sidecar, the last file written, exists."""
        return self.sidecar_path(unit).exists()

    def unit_names(self) -> tuple[str, ...]:
        """The cached units, stock first."""
        return tuple(_unit_name(self.dir, p) for p in self._sidecars())

    def orphans(self) -> tuple[Path, ...]:
        """Parquet files with no sidecar: writes killed between the two files."""
        return tuple(p for p in self._parquets() if not self.has_unit(_unit_name(self.dir, p)))

    def write_unit(self, pull: UnitPull) -> None:
        """Cache one unit, then rebuild the manifest.

        Before writing anything, raises `FileExistsError` if either of the unit's files exists
        (nothing is ever overwritten), and `CacheError` if a cached sidecar can't be read. Once the
        sidecar is written the unit is cached: if rebuilding the manifest then fails, the error
        propagates and `manifest.json` stays stale until the next write (nothing reads it back).
        """
        name = pull.unit.name
        if pull.symbol != self.symbol:
            raise ValueError(f"a {pull.symbol} unit can't go in {self.symbol}'s cache")
        for path in (self.parquet_path(name), self.sidecar_path(name)):
            if path.exists():
                raise FileExistsError(
                    f"{path} exists; cached data is never overwritten. To pull it again, move the "
                    f"unit's parquet and sidecar into {self.dir / SUPERSEDED} (DEC-46)."
                )
        self.units()  # a sidecar that can't be read fails here, before anything is written
        frame = unit_frame(pull)
        data = _parquet_bytes(frame)
        file = f"{name}{PARQUET}"
        record = sidecar(pull, file, hashlib.sha256(data).hexdigest(), entries(pull, frame))
        self._write_pair(name, data, _canonical(record))
        self.rebuild_manifest()

    def _write_pair(self, name: str, data: bytes, record: bytes) -> None:
        parquet = self.parquet_path(name)
        write_new(parquet, data)
        try:
            write_new(self.sidecar_path(name), record)
        except BaseException:
            parquet.unlink()  # written by this call; without its sidecar it isn't a unit
            raise

    def units(self) -> tuple[CachedUnit, ...]:
        """Every cached unit, from its sidecar, stock first. Raises `CacheError` for a sidecar
        in another format, or one whose recorded unit isn't the one its path names."""
        return tuple(_read_unit(p, _unit_name(self.dir, p)) for p in self._sidecars())

    def rebuild_manifest(self) -> None:
        """Rewrite `manifest.json` from the sidecars: every entry, and the data-manifest hash."""
        all_entries = [e for u in self.units() for e in u.entries]
        manifest = {
            "format": FORMAT,
            "symbol": self.symbol,
            "data_manifest_hash": data_manifest_hash(all_entries),
            "units": list(self.unit_names()),
            "entries": [
                e.to_json() for e in sorted(all_entries, key=lambda e: (e.unit, e.instrument))
            ],
        }
        replace_file(self.manifest_path, _canonical(manifest))

    def _sidecars(self) -> list[Path]:
        stock = self.sidecar_path(STOCK_UNIT)
        chains = sorted((self.dir / "chains").glob(f"*{SIDECAR}"))
        return [stock, *chains] if stock.exists() else chains

    def _parquets(self) -> list[Path]:
        stock = self.parquet_path(STOCK_UNIT)
        chains = sorted((self.dir / "chains").glob(f"*{PARQUET}"))
        return [stock, *chains] if stock.exists() else chains


def _unit_name(symbol_dir: Path, path: Path) -> str:
    relative = path.relative_to(symbol_dir).as_posix()
    for suffix in (SIDECAR, PARQUET):
        if relative.endswith(suffix):
            return relative.removesuffix(suffix)
    raise ValueError(f"not a unit file: {path}")


def _read_unit(path: Path, name: str) -> CachedUnit:
    raw: dict[str, Any] = json.loads(path.read_bytes())
    if raw.get("format") != FORMAT:
        raise CacheError(f"{path}: sidecar format {raw.get('format')!r}, expected {FORMAT}")
    if raw["unit"] != name:
        raise CacheError(
            f"{path} records unit {raw['unit']!r}, not {name!r}: a unit renamed in place. Move "
            f"its parquet and sidecar into {SUPERSEDED}/ instead (DEC-46)."
        )
    request: dict[str, Any] = raw["request"]
    return CachedUnit(
        name=name,
        file=raw["file"],
        file_sha256=raw["file_sha256"],
        expiry=None if raw["expiry"] is None else date.fromisoformat(raw["expiry"]),
        right=None if raw["right"] is None else Right(raw["right"]),
        start=date.fromisoformat(request["start"]),
        end_exclusive=date.fromisoformat(request["end_exclusive"]),
        entries=tuple(Entry.from_json(e) for e in raw["entries"]),
        bands=tuple(_cached_band(b) for b in request["bands"]),
        fields=tuple(request["fields"]),
        fields_returned=tuple(raw["fields_returned"]),
    )


def _cached_band(raw: Mapping[str, Any]) -> CachedBand:
    increment: Mapping[str, Any] | None = raw.get("increment")
    return CachedBand(
        region=Region(raw["region"]),
        low=Price.from_dollars(raw["low"]),
        high=Price.from_dollars(raw["high"]),
        step=raw["step_cents"],
        source=None if increment is None else StepSource(increment["source"]),
    )


# --- Encoding ---------------------------------------------------------------------------------


def _parquet_bytes(frame: pl.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.write_parquet(buffer)
    return buffer.getvalue()


def _canonical(value: object) -> bytes:
    """Sorted keys, two-space indent, UTF-8, LF, and a final newline."""
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode()


def _iso(t: datetime | None) -> str | None:
    return None if t is None else t.isoformat()


def _datetime(text: str | None) -> datetime | None:
    return None if text is None else _parse_datetime(text)


def _parse_datetime(text: str) -> datetime:
    return datetime.fromisoformat(text)
