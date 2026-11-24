// The thesis page's wrong-if cards (UI-SPEC §6 › Thesis; PO, TD-08, TD-24, TD-30): K1-K3 as defined,
// each in plain language with the sample it needs and one assessment statement; its numbers, units
// and exact formula behind a disclosure (TD-32). Too small a sample is never a pass.
import { longDate } from "../../components/charts/axis";
import { count } from "../../format/number";
import { completed, variance } from "../../format/thesis";
import type { Thesis, ThesisCondition } from "../../types/generated/thesis";
import { Disclosure, Section, Titled } from "./parts";

interface CardCopy {
  title: string;
  plain: string;
  /** The sample the condition needs, in plain words. */
  needs: (n: number) => string;
}

const CARDS: Readonly<Record<string, CardCopy>> = {
  K1: { title: "The apparent pricing advantage disappears",
        plain: "Over a sufficient sample, implied variance no longer exceeds the variance "
          + "subsequently realized.",
        needs: (n) => `the latest ${n} completed observations with stable credit` },
  K2: { title: "Trading costs consume the opportunity",
        plain: "The proposed trades fail to earn positive average returns after costs.",
        needs: (n) => `the latest ${n} completed trades` },
  K3: { title: "The credit filter provides no benefit",
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
function words(text: string): string {
  return text.replaceAll("_", " ").replaceAll("<=", "≤");
}

function needed(k: ThesisCondition): string {
  const copy = CARDS[k.condition_id];
  return copy === undefined || k.required === null ? k.minimum_sample : copy.needs(k.required);
}

/** The numbers behind the assessment, with their units and date. */
function Evaluation({ k }: { k: ThesisCondition }) {
  if (k.status === "NOT_EVALUATED") {
    return <p>Its value and sample are not measured until then.</p>;
  }
  return (
    <>
      <p>
        {k.value === null ? "No value is available" : `The current value is ${variance(k.value)}`} in
        variance units: VIX&apos;s implied 30-day variance minus the variance that followed, averaged
        over {completed(k.sample ?? 0)} with stable credit.
        {k.assessed_on !== null && ` It is a rolling assessment as of ${longDate(k.assessed_on)}.`}
      </p>
      <p>A positive value means implied exceeded realized. Too small a sample is never read
        as a pass.</p>
    </>
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
        <Evaluation k={k} />
      </Disclosure>
    </Titled>
  );
}

export function Invalidate({ thesis }: { thesis: Thesis }) {
  return (
    <Section id="invalidate" title="What would invalidate the thesis"
             intro={<>Three conditions, fixed in advance. Any one of them would count against the
               thesis and call for a review.</>}>
      <div className="th-cards">
        {thesis.evidence.conditions.map((k) => <Card key={k.condition_id} k={k} />)}
      </div>
    </Section>
  );
}
