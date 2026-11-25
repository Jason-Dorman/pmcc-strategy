"""The tracker as `thesis.json` (T3-01; THESIS-SPEC §10): everything the page shows, from one run.

Pure: a `Tracker`, its evidence and statuses, the sources' coverage and the run's time in; the
public model (`pmcc.export.thesis_models.Thesis`) out. Nothing here is computed afresh; each
value is the tracker's, the evidence's or a status's, renamed for the page. The model refuses a
NaN or an infinity, so a bad number stops the write instead of printing as null.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import final

from pmcc.domain.calendar import SessionCalendar
from pmcc.export.thesis_models import (
    Thesis,
    ThesisCheck,
    ThesisCohort,
    ThesisCohorts,
    ThesisComparison,
    ThesisCondition,
    ThesisCost,
    ThesisCurrent,
    ThesisEpisode,
    ThesisEvidence,
    ThesisLegCost,
    ThesisObservation,
    ThesisParameters,
    ThesisPoint,
    ThesisSignal,
    ThesisSource,
    ThesisVersion,
    ThesisVersionLatest,
    ThesisView,
)
from pmcc.thesis.config import ThesisConfig
from pmcc.thesis.credit import CreditState, assumed_available_at
from pmcc.thesis.evidence import Cohort, Condition, CostNote, Evidence, LegCost
from pmcc.thesis.outcomes import Outcome
from pmcc.thesis.status import CurrentState, Signal
from pmcc.thesis.tracker import TrackedEpisode, Tracker
from pmcc.thesis.versions import Comparison, Latest, Observation, Version, View

RUN_OK = "OK"


@final
@dataclass(frozen=True, slots=True)
class Statuses:
    data_status: str
    expected_by: datetime
    thesis_status: str
    signal: Signal
    current: CurrentState | None


def thesis_file(
    tracker: Tracker,
    found: Evidence,
    compared: Comparison,
    statuses: Statuses,
    sources: Sequence[ThesisSource],
    calendar: SessionCalendar,
    config: ThesisConfig,
    generated_at: datetime,
) -> Thesis:
    outcomes = {o.day: o for o in tracker.outcomes}
    vix = {row.day: row.vix_points for row in tracker.features}
    return Thesis(
        strategy_id=config.strategy_id,
        model_version=config.model_version,
        config_hash=tracker.config_hash,
        generated_at=generated_at.isoformat(),
        data_through=_day(tracker.data_through),
        expected_by=statuses.expected_by.isoformat(),
        run_status=RUN_OK,
        data_status=statuses.data_status,
        thesis_status=statuses.thesis_status,
        evidence_status=found.evidence_status,
        signal=_signal(statuses.signal),
        current=_current(statuses.current, calendar, config),
        parameters=parameters(config),
        comparison=_comparison(compared),
        sources=tuple(sources),
        evidence=_evidence(found),
        episodes=tuple(_episode(e, outcomes, vix) for e in tracker.episodes),
        series=_series(tracker),
    )


def _day(day: date | None) -> str | None:
    return None if day is None else day.isoformat()


def _series(tracker: Tracker) -> tuple[ThesisPoint, ...]:
    return tuple(
        ThesisPoint(
            day=row.day.isoformat(),
            index_close=row.index_close,
            vix=row.vix_points,
            forecast_vol=row.forecast_vol,
            forecast_gap_vol=row.forecast_gap_vol,
            rv_short=row.rv_short,
            rv_long=row.rv_long,
            realized_vol=outcome.realized_vol,
            outcome=outcome.status.value,
            outcome_end=_day(outcome.maturity_day),
            credit_bps=credit.level_bps,
            credit_status=credit.status.value,
            credit_observation_date=_day(credit.observation_date),
            credit_change_short_bps=credit.change_short_bps,
            credit_change_long_bps=credit.change_long_bps,
        )
        for row, outcome, credit in zip(
            tracker.features, tracker.outcomes, tracker.credit, strict=True
        )
    )


def _episode(
    tracked: TrackedEpisode, outcomes: dict[date, Outcome], vix: dict[date, float | None]
) -> ThesisEpisode:
    episode, credit = tracked.episode, tracked.credit
    day = episode.candidate_day
    outcome = outcomes.get(day) if day is not None else None
    return ThesisEpisode(
        episode_id=episode.episode_id,
        shock_day=episode.shock_day.isoformat(),
        window_end=episode.window_end.isoformat(),
        status=episode.status.value,
        candidate_day=_day(day),
        eligibility=None if tracked.eligibility is None else tracked.eligibility.value,
        vix=vix.get(day) if day is not None else None,
        credit_bps=None if credit is None else credit.level_bps,
        credit_change_short_bps=None if credit is None else credit.change_short_bps,
        credit_change_long_bps=None if credit is None else credit.change_long_bps,
        outcome=None if outcome is None else outcome.status.value,
        outcome_end=None if outcome is None else _day(outcome.maturity_day),
        realized_vol=None if outcome is None else outcome.realized_vol,
        premium=None if outcome is None else outcome.realized_variance_premium,
        note=_episode_note(tracked),
    )


def _episode_note(tracked: TrackedEpisode) -> str:
    credit_note = tracked.credit.note if tracked.credit is not None else ""
    return "; ".join(n for n in (tracked.episode.note, credit_note) if n)


def _evidence(found: Evidence) -> ThesisEvidence:
    c = found.cohorts
    return ThesisEvidence(
        cohorts=ThesisCohorts(
            all_sessions=_cohort(c.all_sessions),
            candidates=_cohort(c.candidates),
            stable=_cohort(c.stable),
            unstable=_cohort(c.unstable),
            credit_unavailable=_cohort(c.credit_unavailable),
        ),
        statements=found.statements,
        validation_target_per_cohort=found.validation_target_per_cohort,
        conditions=tuple(_condition(k) for k in found.conditions),
        cost=_cost(found.cost),
    )


def _cohort(cohort: Cohort) -> ThesisCohort:
    return ThesisCohort(
        name=cohort.name,
        count=cohort.count,
        first_day=_day(cohort.first_day),
        last_day=_day(cohort.last_day),
        mean_premium=cohort.mean_premium,
        median_premium=cohort.median_premium,
        mean_vol_gap=cohort.mean_vol_gap,
        median_vol_gap=cohort.median_vol_gap,
        mean_start_vix=cohort.mean_start_vix,
        mean_overstatement=cohort.mean_overstatement,
    )


def _condition(k: Condition) -> ThesisCondition:
    return ThesisCondition(
        condition_id=k.condition_id,
        name=k.name,
        formula=k.formula,
        threshold=k.threshold,
        minimum_sample=k.minimum_sample,
        required=k.required,
        status=k.status.value,
        value=k.value,
        sample=k.sample,
        assessed_on=_day(k.assessed_on),
        note=k.note,
    )


def _cost(note: CostNote) -> ThesisCost:
    return ThesisCost(
        sample_session=note.sample_session.isoformat(),
        sample_expiry=note.sample_expiry.isoformat(),
        sample_vix_points=note.sample_vix_points,
        absolute_delta_low=note.absolute_delta_low,
        absolute_delta_high=note.absolute_delta_high,
        fee_per_contract_transaction_usd=note.fee_per_contract_transaction_usd,
        stressed_spread_multiple=note.stressed_spread_multiple,
        stressed_fee_multiple=note.stressed_fee_multiple,
        puts=_leg(note.puts),
        calls=_leg(note.calls),
        spec_condor=note.spec_condor,
    )


def _leg(leg: LegCost) -> ThesisLegCost:
    return ThesisLegCost(
        legs=leg.legs,
        median_spread_points=leg.median_spread_points,
        median_mid_points=leg.median_mid_points,
        median_spread_fraction_of_mid=leg.median_spread_fraction_of_mid,
        base_share=leg.base_share,
        stressed_share=leg.stressed_share,
    )


def _signal(s: Signal) -> ThesisSignal:
    return ThesisSignal(
        day=_day(s.day),
        status=s.status.value,
        assessment=s.assessment.value,
        episode_id=s.episode_id,
        shock_day=_day(s.shock_day),
        candidate_day=_day(s.candidate_day),
        window_end=_day(s.window_end),
        reason=s.reason,
    )


def _current(
    state: CurrentState | None, calendar: SessionCalendar, config: ThesisConfig
) -> ThesisCurrent | None:
    if state is None:
        return None
    credit: CreditState | None = state.credit
    observed = None if credit is None else credit.observation_date
    available = (
        None
        if observed is None
        else assumed_available_at(observed, calendar, config.credit).isoformat()
    )
    return ThesisCurrent(
        day=state.day.isoformat(),
        vix=state.vix_points,
        shock_level=state.shock_level_points,
        vix_share_at_or_below=state.vix_share_at_or_below,
        vix_ratio=state.vix_ratio,
        forecast_vol=state.forecast_vol,
        forecast_gap_vol=state.forecast_gap_vol,
        rv_short=state.rv_short,
        rv_long=state.rv_long,
        rv_short_earlier=state.checks.earlier_rv_short,
        swings_below_long=state.checks.swings_below_long,
        swings_not_rising=state.checks.swings_not_rising,
        gap_ok=state.checks.gap_ok,
        credit_level_ok=None if credit is None else credit.level_ok,
        credit_change_short_ok=None if credit is None else credit.change_short_ok,
        credit_change_long_ok=None if credit is None else credit.change_long_ok,
        credit_status="UNAVAILABLE" if credit is None else credit.status.value,
        credit_bps=None if credit is None else credit.level_bps,
        credit_observation_date=_day(observed),
        credit_available_at=available,
        credit_change_short_bps=None if credit is None else credit.change_short_bps,
        credit_change_long_bps=None if credit is None else credit.change_long_bps,
        credit_note="" if credit is None else credit.note,
    )


def parameters(config: ThesisConfig) -> ThesisParameters:
    """The thresholds the tracker ran with, for the page's words and lines."""
    forecast, shock, normal = config.forecast, config.shock, config.normalization
    credit = config.credit
    return ThesisParameters(
        history_start=config.history_start,
        decision_time_et=config.decision_time_et,
        horizon_calendar_days=forecast.horizon_calendar_days,
        ewma_lambda=forecast.ewma_lambda,
        initialization_sessions=forecast.initialization_sessions,
        signal_warmup_sessions=forecast.signal_warmup_sessions,
        percentile_lookback_sessions=shock.percentile_lookback_sessions,
        percentile_threshold=shock.percentile_threshold,
        ratio_lookback_sessions=shock.ratio_lookback_sessions,
        minimum_vix_ratio=shock.minimum_vix_ratio,
        search_sessions_after_shock=shock.search_sessions_after_shock,
        short_rv_sessions=normal.short_rv_sessions,
        long_rv_sessions=normal.long_rv_sessions,
        falling_rv_comparison_sessions=normal.falling_rv_comparison_sessions,
        minimum_forecast_gap=normal.minimum_forecast_gap_decimal,
        credit_maximum_level_bps=float(credit.maximum_level_bps),
        credit_maximum_change_short_bps=float(credit.maximum_change_5_observations_bps),
        credit_maximum_change_long_bps=float(credit.maximum_change_20_observations_bps),
        credit_publication_lag_business_days=credit.assumed_publication_lag_business_days,
        credit_publication_time_et=credit.assumed_publication_time_et,
        credit_maximum_age_business_days=credit.maximum_age_business_days,
    )


# --- the two exploratory versions (TD-33) ----------------------------------------------------


def _comparison(c: Comparison) -> ThesisComparison:
    return ThesisComparison(
        methodology_version=c.methodology_version,
        analysis_start=_day(c.analysis_start),
        analysis_end=_day(c.analysis_end),
        spacing_sessions=c.spacing_sessions,
        spacing_calendar_days=c.spacing_calendar_days,
        versions=tuple(_version(v) for v in c.versions),
    )


def _version(v: Version) -> ThesisVersion:
    return ThesisVersion(
        key=v.key.value,
        name=v.name,
        qualifying_days=v.qualifying_days,
        unknown_days=v.unknown_days,
        unconfirmed_stretches=v.unconfirmed_stretches,
        latest=_latest(v.latest),
        views=tuple(_view(w) for w in v.views),
        observations=tuple(_observation(o) for o in v.observations),
        k1=_condition(v.k1),
    )


def _latest(latest: Latest | None) -> ThesisVersionLatest | None:
    if latest is None:
        return None
    return ThesisVersionLatest(
        state=latest.state.value,
        checks=tuple(ThesisCheck(key=k.value, met=met) for k, met in latest.checks.items()),
        stretch_start=_day(latest.stretch_start),
    )


def _view(v: View) -> ThesisView:
    return ThesisView(
        key=v.key.value,
        selected=v.selected,
        completed=v.completed,
        pending=v.pending,
        incomplete=v.incomplete,
        mean_gap=v.mean_gap,
        median_gap=v.median_gap,
        worst_gap=v.worst_gap,
        worst_day=_day(v.worst_day),
        mean_premium=v.mean_premium,
    )


def _observation(o: Observation) -> ThesisObservation:
    return ThesisObservation(
        day=o.day.isoformat(),
        stretch_end=o.stretch_end.isoformat(),
        stretch_sessions=o.stretch_sessions,
        ten_session=o.ten_session,
        thirty_day=o.thirty_day,
        vix=o.vix_points,
        forecast_gap_vol=o.forecast_gap_vol,
        outcome=o.outcome.value,
        outcome_end=_day(o.outcome_end),
        realized_vol=o.realized_vol,
        vol_gap=o.vol_gap,
        premium=o.premium,
    )
