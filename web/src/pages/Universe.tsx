// Universe (UI-SPEC §6.5): every symbol at once. The suitability screen from
// `universe/suitability.json` (DEC-66), the headline by symbol from `universe/headline.json` and the
// pooled universe from `universe/pooled.json` (DEC-105). No readouts: the comparison page has
// each symbol's.
import { useCallback } from "react";

import { STRATEGY_PAGES } from "../app/pages";
import { PageFrame } from "../components/PageFrame";
import { useIndex } from "../data/IndexContext";
import { strategyName, useRules, useUniverseFile } from "../data/useRun";
import { W_FULL } from "../theme/tokens";
import type { Headline } from "../types/generated/headline";
import type { Pooled as PooledFile } from "../types/generated/pooled";
import type { RuleOut } from "../types/generated/rules";
import type { Suitability as SuitabilityFile } from "../types/generated/suitability";
import { Pooled, POOLED_CAPTION } from "./compare/sections";
import { panel, whenLoaded } from "./placeholder";
import { HeadlineBySymbol, Suitability, SuitabilityCaption } from "./universe/sections";

const QUANT = STRATEGY_PAGES.quant;
const NO_RULES: readonly RuleOut[] = [];

export function Universe() {
  const index = useIndex();
  const suitability = useUniverseFile<SuitabilityFile>("suitability");
  const headline = useUniverseFile<Headline>("headline");
  const pooled = useUniverseFile<PooledFile>("pooled");
  const rules = useRules();
  const quantRules = rules.kind === "ready"
    ? rules.value.strategies.find((s) => s.id === QUANT)?.rules ?? NO_RULES
    : NO_RULES;
  const name = useCallback(
    (id: string) => (index.kind === "ready" ? strategyName(index.value, id) : id), [index]);
  return (
    <PageFrame
      panels={[
        { ...panel("suitability", "Symbol suitability", W_FULL,
                   whenLoaded(suitability, (s) => (
                     <Suitability suitability={s} rules={quantRules} />))),
          note: "one reading a week, from quant's picks",
          caption: <SuitabilityCaption rules={quantRules} /> },
        { ...panel("headline", "Headline by symbol", W_FULL,
                   whenLoaded(headline, (h) => (
                     <HeadlineBySymbol headline={h} name={name} quantId={QUANT} />))),
          note: "each symbol's comparison page has the rest",
          caption: <>Return on starting NAV is P&amp;L ÷ the starting cash over the window, not
            annualized; Sharpe is annualized from daily excess returns. Each symbol links to its
            comparison page.</> },
        { ...panel("pooled", "Pooled universe", W_FULL,
                   whenLoaded(pooled, (p) => <Pooled pooled={p} name={name} quantId={QUANT} />)),
          caption: POOLED_CAPTION },
      ]}
    />
  );
}
