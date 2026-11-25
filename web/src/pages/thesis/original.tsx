// The original spike-based version, as a reference (UI-SPEC §6 › Thesis; PO, TD-23, TD-30, TD-33):
// its own state, groups, observations and wrong-if conditions, unchanged and never shown as
// evidence for versions A or B. Every count is of completed (matured) observations.
import { DataTable, type TableColumn } from "../../components/DataTable";
import { count, iv, orDash } from "../../format/number";
import {
  completed,
  eligibilityLabel,
  level,
  outcomeLabel,
  signalLabel,
  variance,
  volPts,
} from "../../format/thesis";
import type { Thesis, ThesisCohort, ThesisEpisode } from "../../types/generated/thesis";
import { lead } from "./assessment";
import { assessment, words } from "./invalidate";
import { Titled } from "./parts";
import { gapPhrase } from "./versions";

/** The same as a sentence of its own. */
export function gapSentence(c: ThesisCohort): string {
  const phrase = gapPhrase(c);
  return phrase === null ? "No completed observation yet."
    : `${phrase.charAt(0).toUpperCase()}${phrase.slice(1)}.`;
}

function unit(c: ThesisCohort): string {
  if (c.count === 0) return "no completed observation yet";
  return c.count === 1 ? "volatility points" : "volatility points, on average";
}

function Group({ title, cohort }: { title: string; cohort: ThesisCohort }) {
  return (
    <Titled className="th-card" title={`${title}: ${completed(cohort.count)}`}>
      <p className="th-figure">
        {cohort.mean_vol_gap === null ? "—" : volPts(cohort.mean_vol_gap).replace(" pts", "")}
        <span className="th-figure-unit">{unit(cohort)}</span>
      </p>
      <p>{gapSentence(cohort)}</p>
    </Titled>
  );
}

/** The limits of the comparison, next to it. */
export function sampleLimits(t: Thesis): string {
  const { stable, unstable } = t.evidence.cohorts;
  const target = t.evidence.validation_target_per_cohort;
  const small = stable.count < target || unstable.count < target;
  const sample = small ? "a very small sample" : "a limited historical sample";
  return `These are preliminary observations from ${sample}. They do not establish trading `
    + "profitability.";
}

/** The observations the comparison leaves out, for want of credit data. */
export function leftOut(t: Thesis): string {
  const n = t.evidence.cohorts.credit_unavailable.count;
  if (n === 0) return "No completed observation is left out for want of credit data.";
  return n === 1
    ? "1 other completed observation is left out of this comparison because credit data was "
      + "unavailable at its assessment."
    : `${count(n)} other completed observations are left out of this comparison because credit data `
      + "was unavailable at their assessment.";
}

const GROUP_NAMES: Readonly<Record<string, string>> = {
  "all matured sessions": "Every session",
  "all candidates": "All qualifying observations",
  "stable credit": "Qualifying, credit stable",
  "unstable credit": "Qualifying, credit not stable",
  "credit unavailable": "Qualifying, credit data unavailable",
};

function groupName(c: ThesisCohort): string {
  return GROUP_NAMES[c.name] ?? c.name;
}

const COHORT_COLUMNS: readonly TableColumn<ThesisCohort>[] = [
  { id: "name", header: "Group", sort: groupName, cell: groupName },
  { id: "n", header: "Completed", num: true, sort: (c) => c.count, cell: (c) => count(c.count) },
  { id: "gap", header: "Gap, mean", num: true, sort: (c) => c.mean_vol_gap ?? undefined,
    cell: (c) => orDash(c.mean_vol_gap, volPts) },
  { id: "gap-median", header: "Gap, median", num: true, sort: (c) => c.median_vol_gap ?? undefined,
    cell: (c) => orDash(c.median_vol_gap, volPts) },
  { id: "mean", header: "Variance premium, mean", num: true,
    sort: (c) => c.mean_premium ?? undefined, cell: (c) => orDash(c.mean_premium, variance) },
  { id: "median", header: "Variance premium, median", num: true,
    sort: (c) => c.median_premium ?? undefined, cell: (c) => orDash(c.median_premium, variance) },
  { id: "vix", header: "Starting VIX, mean", num: true, sort: (c) => c.mean_start_vix ?? undefined,
    cell: (c) => orDash(c.mean_start_vix, level) },
  { id: "first", header: "From", sort: (c) => c.first_day ?? undefined,
    cell: (c) => orDash(c.first_day, String) },
  { id: "last", header: "To", sort: (c) => c.last_day ?? undefined,
    cell: (c) => orDash(c.last_day, String) },
];

const OBSERVATION_COLUMNS: readonly TableColumn<ThesisEpisode>[] = [
  { id: "day", header: "Observation", sort: (e) => e.candidate_day ?? undefined,
    cell: (e) => orDash(e.candidate_day, String) },
  { id: "credit", header: "Credit at its assessment", sort: (e) => e.eligibility ?? undefined,
    cell: (e) => orDash(e.eligibility, eligibilityLabel) },
  { id: "vix", header: "VIX", num: true, sort: (e) => e.vix ?? undefined,
    cell: (e) => orDash(e.vix, level) },
  { id: "realized", header: "Following 30 days", num: true,
    sort: (e) => e.realized_vol ?? undefined,
    cell: (e) => (e.realized_vol === null ? orDash(e.outcome, outcomeLabel) : iv(e.realized_vol)) },
  { id: "premium", header: "Variance premium", num: true, sort: (e) => e.premium ?? undefined,
    cell: (e) => orDash(e.premium, variance) },
  { id: "end", header: "Window ends", sort: (e) => e.outcome_end ?? undefined,
    cell: (e) => orDash(e.outcome_end, String) },
];

function History({ thesis }: { thesis: Thesis }) {
  const c = thesis.evidence.cohorts;
  const groups = [c.all_sessions, c.candidates, c.stable, c.unstable, c.credit_unavailable];
  const observed = thesis.episodes.filter((e) => e.candidate_day !== null).reverse();
  return (
    <>
      <p>The table sets out every group of completed (matured) observations. The gap is VIX minus the
        volatility that followed, in volatility points. The variance premium is the same comparison
        in variance: VIX&apos;s implied 30-day variance minus the variance that followed.</p>
      <DataTable label="Original groups" rows={groups} columns={COHORT_COLUMNS} rowId={(g) => g.name} grow />
      <p>The table lists each qualifying observation, newest first, with what credit was at its
        assessment and what followed.</p>
      <DataTable label="Original qualifying observations" rows={observed} columns={OBSERVATION_COLUMNS}
                 rowId={(e) => e.episode_id} />
      <p className="th-caption">
        A larger gap can reflect a higher starting VIX, and consecutive sessions share most of their
        30 days, so the every-session row is far fewer independent observations than its count. A
        future validation target is {thesis.evidence.validation_target_per_cohort} completed
        observations in each credit group.
      </p>
    </>
  );
}

/** The original's wrong-if conditions, as they were defined and stood. */
function Conditions({ thesis }: { thesis: Thesis }) {
  return (
    <ul className="th-list">
      {thesis.evidence.conditions.map((k) => (
        <li key={k.condition_id}>
          <b>{k.condition_id}.</b> {words(k.formula)}; {words(k.threshold)}. Needs{" "}
          {k.minimum_sample}. {assessment(k)}
        </li>
      ))}
    </ul>
  );
}

export function OriginalReference({ thesis }: { thesis: Thesis }) {
  const { stable, unstable } = thesis.evidence.cohorts;
  return (
    <>
      <p>
        <b>This is the original version, kept as a reference. It is not evidence for versions A or
          B.</b> It looked only in the ten sessions after a spike in VIX, for the first session whose
        gap was wide enough and whose market swings had eased, and then read credit at that session.
      </p>
      <p>Its state today: {signalLabel(thesis.signal.status)}. {lead(thesis.signal)}</p>
      <div className="th-pair">
        <Group title="Original, stable credit" cohort={stable} />
        <Group title="Original, unstable credit" cohort={unstable} />
      </div>
      {!(stable.count && unstable.count) && (
        <p>Credit-regime comparison unavailable in this sample.</p>
      )}
      <p><b>{sampleLimits(thesis)}</b> {leftOut(thesis)}</p>
      <History thesis={thesis} />
      <p>Its wrong-if conditions, as defined and as they stand:</p>
      <Conditions thesis={thesis} />
    </>
  );
}
