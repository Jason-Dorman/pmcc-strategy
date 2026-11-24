"""The tracker's evidence: preliminary cohorts, K1-K3 and R5's note (THESIS-SPEC §8, §9; T2-02).

Pure, on a `Tracker` in memory. Every number is from matured outcomes only (§5.2): a pending or
incomplete outcome counts nowhere.

- **Cohorts** (§8.2 analysis D, as scoped by TD-03): every matured session; every matured
  candidate; and the candidates by their credit at the decision, stable (`ELIGIBLE`), unstable
  (`FILTERED_OUT`) and without credit data (`CREDIT_UNAVAILABLE`). Each has its count, date range,
  mean and median `realized_variance_premium` (implied less realized 30-day total variance, §5.2,
  decimal), the mean and median gap between VIX and the realized vol that followed (decimal vol),
  the mean starting VIX (the gap may only reflect a higher start, §8.2), and the mean share by
  which VIX overstated the realized vol, R5's rough edge (TD-21).
- **Preliminary historical evidence** (PO, TD-23): plain-language sentences on what the cohorts
  show, never a SUPPORTIVE / MIXED / UNSUPPORTIVE label. §8.4's 20 per cohort is a documented
  future validation target: shown against the counts, it never blocks or stops anything.
  `evidence_status` stays `INSUFFICIENT_EVIDENCE`, since full statistical validation is out of
  this assignment's scope.
- **K1** (TD-08, TD-24): the mean premium over the latest 30 matured stable-credit candidates; a
  current rolling assessment, `INSUFFICIENT_DATA` below 30 (its provisional value still shown),
  else `FAIL` at or below 0 and `PASS` above. No persistent latch in this milestone.
- **K2, K3** (TD-08): their definitions, thresholds and samples; not evaluated.
- **R5's cost** (TD-21): `configs/thesis.yaml`'s `r5_cost`, one dated sample of SPXW's measured
  spreads: a round trip at the natural price gives up about one full spread a leg, plus two fee
  transactions, as a share of the leg's mid; and a stressed case.
"""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import final

from pmcc.thesis.config import ThesisConfig
from pmcc.thesis.outcomes import Outcome, OutcomeStatus
from pmcc.thesis.tracker import Eligibility, Tracker

EVIDENCE_STATUS = "INSUFFICIENT_EVIDENCE"
NOT_EVALUATED = "Not yet evaluated — requires strategy backtesting"
SMALL_SAMPLE = "A sample this small does not establish a reliable edge."
OUT_OF_SCOPE = (
    "Full statistical validation and trade-based profitability testing are outside this "
    "assignment's scope."
)
NO_COMPARISON = "Credit-regime comparison unavailable in this sample."
NEITHER_GROUP = "Neither credit group has a matured episode yet."
_TRANSACTIONS_PER_LEG = 2  # opened and closed


class ConditionStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NOT_EVALUATED = "NOT_EVALUATED"


@final
@dataclass(frozen=True, slots=True)
class Point:
    """One matured session's outcome, with the VIX it started from."""

    day: date
    vix_points: float
    premium: float  # realized_variance_premium, 30-day total variance, decimal
    realized_vol: float  # realized_vol_30, decimal

    @property
    def vol_gap(self) -> float:
        return self.vix_points / 100 - self.realized_vol

    @property
    def overstatement(self) -> float:
        """The share by which VIX overstated the realized vol that followed."""
        return self.vol_gap / (self.vix_points / 100)


@final
@dataclass(frozen=True, slots=True)
class Cohort:
    name: str
    count: int
    first_day: date | None
    last_day: date | None
    mean_premium: float | None
    median_premium: float | None
    mean_vol_gap: float | None
    median_vol_gap: float | None
    mean_start_vix: float | None
    mean_overstatement: float | None


@final
@dataclass(frozen=True, slots=True)
class Cohorts:
    all_sessions: Cohort
    candidates: Cohort
    stable: Cohort
    unstable: Cohort
    credit_unavailable: Cohort


@final
@dataclass(frozen=True, slots=True)
class Condition:
    condition_id: str
    name: str
    formula: str
    threshold: str
    minimum_sample: str
    status: ConditionStatus
    value: float | None
    sample: int | None
    assessed_on: date | None
    note: str


@final
@dataclass(frozen=True, slots=True)
class LegCost:
    """One side's measured cost per contract, a round trip, as a share of its mid."""

    legs: int
    median_spread_points: float
    median_mid_points: float
    median_spread_fraction_of_mid: float
    base_share: float
    stressed_share: float


@final
@dataclass(frozen=True, slots=True)
class CostNote:
    sample_session: date
    sample_expiry: date
    sample_vix_points: float
    absolute_delta_low: float
    absolute_delta_high: float
    fee_per_contract_transaction_usd: float
    stressed_spread_multiple: float
    stressed_fee_multiple: float
    puts: LegCost
    calls: LegCost
    spec_condor: str


@final
@dataclass(frozen=True, slots=True)
class Evidence:
    cohorts: Cohorts
    statements: tuple[str, ...]
    validation_target_per_cohort: int
    evidence_status: str
    conditions: tuple[Condition, Condition, Condition]
    cost: CostNote


def evidence(tracker: Tracker, config: ThesisConfig) -> Evidence:
    found = cohorts(tracker)
    target = config.evidence.minimum_matured_events_per_credit_cohort
    return Evidence(
        cohorts=found,
        statements=statements(found),
        validation_target_per_cohort=target,
        evidence_status=EVIDENCE_STATUS,
        conditions=(k1(tracker, config), k2(config), k3(config)),
        cost=cost_note(config),
    )


# --- cohorts ---------------------------------------------------------------------------------


def cohorts(tracker: Tracker) -> Cohorts:
    points = matured_points(tracker)
    by_day = {p.day: p for p in points}
    candidates = [
        (e.eligibility, by_day[day])
        for e in tracker.episodes
        if (day := e.episode.candidate_day) is not None and day in by_day
    ]

    def of(eligibility: Eligibility) -> list[Point]:
        return [p for kind, p in candidates if kind is eligibility]

    return Cohorts(
        all_sessions=cohort("all matured sessions", points),
        candidates=cohort("all candidates", [p for _, p in candidates]),
        stable=cohort("stable credit", of(Eligibility.ELIGIBLE)),
        unstable=cohort("unstable credit", of(Eligibility.FILTERED_OUT)),
        credit_unavailable=cohort("credit unavailable", of(Eligibility.CREDIT_UNAVAILABLE)),
    )


def matured_points(tracker: Tracker) -> list[Point]:
    """Every session whose outcome matured, in date order."""
    return [
        point
        for row, outcome in zip(tracker.features, tracker.outcomes, strict=True)
        if (point := _point(row.vix_points, outcome)) is not None
    ]


def _point(vix: float | None, outcome: Outcome) -> Point | None:
    premium, realized = outcome.realized_variance_premium, outcome.realized_vol
    if outcome.status is not OutcomeStatus.MATURED or vix is None:
        return None
    if premium is None or realized is None:
        return None
    return Point(outcome.day, vix, premium, realized)


def cohort(name: str, points: Sequence[Point]) -> Cohort:
    if not points:
        return Cohort(name, 0, None, None, None, None, None, None, None, None)
    premiums = [p.premium for p in points]
    gaps = [p.vol_gap for p in points]
    return Cohort(
        name=name,
        count=len(points),
        first_day=points[0].day,
        last_day=points[-1].day,
        mean_premium=statistics.fmean(premiums),
        median_premium=statistics.median(premiums),
        mean_vol_gap=statistics.fmean(gaps),
        median_vol_gap=statistics.median(gaps),
        mean_start_vix=statistics.fmean(p.vix_points for p in points),
        mean_overstatement=statistics.fmean(p.overstatement for p in points),
    )


# --- plain language (TD-23) ------------------------------------------------------------------


def statements(found: Cohorts) -> tuple[str, ...]:
    """What the cohorts show, in plain words, with their limits."""
    out = [_all_sessions(found.all_sessions)]
    out += _candidates(found)
    out += [SMALL_SAMPLE, OUT_OF_SCOPE]
    return tuple(out)


def _all_sessions(all_sessions: Cohort) -> str:
    if all_sessions.count == 0 or all_sessions.mean_premium is None:
        return "No session's 30-day outcome has matured yet; the daily forecast tracker continues."
    return (
        f"Across the {all_sessions.count} sessions with a matured outcome, from "
        f"{all_sessions.first_day} to {all_sessions.last_day}, the average premium was "
        f"{_sign(all_sessions.mean_premium)}."
    )


def _candidates(found: Cohorts) -> list[str]:
    if found.candidates.count == 0:
        return ["No candidate episode's outcome has matured yet."]
    out: list[str] = []
    for group in (found.stable, found.unstable):
        if group.count and group.mean_premium is not None:
            episodes = "episode" if group.count == 1 else "episodes"
            out.append(
                f"The average premium was {_sign(group.mean_premium)} in the {group.count} "
                f"available {group.name.replace(' ', '-')} {episodes}."
            )
    if not (found.stable.count or found.unstable.count):
        out.append(NEITHER_GROUP)
    if not (found.stable.count and found.unstable.count):
        out.append(NO_COMPARISON)
    if found.credit_unavailable.count:
        out.append(_without_credit(found.credit_unavailable.count))
    return out


def _without_credit(count: int) -> str:
    who = "1 matured candidate has" if count == 1 else f"{count} matured candidates have"
    whose, they = ("its", "it is") if count == 1 else ("their", "they are")
    return f"{who} no credit data at {whose} decision, so {they} in neither group."


def _sign(value: float) -> str:
    if value > 0:
        return "positive"
    return "negative" if value < 0 else "zero"


# --- K1-K3 (TD-08, TD-24) --------------------------------------------------------------------


def k1(tracker: Tracker, config: ThesisConfig) -> Condition:
    """The mean premium over the latest matured stable-credit candidates, a rolling assessment."""
    window = config.evidence.kill_window_selected_events
    by_day = {p.day: p for p in matured_points(tracker)}
    stable = [
        by_day[day]
        for e in tracker.episodes
        if e.eligibility is Eligibility.ELIGIBLE
        and (day := e.episode.candidate_day) is not None
        and day in by_day
    ]
    latest = stable[-window:]
    value = statistics.fmean(p.premium for p in latest) if latest else None
    return Condition(
        condition_id="K1",
        name="Priced risk is not excessive",
        formula=(
            f"mean realized_variance_premium over the latest {window} matured stable-credit "
            "candidate episodes"
        ),
        threshold="wrong if <= 0",
        minimum_sample=f"{window} matured selected episodes",
        status=_k1_status(value, len(stable), window),
        value=value,
        sample=len(stable),
        assessed_on=tracker.data_through,
        note=(
            "A current rolling assessment, recomputed each night; persistent failure tracking "
            "and resumption controls are not implemented in this milestone."
        ),
    )


def _k1_status(value: float | None, sample: int, window: int) -> ConditionStatus:
    if value is None or sample < window:
        return ConditionStatus.INSUFFICIENT_DATA
    return ConditionStatus.FAIL if value <= 0 else ConditionStatus.PASS


def k2(config: ThesisConfig) -> Condition:
    trades = config.evidence.kill_window_completed_trades
    return _not_evaluated(
        "K2",
        "Edge does not survive costs",
        f"mean net return on initial maximum-loss budget over the latest {trades} completed "
        "full-policy trades",
        "wrong if <= 0",
        f"{trades} resolved trades",
    )


def k3(config: ThesisConfig) -> Condition:
    months = config.evidence.credit_comparison_window_months
    events = config.evidence.minimum_matured_events_per_credit_cohort
    return _not_evaluated(
        "K3",
        "Credit distinction fails",
        f"in the trailing {months} months, mean standardized-event net return for stable-credit "
        "candidates against unstable-credit candidates, with identical non-credit exits and base "
        "costs",
        "wrong if stable <= unstable",
        f"at least {events} completed events per disjoint cohort",
    )


def _not_evaluated(
    condition_id: str, name: str, formula: str, threshold: str, sample: str
) -> Condition:
    return Condition(
        condition_id=condition_id,
        name=name,
        formula=formula,
        threshold=threshold,
        minimum_sample=sample,
        status=ConditionStatus.NOT_EVALUATED,
        value=None,
        sample=None,
        assessed_on=None,
        note=NOT_EVALUATED,
    )


# --- R5's cost (TD-21) -----------------------------------------------------------------------


def cost_note(config: ThesisConfig) -> CostNote:
    sample = config.r5_cost
    fee_points = config.cost_sample.fee_per_contract_transaction_usd / (
        config.cost_sample.contract_multiplier
    )

    def side(legs: int, spread: float, mid: float, fraction: float) -> LegCost:
        fees = _TRANSACTIONS_PER_LEG * fee_points / mid
        return LegCost(
            legs=legs,
            median_spread_points=spread,
            median_mid_points=mid,
            median_spread_fraction_of_mid=fraction,
            base_share=fraction + fees,
            stressed_share=(
                sample.stressed_spread_multiple * fraction + sample.stressed_fee_multiple * fees
            ),
        )

    return CostNote(
        sample_session=date.fromisoformat(sample.sample_session),
        sample_expiry=date.fromisoformat(sample.sample_expiry),
        sample_vix_points=sample.sample_vix_points,
        absolute_delta_low=sample.absolute_delta_low,
        absolute_delta_high=sample.absolute_delta_high,
        fee_per_contract_transaction_usd=config.cost_sample.fee_per_contract_transaction_usd,
        stressed_spread_multiple=sample.stressed_spread_multiple,
        stressed_fee_multiple=sample.stressed_fee_multiple,
        puts=side(
            sample.put_legs,
            sample.put_median_spread_points,
            sample.put_median_mid_points,
            sample.put_median_spread_fraction_of_mid,
        ),
        calls=side(
            sample.call_legs,
            sample.call_median_spread_points,
            sample.call_median_mid_points,
            sample.call_median_spread_fraction_of_mid,
        ),
        spec_condor=sample.spec_condor,
    )
