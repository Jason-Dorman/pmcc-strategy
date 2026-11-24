// The thesis page's wrong-if conditions, preliminary evidence and alpha/cost note (UI-SPEC §6 ›
// Thesis; T4-01; PO, TD-08, TD-21, TD-23, TD-24). Every sentence of evidence and every number is
// the file's; nothing here classifies it.
import { KeyValue } from "../../components/cells";
import { longDate } from "../../components/charts/axis";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { Note } from "../../components/Note";
import { count, iv, orDash, pct } from "../../format/number";
import {
  conditionLabel,
  eligibilityLabel,
  level,
  outcomeLabel,
  shareSigned,
  variance,
  volPts,
} from "../../format/thesis";
import type {
  Thesis,
  ThesisCohort,
  ThesisCondition,
  ThesisCost,
  ThesisEpisode,
  ThesisLegCost,
} from "../../types/generated/thesis";

const STATUS_CLASS: Readonly<Record<string, string>> = {
  FAIL: "pm-flag",
  INSUFFICIENT_DATA: "pm-skip",
  NOT_EVALUATED: "pm-label",
};

/** The spec's formula as a reader's: its identifiers as words, its signs as signs. */
function words(text: string): string {
  return text.replaceAll("_", " ").replaceAll("<=", "≤");
}

const CONDITION_COLUMNS: readonly TableColumn<ThesisCondition>[] = [
  { id: "id", header: "ID", sort: (k) => k.condition_id, cell: (k) => k.condition_id },
  { id: "name", header: "The thesis is wrong if", sort: (k) => k.name,
    cell: (k) => <div className="pm-prose"><b>{k.name}</b>: {words(k.formula)}; {words(k.threshold)}.</div> },
  { id: "minimum", header: "Needs", sort: (k) => k.minimum_sample, cell: (k) => k.minimum_sample },
  { id: "sample", header: "Sample", num: true, sort: (k) => k.sample ?? undefined,
    cell: (k) => (k.sample === null ? "Unavailable" : count(k.sample)) },
  { id: "value", header: "Current value", num: true, sort: (k) => k.value ?? undefined,
    cell: (k) => (k.value === null ? "Unavailable"
      : `${variance(k.value)}${k.status === "INSUFFICIENT_DATA" ? " (provisional)" : ""}`) },
  { id: "assessed", header: "Assessed on", sort: (k) => k.assessed_on ?? undefined,
    cell: (k) => orDash(k.assessed_on, String) },
  { id: "status", header: "Status", sort: (k) => k.status,
    cell: (k) => <span className={STATUS_CLASS[k.status]}>{conditionLabel(k.status)}</span> },
  { id: "note", header: "Note", sort: (k) => k.note,
    cell: (k) => <div className="pm-prose">{k.note}</div> },
];

export function Conditions({ thesis }: { thesis: Thesis }) {
  return <DataTable label="Wrong-if conditions" rows={thesis.evidence.conditions}
                    columns={CONDITION_COLUMNS} rowId={(k) => k.condition_id} wrap grow />;
}

// ---- the evidence -------------------------------------------------------------------------------

const COHORT_NAMES: Readonly<Record<string, string>> = {
  "all matured sessions": "All sessions",
  "all candidates": "All candidates",
  "stable credit": "Stable-credit candidates",
  "unstable credit": "Unstable-credit candidates",
  "credit unavailable": "Candidates without credit data",
};

function cohortName(c: ThesisCohort): string {
  return COHORT_NAMES[c.name] ?? c.name;
}

const COHORT_COLUMNS: readonly TableColumn<ThesisCohort>[] = [
  { id: "name", header: "Group", sort: cohortName, cell: cohortName },
  { id: "n", header: "Matured", num: true, sort: (c) => c.count, cell: (c) => count(c.count) },
  { id: "mean", header: "Mean variance premium", num: true,
    sort: (c) => c.mean_premium ?? undefined, cell: (c) => orDash(c.mean_premium, variance) },
  { id: "median", header: "Median", num: true, sort: (c) => c.median_premium ?? undefined,
    cell: (c) => orDash(c.median_premium, variance) },
  { id: "gap", header: "VIX − realized, mean", num: true, sort: (c) => c.mean_vol_gap ?? undefined,
    cell: (c) => orDash(c.mean_vol_gap, volPts) },
  { id: "gap-median", header: "Median", num: true, sort: (c) => c.median_vol_gap ?? undefined,
    cell: (c) => orDash(c.median_vol_gap, volPts) },
  { id: "vix", header: "Starting VIX, mean", num: true, sort: (c) => c.mean_start_vix ?? undefined,
    cell: (c) => orDash(c.mean_start_vix, level) },
  { id: "first", header: "From", sort: (c) => c.first_day ?? undefined,
    cell: (c) => orDash(c.first_day, String) },
  { id: "last", header: "To", sort: (c) => c.last_day ?? undefined,
    cell: (c) => orDash(c.last_day, String) },
];

function cohortsOf(t: Thesis): ThesisCohort[] {
  const c = t.evidence.cohorts;
  return [c.all_sessions, c.candidates, c.stable, c.unstable, c.credit_unavailable];
}

/** Every candidate, newest first: the episodes the groups above are made of. */
function candidatesOf(t: Thesis): ThesisEpisode[] {
  return t.episodes.filter((e) => e.candidate_day !== null).reverse();
}

const CANDIDATE_COLUMNS: readonly TableColumn<ThesisEpisode>[] = [
  { id: "day", header: "Candidate", sort: (e) => e.candidate_day ?? undefined,
    cell: (e) => orDash(e.candidate_day, String) },
  { id: "credit", header: "Credit at its decision", sort: (e) => e.eligibility ?? undefined,
    cell: (e) => orDash(e.eligibility, eligibilityLabel) },
  { id: "vix", header: "VIX", num: true, sort: (e) => e.vix ?? undefined,
    cell: (e) => orDash(e.vix, level) },
  { id: "realized", header: "Realized after", num: true, sort: (e) => e.realized_vol ?? undefined,
    cell: (e) => (e.realized_vol === null ? orDash(e.outcome, outcomeLabel) : iv(e.realized_vol)) },
  { id: "premium", header: "Variance premium", num: true, sort: (e) => e.premium ?? undefined,
    cell: (e) => orDash(e.premium, variance) },
  { id: "end", header: "Outcome ends", sort: (e) => e.outcome_end ?? undefined,
    cell: (e) => orDash(e.outcome_end, String) },
];

export function HistoricalEvidence({ thesis }: { thesis: Thesis }) {
  const { evidence } = thesis;
  const { stable, unstable } = evidence.cohorts;
  const target = evidence.validation_target_per_cohort;
  return (
    <>
      <Note>
        {evidence.statements.map((s) => <p key={s}>{s}</p>)}
      </Note>
      <DataTable label="Preliminary historical evidence" rows={cohortsOf(thesis)}
                 columns={COHORT_COLUMNS} rowId={(c) => c.name} grow narrow />
      <Note>
        <p>
          The variance premium is VIX&apos;s implied 30-day variance minus the variance then
          realized, in the same units: positive means options overpriced the moves that followed. A
          larger gap can also reflect a higher starting VIX. Exploratory: credit data covers about
          three years. A future validation target is {target} matured episodes in each credit group;
          there are {stable.count} with stable credit and {unstable.count} with unstable so far.
        </p>
      </Note>
      <DataTable label="Candidates" rows={candidatesOf(thesis)} columns={CANDIDATE_COLUMNS}
                 rowId={(e) => e.episode_id} narrow />
    </>
  );
}

// ---- alpha and cost -----------------------------------------------------------------------------

interface EdgeRow {
  cohort: ThesisCohort;
}

const EDGE_COLUMNS: readonly TableColumn<EdgeRow>[] = [
  { id: "name", header: "Edge: variance premium", sort: (r) => cohortName(r.cohort),
    cell: (r) => cohortName(r.cohort) },
  { id: "n", header: "N", num: true, sort: (r) => r.cohort.count,
    cell: (r) => count(r.cohort.count) },
  { id: "mean", header: "Mean", num: true, sort: (r) => r.cohort.mean_premium ?? undefined,
    cell: (r) => orDash(r.cohort.mean_premium, variance) },
  { id: "median", header: "Median", num: true, sort: (r) => r.cohort.median_premium ?? undefined,
    cell: (r) => orDash(r.cohort.median_premium, variance) },
  { id: "share", header: "Of VIX", num: true,
    sort: (r) => r.cohort.mean_overstatement ?? undefined,
    cell: (r) => orDash(r.cohort.mean_overstatement, shareSigned) },
];

interface CostRow {
  name: string;
  leg: ThesisLegCost;
}

const COST_COLUMNS: readonly TableColumn<CostRow>[] = [
  { id: "name", header: "Cost: one leg, round trip", sort: (r) => r.name, cell: (r) => r.name },
  { id: "n", header: "N", num: true, sort: (r) => r.leg.legs, cell: (r) => count(r.leg.legs) },
  { id: "base", header: "Share of value", num: true, sort: (r) => r.leg.base_share,
    cell: (r) => pct(r.leg.base_share) },
  { id: "stressed", header: "Stressed", num: true, sort: (r) => r.leg.stressed_share,
    cell: (r) => pct(r.leg.stressed_share) },
];

function costRows(cost: ThesisCost): CostRow[] {
  return [{ name: "Put", leg: cost.puts }, { name: "Call", leg: cost.calls }];
}

/** The rough reading, in the file's own numbers, with no verdict (TD-07, TD-21). */
export function roughReading(t: Thesis): string {
  const { candidates } = t.evidence.cohorts;
  const { puts, calls } = t.evidence.cost;
  if (candidates.mean_overstatement === null) {
    return "No candidate's outcome has matured, so there is no edge to set against the cost yet.";
  }
  const side = candidates.mean_overstatement >= 0 ? "overstated" : "understated";
  return `Across ${count(candidates.count)} matured candidates, VIX ${side} the volatility that `
    + `followed by ${pct(Math.abs(candidates.mean_overstatement))} on average, before costs. `
    + `Opening and closing one leg cost about ${pct(puts.base_share)} of a put's value and `
    + `${pct(calls.base_share)} of a call's on the sample day.`;
}

export function AlphaCost({ thesis }: { thesis: Thesis }) {
  const { cost } = thesis.evidence;
  return (
    <>
      <Note>
        <p><b>Gross economic premium, not tradable alpha.</b> {roughReading(thesis)} The two are on
          roughly comparable scales only if an option&apos;s value moves in proportion to volatility,
          which it does not exactly. A four-leg condor pays its cost on every leg.</p>
      </Note>
      <div className="pm-stack">
        <DataTable label="Edge" rows={cohortsOf(thesis).map((cohort) => ({ cohort }))}
                   columns={EDGE_COLUMNS} rowId={(r) => r.cohort.name} grow narrow />
        <DataTable label="Cost" rows={costRows(cost)} columns={COST_COLUMNS}
                   rowId={(r) => r.name} grow narrow />
      </div>
      <KeyValue label="Cost assumptions" rows={[
        ["Sampled at the close of", longDate(cost.sample_session)],
        ["S&P 500 weekly options expiring", longDate(cost.sample_expiry)],
        ["VIX that day", level(cost.sample_vix_points)],
        ["Legs between (absolute delta)", `${cost.absolute_delta_low} and ${cost.absolute_delta_high}`],
        ["Median bid–ask spread, puts", `${level(cost.puts.median_spread_points)} points, `
          + `${pct(cost.puts.median_spread_fraction_of_mid)} of mid`],
        ["Median bid–ask spread, calls", `${level(cost.calls.median_spread_points)} points, `
          + `${pct(cost.calls.median_spread_fraction_of_mid)} of mid`],
        ["Fee per contract, each way", `$${cost.fee_per_contract_transaction_usd.toFixed(2)}`],
        ["Stressed case", `${cost.stressed_spread_multiple}× spread, `
          + `${cost.stressed_fee_multiple}× fees`],
        ["The thesis's iron condor", cost.spec_condor],
      ]} />
      <Note>
        <p>Of VIX is the mean share by which VIX overstated the volatility that followed. Share of
          value is the spread plus two fees, over the option&apos;s mid.</p>
        <p>Limitations: one day&apos;s closing quotes, on a day VIX had spiked; a round trip is taken
          to cost one full spread; no fills, margin, slippage or tail losses; and no net return is
          claimed. The edge is measured on the index, not on any option traded.</p>
      </Note>
    </>
  );
}
