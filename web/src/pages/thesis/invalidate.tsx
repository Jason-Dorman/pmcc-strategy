// The thesis page's wrong-if cards (UI-SPEC §6 › Thesis; PO, TD-08, TD-24, TD-30, TD-33): the first
// revised and assessed for versions A and B apart, the other two as defined for the backtest, each in
// plain language with the sample it needs and one assessment statement; its numbers, units
// and exact formula behind a disclosure (TD-32). Too small a sample is never a pass.
import { longDate } from "../../components/charts/axis";
import { count } from "../../format/number";
import { completed, variance } from "../../format/thesis";
import type { Thesis, ThesisComparison, ThesisCondition } from "../../types/generated/thesis";
import { Disclosure, NotAvailable, Section, Titled } from "./parts";

interface CardCopy {
  title: string;
  plain: string;
  /** The sample the condition needs, in plain words. */
  needs: (n: number) => string;
}

const CARDS: Readonly<Record<string, CardCopy>> = {
  K2: { title: "Returns fail to remain positive after costs",
        plain: "The strategy's actual trades fail to earn positive average returns after costs.",
        needs: (n) => `the latest ${n} completed trades` },
  K3: { title: "Stable-credit selection provides no benefit",
        plain: "Trades selected during stable credit conditions perform no better than comparable "
          + "trades during unstable conditions.",
        needs: (n) => `at least ${n} completed trades in each credit group` },
};

const NEXT_PHASE = "Evaluated in the next phase: strategy backtesting.";

/** `5 of the required 30 observations are available`. */
function available(sample: number, required: number): string {
  return `${count(sample)} of the required ${count(required)} observations `
    + `${sample === 1 ? "is" : "are"} available`;
}

function signOf(value: number): string {
  if (value > 0) return "positive";
  return value < 0 ? "negative" : "zero";
}

/** Too few observations: the average so far and how few, never a pass. */
function insufficient(k: ThesisCondition): string {
  const sample = k.sample ?? 0;
  const few = k.required === null ? `${completed(sample)} so far, fewer than required`
    : available(sample, k.required);
  if (k.value === null) {
    return sample === 0 ? `The average variance premium cannot be assessed yet: ${few}.`
      : `The average variance premium is unavailable; only ${few}.`;
  }
  return `The average variance premium is currently ${signOf(k.value)}, `
    + `${k.value > 0 ? "but" : "and"} only ${few}.`;
}

function assessed(k: ThesisCondition): string {
  const sign = k.value === null ? "unavailable" : signOf(k.value);
  const over = k.required === null ? "the required observations"
    : `the latest ${count(k.required)} observations`;
  return k.status === "FAIL"
    ? `The average variance premium over ${over} is ${sign}: this condition holds, so the thesis `
      + "needs review."
    : `The average variance premium over ${over} is ${sign}: this condition does not hold on the `
      + "current rolling sample.";
}

/** A condition's one assessment statement, by the backend's status. */
export function assessment(k: ThesisCondition): string {
  if (k.status === "NOT_EVALUATED") return NEXT_PHASE;
  return k.status === "INSUFFICIENT_DATA" ? insufficient(k) : assessed(k);
}

const STATUS_ICONS: Readonly<Record<string, string>> = {
  NOT_EVALUATED: "○", INSUFFICIENT_DATA: "◐", FAIL: "✕", PASS: "✓",
};

/** The spec's formula as a reader's: its identifiers as words, its signs as signs. */
export function words(text: string): string {
  return text.replaceAll("_", " ").replaceAll("<=", "≤");
}

function needed(k: ThesisCondition): string {
  const copy = CARDS[k.condition_id];
  return copy === undefined || k.required === null ? k.minimum_sample : copy.needs(k.required);
}

/** The numbers behind one version's revised first condition, with their units and date. */
function Numbers({ k }: { k: ThesisCondition }) {
  return (
    <p>
      <b>{k.condition_id}.</b> {words(k.formula)}; {words(k.threshold)}. Needs {k.minimum_sample}.{" "}
      {k.value === null ? "No value is available" : `The current value is ${variance(k.value)}`} in
      variance units, over {completed(k.sample ?? 0)}
      {k.assessed_on !== null && `, a rolling assessment as of ${longDate(k.assessed_on)}`}.
    </p>
  );
}

/** The first condition, revised: one statement per version (TD-33). */
function PremiumCard({ c }: { c: ThesisComparison | null }) {
  return (
    <Titled className="th-card th-status-premium" title="The observed variance premium disappears">
      <p>Over a sufficient sample, implied variance no longer exceeds the variance subsequently
        realized.</p>
      {c === null ? (
        <NotAvailable>The versions&apos; results are not in this data file. They arrive with the next
          nightly update.</NotAvailable>
      ) : (
        <>
          <p className="th-caption">
            Needs, for each version: the latest {c.versions[0]?.k1.required ?? ""} completed
            observations at least {c.spacing_calendar_days} calendar days apart.
          </p>
          {c.versions.map((v) => (
            <p className="th-status" key={v.key}>
              <span aria-hidden="true">{STATUS_ICONS[v.k1.status] ?? "○"}</span> Version {v.key}:{" "}
              {assessment(v.k1)}
            </p>
          ))}
          <Disclosure title="Exact formula and evaluation">
            {c.versions.map((v) => <Numbers key={v.key} k={v.k1} />)}
            <p>A positive value means implied exceeded realized. Too small a sample is never read as a
              pass. This is a revised observation definition; the original version&apos;s is kept in
              its reference section.</p>
          </Disclosure>
        </>
      )}
    </Titled>
  );
}

function Card({ k }: { k: ThesisCondition }) {
  const copy = CARDS[k.condition_id];
  return (
    <Titled className={`th-card th-status-${k.status.toLowerCase()}`} title={copy?.title ?? k.name}>
      <p>{copy?.plain ?? words(k.formula)}</p>
      <p className="th-caption">Needs: {needed(k)}.</p>
      <p className="th-status">
        <span aria-hidden="true">{STATUS_ICONS[k.status] ?? "○"}</span> {assessment(k)}
      </p>
      <Disclosure title="Exact formula and evaluation">
        <p><b>{k.condition_id}.</b> {words(k.formula)}; {words(k.threshold)}. Needs{" "}
          {k.minimum_sample}.</p>
        <p>Its value and sample are not measured until then. The backtest would run versions A and B
          on the same contracts, sizing, costs and exits.</p>
      </Disclosure>
    </Titled>
  );
}

export function Invalidate({ thesis }: { thesis: Thesis }) {
  return (
    <Section id="invalidate" title="What would invalidate the thesis"
             intro={<>Three defined conditions for reviewing this thesis. Any one of them would count
               against it and call for reassessment.</>}>
      <div className="th-cards">
        <PremiumCard c={thesis.comparison} />
        {thesis.evidence.conditions.filter((k) => k.status === "NOT_EVALUATED")
          .map((k) => <Card key={k.condition_id} k={k} />)}
      </div>
    </Section>
  );
}
