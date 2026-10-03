"""The site's own files (ARCHITECTURE §12): `index.json`, what exists, and `rules.json`, the Trade
rules page's source. `pmcc export` derives both from the results (`pmcc.export.site`)."""

from collections.abc import Mapping

from pydantic import Field

from pmcc.config.matrix import Family
from pmcc.config.strategy import Detail, Section
from pmcc.config.universe import RiskFreeRate, Window
from pmcc.export.base import SCHEMA_VERSION, Dollars, Model, SchemaVersion
from pmcc.export.models import DataSource

# ---- index.json ---------------------------------------------------------------------------------


class IndexRun(Model):
    run_id: str
    strategy_id: str
    name: str
    detail: Detail
    sections: tuple[Section, ...]
    path: str  # relative to index.json
    data_source: DataSource  # synthetic shows the banner (DEC-74)
    config_hash: str
    git_sha: str


class IndexSymbol(Model):
    symbol: str
    runs: tuple[IndexRun, ...]
    files: Mapping[str, str]  # robustness, fill_check, coverage → path, once written


class Index(Model):
    """`index.json`: the site loads it first (ARCHITECTURE §13)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    pmcc_version: str  # the exporter's
    window: Window
    risk_free_rate: RiskFreeRate
    starting_cash: Dollars
    symbols: tuple[IndexSymbol, ...]
    universe: Mapping[str, str]  # pooled, headline, pooled_fill_check, suitability → path


# ---- rules.json ---------------------------------------------------------------------------------


class RuleOut(Model):
    """A rule as it ran: its params and its write-up rendered from them (DEC-52)."""

    id: str
    name: str
    kind: str
    params: Mapping[str, float | int | str]  # dollars "0.1000", clock times "15:00"
    shown: Mapping[str, str]  # each param as its text shows it: "1.20", "$0.10", "3%" (P7-03)
    condition: str
    action: str
    rationale: str


class RuleChange(Model):
    """How a variant's rule differs from its strategy's."""

    rule_id: str
    change: str = Field(pattern="^(added|removed|replaced|params|text)$")


class StrategyRules(Model):
    id: str  # the run ID
    name: str
    strategy_id: str
    # Its part of the run matrix, read from the robustness tables that hold it; null for a variant
    # none does (P7-03: the Trade rules page's ablations and sensitivity panels)
    family: Family | None
    detail: Detail
    spread_capture: float
    fee_per_contract: Dollars
    rules: tuple[RuleOut, ...]
    changes: tuple[RuleChange, ...]  # against `strategy_id`'s rules; none for a strategy


class Rules(Model):
    """`rules.json`: the Trade rules page (UI-SPEC §6.3)."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    strategies: tuple[StrategyRules, ...]
