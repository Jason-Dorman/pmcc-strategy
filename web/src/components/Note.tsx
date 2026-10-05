// Prose (UI-SPEC §2): `<b>` renders amber, as emphasis, which is chrome and never data. Long
// reference material folds into a disclosure so the prose leads.
import { useState, type ReactNode } from "react";

export function Note({ children }: { children: ReactNode }) {
  return <div className="pm-note">{children}</div>;
}

export function Details({ summary, children, table = false, lazy = false }: {
  summary: string;
  children: ReactNode;
  /** The disclosure holds a table (a chart's values), one column wide, not prose. */
  table?: boolean;
  /** Its body is built only once it is first opened: a table over every pair of the fill check
   * (100,000 rows) costs nothing until a reader asks for it. */
  lazy?: boolean;
}) {
  const [opened, setOpened] = useState(!lazy);
  return (
    <details className="pm-details"
             onToggle={(e) => opened || setOpened(e.currentTarget.open)}>
      <summary>{summary}</summary>
      <div className={table ? "pm-details-table" : "pm-details-body pm-note"}>
        {opened && children}
      </div>
    </details>
  );
}

/** An in-panel empty state: a missing run, an unknown symbol, a section not built yet. */
export function Empty({ children }: { children: ReactNode }) {
  return <div className="pm-empty">{children}</div>;
}

/** A panel body while its data loads: a flat block, no spinner (UI-SPEC §8). */
export function Loading() {
  return <div className="pm-loading" role="status" aria-label="Loading" />;
}
