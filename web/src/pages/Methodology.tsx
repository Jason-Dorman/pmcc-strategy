// Methodology (UI-SPEC §6.4): where the backtest stops, how it times decisions and fills them,
// how robust its result is, and what it assumes. The limits lead (PO, DEC-116). The data panels
// follow the symbol (the index's first when the route names none): the fill check with the
// pooled fit beside it, and the grid, friction and timing tables (DEC-105); r is the index's.
// The prose's figures are read from both full runs, `robustness.json` and `rules.json` as the
// page renders (DEC-109).
import { useParams } from "react-router-dom";

import { STRATEGY_PAGES } from "../app/pages";
import { Empty } from "../components/Note";
import { PageFrame } from "../components/PageFrame";
import { RobustnessTable } from "../components/RobustnessTable";
import { useIndex } from "../data/IndexContext";
import { both, type Loaded } from "../data/state";
import { useRules, useRun, useSymbolFile, useUniverseFile } from "../data/useRun";
import { W_FULL, W_HALF } from "../theme/tokens";
import type { FillCheck } from "../types/generated/fill_check";
import type { PooledFillCheck } from "../types/generated/pooled_fill_check";
import type { Robustness } from "../types/generated/robustness";
import { BarTiming, FillModel, Limits, ruleNames } from "./methodology/prose";
import { Assumptions, MidVsPrint, scatterCaption, TimingPanel } from "./methodology/sections";
import { panel, whenLoaded } from "./placeholder";

function value<T>(state: Loaded<T>): T | null {
  return state.kind === "ready" ? state.value : null;
}

function fillPanel(key: string, name: string, group: string, what: string,
                   fill: Loaded<FillCheck>, pooled: PooledFillCheck | null) {
  return {
    ...panel(key, name, W_HALF, whenLoaded(fill, (f) => {
      const found = f.groups.find((g) => g.group === group);
      return found
        ? <MidVsPrint symbol={f.symbol} group={found} label={name}
                      pooled={pooled?.groups.find((g) => g.group === group)} />
        : <Empty>No results for {f.symbol} / {group}.</Empty>;
    })),
    note: "every pair",
    caption: scatterCaption(what),
  };
}

/** The symbols with runs, and the one the page shows: the route's, else the index's first. */
function useSymbols(): { symbol: string; symbols: string[] } {
  const index = value(useIndex());
  const symbols = index?.symbols.filter((s) => s.runs.length > 0).map((s) => s.symbol) ?? [];
  const { symbol = symbols[0] ?? "" } = useParams();
  return { symbol, symbols };
}

export function Methodology() {
  const index = useIndex();
  const { symbol, symbols } = useSymbols();
  const runs = both(useRun(symbol, STRATEGY_PAGES.quant), useRun(symbol, STRATEGY_PAGES.baseline));
  const fill = useSymbolFile<FillCheck>(symbol, "fill_check");
  const robustness = useSymbolFile<Robustness>(symbol, "robustness");
  const pooledFill = value(useUniverseFile<PooledFillCheck>("pooled_fill_check"));
  const rules = value(useRules());
  const pair = value(runs);
  const name = ruleNames(pair ?? []);
  return (
    <PageFrame
      panels={[
        panel("limits", "Limits of this backtest", W_FULL,
              whenLoaded(runs, (rs) => (
                <Limits runs={rs} robustness={value(robustness)} rules={rules}
                        symbols={symbols} />)),
              false),
        panel("timing", "Bar timing and look-ahead guard", W_FULL, <BarTiming name={name} />,
              false),
        panel("fills", "Fill model", W_FULL, <FillModel rules={rules} />, false),
        fillPanel("shorts", "Mid vs print — weekly shorts", "shorts", "weekly call", fill,
                  pooledFill),
        fillPanel("longs", "Mid vs print — long-dated longs", "longs", "long-dated call", fill,
                  pooledFill),
        { ...panel("grid", "Parameter grid", W_FULL,
                   whenLoaded(robustness, (r) => (
                     <RobustnessTable label="Parameter grid" rows={r.grid} against="quant" />))),
          note: "one parameter at a time",
          caption: <>Quant at its defaults, then one parameter moved at a time. Every run is
            published and none is picked as best; the defaults were fixed before the first
            run.</> },
        { ...panel("friction", "Friction", W_HALF,
                   whenLoaded(robustness, (r) => (
                     <RobustnessTable label="Friction" rows={r.friction} against="its own at 0" />
                   ))),
          note: "each strategy against itself",
          caption: <>Each strategy at <code>spread_capture</code> 0, then each capture against
            it: Δ is the run&apos;s P&amp;L less the same strategy&apos;s at the mid.</> },
        { ...panel("entry", "Entry timing", W_HALF,
                   whenLoaded(robustness, (r) => <TimingPanel robustness={r} />)),
          note: "the baseline against itself",
          caption: <>The baseline with its entry trigger replaced by one fixed Monday bar, once per
            bar. The range and standard deviation are over the fixed bars alone. Timing is called
            fragile when any fixed bar&apos;s mean weekly return falls outside the
            baseline&apos;s 95% CI: then it moved the result more than the sample&apos;s own
            noise.</> },
        { ...panel("assumptions", "Stated assumptions", W_FULL,
                   whenLoaded(index, (i) => <Assumptions rate={i.risk_free_rate} />)),
          caption: <>The rate&apos;s full source is on its hover.</> },
      ]}
      manifests={pair ? pair.map((r) => r.manifest) : []}
    />
  );
}
