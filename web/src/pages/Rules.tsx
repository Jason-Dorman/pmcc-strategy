// Trade rules (UI-SPEC §6.3), rendered from rules.json (DEC-52): nothing on it is typed in. Both
// strategies' entry rules, gates and exits side by side with their live values and rationales,
// then the ablations and the sensitivity runs. Arriving at `#/rules/X-S3` scrolls to that rule's
// row and outlines it; every blotter row and gate-log entry links here (UI-SPEC §7).
import type { ReactNode } from "react";
import { useParams } from "react-router-dom";

import { Empty } from "../components/Note";
import { PageFrame } from "../components/PageFrame";
import { useRules } from "../data/useRun";
import { W_FULL, W_HALF } from "../theme/tokens";
import type { Rules as RulesFile } from "../types/generated/rules";
import { panel, whenLoaded } from "./placeholder";
import { pairOf, type Pair } from "./rules/model";
import { Ablations, HowRulesWork, RuleTable, Sensitivity } from "./rules/sections";

/** A body that needs both strategies' rules. */
function withPair(rules: RulesFile, body: (pair: Pair) => ReactNode) {
  const pair = pairOf(rules);
  return pair ? body(pair) : <Empty>No results for the baseline and quant strategies.</Empty>;
}

export function Rules() {
  const { ruleId } = useParams();
  const rules = useRules();
  const table = (section: "entry" | "gate" | "exit") =>
    whenLoaded(rules, (r) => withPair(r, (pair) => (
      <RuleTable pair={pair} section={section} target={ruleId} />)));
  return (
    <PageFrame
      panels={[
        panel("how", "How rules work", W_FULL,
              whenLoaded(rules, (r) => withPair(r, (pair) => (
                <HowRulesWork pair={pair} ruleId={ruleId} />))), false),
        { ...panel("entry", "Entry rules", W_FULL, table("entry")),
          note: "baseline and quant side by side, with the values they ran",
          caption: <>Quant reads Same where it runs the baseline&apos;s rule. ▸ opens a rule&apos;s
            rationale.</> },
        { ...panel("gates", "Skip-week gates", W_FULL, table("gate")),
          note: "checked in order at the week-open decision bar",
          caption: <>A gate that fires keeps the long and sells no short that week; the gate log
            on the quant page has each week&apos;s values. On shows the threshold the gate ran
            at.</> },
        { ...panel("exits", "Exit rules", W_FULL, table("exit")),
          note: "each trigger and what it does",
          caption: <>The rationales say why the short is never exercised, why there are no rolls,
            and why the Friday check keeps a buffer.</> },
        { ...panel("ablations", "Ablations", W_HALF,
                   whenLoaded(rules, (r) => <Ablations rules={r} />)),
          note: "quant with one layer switched off",
          caption: <>Each ablation is quant with the rule shown replaced or removed, and nothing else.
            The comparison page has their results.</> },
        { ...panel("sensitivity", "Sensitivity", W_HALF,
                   whenLoaded(rules, (r) => <Sensitivity rules={r} />)),
          note: "each run against the strategy it varies",
          caption: <>Robustness checks, not optimization: every run is published and none is
            picked as best. The methodology page has their results.</> },
      ]}
    />
  );
}
