"""`configs/thesis.yaml`: the tracker's predeclared v1 parameters (THESIS-SPEC §13; TD-03).

Strict: every key the tracker reads must be there, with the right type and range, and no other
key may be, so a misspelt threshold fails at load rather than quietly taking a default.
`config_hash` is the sha256 of the loaded values as canonical JSON, for the public files'
provenance (§10). The file is found from this module, not the working directory.
"""

import hashlib
import json
from datetime import date, time
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from pmcc.config.yaml_file import read_yaml

THESIS_PATH = Path(__file__).resolve().parents[2] / "configs" / "thesis.yaml"


class ThesisConfigError(ValueError):
    """`configs/thesis.yaml` doesn't hold what the tracker needs."""


class _Section(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ForecastConfig(_Section):
    """§5.1, §5.2: the horizon, the EWMA and the warmup."""

    horizon_calendar_days: int = Field(ge=1)
    ewma_lambda: float = Field(gt=0, lt=1)
    initialization_sessions: int = Field(ge=1)
    signal_warmup_sessions: int = Field(ge=1)


class ShockConfig(_Section):
    """§5.3: what opens an episode, and its fixed search window."""

    percentile_lookback_sessions: int = Field(ge=2)
    percentile_threshold: float = Field(gt=0, lt=1)
    ratio_lookback_sessions: int = Field(ge=1)
    minimum_vix_ratio: float = Field(gt=0)
    search_sessions_after_shock: int = Field(ge=1)


class NormalizationConfig(_Section):
    """§5.4: the three tests a candidate session meets."""

    short_rv_sessions: int = Field(ge=2)
    long_rv_sessions: int = Field(ge=2)
    falling_rv_comparison_sessions: int = Field(ge=1)
    minimum_forecast_gap_decimal: float

    @model_validator(mode="after")
    def _short_below_long(self) -> Self:
        if self.short_rv_sessions >= self.long_rv_sessions:
            raise ValueError("short_rv_sessions must be fewer than long_rv_sessions")
        return self


class CreditConfig(_Section):
    """§4.4, §5.5: stable credit, and when an observation may be used."""

    maximum_level_bps: float
    maximum_change_5_observations_bps: float
    maximum_change_20_observations_bps: float
    assumed_publication_lag_business_days: int = Field(ge=0)
    assumed_publication_time_et: str
    maximum_age_business_days: int = Field(ge=0)

    @model_validator(mode="after")
    def _time(self) -> Self:
        parse_hhmm(self.assumed_publication_time_et, "assumed_publication_time_et")
        return self

    @property
    def publication_time(self) -> time:
        return parse_hhmm(self.assumed_publication_time_et, "assumed_publication_time_et")


class EvidenceConfig(_Section):
    """§9's sample sizes and windows, which K1 (T2-02) reads."""

    minimum_matured_events_per_credit_cohort: int = Field(ge=1)
    kill_window_selected_events: int = Field(ge=1)
    kill_window_completed_trades: int = Field(ge=1)
    credit_comparison_window_months: int = Field(ge=1)


class CostSampleConfig(_Section):
    """R5's cost sample (TD-07, TD-14): one rough SPXW condor at a close, by §6.2's contract
    rules, §6.3's spread test and §7.2's fees; the rate and the strike windows are the probe's."""

    target_dte_calendar_days: int = Field(ge=1)
    minimum_dte_calendar_days: int = Field(ge=1)
    maximum_dte_calendar_days: int = Field(ge=1)
    absolute_short_delta_target: float = Field(gt=0, lt=0.5)
    delta_tolerance: float = Field(gt=0, lt=0.5)
    target_wing_width_spot_fraction: float = Field(gt=0)
    maximum_wing_width_target_multiple: float = Field(ge=1)
    maximum_spread_points: float = Field(gt=0)
    maximum_spread_fraction_of_mid: float = Field(gt=0)
    fee_per_contract_transaction_usd: float = Field(ge=0)
    contract_multiplier: int = Field(ge=1)
    rate_decimal: float
    strike_step_points: int = Field(ge=1)
    put_window_low: float = Field(gt=0)
    put_window_high: float = Field(gt=0)
    call_window_low: float = Field(gt=0)
    call_window_high: float = Field(gt=0)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if not (
            self.minimum_dte_calendar_days
            <= self.target_dte_calendar_days
            <= self.maximum_dte_calendar_days
        ):
            raise ValueError("the DTEs must run minimum <= target <= maximum")
        if (
            self.put_window_low >= self.put_window_high
            or self.call_window_low >= self.call_window_high
        ):
            raise ValueError("each strike window's low must be below its high")
        return self


class ComparisonConfig(_Section):
    """The two exploratory versions' counting views and revised K1 (PO, TD-33). Their conditions
    are the sections above's, unchanged."""

    methodology_version: str = Field(min_length=1)
    spacing_sessions: int = Field(ge=1)
    spacing_calendar_days: int = Field(ge=1)
    kill_window_observations: int = Field(ge=1)


class R5CostConfig(_Section):
    """R5's measured cost (PO, TD-21): one dated sample of SPXW's spreads at a close, from the
    probe (TD-20), for the legs within an absolute-delta band; and the stressed case's multiples."""

    sample_session: str
    sample_expiry: str
    sample_vix_points: float = Field(gt=0)
    sample_probe: str = Field(min_length=1)
    absolute_delta_low: float = Field(gt=0, lt=1)
    absolute_delta_high: float = Field(gt=0, lt=1)
    put_legs: int = Field(ge=1)
    put_median_spread_points: float = Field(gt=0)
    put_median_mid_points: float = Field(gt=0)
    put_median_spread_fraction_of_mid: float = Field(gt=0)
    call_legs: int = Field(ge=1)
    call_median_spread_points: float = Field(gt=0)
    call_median_mid_points: float = Field(gt=0)
    call_median_spread_fraction_of_mid: float = Field(gt=0)
    stressed_spread_multiple: float = Field(ge=1)
    stressed_fee_multiple: float = Field(ge=1)
    spec_condor: str = Field(min_length=1)

    @model_validator(mode="after")
    def _dates(self) -> Self:
        for name in ("sample_session", "sample_expiry"):
            try:
                date.fromisoformat(getattr(self, name))
            except ValueError:
                raise ValueError(f"r5_cost.{name} must be YYYY-MM-DD") from None
        if self.absolute_delta_low >= self.absolute_delta_high:
            raise ValueError("r5_cost's delta band's low must be below its high")
        return self


class ThesisConfig(_Section):
    strategy_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    timezone: Literal["America/New_York"]
    history_start: str
    decision_time_et: str
    update_due_time_et: str
    forecast: ForecastConfig
    shock: ShockConfig
    normalization: NormalizationConfig
    credit: CreditConfig
    evidence: EvidenceConfig
    comparison: ComparisonConfig
    cost_sample: CostSampleConfig
    r5_cost: R5CostConfig

    @model_validator(mode="after")
    def _formats(self) -> Self:
        parse_hhmm(self.decision_time_et, "decision_time_et")
        parse_hhmm(self.update_due_time_et, "update_due_time_et")
        try:
            date.fromisoformat(self.history_start)
        except ValueError:
            raise ValueError(
                f"history_start must be YYYY-MM-DD, got {self.history_start}"
            ) from None
        return self

    @property
    def decision_time(self) -> time:
        """When a session's signal is decided, New York time (§7.1: no earlier than 20:30)."""
        return parse_hhmm(self.decision_time_et, "decision_time_et")

    @property
    def update_due_time(self) -> time:
        """When, the day after a session, its run should have published (New York)."""
        return parse_hhmm(self.update_due_time_et, "update_due_time_et")

    @property
    def history_start_day(self) -> date:
        return date.fromisoformat(self.history_start)

    def canonical_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))

    def config_hash(self) -> str:
        """sha256 of `canonical_json()` in UTF-8."""
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


def parse_hhmm(text: str, name: str) -> time:
    """`HH:MM`, 24-hour. Raises `ValueError` naming the key for anything else."""
    hours, sep, minutes = text.partition(":")
    if not (
        sep and len(hours) == 2 and len(minutes) == 2 and hours.isdigit() and minutes.isdigit()
    ):
        raise ValueError(f"{name} must be HH:MM, got {text!r}")
    try:
        return time(int(hours), int(minutes))
    except ValueError:
        raise ValueError(f"{name} must be HH:MM, got {text!r}") from None


def load_thesis_config(path: Path = THESIS_PATH) -> ThesisConfig:
    """The validated file. Raises `ThesisConfigError` saying what is wrong."""
    try:
        return ThesisConfig.model_validate(read_yaml(path))
    except ValidationError as exc:
        raise ThesisConfigError(f"{path.name}: {exc}") from None
