// The strategy page (UI-SPEC §6.2): one component tree for both strategies. The optional sections
// come from the run's `report.sections` (DEC-54); the page never checks a strategy's name. The
// panels are built at P7-01.
import type { ReactNode } from "react";
import { useParams } from "react-router-dom";

import { STRATEGY_PAGES } from "../app/pages";
import { pending, PageFrame } from "../components/PageFrame";
import type { PanelSpec } from "../components/PanelGrid";
import { useRun } from "../data/useRun";
import type { RunResult, Section } from "../types/generated/run_result";
import { W_FULL, W_HALF } from "../theme/tokens";
import { panel, toCome, whenLoaded } from "./placeholder";

function panels(run: RunResult | undefined, body: (text: (r: RunResult) => string) => ReactNode):
    PanelSpec[] {
  const sections: readonly Section[] = run?.config.strategy.report.sections ?? [];
  const optional = (section: Section, spec: PanelSpec) => (sections.includes(section) ? [spec] : []);
  return [
    panel("account", "Account", W_FULL, body((r) => `${r.ledger?.length ?? 0} ledger bars`)),
    panel("regt", "Reg T", W_HALF, body(() => "Reg T panel")),
    panel("cycles", "Cycle statistics", W_HALF, body(() => "cycle statistics")),
    panel("legs", "Leg attribution", W_FULL, body(() => "leg attribution")),
    panel("blotter", "Blotter", W_FULL, body((r) => `${r.blotter?.length ?? 0} rows`)),
    ...optional("gate_log", panel("gates", "Gate log", W_FULL,
                                  body((r) => `${r.gate_log?.length ?? 0} weeks`))),
    panel("ledger", "Ledger", W_FULL, body((r) => `${r.ledger?.length ?? 0} bars`)),
    ...optional("greek_attribution", panel("greeks", "Greek attribution", W_FULL,
                                           body(() => "Greek attribution"))),
  ];
}

export function Strategy({ page }: { page: keyof typeof STRATEGY_PAGES }) {
  const { symbol = "" } = useParams();
  const state = useRun(symbol, STRATEGY_PAGES[page]);
  const run = state.kind === "ready" ? state.value : undefined;
  const body = (text: (r: RunResult) => string) =>
    whenLoaded(state, (r) => toCome("P7-01", text(r)));
  return (
    <PageFrame
      readouts={pending([
        ["Ending NAV", "Cash + long call − short call + stock"],
        ["P&L", "Ending NAV − starting cash"],
        ["Return on starting NAV", "P&L ÷ starting cash"],
        ["Return on capital deployed", "P&L ÷ peak long-leg cost"],
        ["Max drawdown", "Largest fall in NAV from a peak"],
        ["Min available funds", "NAV − initial margin, at its lowest"],
        ["Weeks traded / skipped", "Skips counted by rule"],
      ])}
      panels={panels(run, body)}
      manifests={run ? [run.manifest] : []}
    />
  );
}
