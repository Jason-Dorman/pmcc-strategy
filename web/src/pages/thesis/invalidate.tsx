// The thesis page's wrong-if cards (UI-SPEC §6 › Thesis; PO, TD-08, TD-24, TD-30): K1-K3 as defined,
// each in plain language with its status, sample and exact formula. An unmeasured value is said to
// be unmeasured, never zero, and too small a sample is never a pass.
import type { ReactNode } from "react";

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
        needs: (n) => `The latest ${n} completed observations with stable credit` },
  K2: { title: "Trading costs consume the opportunity",
        plain: "The proposed trades fail to earn positive average returns after costs.",
        needs: (n) => `The latest ${n} completed trades` },
  K3: { title: "The credit filter provides no benefit",
        plain: "Trades selected during stable credit conditions perform no better than comparable "
          + "trades during unstable conditions.",
        needs: (n) => `At least ${n} completed trades in each credit group` },
};

const NEXT_PHASE = "Evaluated in the next phase: strategy backtesting.";

function preliminary(k: ThesisCondition): string {
  const n = count(k.sample ?? 0);
  return k.required === null
    ? `Preliminary: ${n} observations available, of ${k.minimum_sample} required`
    : `Preliminary: ${n} of the required ${k.required} observations available`;
}

/** A condition's status in words, with its sample. */
export function conditionStatus(k: ThesisCondition): string {
  if (k.status === "NOT_EVALUATED") return NEXT_PHASE;
  if (k.status === "INSUFFICIENT_DATA") return preliminary(k);
  return k.status === "FAIL" ? "Triggered: this condition holds, so the thesis needs review"
    : "Not triggered on the current rolling sample";
}

const STATUS_ICONS: Readonly<Record<string, string>> = {
  NOT_EVALUATED: "○", INSUFFICIENT_DATA: "◐", FAIL: "✕", PASS: "✓",
};

/** The spec's formula as a reader's: its identifiers as words, its signs as signs. */
function words(text: string): string {
  return text.replaceAll("_", " ").replaceAll("<=", "≤");
}

function Row({ name, children }: { name: string; children: ReactNode }) {
  return <div><dt>{name}</dt><dd>{children}</dd></div>;
}

function needed(k: ThesisCondition): string {
  const copy = CARDS[k.condition_id];
  return copy === undefined || k.required === null ? k.minimum_sample : copy.needs(k.required);
}

function Facts({ k }: { k: ThesisCondition }) {
  return (
    <dl className="th-facts">
      <Row name="Sample needed">{needed(k)}</Row>
      <Row name="Available">{k.sample === null ? "Not measured yet" : completed(k.sample)}</Row>
      <Row name="Current value">
        {k.value === null ? "Not measured yet"
          : `${variance(k.value)} variance units on average: implied minus realized, over 30 days`}
      </Row>
      {k.assessed_on !== null && (
        <Row name="Rolling assessment">as of {longDate(k.assessed_on)}</Row>
      )}
    </dl>
  );
}

function Card({ k }: { k: ThesisCondition }) {
  const copy = CARDS[k.condition_id];
  return (
    <Titled className={`th-card th-status-${k.status.toLowerCase()}`} title={copy?.title ?? k.name}>
      <p>{copy?.plain ?? words(k.formula)}</p>
      <p className="th-status">
        <span aria-hidden="true">{STATUS_ICONS[k.status] ?? "○"}</span> {conditionStatus(k)}
      </p>
      <Facts k={k} />
      <Disclosure title="Exact formula and evaluation">
        <p><b>{k.condition_id}.</b> {words(k.formula)}; {words(k.threshold)}. Needs{" "}
          {k.minimum_sample}.</p>
        {k.value !== null && (
          <p>The variance premium is VIX&apos;s implied 30-day variance minus the variance that
            followed, so a positive value means implied exceeded realized. Only completed
            observations with stable credit count.</p>
        )}
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
