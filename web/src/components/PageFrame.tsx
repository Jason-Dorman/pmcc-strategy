// A page's frame (UI-SPEC §6): readouts first, then the panels. No page has a footer: the run
// manifest stays in every results file (PO, DEC-121).
import { PanelGrid, type PanelSpec } from "./PanelGrid";
import { Readouts, type Readout } from "./Readouts";

export interface PageFrameProps {
  readouts?: readonly Readout[];
  panels: readonly PanelSpec[];
}

export function PageFrame({ readouts = [], panels }: PageFrameProps) {
  return (
    <main>
      {readouts.length > 0 && <Readouts items={readouts} />}
      <PanelGrid panels={panels} />
    </main>
  );
}

/** Readouts named by the page, with their values still to come (P7). */
export function pending(labels: readonly [string, string][]): Readout[] {
  return labels.map(([label, hint]) => ({ label, value: "—", hint }));
}
