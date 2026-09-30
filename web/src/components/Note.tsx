// Prose (UI-SPEC §2): `<b>` renders amber, as emphasis, which is chrome and never data. Long
// reference material folds into a disclosure so the prose leads.
import type { ReactNode } from "react";

export function Note({ children }: { children: ReactNode }) {
  return <div className="pm-note">{children}</div>;
}

export function Details({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <details className="pm-details">
      <summary>{summary}</summary>
      <div className="pm-note">{children}</div>
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
