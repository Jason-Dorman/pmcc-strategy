"""`live.json`: the live wheel's page (L4-01; UI-SPEC §6 › Live). `pmcc export` builds it from the
committed files the nightly run and Sanji leave at the repo root (`pmcc.export.live`)."""

from typing import Literal

from pydantic import ConfigDict, Field

from pmcc.export.base import SCHEMA_VERSION, Dollars, Model, SchemaVersion


class LiveRuleOut(Model):
    """A rule of `configs/live.yaml`, in its words with its params filled in."""

    id: str
    rule: str
    words: str


class LiveRiskFree(Model):
    investment_yield_pct: float  # the T-bill's quoted yield (LD-13)
    observed: str
    source: str
    rate: float  # continuously compounded, as the pricer reads it


class LiveOrder(Model):
    """An order as `open_orders.json` holds it (the order language's fields)."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        json_schema_serialization_defaults_required=True,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    id: str
    for_: str = Field(alias="for")
    order_type: str
    action: str
    qty: int
    underlying: int
    contract: str
    expiry: str | None
    strike: str | None
    ref: str | None
    lmt_prc: str | None


class LivePick(Model):
    """The option a night picked, and its quote at the close (PO, LD-15). Rows logged before the
    quote was (Nov 15's) hold null for it."""

    contract: str
    strike: str
    expiry: str
    delta: float
    iv: float
    bid: Dollars | None = None
    ask: Dollars | None = None
    mid: Dollars | None = None
    spread: float | None = None  # (ask − bid) / mid, as L-T1 reads it


class LiveRun(Model):
    """A row of `live/runs.jsonl`: one night's run."""

    run_at: str
    last_session: str
    next_session: str
    state: str | None  # null when the book couldn't be read
    cash: Dollars | None
    cost_basis: Dollars | None
    outcome: Literal["order", "no_order", "failed"]
    rule: str
    reason: str
    order_id: str | None
    # The strike token the order sent (`pct:-5`, PO, LD-29); null on a night with no order,
    # and on rows logged before it was (Nov 15's)
    strike_sent: str | None = None
    pick: LivePick | None
    open_orders: int | None


class SanjiFileOut(Model):
    """One of Sanji's files, its text exactly as he wrote it: its format is unknown until he
    resolves an order (L5-01), so it is published, never parsed, and can't fail the export."""

    path: str  # where it was found, relative to the repo root (`mkt/` first)
    text: str


class LiveBacktest(Model):
    """The wheel's backtest on the symbol (Spec › Why the wheel), from its committed result."""

    path: str  # the result's index path
    start: str
    end: str
    starting_cash: Dollars
    pnl: Dollars
    return_on_starting_cash: float
    sharpe_annualized: float | None
    baseline_sharpe_annualized: float | None  # the baseline PMCC's, same symbol, window and r


class Live(Model):
    """`live.json`: the live wheel as the nightly run and Sanji last left it."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    symbol: str
    underlying_conid: int
    starting_cash: Dollars
    risk_free: LiveRiskFree
    rules: tuple[LiveRuleOut, ...]
    orders: tuple[LiveOrder, ...]  # `open_orders.json`, in its order
    positions: SanjiFileOut | None  # null before Sanji writes it
    fills: SanjiFileOut | None
    runs: tuple[LiveRun, ...]  # the run log, oldest first, as logged; none before the first run
    backtest: LiveBacktest | None
