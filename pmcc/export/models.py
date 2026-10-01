"""Result models: one run's file, `results/{SYM}/{run_id}.json` (ARCHITECTURE §12).

A result holds the manifest, the resolved config with its rendered rule text, the starting cash
and the summary. A full-detail run adds its records (blotter, ledger, gate log), its cycles and,
from P6-03, its attribution; a summary run holds none of them (PO, DEC-54). The strategy's
`report` block decides which (`config.strategy.report`). Every summary holds the run's analytics
(P6, DEC-60 to DEC-62), the invariants it held and the ledger's flag counts. The analytics are
nullable so that results written before P6 still validate until P6-09 re-runs them (DEC-101).

Typed dollars and prices are `Decimal` (exact $0.0001 units, DEC-44) and serialize as 4-dp JSON
numbers. The config keeps its own dump, dollars as "0.1000" strings, since that is what its hash
covers (DEC-90); and the free-form maps (blotter audit, gate-log values) carry dollars as the engine
records them, exact 4-dp strings (PO, DEC-92). Write a result through `pmcc.export.results`, never
`model_dump_json`: only the canonical writer is byte-stable (DEC-50).
"""

from collections.abc import Mapping
from datetime import date, datetime
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from pmcc.config.strategy import Detail, RunConfig
from pmcc.export.analytics_models import (
    Attribution,
    Cycle,
    CycleStats,
    Metrics,
    NavPoint,
    WeeklyReturn,
)
from pmcc.export.base import SCHEMA_VERSION, Dollars, ScalarMap, SchemaVersion
from pmcc.export.base import Model as _Model


class DataSource(StrEnum):
    LSEG = "lseg"
    SYNTHETIC = "synthetic"  # the site shows a banner (DEC-74)


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
    strike: Dollars | None


class BlotterRow(_Model):
    """A booked trade (Spec › Blotter). `audit` holds what `pmcc verify` re-derives INV-03, 06
    and 08 from; its bid and ask are $0.0001 units, as the engine records them."""

    time: datetime
    instrument: InstrumentOut
    side: str
    qty: int
    limit: Dollars | None
    fill: Dollars | None
    fee: Dollars
    cash_delta: Dollars
    rule_id: str
    notes: str
    audit: ScalarMap


class LegOut(_Model):
    instrument: InstrumentOut
    qty: int
    mark: Dollars
    stale: bool
    delta: float | None


class StockOut(_Model):
    instrument: InstrumentOut
    shares: int  # negative when short
    mark: Dollars
    stale: bool


class LedgerRowOut(_Model):
    """One bar's positions, cash, NAV and Reg T (Spec › Ledger)."""

    time: datetime
    long: LegOut | None
    short: LegOut | None
    stock: StockOut | None
    cash: Dollars
    nav: Dollars
    im: Dollars
    mm: Dollars
    available_funds: Dollars
    excess_equity: Dollars
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


class InvariantCheck(_Model):
    """A runtime invariant the engine checked on every bar or event of the run (ARCHITECTURE §8.4).
    A run that broke one writes nothing (DEC-49), so a result records only invariants that held;
    `pmcc verify` refuses a file saying otherwise."""

    id: str = Field(pattern=r"^INV-\d{2}$")
    held: bool


class Summary(_Model):
    """Every run's summary (PO, DEC-54), with its analytics (DEC-60 to DEC-62): null only in a
    result written before P6."""

    metrics: Metrics | None = None
    cycle_stats: CycleStats | None = None
    exit_mix: Mapping[str, int] | None = None  # by rule ID
    skips_by_rule: Mapping[str, int] | None = None
    nav_close: tuple[NavPoint, ...] | None = None
    weekly_returns: tuple[WeeklyReturn, ...] | None = None
    flag_counts: Mapping[str, int]  # ledger rows carrying each flag
    invariants: tuple[InvariantCheck, ...]


class RunResult(_Model):
    """One run on one symbol: `results/{symbol}/{run_id}.json`."""

    schema_version: SchemaVersion = Field(default=SCHEMA_VERSION)
    manifest: Manifest
    config: RunConfig
    rule_text: Mapping[str, RuleTextOut]
    starting_cash: Dollars
    summary: Summary
    blotter: tuple[BlotterRow, ...] | None = None  # full detail only
    ledger: tuple[LedgerRowOut, ...] | None = None
    gate_log: tuple[GateLogRowOut, ...] | None = None
    cycles: tuple[Cycle, ...] | None = None  # full detail (P6-02)
    attribution: Attribution | None = None

    @model_validator(mode="after")
    def _detail(self) -> Self:
        """A full run keeps its records; a summary run keeps none (DEC-54)."""
        records = {"blotter": self.blotter, "ledger": self.ledger, "gate_log": self.gate_log}
        if self.config.strategy.report.detail is Detail.FULL:
            missing = [k for k, v in records.items() if v is None]
            if missing:
                raise ValueError(f"a full-detail result needs its {', '.join(missing)}")
        else:
            records |= {"cycles": self.cycles, "attribution": self.attribution}
            kept = [k for k, v in records.items() if v is not None]
            if kept:
                raise ValueError(f"a summary result keeps no {', '.join(kept)}")
        return self
