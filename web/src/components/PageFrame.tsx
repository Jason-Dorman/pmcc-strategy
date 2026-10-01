// A page's frame (UI-SPEC §6): readouts first, then the panels, then the manifest footer.
import { useIndex } from "../data/IndexContext";
import type { Manifest } from "../types/generated/run_result";
import { ManifestFooter } from "./ManifestFooter";
import { PanelGrid, type PanelSpec } from "./PanelGrid";
import { Readouts, type Readout } from "./Readouts";

export interface PageFrameProps {
  readouts?: readonly Readout[];
  panels: readonly PanelSpec[];
  manifests?: readonly Manifest[];
}

export function PageFrame({ readouts = [], panels, manifests = [] }: PageFrameProps) {
  const index = useIndex();
  const exporter = index.kind === "ready" ? index.value.pmcc_version : undefined;
  return (
    <>
      <main>
        {readouts.length > 0 && <Readouts items={readouts} />}
        <PanelGrid panels={panels} />
      </main>
      {/* After main, not in it: a footer inside main isn't the page's contentinfo landmark */}
      <ManifestFooter manifests={manifests} exporter={exporter} />
    </>
  );
}

/** Readouts named by the page, with their values still to come (P7). */
export function pending(labels: readonly [string, string][]): Readout[] {
  return labels.map(([label, hint]) => ({ label, value: "—", hint }));
}
