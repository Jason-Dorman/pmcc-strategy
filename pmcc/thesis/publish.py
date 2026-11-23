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

from pmcc.export.thesis_models import (
    Thesis,
    ThesisCohort,
    ThesisCohorts,
    ThesisCondition,
    ThesisCost,
    ThesisCurrent,
    ThesisEpisode,
    ThesisEvidence,
    ThesisLegCost,
    ThesisPoint,
    ThesisSignal,
    ThesisSource,
)
from pmcc.thesis.config import ThesisConfig
from pmcc.thesis.credit import CreditState
from pmcc.thesis.evidence import Cohort, Condition, CostNote, Evidence, LegCost
from pmcc.thesis.outcomes import Outcome
from pmcc.thesis.status import CurrentState, Signal
from pmcc.thesis.tracker import TrackedEpisode, Tracker

RUN_OK = "OK"


@final
@dataclass(frozen=True, slots=True)
class Statuses:
    data_status: str
    thesis_status: str
    signal: Signal
    current: CurrentState | None


def thesis_file(
    tracker: Tracker,
    found: Evidence,
    statuses: Statuses,
    sources: Sequence[ThesisSource],
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
        run_status=RUN_OK,
        data_status=statuses.data_status,
        thesis_status=statuses.thesis_status,
        evidence_status=found.evidence_status,
        signal=_signal(statuses.signal),
        current=_current(statuses.current),
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
            credit_bps=credit.level_bps,
            credit_status=credit.status.value,
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


def _current(state: CurrentState | None) -> ThesisCurrent | None:
    if state is None:
        return None
    credit: CreditState | None = state.credit
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
        credit_status="UNAVAILABLE" if credit is None else credit.status.value,
        credit_bps=None if credit is None else credit.level_bps,
        credit_observation_date=None if credit is None else _day(credit.observation_date),
        credit_change_short_bps=None if credit is None else credit.change_short_bps,
        credit_change_long_bps=None if credit is None else credit.change_long_bps,
        credit_note="" if credit is None else credit.note,
    )
