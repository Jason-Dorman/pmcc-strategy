// A panel (UI-SPEC §2): a header of [n] (amber mono), NAME (display caps) and a one-line note,
// then the body, then an HTML caption that wraps. Panels holding a figure or table are numbered
// at render time, in page order (PanelGrid); prose panels aren't.
import type { ReactNode } from "react";

import type { PanelWidth } from "../theme/tokens";

export interface PanelProps {
  name: string;
  width: PanelWidth;
  n?: number | undefined;
  note?: string | undefined;
  caption?: ReactNode;
  children: ReactNode;
}

export function Panel({ name, width, n, note, caption, children }: PanelProps) {
  return (
    <section className={`pm-panel pm-w${width}`} aria-label={name}>
      <div className="pm-panel-head">
        <div>
          {n !== undefined && <span className="pm-panel-n">[{n}]</span>}
          <span className="pm-panel-name">{name}</span>
        </div>
        {note && <div className="pm-panel-note">{note}</div>}
      </div>
      <div className="pm-panel-body">{children}</div>
      {caption && <div className="pm-caption">{caption}</div>}
    </section>
  );
}
