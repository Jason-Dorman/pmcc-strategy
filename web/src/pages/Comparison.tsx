// Comparison, the landing page (UI-SPEC §6.1): quant against the baseline on one symbol. The
// readouts and headline come from each strategy's summary, the NAV chart from both full runs'
// ledgers, the pooled universe from `universe/pooled.json` and the ablations from the symbol's
// `robustness.json` (DEC-105); the purpose panel's sentence on the result's main limit reads both
// runs' leg attribution (DEC-109).
import { useParams } from "react-router-dom";

import { STRATEGY_PAGES } from "../app/pages";
import { pending, PageFrame } from "../components/PageFrame";
import { RobustnessTable } from "../components/RobustnessTable";
import { useIndex } from "../data/IndexContext";
import { both } from "../data/state";
import { strategyName, useRun, useSymbolFile, useUniverseFile } from "../data/useRun";
import { W_FULL, W_HALF } from "../theme/tokens";
import type { Pooled as PooledFile } from "../types/generated/pooled";
import type { Robustness } from "../types/generated/robustness";
import { READOUT_HINTS, readouts } from "./compare/figures";
import { Headline, NavCompare, Pooled, POOLED_CAPTION, Purpose } from "./compare/sections";
import { panel, whenLoaded } from "./placeholder";

const QUANT = STRATEGY_PAGES.quant;

export function Comparison() {
  const { symbol = "" } = useParams();
  const index = useIndex();
  const runs = both(useRun(symbol, QUANT), useRun(symbol, STRATEGY_PAGES.baseline));
  const robustness = useSymbolFile<Robustness>(symbol, "robustness");
  const pooled = useUniverseFile<PooledFile>("pooled");
  const ready = runs.kind === "ready" ? runs.value : null;
  const name = (id: string) => (index.kind === "ready" ? strategyName(index.value, id) : id);
  return (
    <PageFrame
      readouts={ready ? readouts(...ready) : pending(READOUT_HINTS.map(([l, h]) => [l, h]))}
      panels={[
        panel("purpose", "Purpose", W_FULL, <Purpose symbol={symbol} runs={ready} />, false),
        { ...panel("nav", "NAV — baseline vs quant", W_FULL,
                   whenLoaded(runs, ([q, b]) => <NavCompare quant={q} baseline={b} />)),
          note: "every hourly bar",
          caption: <>Each strategy&apos;s NAV from the same starting cash; hover for both and the
            difference. Each strategy&apos;s page has its account in full.</> },
        { ...panel("headline", "Headline", W_HALF,
                   whenLoaded(runs, (rs) => <Headline runs={rs} />)),
          caption: <>Return on starting NAV is P&amp;L ÷ the starting cash over the window, not
            annualized. Sharpe is the excess daily return over the risk-free rate ÷ its standard
            deviation, × √252. Payoff is the average winning week ÷ the average losing week; the
            CI resamples whole weeks.</> },
        { ...panel("pooled", "Pooled universe", W_HALF,
                   whenLoaded(pooled, (p) => <Pooled pooled={p} name={name} quantId={QUANT} />)),
          caption: POOLED_CAPTION },
        { ...panel("ablations", "Ablations", W_FULL,
                   whenLoaded(robustness, (r) => (
                     <RobustnessTable label="Ablations" rows={r.ablations} against="quant" />))),
          note: "each against quant",
          caption: <>Each ablation switches off one quant layer and keeps the rest. Δ is its
            P&amp;L less quant&apos;s, so a positive Δ means quant did better without that
            layer.</> },
      ]}
      manifests={ready ? ready.map((r) => r.manifest) : []}
    />
  );
}
