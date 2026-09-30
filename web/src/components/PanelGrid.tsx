// The 10-column panel grid (UI-SPEC §2). It numbers its figure and table panels [1], [2], … in
// page order as it renders them, so a page showing fewer sections (the baseline's strategy page)
// renumbers itself (DEC-54).
import type { ReactNode } from "react";

import type { PanelWidth } from "../theme/tokens";
import { Panel } from "./Panel";

export interface PanelSpec {
  key: string;
  name: string;
  width: PanelWidth;
  numbered: boolean; // a figure or a table; prose isn't numbered
  note?: string;
  caption?: ReactNode;
  body: ReactNode;
}

export function numbered(specs: readonly PanelSpec[]): (number | undefined)[] {
  let n = 0;
  return specs.map((spec) => (spec.numbered ? ++n : undefined));
}

export function PanelGrid({ panels }: { panels: readonly PanelSpec[] }) {
  const numbers = numbered(panels);
  return (
    <div className="pm-grid">
      {panels.map((spec, i) => (
        <Panel
          key={spec.key}
          name={spec.name}
          width={spec.width}
          n={numbers[i]}
          note={spec.note}
          caption={spec.caption}
        >
          {spec.body}
        </Panel>
      ))}
    </div>
  );
}
