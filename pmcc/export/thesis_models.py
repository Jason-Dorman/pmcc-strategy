"""`thesis.json`: the volatility thesis's page (T3-01; THESIS-SPEC §10). `thesis run` writes it to
`live/thesis/thesis.json` each night; `pmcc export` checks it against this model and publishes it.

Every field is always there; a value not known is an explicit null. NaN and infinities are
refused, not written (§10: block NaN/Infinity). A field added after the first night's file
(T4-01's) defaults to null, so that file still reads; every file written since holds it. Dates are
`YYYY-MM-DD`; times are ISO 8601 with their offset. Volatilities are decimals (0.18 is 18%); VIX
is in its own points; the credit spread in basis points; premiums are 30-day total variance (§5.2),
decimal.
"""

from pydantic import ConfigDict

from pmcc.export.base import SCHEMA_VERSION, Model, SchemaVersion


class _Strict(Model):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        json_schema_serialization_defaults_required=True,
        allow_inf_nan=False,
    )


class ThesisSource(_Strict):
    """Where a series comes from, and what it covered this run (§10's provenance)."""

    series: str  # index, vix, credit
    provider: str
    identifier: str
    first: str | None
    last: str | None
    observations: int
    units: str
    note: str


class ThesisPoint(_Strict):
    """One session: what was known at its close, and the 30-day outcome once it matured."""

    day: str
    index_close: float | None
    vix: float | None
    forecast_vol: float | None
    forecast_gap_vol: float | None
    rv_short: float | None
    rv_long: float | None
    realized_vol: float | None  # the 30 days after `day`, once matured; null until then
    outcome: str  # MATURED, PENDING, INCOMPLETE, UNAVAILABLE
    outcome_end: str | None = None  # the outcome window's last session
    credit_bps: float | None  # the latest usable observation at the decision
    credit_status: str  # STABLE, UNSTABLE, UNAVAILABLE
    credit_observation_date: str | None = None
    credit_change_short_bps: float | None = None  # against 5 observations earlier
    credit_change_long_bps: float | None = None  # against 20 observations earlier


class ThesisEpisode(_Strict):
    episode_id: str
    shock_day: str
    window_end: str
    status: str  # CANDIDATE, NO_CANDIDATE, INCOMPLETE_CANDIDATE_SEARCH, SEARCHING
    candidate_day: str | None
    eligibility: str | None  # ELIGIBLE, FILTERED_OUT, CREDIT_UNAVAILABLE
    vix: float | None  # at the candidate
    credit_bps: float | None
    credit_change_short_bps: float | None
    credit_change_long_bps: float | None
    outcome: str | None
    outcome_end: str | None = None
    realized_vol: float | None
    premium: float | None
    note: str


class ThesisCohort(_Strict):
    name: str
    count: int
    first_day: str | None
    last_day: str | None
    mean_premium: float | None
    median_premium: float | None
    mean_vol_gap: float | None
    median_vol_gap: float | None
    mean_start_vix: float | None
    mean_overstatement: float | None


class ThesisCondition(_Strict):
    condition_id: str
    name: str
    formula: str
    threshold: str
    minimum_sample: str
    required: int | None = None  # the minimum sample's count
    status: str  # PASS, FAIL, INSUFFICIENT_DATA, NOT_EVALUATED
    value: float | None
    sample: int | None
    assessed_on: str | None
    note: str


class ThesisLegCost(_Strict):
    legs: int
    median_spread_points: float
    median_mid_points: float
    median_spread_fraction_of_mid: float
    base_share: float
    stressed_share: float


class ThesisCost(_Strict):
    sample_session: str
    sample_expiry: str
    sample_vix_points: float
    absolute_delta_low: float
    absolute_delta_high: float
    fee_per_contract_transaction_usd: float
    stressed_spread_multiple: float
    stressed_fee_multiple: float
    puts: ThesisLegCost
    calls: ThesisLegCost
    spec_condor: str


class ThesisCohorts(_Strict):
    all_sessions: ThesisCohort
    candidates: ThesisCohort
    stable: ThesisCohort
    unstable: ThesisCohort
    credit_unavailable: ThesisCohort


class ThesisEvidence(_Strict):
    cohorts: ThesisCohorts
    statements: tuple[str, ...]
    validation_target_per_cohort: int
    conditions: tuple[ThesisCondition, ...]
    cost: ThesisCost


class ThesisSignal(_Strict):
    day: str | None
    status: str
    assessment: str  # OK, BLOCKED
    episode_id: str | None
    shock_day: str | None
    candidate_day: str | None
    window_end: str | None
    reason: str


class ThesisCurrent(_Strict):
    day: str
    vix: float | None
    shock_level: float | None
    vix_share_at_or_below: float | None
    vix_ratio: float | None
    forecast_vol: float | None
    forecast_gap_vol: float | None
    rv_short: float | None
    rv_long: float | None
    rv_short_earlier: float | None = None  # RV5 at the comparison session, three earlier
    # §5.4's and §5.5's tests as they read that day, by the tracker's own rules (TD-30)
    swings_below_long: bool | None = None
    swings_not_rising: bool | None = None
    gap_ok: bool | None = None
    credit_level_ok: bool | None = None
    credit_change_short_ok: bool | None = None
    credit_change_long_ok: bool | None = None
    credit_status: str
    credit_bps: float | None
    credit_observation_date: str | None
    credit_available_at: str | None = None  # ISO 8601, New York: assumed (§4.4)
    credit_change_short_bps: float | None
    credit_change_long_bps: float | None
    credit_note: str


class ThesisParameters(_Strict):
    """The rules' thresholds, from `configs/thesis.yaml`, so the page never retypes one."""

    history_start: str
    decision_time_et: str
    horizon_calendar_days: int
    ewma_lambda: float
    initialization_sessions: int
    signal_warmup_sessions: int
    percentile_lookback_sessions: int
    percentile_threshold: float
    ratio_lookback_sessions: int
    minimum_vix_ratio: float
    search_sessions_after_shock: int
    short_rv_sessions: int
    long_rv_sessions: int
    falling_rv_comparison_sessions: int
    minimum_forecast_gap: float
    credit_maximum_level_bps: float
    credit_maximum_change_short_bps: float
    credit_maximum_change_long_bps: float
    credit_publication_lag_business_days: int
    credit_publication_time_et: str
    credit_maximum_age_business_days: int


class Thesis(_Strict):
    """`thesis.json`: the tracker as the nightly run last left it."""

    schema_version: SchemaVersion = SCHEMA_VERSION
    strategy_id: str
    model_version: str
    config_hash: str
    generated_at: str
    data_through: str | None
    expected_by: str | None = None  # ISO 8601: the next session's file is due by then
    run_status: str  # OK, PARTIAL, FAILED
    data_status: str  # CURRENT, STALE, BLOCKED
    thesis_status: str  # PROVISIONAL, PAUSED
    evidence_status: str  # INSUFFICIENT_EVIDENCE in this milestone (TD-23)
    signal: ThesisSignal
    current: ThesisCurrent | None
    parameters: ThesisParameters | None = None
    sources: tuple[ThesisSource, ...]
    evidence: ThesisEvidence
    episodes: tuple[ThesisEpisode, ...]
    series: tuple[ThesisPoint, ...]
