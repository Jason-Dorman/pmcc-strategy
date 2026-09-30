"""Result models: one run's file, `results/{SYM}/{run_id}.json` (ARCHITECTURE §12).

Provisional (P3-08): the manifest, the resolved config with its rendered rule text, the starting
cash, and the run's records (blotter, ledger, gate log). The summary, cycles and attribution join
at P4-05 and P6, and the JSON Schema with them.

Typed dollars and prices are `Decimal` (exact $0.0001 units, DEC-44) and serialize as 4-dp JSON
numbers. The config keeps its own dump, dollars as "0.1000" strings, since that is what its hash
covers (DEC-90); and the free-form maps (blotter audit, gate-log values) carry dollars as the engine
records them, exact 4-dp strings (PO, DEC-92). Write a result through `pmcc.export.results`, never
`model_dump_json`: only the canonical writer is byte-stable (DEC-50).
"""

from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, WithJsonSchema, field_serializer

from pmcc.config.strategy import RunConfig

SCHEMA_VERSION = 1

_SCALAR_TYPES = (float, int, str, bool, type(None))
_JSON_SCALARS = ["number", "string", "boolean", "null"]


def _exact_scalars(values: Mapping[str, Any]) -> Mapping[str, Any]:
    """Refuses a value that isn't exactly a JSON scalar type: strict mode alone would read a
    `Decimal`, a numpy number or a numpy bool as a float."""
    for key, value in values.items():
        if type(value) not in _SCALAR_TYPES:
            raise ValueError(f"{key}: {type(value).__name__} isn't a JSON scalar: {value!r}")
    return values


# A blotter audit or gate-log value map.
ScalarMap = Annotated[
    Mapping[str, Any],
    AfterValidator(_exact_scalars),
    WithJsonSchema({"type": "object", "additionalProperties": {"type": _JSON_SCALARS}}),
]


class DataSource(StrEnum):
    LSEG = "lseg"
    SYNTHETIC = "synthetic"  # the site shows a banner (DEC-74)


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class Manifest(_Model):
    """What produced the run (Spec › Run manifest). INV-13 ignores `run_timestamp` and `git_sha`
    (PO, DEC-50)."""

    run_id: str
    symbol: str
    strategy_id: str
    git_sha: str
    git_dirty: bool  # results/ excluded; untracked files count (PO, DEC-50)
    config_hash: str
    data_manifest_hash: str
    lock_hash: str  # sha256 of uv.lock
    run_timestamp: datetime
    data_source: DataSource
    pmcc_version: str


class RuleTextOut(_Model):
    condition: str
    action: str
    rationale: str


class InstrumentOut(_Model):
    """What a row trades or holds. `ric` is the RIC the cache answered with; `occ`, `expiry` and
    `strike` are null for the stock."""

    ric: str
    occ: str | None
    kind: str  # "call", "put" or "stock"
    expiry: date | None
    strike: Decimal | None


class BlotterRow(_Model):
    """A booked trade (Spec › Blotter). `audit` holds what `pmcc verify` re-derives INV-03, 06
    and 08 from; its bid and ask are $0.0001 units, as the engine records them."""

    time: datetime
    instrument: InstrumentOut
    side: str
    qty: int
    limit: Decimal | None
    fill: Decimal | None
    fee: Decimal
    cash_delta: Decimal
    rule_id: str
    notes: str
    audit: ScalarMap


class LegOut(_Model):
    instrument: InstrumentOut
    qty: int
    mark: Decimal
    stale: bool
    delta: float | None


class StockOut(_Model):
    instrument: InstrumentOut
    shares: int  # negative when short
    mark: Decimal
    stale: bool


class LedgerRowOut(_Model):
    """One bar's positions, cash, NAV and Reg T (Spec › Ledger)."""

    time: datetime
    long: LegOut | None
    short: LegOut | None
    stock: StockOut | None
    cash: Decimal
    nav: Decimal
    im: Decimal
    mm: Decimal
    available_funds: Decimal
    excess_equity: Decimal
    flags: tuple[str, ...]


class GateOut(_Model):
    rule_id: str
    status: str
    values: ScalarMap
    reason: str


class OutcomeOut(_Model):
    kind: str  # "sold" or "skipped"
    rule_id: str


class GateLogRowOut(_Model):
    """One week-open session's short decision (Spec › Gate log; DEC-22)."""

    session: date
    decision_time: datetime | None
    selected: ScalarMap | None
    gates: tuple[GateOut, ...]
    outcome: OutcomeOut
    notes: str


class RunResult(_Model):
    """One run on one symbol: `results/{symbol}/{run_id}.json`."""

    schema_version: int = Field(default=SCHEMA_VERSION)
    manifest: Manifest
    config: RunConfig
    rule_text: Mapping[str, RuleTextOut]
    starting_cash: Decimal
    blotter: tuple[BlotterRow, ...]
    ledger: tuple[LedgerRowOut, ...]
    gate_log: tuple[GateLogRowOut, ...]

    @field_serializer("config")
    def _config_as_hashed(self, config: RunConfig) -> dict[str, Any]:
        """The config exactly as its hash covers it (`RunConfig.canonical_json`)."""
        return config.model_dump(mode="json")
